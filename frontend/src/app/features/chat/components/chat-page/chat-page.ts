import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';

import { ActivityPanel } from '../activity-panel/activity-panel';
import { MessageList } from '../message-list/message-list';
import { PromptInput } from '../prompt-input/prompt-input';
import { ChatStateService } from '../../services/chat-state.service';

@Component({
  selector: 'app-chat-page',
  imports: [
    AsyncPipe,
    ActivityPanel,
    MessageList,
    PromptInput,
  ],
  templateUrl: './chat-page.html',
  styleUrl: './chat-page.scss',
})
export class ChatPage {
  private readonly chatState = inject(ChatStateService);

  readonly state$ = this.chatState.state$;

  sendPrompt(prompt: string): void {
    this.chatState.sendMessage(prompt);
  }

  resetConversation(): void {
    this.chatState.resetConversation();
  }

  clearError(): void {
    this.chatState.clearError();
  }
}
