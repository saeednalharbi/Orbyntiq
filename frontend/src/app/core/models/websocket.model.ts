export type WebSocketConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected';

export interface ChatStreamRequest {
  type: 'chat';
  request_id: string;
  message: string;
}

export interface AgentExecuteWebSocketRequest {
  type: 'agent_execute';
  request_id: string;
  query: string;
  conversation_id: string | null;
  max_hops: number;
}

export interface CancelStreamRequest {
  type: 'cancel';
  request_id: string;
}

export interface PingRequest {
  type: 'ping';
}

export type ClientWebSocketMessage =
  | ChatStreamRequest
  | AgentExecuteWebSocketRequest
  | CancelStreamRequest
  | PingRequest;

export interface StreamStartedEvent {
  type: 'started';
  request_id: string;
  model: string;
}

export interface StreamChunkEvent {
  type: 'chunk';
  request_id: string;
  content: string;
}

export interface StreamCompletedEvent {
  type: 'completed';
  request_id: string;
  model: string;
}

export interface StreamCancelledEvent {
  type: 'cancelled';
  request_id: string;
}

export interface AgentWorkflowEvent {
  type: 'agent_event';
  request_id: string;
  execution_id: string;
  sequence: number;
  event_type: string;
  agent_name: string | null;
  payload: Record<string, unknown>;
}

export interface PongEvent {
  type: 'pong';
}

export interface StreamErrorEvent {
  type: 'error';
  request_id: string;
  message: string;
  code: string;
}

export type ServerWebSocketEvent =
  | StreamStartedEvent
  | StreamChunkEvent
  | StreamCompletedEvent
  | StreamCancelledEvent
  | AgentWorkflowEvent
  | PongEvent
  | StreamErrorEvent;
