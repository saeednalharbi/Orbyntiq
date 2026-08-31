import { Injectable, OnDestroy } from '@angular/core';
import {
  BehaviorSubject,
  Subject,
  distinctUntilChanged,
  map,
} from 'rxjs';

import { API_CONFIG } from '../config/api.config';
import {
  CancelStreamRequest,
  ChatStreamRequest,
  ClientWebSocketMessage,
  PingRequest,
  ServerWebSocketEvent,
  WebSocketConnectionState,
} from '../models/websocket.model';

export const WEBSOCKET_HEARTBEAT_INTERVAL_MS = 30_000;
export const WEBSOCKET_RECONNECT_BASE_DELAY_MS = 500;
export const WEBSOCKET_RECONNECT_MAX_DELAY_MS = 4_000;
export const WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 5;

const SERVER_EVENT_TYPES = new Set([
  'started',
  'chunk',
  'completed',
  'cancelled',
  'pong',
  'error',
]);

@Injectable({
  providedIn: 'root',
})
export class WebSocketService implements OnDestroy {
  private socket: WebSocket | null = null;

  private heartbeatTimer:
    | ReturnType<typeof setInterval>
    | null = null;

  private reconnectTimer:
    | ReturnType<typeof setTimeout>
    | null = null;

  private reconnectAttempts = 0;
  private deliberateDisconnect = false;

  private readonly eventSubject =
    new Subject<ServerWebSocketEvent>();

  private readonly connectionStateSubject =
    new BehaviorSubject<WebSocketConnectionState>(
      'disconnected',
    );

  readonly events$ = this.eventSubject.asObservable();

  readonly connectionState$ =
    this.connectionStateSubject
      .asObservable()
      .pipe(distinctUntilChanged());

  readonly isConnected$ = this.connectionState$.pipe(
    map((state) => state === 'connected'),
    distinctUntilChanged(),
  );

  connect(): void {
    this.deliberateDisconnect = false;

    this.clearReconnectTimer();
    this.openSocket();
  }

  disconnect(): void {
    this.deliberateDisconnect = true;

    this.stopHeartbeat();
    this.clearReconnectTimer();

    this.reconnectAttempts = 0;

    const socket = this.socket;

    this.socket = null;

    if (
      socket !== null &&
      socket.readyState !== WebSocket.CLOSED
    ) {
      socket.close(1000, 'Client disconnect.');
    }

    this.connectionStateSubject.next(
      'disconnected',
    );
  }

  sendChat(
    requestId: string,
    message: string,
  ): void {
    const request: ChatStreamRequest = {
      type: 'chat',
      request_id: requestId,
      message,
    };

    this.send(request);
  }

  cancel(requestId: string): void {
    const request: CancelStreamRequest = {
      type: 'cancel',
      request_id: requestId,
    };

    this.send(request);
  }

  ping(): void {
    const request: PingRequest = {
      type: 'ping',
    };

    this.send(request);
  }

  ngOnDestroy(): void {
    this.disconnect();

    this.eventSubject.complete();
    this.connectionStateSubject.complete();
  }

  private openSocket(): void {
    if (
      this.socket?.readyState === WebSocket.CONNECTING ||
      this.socket?.readyState === WebSocket.OPEN
    ) {
      return;
    }

    this.stopHeartbeat();

    this.connectionStateSubject.next('connecting');

    let socket: WebSocket;

    try {
      socket = new WebSocket(
        API_CONFIG.websocket.chat,
      );
    } catch {
      this.connectionStateSubject.next(
        'disconnected',
      );

      this.scheduleReconnect();
      return;
    }

    this.socket = socket;

    socket.onopen = () => {
      if (this.socket !== socket) {
        return;
      }

      this.reconnectAttempts = 0;

      this.connectionStateSubject.next(
        'connected',
      );

      this.startHeartbeat();
    };

    socket.onmessage = (
      event: MessageEvent<unknown>,
    ) => {
      if (this.socket !== socket) {
        return;
      }

      const parsedEvent =
        this.parseServerEvent(event.data);

      if (parsedEvent !== null) {
        this.eventSubject.next(parsedEvent);
      }
    };

    socket.onerror = () => {
      if (this.socket !== socket) {
        return;
      }

      this.stopHeartbeat();
    };

    socket.onclose = () => {
      if (this.socket !== socket) {
        return;
      }

      this.stopHeartbeat();

      this.socket = null;

      this.connectionStateSubject.next(
        'disconnected',
      );

      if (!this.deliberateDisconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (
      this.deliberateDisconnect ||
      this.reconnectTimer !== null ||
      this.reconnectAttempts >=
        WEBSOCKET_MAX_RECONNECT_ATTEMPTS
    ) {
      return;
    }

    const delay = Math.min(
      WEBSOCKET_RECONNECT_BASE_DELAY_MS *
        2 ** this.reconnectAttempts,
      WEBSOCKET_RECONNECT_MAX_DELAY_MS,
    );

    this.reconnectAttempts += 1;

    this.connectionStateSubject.next(
      'connecting',
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;

      if (!this.deliberateDisconnect) {
        this.openSocket();
      }
    }, delay);
  }

  private send(
    message: ClientWebSocketMessage,
  ): void {
    if (
      this.socket === null ||
      this.socket.readyState !== WebSocket.OPEN
    ) {
      throw new Error(
        'Orbyntiq WebSocket is not connected.',
      );
    }

    this.socket.send(
      JSON.stringify(message),
    );
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (
        this.socket?.readyState === WebSocket.OPEN
      ) {
        this.ping();
      }
    }, WEBSOCKET_HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer === null) {
      return;
    }

    clearInterval(this.heartbeatTimer);

    this.heartbeatTimer = null;
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer === null) {
      return;
    }

    clearTimeout(this.reconnectTimer);

    this.reconnectTimer = null;
  }

  private parseServerEvent(
    data: unknown,
  ): ServerWebSocketEvent | null {
    if (typeof data !== 'string') {
      return null;
    }

    try {
      const parsed: unknown = JSON.parse(data);

      if (
        typeof parsed !== 'object' ||
        parsed === null ||
        !('type' in parsed) ||
        typeof parsed.type !== 'string' ||
        !SERVER_EVENT_TYPES.has(parsed.type)
      ) {
        return null;
      }

      return parsed as ServerWebSocketEvent;
    } catch {
      return null;
    }
  }
}
