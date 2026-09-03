export type PlatformState =
  | 'healthy'
  | 'degraded';

export type PlatformComponentState =
  | 'healthy'
  | 'degraded'
  | 'unavailable'
  | 'configured'
  | 'disabled';

export interface PlatformComponentStatus {
  status: PlatformComponentState;
  detail: string | null;
}

export interface LlmComponentStatus
  extends PlatformComponentStatus {
  provider: string;
  model: string;
}

export interface McpComponentStatus
  extends PlatformComponentStatus {
  retriever_configured: boolean;
  rag_configured: boolean;
}

export interface ObservabilityComponentStatus
  extends PlatformComponentStatus {
  metrics_enabled: boolean;
  tracing_enabled: boolean;
}

export interface PlatformComponents {
  api: PlatformComponentStatus;
  redis: PlatformComponentStatus;
  mongodb: PlatformComponentStatus;
  qdrant: PlatformComponentStatus;
  multi_agent: PlatformComponentStatus;
  mcp: McpComponentStatus;
  llm: LlmComponentStatus;
  observability: ObservabilityComponentStatus;
}

export interface PlatformRuntimeConfig {
  embedding_provider: string;
  embedding_model: string;
  embedding_dimension: number;

  qdrant_collection: string;

  rag_retrieval_limit: number;
  rag_chunk_character_limit: number;
  rag_max_output_tokens: number;

  llm_max_concurrency: number;
  ollama_keep_alive: string;

  metrics_path: string;
  otel_service_name: string;
  otel_exporter_enabled: boolean;
}

export interface PlatformStatusResponse {
  status: PlatformState;
  service: string;
  environment: string;
  components: PlatformComponents;
  runtime: PlatformRuntimeConfig;
}

export interface PlatformStatusViewState {
  data: PlatformStatusResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}
