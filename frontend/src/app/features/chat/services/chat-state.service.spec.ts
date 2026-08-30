import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Observable, of, throwError } from 'rxjs';

import { ChatResponse } from '../../../core/models/llm.model';
import { LlmService } from '../../../core/services/llm.service';
import { ChatState } from '../chat.model';
import { ChatStateService } from './chat-state.service';

const MOCK_RESPONSE: ChatResponse = {
  content: 'Hello from Orbyntiq',
  model: 'test-model',
  usage: {
    prompt_tokens: 5,
    completion_tokens: 4,
  },
};

class FakeLlmService {
  response$: Observable<ChatResponse> = of(MOCK_RESPONSE);

  chat(_prompt: string): Observable<ChatResponse> {
    return this.response$;
  }
}

describe('ChatStateService', () => {
  let service: ChatStateService;
  let llmService: FakeLlmService;
  let latestState: ChatState;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ChatStateService,
        {
          provide: LlmService,
          useClass: FakeLlmService,
        },
      ],
    });

    service = TestBed.inject(ChatStateService);
    llmService = TestBed.inject(
      LlmService,
    ) as unknown as FakeLlmService;

    service.state$.subscribe((state) => {
      latestState = state;
    });
  });

  it('should add user and assistant messages', () => {
    service.sendMessage('Hello');

    expect(latestState.messages).toHaveLength(2);
    expect(latestState.messages[0].role).toBe('user');
    expect(latestState.messages[0].content).toBe('Hello');
    expect(latestState.messages[1].role).toBe('assistant');
    expect(latestState.messages[1].content).toBe(
      'Hello from Orbyntiq',
    );
    expect(latestState.lastModel).toBe('test-model');
    expect(latestState.lastUsage).toEqual(
      MOCK_RESPONSE.usage,
    );
    expect(latestState.isLoading).toBe(false);
  });

  it('should reject prompts longer than the backend limit', () => {
    service.sendMessage('a'.repeat(20_001));

    expect(latestState.messages).toHaveLength(0);
    expect(latestState.error).toBe(
      'Prompt cannot exceed 20,000 characters.',
    );
  });

  it('should expose backend error details', () => {
    llmService.response$ = throwError(
      () =>
        new HttpErrorResponse({
          status: 503,
          error: {
            detail:
              'The configured local LLM model is unavailable.',
          },
        }),
    );

    service.sendMessage('Hello');

    expect(latestState.messages).toHaveLength(1);
    expect(latestState.error).toBe(
      'The configured local LLM model is unavailable.',
    );
    expect(latestState.isLoading).toBe(false);
  });

  it('should reset the conversation', () => {
    service.sendMessage('Hello');
    service.resetConversation();

    expect(latestState.messages).toHaveLength(0);
    expect(latestState.error).toBeNull();
    expect(latestState.lastModel).toBeNull();
    expect(latestState.lastUsage).toBeNull();
  });
});
