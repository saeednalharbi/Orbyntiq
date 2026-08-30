import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_CONFIG } from '../config/api.config';
import { ChatRequest, ChatResponse } from '../models/llm.model';

@Injectable({
  providedIn: 'root',
})
export class LlmService {
  private readonly http = inject(HttpClient);

  chat(prompt: string): Observable<ChatResponse> {
    const request: ChatRequest = {
      prompt,
    };

    return this.http.post<ChatResponse>(
      API_CONFIG.llm.chat,
      request,
    );
  }
}
