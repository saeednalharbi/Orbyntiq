import {
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-prompt-input',
  imports: [FormsModule],
  templateUrl: './prompt-input.html',
  styleUrl: './prompt-input.scss',
})
export class PromptInput {
  @Input()
  disabled = false;

  @Output()
  readonly promptSubmit = new EventEmitter<string>();

  @Output()
  readonly conversationReset = new EventEmitter<void>();

  prompt = '';

  submitPrompt(): void {
    const prompt = this.prompt.trim();

    if (!prompt || this.disabled) {
      return;
    }

    this.promptSubmit.emit(prompt);
    this.prompt = '';
  }

  handleKeydown(event: KeyboardEvent): void {
    if (
      event.key === 'Enter' &&
      !event.shiftKey
    ) {
      event.preventDefault();
      this.submitPrompt();
    }
  }
}
