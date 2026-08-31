import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';

import { API_CONFIG } from '../config/api.config';
import {
  ServerWebSocketEvent,
  WebSocketConnectionState,
} from '../models/websocket.model';
import {
  WEBSOCKET_HEARTBEAT_INTERVAL_MS,
  WEBSOCKET_RECONNECT_BASE_DELAY_MS,
  WebSocketService,
} from './websocket.service';

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  static instances: FakeWebSocket[] = [];

  readonly url: string;

  readyState = FakeWebSocket.CONNECTING;

  sentMessages: string[] = [];

  onopen:
    | ((event: Event) => void)
    | null = null;

  onmessage:
    | ((event: MessageEvent<unknown>) => void)
    | null = null;

  onerror:
    | ((event: Event) => void)
    | null = null;

  onclose:
    | ((event: CloseEvent) => void)
    | null = null;

  constructor(url: string) {
    this.url = url;

    FakeWebSocket.instances.push(this);
  }

  open(): void {
    this.readyState = FakeWebSocket.OPEN;

    this.onopen?.({} as Event);
  }

  receive(data: unknown): void {
    this.onmessage?.({
      data: JSON.stringify(data),
    } as MessageEvent<unknown>);
  }

  send(data: string): void {
    this.sentMessages.push(data);
  }

  close(
    code = 1000,
    reason = '',
  ): void {
    this.readyState = FakeWebSocket.CLOSED;

    this.onclose?.({
      code,
      reason,
    } as CloseEvent);
  }
}

describe('WebSocketService', () => {
  let service: WebSocketService;
  let originalWebSocket: typeof WebSocket;

  beforeEach(() => {
    originalWebSocket = globalThis.WebSocket;

    FakeWebSocket.instances = [];

    globalThis.WebSocket =
      FakeWebSocket as unknown as typeof WebSocket;

    TestBed.configureTestingModule({
      providers: [WebSocketService],
    });

    service = TestBed.inject(WebSocketService);
  });

  afterEach(() => {
    service.disconnect();

    globalThis.WebSocket = originalWebSocket;

    vi.useRealTimers();
  });

  it('should connect to the configured WebSocket endpoint', () => {
    const states: WebSocketConnectionState[] = [];

    service.connectionState$.subscribe(
      (state) => {
        states.push(state);
      },
    );

    service.connect();

    const socket = FakeWebSocket.instances[0];

    expect(socket.url).toBe(
      API_CONFIG.websocket.chat,
    );

    expect(states).toEqual([
      'disconnected',
      'connecting',
    ]);

    socket.open();

    expect(states).toEqual([
      'disconnected',
      'connecting',
      'connected',
    ]);
  });

  it('should expose typed server events', () => {
    const events: ServerWebSocketEvent[] = [];

    service.events$.subscribe((event) => {
      events.push(event);
    });

    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    socket.receive({
      type: 'chunk',
      request_id: 'req-123',
      content: 'Hello',
    });

    expect(events).toEqual([
      {
        type: 'chunk',
        request_id: 'req-123',
        content: 'Hello',
      },
    ]);
  });

  it('should send chat requests', () => {
    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    service.sendChat(
      'req-123',
      'Hello Orbyntiq',
    );

    expect(
      JSON.parse(socket.sentMessages[0]),
    ).toEqual({
      type: 'chat',
      request_id: 'req-123',
      message: 'Hello Orbyntiq',
    });
  });

  it('should send cancellation requests', () => {
    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    service.cancel('req-123');

    expect(
      JSON.parse(socket.sentMessages[0]),
    ).toEqual({
      type: 'cancel',
      request_id: 'req-123',
    });
  });

  it('should send heartbeat pings while connected', () => {
    vi.useFakeTimers();

    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    vi.advanceTimersByTime(
      WEBSOCKET_HEARTBEAT_INTERVAL_MS,
    );

    expect(socket.sentMessages).toHaveLength(1);

    expect(
      JSON.parse(socket.sentMessages[0]),
    ).toEqual({
      type: 'ping',
    });
  });

  it('should return to disconnected state when deliberately closed', () => {
    const states: WebSocketConnectionState[] = [];

    service.connectionState$.subscribe(
      (state) => {
        states.push(state);
      },
    );

    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    service.disconnect();

    expect(states.at(-1)).toBe(
      'disconnected',
    );
  });

  it('should reconnect after an unexpected disconnect', () => {
    vi.useFakeTimers();

    service.connect();

    const firstSocket =
      FakeWebSocket.instances[0];

    firstSocket.open();

    firstSocket.close(
      1006,
      'Unexpected disconnect.',
    );

    expect(
      FakeWebSocket.instances,
    ).toHaveLength(1);

    vi.advanceTimersByTime(
      WEBSOCKET_RECONNECT_BASE_DELAY_MS,
    );

    expect(
      FakeWebSocket.instances,
    ).toHaveLength(2);

    const secondSocket =
      FakeWebSocket.instances[1];

    expect(secondSocket.url).toBe(
      API_CONFIG.websocket.chat,
    );

    secondSocket.open();
  });

  it('should not reconnect after a deliberate disconnect', () => {
    vi.useFakeTimers();

    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    service.disconnect();

    vi.advanceTimersByTime(
      WEBSOCKET_RECONNECT_BASE_DELAY_MS * 4,
    );

    expect(
      FakeWebSocket.instances,
    ).toHaveLength(1);
  });

  it('should reject sends while disconnected', () => {
    expect(() => {
      service.sendChat(
        'req-123',
        'Hello',
      );
    }).toThrowError(
      'Orbyntiq WebSocket is not connected.',
    );
  });

  it('should ignore invalid server messages', () => {
    const events: ServerWebSocketEvent[] = [];

    service.events$.subscribe((event) => {
      events.push(event);
    });

    service.connect();

    const socket = FakeWebSocket.instances[0];

    socket.open();

    socket.onmessage?.({
      data: 'not-json',
    } as MessageEvent<unknown>);

    socket.receive({
      invalid: true,
    });

    expect(events).toEqual([]);
  });
});
