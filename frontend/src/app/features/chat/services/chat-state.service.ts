import { HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  BehaviorSubject,
  EMPTY,
  catchError,
  distinctUntilChanged,
  finalize,
  map,
  tap,
} from 'rxjs';

import { LlmService } from '../../../core/services/llm.service';
import { ChatMessage, ChatState } from '../chat.model';

const INITIAL_CHAT_STATE: ChatState = {
  messages: [],
  isLoading: false,
  error: null,
  lastModel: null,
  lastUsage: null,
};

@Injectable({
  providedIn: 'root',
})
export class ChatStateService {
  private readonly llmService = inject(LlmService);
  private readonly stateSubject =
    new BehaviorSubject<ChatState>(INITIAL_CHAT_STATE);

  private messageCounter = 0;

  readonly state$ = this.stateSubject.asObservable();

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

  sendMessage(rawPrompt: string): void {
    const prompt = rawPrompt.trim();

    if (!prompt || this.stateSubject.value.isLoading) {
      return;
    }

    if (prompt.length > 20_000) {
      this.patchState({
        error: 'Prompt cannot exceed 20,000 characters.',
      });
      return;
    }

    const userMessage = this.createMessage('user', prompt);

    this.patchState({
      messages: [
        ...this.stateSubject.value.messages,
        userMessage,
      ],
      isLoading: true,
      error: null,
    });

    this.llmService
      .chat(prompt)
      .pipe(
        tap((response) => {
          const assistantMessage = this.createMessage(
            'assistant',
            response.content,
            response.model,
            response.usage,
          );

          this.patchState({
            messages: [
              ...this.stateSubject.value.messages,
              assistantMessage,
            ],
            lastModel: response.model,
            lastUsage: response.usage,
          });
        }),
        catchError((error: unknown) => {
          this.patchState({
            error: this.getErrorMessage(error),
          });

          return EMPTY;
        }),
        finalize(() => {
          this.patchState({
            isLoading: false,
          });
        }),
      )
      .subscribe();
  }

  clearError(): void {
    this.patchState({
      error: null,
    });
  }

  resetConversation(): void {
    this.stateSubject.next(INITIAL_CHAT_STATE);
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

  private getErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;

      if (
        typeof detail === 'string' &&
        detail.trim().length > 0
      ) {
        return detail;
      }

      if (error.status === 0) {
        return 'Unable to reach the Orbyntiq API.';
      }
    }

    return 'Something went wrong while contacting the AI service.';
  }
}
