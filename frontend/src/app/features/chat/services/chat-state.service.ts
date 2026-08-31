import {
  DestroyRef,
  inject,
  Injectable,
} from '@angular/core';
import {
  takeUntilDestroyed,
} from '@angular/core/rxjs-interop';
import {
  BehaviorSubject,
  distinctUntilChanged,
  map,
} from 'rxjs';

import {
  ServerWebSocketEvent,
  WebSocketConnectionState,
} from '../../../core/models/websocket.model';
import { WebSocketService } from '../../../core/services/websocket.service';
import {
  ChatMessage,
  ChatState,
} from '../chat.model';

const INITIAL_CHAT_STATE: ChatState = {
  messages: [],
  isLoading: false,
  error: null,
  lastModel: null,
  lastUsage: null,
};

interface PendingChatRequest {
  requestId: string;
  prompt: string;
}

@Injectable({
  providedIn: 'root',
})
export class ChatStateService {
  private readonly websocketService =
    inject(WebSocketService);

  private readonly destroyRef =
    inject(DestroyRef);

  private readonly stateSubject =
    new BehaviorSubject<ChatState>(
      INITIAL_CHAT_STATE,
    );

  private messageCounter = 0;
  private requestCounter = 0;

  private connectionState:
    WebSocketConnectionState =
      'disconnected';

  private pendingRequest:
    PendingChatRequest | null = null;

  private activeRequestId:
    string | null = null;

  private activeAssistantMessageId:
    string | null = null;

  readonly state$ =
    this.stateSubject.asObservable();

  readonly messages$ = this.state$.pipe(
    map((state) => state.messages),
    distinctUntilChanged(),
  );

  readonly isLoading$ = this.state$.pipe(
    map((state) => state.isLoading),
    distinctUntilChanged(),
  );

  readonly error$ = this.state$.pipe(
    map((state) => state.error),
    distinctUntilChanged(),
  );

  constructor() {
    this.websocketService.connectionState$
      .pipe(
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((state) => {
        this.handleConnectionState(state);
      });

    this.websocketService.events$
      .pipe(
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((event) => {
        this.handleServerEvent(event);
      });
  }

  sendMessage(rawPrompt: string): void {
    const prompt = rawPrompt.trim();

    if (
      !prompt ||
      this.stateSubject.value.isLoading
    ) {
      return;
    }

    if (prompt.length > 20_000) {
      this.patchState({
        error:
          'Prompt cannot exceed 20,000 characters.',
      });

      return;
    }

    const userMessage = this.createMessage(
      'user',
      prompt,
    );

    const requestId = this.createRequestId();

    this.activeRequestId = requestId;
    this.activeAssistantMessageId = null;

    this.pendingRequest = {
      requestId,
      prompt,
    };

    this.patchState({
      messages: [
        ...this.stateSubject.value.messages,
        userMessage,
      ],
      isLoading: true,
      error: null,
      lastUsage: null,
    });

    if (
      this.connectionState === 'connected'
    ) {
      this.sendPendingRequest();
      return;
    }

    this.websocketService.connect();
  }

  cancelResponse(): void {
    if (
      this.activeRequestId === null ||
      !this.stateSubject.value.isLoading
    ) {
      return;
    }

    if (this.pendingRequest !== null) {
      this.pendingRequest = null;

      this.removeEmptyAssistantMessage();
      this.clearActiveRequest();

      this.patchState({
        isLoading: false,
      });

      return;
    }

    if (
      this.connectionState !== 'connected'
    ) {
      return;
    }

    this.websocketService.cancel(
      this.activeRequestId,
    );
  }

  clearError(): void {
    this.patchState({
      error: null,
    });
  }

  resetConversation(): void {
    const requestId = this.activeRequestId;

    const requestWasSent =
      this.pendingRequest === null;

    this.pendingRequest = null;
    this.clearActiveRequest();

    if (
      requestId !== null &&
      requestWasSent &&
      this.connectionState === 'connected'
    ) {
      try {
        this.websocketService.cancel(
          requestId,
        );
      } catch {
        // Reset still succeeds if the socket
        // closes before cancellation is sent.
      }
    }

    this.stateSubject.next(
      INITIAL_CHAT_STATE,
    );
  }

  private handleConnectionState(
    state: WebSocketConnectionState,
  ): void {
    this.connectionState = state;

    if (state === 'connected') {
      this.sendPendingRequest();
      return;
    }

    if (
      state === 'disconnected' &&
      this.activeRequestId !== null &&
      this.pendingRequest === null &&
      this.stateSubject.value.isLoading
    ) {
      this.removeEmptyAssistantMessage();

      this.clearActiveRequest();

      this.patchState({
        isLoading: false,
        error:
          'The real-time connection was interrupted. Orbyntiq is reconnecting.',
      });
    }
  }

  private sendPendingRequest(): void {
    const request = this.pendingRequest;

    if (
      request === null ||
      this.connectionState !== 'connected'
    ) {
      return;
    }

    this.pendingRequest = null;

    try {
      this.websocketService.sendChat(
        request.requestId,
        request.prompt,
      );
    } catch {
      this.clearActiveRequest();

      this.patchState({
        isLoading: false,
        error:
          'Unable to send the request through the real-time connection.',
      });
    }
  }

  private handleServerEvent(
    event: ServerWebSocketEvent,
  ): void {
    if (event.type === 'pong') {
      return;
    }

    if (
      'request_id' in event &&
      event.request_id !==
        this.activeRequestId
    ) {
      return;
    }

    switch (event.type) {
      case 'started':
        this.handleStartedEvent(
          event.model,
        );
        break;

      case 'chunk':
        this.handleChunkEvent(
          event.content,
        );
        break;

      case 'completed':
        this.handleCompletedEvent(
          event.model,
        );
        break;

      case 'cancelled':
        this.removeEmptyAssistantMessage();
        this.clearActiveRequest();

        this.patchState({
          isLoading: false,
        });

        break;

      case 'error':
        this.removeEmptyAssistantMessage();
        this.clearActiveRequest();

        this.patchState({
          isLoading: false,
          error: event.message,
        });

        break;
    }
  }

  private handleStartedEvent(
    model: string,
  ): void {
    if (this.activeRequestId === null) {
      return;
    }

    if (
      this.activeAssistantMessageId === null
    ) {
      const assistantMessage =
        this.createMessage(
          'assistant',
          '',
          model,
        );

      this.activeAssistantMessageId =
        assistantMessage.id;

      this.patchState({
        messages: [
          ...this.stateSubject.value.messages,
          assistantMessage,
        ],
        lastModel: model,
        lastUsage: null,
      });
    }
  }

  private handleChunkEvent(
    content: string,
  ): void {
    if (
      this.activeRequestId === null ||
      content.length === 0
    ) {
      return;
    }

    if (
      this.activeAssistantMessageId === null
    ) {
      const assistantMessage =
        this.createMessage(
          'assistant',
          '',
        );

      this.activeAssistantMessageId =
        assistantMessage.id;

      this.patchState({
        messages: [
          ...this.stateSubject.value.messages,
          assistantMessage,
        ],
      });
    }

    const assistantMessageId =
      this.activeAssistantMessageId;

    this.patchState({
      messages:
        this.stateSubject.value.messages.map(
          (message) =>
            message.id ===
            assistantMessageId
              ? {
                  ...message,
                  content:
                    message.content +
                    content,
                }
              : message,
        ),
    });
  }

  private handleCompletedEvent(
    model: string,
  ): void {
    const assistantMessageId =
      this.activeAssistantMessageId;

    const messages =
      assistantMessageId === null
        ? this.stateSubject.value.messages
        : this.stateSubject.value.messages.map(
            (message) =>
              message.id ===
              assistantMessageId
                ? {
                    ...message,
                    model,
                  }
                : message,
          );

    this.clearActiveRequest();

    this.patchState({
      messages,
      isLoading: false,
      error: null,
      lastModel: model,
      lastUsage: null,
    });
  }

  private removeEmptyAssistantMessage(): void {
    const assistantMessageId =
      this.activeAssistantMessageId;

    if (assistantMessageId === null) {
      return;
    }

    const assistantMessage =
      this.stateSubject.value.messages.find(
        (message) =>
          message.id ===
          assistantMessageId,
      );

    if (
      assistantMessage === undefined ||
      assistantMessage.content.length > 0
    ) {
      return;
    }

    this.patchState({
      messages:
        this.stateSubject.value.messages.filter(
          (message) =>
            message.id !==
            assistantMessageId,
        ),
    });
  }

  private clearActiveRequest(): void {
    this.pendingRequest = null;
    this.activeRequestId = null;
    this.activeAssistantMessageId = null;
  }

  private createRequestId(): string {
    this.requestCounter += 1;

    return `request-${this.requestCounter}`;
  }

  private createMessage(
    role: ChatMessage['role'],
    content: string,
    model?: string,
    usage?: ChatMessage['usage'],
  ): ChatMessage {
    this.messageCounter += 1;

    return {
      id: `message-${this.messageCounter}`,
      role,
      content,
      createdAt: new Date().toISOString(),
      ...(model ? { model } : {}),
      ...(usage ? { usage } : {}),
    };
  }

  private patchState(
    changes: Partial<ChatState>,
  ): void {
    this.stateSubject.next({
      ...this.stateSubject.value,
      ...changes,
    });
  }
}
