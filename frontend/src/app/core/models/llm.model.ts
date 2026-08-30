export interface ChatRequest {
  prompt: string;
}

export interface TokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
}

export interface ChatResponse {
  content: string;
  model: string;
  usage: TokenUsage;
}
