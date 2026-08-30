import { environment } from '../../../environments/environment';

export const API_CONFIG = {
  baseUrl: environment.apiBaseUrl,
  llm: {
    chat: `${environment.apiBaseUrl}/llm/chat`,
  },
} as const;
