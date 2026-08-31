export type WebSocketConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected';

export interface ChatStreamRequest {
  type: 'chat';
  request_id: string;
  message: string;
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
  | PongEvent
  | StreamErrorEvent;
