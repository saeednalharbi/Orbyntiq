import {
  WebSocketConnectionState,
} from '../../../core/models/websocket.model';

export type WorkspaceMode =
  | 'agent'
  | 'direct';

export type WorkspaceRole =
  | 'user'
  | 'assistant';

export type WorkspaceExecutionStatus =
  | 'idle'
  | 'running'
  | 'completed'
  | 'cancelled'
  | 'failed';

export type AgentRoute =
  | 'research'
  | 'mcp'
  | 'general';

export interface WorkspaceSource {
  readonly [key: string]: unknown;
}

export interface WorkspaceMessage {
  id: string;
  role: WorkspaceRole;
  content: string;
  createdAt: string;
  model?: string;
  sources?: readonly WorkspaceSource[];
}

export interface WorkspaceWorkflowEvent {
  sequence: number;
  eventType: string;
  agentName: string | null;
  payload: Readonly<Record<string, unknown>>;
}

export interface WorkspaceExecution {
  requestId: string;
  executionId: string | null;
  status: WorkspaceExecutionStatus;
  route: AgentRoute | null;
  routeReason: string | null;
  hopCount: number | null;
  events: readonly WorkspaceWorkflowEvent[];
  sources: readonly WorkspaceSource[];
  errors: readonly string[];
}

export interface WorkspaceState {
  mode: WorkspaceMode;
  messages: readonly WorkspaceMessage[];
  connectionState: WebSocketConnectionState;
  isRunning: boolean;
  error: string | null;
  activeRequestId: string | null;
  conversationId: string;
  lastModel: string | null;
  execution: WorkspaceExecution | null;
}
