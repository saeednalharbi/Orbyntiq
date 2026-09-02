import { environment } from '../../../environments/environment';

const websocketBaseUrl = environment.apiBaseUrl
  .replace(/^https:\/\//, 'wss://')
  .replace(/^http:\/\//, 'ws://');

export const API_CONFIG = {
  baseUrl: environment.apiBaseUrl,
  llm: {
    chat: `${environment.apiBaseUrl}/llm/chat`,
  },
  knowledge: {
    status: `${environment.apiBaseUrl}/knowledge/status`,
    documents: `${environment.apiBaseUrl}/knowledge/documents`,
    search: `${environment.apiBaseUrl}/knowledge/search`,
    ingest: `${environment.apiBaseUrl}/knowledge/ingest`,
  },
  websocket: {
    chat: `${websocketBaseUrl}/ws/chat`,
  },
} as const;
