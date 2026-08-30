import { Component, Input } from '@angular/core';

import { ChatMessage } from '../../chat.model';

@Component({
  selector: 'app-message-list',
  templateUrl: './message-list.html',
  styleUrl: './message-list.scss',
})
export class MessageList {
  @Input({ required: true })
  messages: readonly ChatMessage[] = [];

  @Input()
  isLoading = false;
}
