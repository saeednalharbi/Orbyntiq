import { TokenUsage } from '../../core/models/llm.model';

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  model?: string;
  usage?: TokenUsage;
}

export interface ChatState {
  messages: readonly ChatMessage[];
  isLoading: boolean;
  error: string | null;
  lastModel: string | null;
  lastUsage: TokenUsage | null;
}
