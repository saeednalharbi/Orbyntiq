import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { API_CONFIG } from '../config/api.config';
import { ChatResponse } from '../models/llm.model';
import { LlmService } from './llm.service';

describe('LlmService', () => {
  let service: LlmService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        LlmService,
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(LlmService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should POST the prompt to the LLM chat endpoint', () => {
    const mockResponse: ChatResponse = {
      content: 'Hello from Orbyntiq',
      model: 'test-model',
      usage: {
        prompt_tokens: 5,
        completion_tokens: 4,
      },
    };

    service.chat('Hello').subscribe((response) => {
      expect(response).toEqual(mockResponse);
    });

    const request = httpTesting.expectOne(API_CONFIG.llm.chat);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      prompt: 'Hello',
    });

    request.flush(mockResponse);
  });

  it('should preserve nullable token usage values', () => {
    const mockResponse: ChatResponse = {
      content: 'Response',
      model: 'test-model',
      usage: {
        prompt_tokens: null,
        completion_tokens: null,
      },
    };

    service.chat('Test').subscribe((response) => {
      expect(response.usage.prompt_tokens).toBeNull();
      expect(response.usage.completion_tokens).toBeNull();
    });

    const request = httpTesting.expectOne(API_CONFIG.llm.chat);

    request.flush(mockResponse);
  });
});
