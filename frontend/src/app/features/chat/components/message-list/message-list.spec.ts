import { TestBed } from '@angular/core/testing';

import { ChatMessage } from '../../chat.model';
import { MessageList } from './message-list';

describe('MessageList', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MessageList],
    }).compileComponents();
  });

  it('should render the empty conversation state', () => {
    const fixture = TestBed.createComponent(MessageList);

    fixture.componentRef.setInput('messages', []);
    fixture.detectChanges();

    const element =
      fixture.nativeElement as HTMLElement;

    expect(element.textContent).toContain(
      'How can Orbyntiq help?',
    );
  });

  it('should render user and assistant messages', () => {
    const fixture = TestBed.createComponent(MessageList);

    const messages: ChatMessage[] = [
      {
        id: 'message-1',
        role: 'user',
        content: 'Hello',
        createdAt: '2026-08-30T00:00:00.000Z',
      },
      {
        id: 'message-2',
        role: 'assistant',
        content: 'Hello from Orbyntiq',
        createdAt: '2026-08-30T00:00:01.000Z',
        model: 'test-model',
        usage: {
          prompt_tokens: 2,
          completion_tokens: 4,
        },
      },
    ];

    fixture.componentRef.setInput(
      'messages',
      messages,
    );

    fixture.detectChanges();

    const element =
      fixture.nativeElement as HTMLElement;

    expect(
      element.querySelectorAll('.message'),
    ).toHaveLength(2);

    expect(element.textContent).toContain('Hello');
    expect(element.textContent).toContain(
      'Hello from Orbyntiq',
    );
    expect(element.textContent).toContain('test-model');
  });
});
