import { environment } from '../../../environments/environment';

const websocketBaseUrl = environment.apiBaseUrl
  .replace(/^https:\/\//, 'wss://')
  .replace(/^http:\/\//, 'ws://');

export const API_CONFIG = {
  baseUrl: environment.apiBaseUrl,
  llm: {
    chat: `${environment.apiBaseUrl}/llm/chat`,
  },
  websocket: {
    chat: `${websocketBaseUrl}/ws/chat`,
  },
} as const;
