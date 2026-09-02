import {
  DestroyRef,
  Injectable,
  inject,
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
  AgentWorkflowEvent,
  ServerWebSocketEvent,
  WebSocketConnectionState,
} from '../../../core/models/websocket.model';
import {
  WebSocketService,
} from '../../../core/services/websocket.service';
import {
  AgentRoute,
  WorkspaceExecution,
  WorkspaceMessage,
  WorkspaceMode,
  WorkspaceSource,
  WorkspaceState,
  WorkspaceWorkflowEvent,
} from '../models/workspace.model';

interface PendingRequest {
  requestId: string;
  query: string;
  mode: WorkspaceMode;
}

@Injectable({
  providedIn: 'root',
})
export class WorkspaceStateService {
  private readonly websocket =
    inject(WebSocketService);

  private readonly destroyRef =
    inject(DestroyRef);

  private readonly stateSubject =
    new BehaviorSubject<WorkspaceState>(
      this.createInitialState(),
    );

  private requestCounter = 0;
  private messageCounter = 0;
  private conversationCounter = 0;

  private pendingRequest:
    PendingRequest | null = null;

  private activeAssistantMessageId:
    string | null = null;

  readonly state$ =
    this.stateSubject.asObservable();

  readonly connectionState$ =
    this.state$.pipe(
      map((state) => state.connectionState),
      distinctUntilChanged(),
    );

  readonly isRunning$ =
    this.state$.pipe(
      map((state) => state.isRunning),
      distinctUntilChanged(),
    );

  constructor() {
    this.websocket.connectionState$
      .pipe(
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((state) => {
        this.handleConnectionState(state);
      });

    this.websocket.events$
      .pipe(
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((event) => {
        this.handleServerEvent(event);
      });
  }

  setMode(mode: WorkspaceMode): void {
    if (
      mode === this.stateSubject.value.mode ||
      this.stateSubject.value.isRunning
    ) {
      return;
    }

    this.patchState({
      mode,
      error: null,
      execution: null,
    });
  }

  submit(rawQuery: string): void {
    const query = rawQuery.trim();

    if (
      query.length === 0 ||
      this.stateSubject.value.isRunning
    ) {
      return;
    }

    if (query.length > 20_000) {
      this.patchState({
        error:
          'Query cannot exceed 20,000 characters.',
      });

      return;
    }

    const mode = this.stateSubject.value.mode;
    const requestId = this.createRequestId();

    const userMessage =
      this.createMessage(
        'user',
        query,
      );

    const execution =
      mode === 'agent'
        ? this.createExecution(requestId)
        : null;

    this.pendingRequest = {
      requestId,
      query,
      mode,
    };

    this.activeAssistantMessageId = null;

    this.patchState({
      messages: [
        ...this.stateSubject.value.messages,
        userMessage,
      ],
      isRunning: true,
      error: null,
      activeRequestId: requestId,
      lastModel:
        mode === 'direct'
          ? null
          : this.stateSubject.value.lastModel,
      execution,
    });

    if (
      this.stateSubject.value.connectionState ===
      'connected'
    ) {
      this.sendPendingRequest();
      return;
    }

    this.websocket.connect();
  }

  cancel(): void {
    const state = this.stateSubject.value;

    if (
      !state.isRunning ||
      state.activeRequestId === null
    ) {
      return;
    }

    if (this.pendingRequest !== null) {
      this.pendingRequest = null;

      this.finishCancelledRequest();
      return;
    }

    if (
      state.connectionState !== 'connected'
    ) {
      return;
    }

    this.websocket.cancel(
      state.activeRequestId,
    );
  }

  resetConversation(): void {
    const state = this.stateSubject.value;

    if (
      state.isRunning &&
      state.activeRequestId !== null &&
      this.pendingRequest === null &&
      state.connectionState === 'connected'
    ) {
      try {
        this.websocket.cancel(
          state.activeRequestId,
        );
      } catch {
        // Reset remains deterministic even if the
        // WebSocket closes before cancellation.
      }
    }

    const mode = state.mode;
    const connectionState =
      state.connectionState;

    this.pendingRequest = null;
    this.activeAssistantMessageId = null;

    this.stateSubject.next({
      ...this.createInitialState(mode),
      connectionState,
    });
  }

  clearError(): void {
    this.patchState({
      error: null,
    });
  }

  private handleConnectionState(
    connectionState: WebSocketConnectionState,
  ): void {
    const previous =
      this.stateSubject.value.connectionState;

    this.patchState({
      connectionState,
    });

    if (connectionState === 'connected') {
      this.sendPendingRequest();
      return;
    }

    if (
      connectionState === 'disconnected' &&
      previous === 'connected' &&
      this.stateSubject.value.isRunning &&
      this.pendingRequest === null
    ) {
      this.removeEmptyAssistantMessage();

      this.patchExecution({
        status: 'failed',
      });

      this.clearActiveRequest();

      this.patchState({
        isRunning: false,
        error:
          'The real-time connection was interrupted. Orbyntiq is reconnecting.',
      });
    }
  }

  private sendPendingRequest(): void {
    const pending = this.pendingRequest;

    if (
      pending === null ||
      this.stateSubject.value.connectionState !==
        'connected'
    ) {
      return;
    }

    this.pendingRequest = null;

    try {
      if (pending.mode === 'agent') {
        this.websocket.sendAgentExecution(
          pending.requestId,
          pending.query,
          this.stateSubject.value.conversationId,
          4,
        );

        return;
      }

      this.websocket.sendChat(
        pending.requestId,
        pending.query,
      );
    } catch {
      this.patchExecution({
        status: 'failed',
      });

      this.clearActiveRequest();

      this.patchState({
        isRunning: false,
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
        this.stateSubject.value.activeRequestId
    ) {
      return;
    }

    switch (event.type) {
      case 'started':
        this.handleDirectStarted(
          event.model,
        );
        break;

      case 'chunk':
        this.handleDirectChunk(
          event.content,
        );
        break;

      case 'completed':
        this.handleDirectCompleted(
          event.model,
        );
        break;

      case 'agent_event':
        this.handleAgentEvent(event);
        break;

      case 'cancelled':
        this.finishCancelledRequest();
        break;

      case 'error':
        this.removeEmptyAssistantMessage();

        this.patchExecution({
          status: 'failed',
        });

        this.clearActiveRequest();

        this.patchState({
          isRunning: false,
          error: event.message,
        });

        break;
    }
  }

  private handleDirectStarted(
    model: string,
  ): void {
    if (
      this.stateSubject.value.mode !==
        'direct'
    ) {
      return;
    }

    this.ensureAssistantMessage(model);

    this.patchState({
      lastModel: model,
    });
  }

  private handleDirectChunk(
    content: string,
  ): void {
    if (
      this.stateSubject.value.mode !==
        'direct' ||
      content.length === 0
    ) {
      return;
    }

    const messageId =
      this.ensureAssistantMessage();

    this.patchState({
      messages:
        this.stateSubject.value.messages.map(
          (message) =>
            message.id === messageId
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

  private handleDirectCompleted(
    model: string,
  ): void {
    if (
      this.stateSubject.value.mode !==
        'direct'
    ) {
      return;
    }

    const messageId =
      this.activeAssistantMessageId;

    const messages =
      messageId === null
        ? this.stateSubject.value.messages
        : this.stateSubject.value.messages.map(
            (message) =>
              message.id === messageId
                ? {
                    ...message,
                    model,
                  }
                : message,
          );

    this.clearActiveRequest();

    this.patchState({
      messages,
      isRunning: false,
      error: null,
      lastModel: model,
    });
  }

  private handleAgentEvent(
    event: AgentWorkflowEvent,
  ): void {
    if (
      this.stateSubject.value.mode !==
        'agent'
    ) {
      return;
    }

    const workflowEvent:
      WorkspaceWorkflowEvent = {
        sequence: event.sequence,
        eventType: event.event_type,
        agentName: event.agent_name,
        payload: event.payload,
      };

    const currentExecution =
      this.stateSubject.value.execution;

    if (currentExecution === null) {
      return;
    }

    const execution: WorkspaceExecution = {
      ...currentExecution,
      executionId:
        event.execution_id ||
        currentExecution.executionId,
      events: [
        ...currentExecution.events,
        workflowEvent,
      ],
    };

    switch (event.event_type) {
      case 'execution_started':
        execution.status = 'running';
        break;

      case 'routing_completed':
        execution.route =
          this.readRoute(
            event.payload['route'],
          );

        execution.routeReason =
          this.readString(
            event.payload['route_reason'],
          );

        break;

      case 'agent_result':
        this.mergeAgentResult(
          execution,
          event.payload,
        );
        break;

      case 'execution_completed':
        this.completeAgentExecution(
          execution,
          event.payload,
        );

        return;

      case 'execution_failed':
        execution.status = 'failed';

        {
          const error =
            this.readString(
              event.payload['error'],
            );

          if (error !== null) {
            execution.errors = [
              ...execution.errors,
              error,
            ];
          }
        }

        this.clearActiveRequest();

        this.patchState({
          execution,
          isRunning: false,
          error:
            execution.errors.at(-1) ??
            'Multi-agent execution failed.',
        });

        return;
    }

    this.patchState({
      execution,
    });
  }

  private mergeAgentResult(
    execution: WorkspaceExecution,
    payload: Readonly<Record<string, unknown>>,
  ): void {
    const error =
      this.readString(
        payload['error'],
      );

    if (
      error !== null &&
      !execution.errors.includes(error)
    ) {
      execution.errors = [
        ...execution.errors,
        error,
      ];
    }

    const sources =
      this.readSources(
        payload['sources'],
      );

    if (sources.length > 0) {
      execution.sources = [
        ...execution.sources,
        ...sources,
      ];
    }
  }

  private completeAgentExecution(
    execution: WorkspaceExecution,
    payload: Readonly<Record<string, unknown>>,
  ): void {
    execution.status = 'completed';

    execution.route =
      this.readRoute(
        payload['route'],
      ) ?? execution.route;

    execution.hopCount =
      this.readNumber(
        payload['hop_count'],
      );

    execution.sources =
      this.readSources(
        payload['sources'],
      );

    execution.errors =
      this.readStrings(
        payload['errors'],
      );

    const finalResponse =
      this.readString(
        payload['final_response'],
      ) ?? '';

    if (finalResponse.length > 0) {
      const assistant =
        this.createMessage(
          'assistant',
          finalResponse,
          undefined,
          execution.sources,
        );

      this.patchState({
        messages: [
          ...this.stateSubject.value.messages,
          assistant,
        ],
      });
    }

    this.clearActiveRequest();

    this.patchState({
      execution,
      isRunning: false,
      error:
        execution.errors.length > 0
          ? execution.errors.join(' ')
          : null,
    });
  }

  private finishCancelledRequest(): void {
    this.removeEmptyAssistantMessage();

    this.patchExecution({
      status: 'cancelled',
    });

    this.clearActiveRequest();

    this.patchState({
      isRunning: false,
    });
  }

  private ensureAssistantMessage(
    model?: string,
  ): string {
    if (
      this.activeAssistantMessageId !== null
    ) {
      return this.activeAssistantMessageId;
    }

    const assistant =
      this.createMessage(
        'assistant',
        '',
        model,
      );

    this.activeAssistantMessageId =
      assistant.id;

    this.patchState({
      messages: [
        ...this.stateSubject.value.messages,
        assistant,
      ],
    });

    return assistant.id;
  }

  private removeEmptyAssistantMessage(): void {
    const id =
      this.activeAssistantMessageId;

    if (id === null) {
      return;
    }

    const message =
      this.stateSubject.value.messages.find(
        (item) => item.id === id,
      );

    if (
      message === undefined ||
      message.content.length > 0
    ) {
      return;
    }

    this.patchState({
      messages:
        this.stateSubject.value.messages.filter(
          (item) => item.id !== id,
        ),
    });
  }

  private patchExecution(
    changes: Partial<WorkspaceExecution>,
  ): void {
    const execution =
      this.stateSubject.value.execution;

    if (execution === null) {
      return;
    }

    this.patchState({
      execution: {
        ...execution,
        ...changes,
      },
    });
  }

  private clearActiveRequest(): void {
    this.pendingRequest = null;
    this.activeAssistantMessageId = null;

    this.patchState({
      activeRequestId: null,
    });
  }

  private createExecution(
    requestId: string,
  ): WorkspaceExecution {
    return {
      requestId,
      executionId: null,
      status: 'running',
      route: null,
      routeReason: null,
      hopCount: null,
      events: [],
      sources: [],
      errors: [],
    };
  }

  private createInitialState(
    mode: WorkspaceMode = 'agent',
  ): WorkspaceState {
    return {
      mode,
      messages: [],
      connectionState: 'disconnected',
      isRunning: false,
      error: null,
      activeRequestId: null,
      conversationId:
        this.createConversationId(),
      lastModel: null,
      execution: null,
    };
  }

  private createRequestId(): string {
    this.requestCounter += 1;

    return (
      `workspace-${Date.now()}-` +
      `${this.requestCounter}`
    );
  }

  private createConversationId(): string {
    this.conversationCounter += 1;

    return (
      `conversation-${Date.now()}-` +
      `${this.conversationCounter}`
    );
  }

  private createMessage(
    role: WorkspaceMessage['role'],
    content: string,
    model?: string,
    sources?: readonly WorkspaceSource[],
  ): WorkspaceMessage {
    this.messageCounter += 1;

    return {
      id:
        `workspace-message-` +
        `${this.messageCounter}`,
      role,
      content,
      createdAt:
        new Date().toISOString(),
      ...(model
        ? { model }
        : {}),
      ...(sources &&
      sources.length > 0
        ? { sources }
        : {}),
    };
  }

  private readString(
    value: unknown,
  ): string | null {
    return typeof value === 'string'
      ? value
      : null;
  }

  private readNumber(
    value: unknown,
  ): number | null {
    return typeof value === 'number'
      ? value
      : null;
  }

  private readRoute(
    value: unknown,
  ): AgentRoute | null {
    return value === 'research' ||
      value === 'mcp' ||
      value === 'general'
      ? value
      : null;
  }

  private readStrings(
    value: unknown,
  ): readonly string[] {
    if (!Array.isArray(value)) {
      return [];
    }

    return value.filter(
      (item): item is string =>
        typeof item === 'string',
    );
  }

  private readSources(
    value: unknown,
  ): readonly WorkspaceSource[] {
    if (!Array.isArray(value)) {
      return [];
    }

    return value.filter(
      (
        item,
      ): item is WorkspaceSource =>
        typeof item === 'object' &&
        item !== null &&
        !Array.isArray(item),
    );
  }

  private patchState(
    changes: Partial<WorkspaceState>,
  ): void {
    this.stateSubject.next({
      ...this.stateSubject.value,
      ...changes,
    });
  }
}
