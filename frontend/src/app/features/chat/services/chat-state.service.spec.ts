import { TestBed } from '@angular/core/testing';
import {
  BehaviorSubject,
  Subject,
} from 'rxjs';

import {
  ServerWebSocketEvent,
  WebSocketConnectionState,
} from '../../../core/models/websocket.model';
import { WebSocketService } from '../../../core/services/websocket.service';
import { ChatState } from '../chat.model';
import { ChatStateService } from './chat-state.service';

interface SentChat {
  requestId: string;
  message: string;
}

class FakeWebSocketService {
  private readonly connectionStateSubject =
    new BehaviorSubject<WebSocketConnectionState>(
      'disconnected',
    );

  private readonly eventSubject =
    new Subject<ServerWebSocketEvent>();

  readonly connectionState$ =
    this.connectionStateSubject.asObservable();

  readonly events$ =
    this.eventSubject.asObservable();

  sentChats: SentChat[] = [];
  cancelledRequestIds: string[] = [];
  connectCalls = 0;

  connect(): void {
    this.connectCalls += 1;
    this.connectionStateSubject.next('connecting');
    this.connectionStateSubject.next('connected');
  }

  sendChat(
    requestId: string,
    message: string,
  ): void {
    this.sentChats.push({
      requestId,
      message,
    });
  }

  cancel(requestId: string): void {
    this.cancelledRequestIds.push(requestId);
  }

  emit(event: ServerWebSocketEvent): void {
    this.eventSubject.next(event);
  }
}

describe('ChatStateService', () => {
  let service: ChatStateService;
  let websocketService: FakeWebSocketService;
  let latestState: ChatState;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ChatStateService,
        {
          provide: WebSocketService,
          useClass: FakeWebSocketService,
        },
      ],
    });

    service = TestBed.inject(ChatStateService);

    websocketService = TestBed.inject(
      WebSocketService,
    ) as unknown as FakeWebSocketService;

    service.state$.subscribe((state) => {
      latestState = state;
    });
  });

  it('should stream assistant chunks into one message', () => {
    service.sendMessage('Hello');

    expect(websocketService.connectCalls).toBe(1);
    expect(websocketService.sentChats).toHaveLength(1);

    const requestId =
      websocketService.sentChats[0].requestId;

    expect(
      websocketService.sentChats[0].message,
    ).toBe('Hello');

    expect(latestState.messages).toHaveLength(1);
    expect(latestState.messages[0].role).toBe('user');
    expect(latestState.isLoading).toBe(true);

    websocketService.emit({
      type: 'started',
      request_id: requestId,
      model: 'test-model',
    });

    expect(latestState.messages).toHaveLength(2);
    expect(latestState.messages[1].role).toBe(
      'assistant',
    );
    expect(latestState.messages[1].content).toBe('');

    websocketService.emit({
      type: 'chunk',
      request_id: requestId,
      content: 'Hello',
    });

    expect(latestState.messages[1].content).toBe(
      'Hello',
    );

    websocketService.emit({
      type: 'chunk',
      request_id: requestId,
      content: ' from Orbyntiq',
    });

    expect(latestState.messages[1].content).toBe(
      'Hello from Orbyntiq',
    );

    websocketService.emit({
      type: 'completed',
      request_id: requestId,
      model: 'test-model',
    });

    expect(latestState.messages[1].content).toBe(
      'Hello from Orbyntiq',
    );
    expect(latestState.messages[1].model).toBe(
      'test-model',
    );
    expect(latestState.lastModel).toBe('test-model');
    expect(latestState.lastUsage).toBeNull();
    expect(latestState.isLoading).toBe(false);
  });

  it('should reject prompts longer than the backend limit', () => {
    service.sendMessage('a'.repeat(20_001));

    expect(latestState.messages).toHaveLength(0);
    expect(latestState.error).toBe(
      'Prompt cannot exceed 20,000 characters.',
    );

    expect(websocketService.sentChats).toHaveLength(0);
    expect(websocketService.connectCalls).toBe(0);
  });

  it('should expose streaming errors and preserve partial output', () => {
    service.sendMessage('Hello');

    const requestId =
      websocketService.sentChats[0].requestId;

    websocketService.emit({
      type: 'started',
      request_id: requestId,
      model: 'test-model',
    });

    websocketService.emit({
      type: 'chunk',
      request_id: requestId,
      content: 'Partial answer',
    });

    websocketService.emit({
      type: 'error',
      request_id: requestId,
      message: 'LLM streaming request failed.',
      code: 'stream_error',
    });

    expect(latestState.messages).toHaveLength(2);
    expect(latestState.messages[1].content).toBe(
      'Partial answer',
    );

    expect(latestState.error).toBe(
      'LLM streaming request failed.',
    );

    expect(latestState.isLoading).toBe(false);
  });

  it('should cancel an active streamed response', () => {
    service.sendMessage('Hello');

    const requestId =
      websocketService.sentChats[0].requestId;

    websocketService.emit({
      type: 'started',
      request_id: requestId,
      model: 'test-model',
    });

    websocketService.emit({
      type: 'chunk',
      request_id: requestId,
      content: 'Partial',
    });

    service.cancelResponse();

    expect(
      websocketService.cancelledRequestIds,
    ).toEqual([requestId]);

    websocketService.emit({
      type: 'cancelled',
      request_id: requestId,
    });

    expect(latestState.messages[1].content).toBe(
      'Partial',
    );
    expect(latestState.isLoading).toBe(false);
  });

  it('should ignore events belonging to another request', () => {
    service.sendMessage('Hello');

    websocketService.emit({
      type: 'chunk',
      request_id: 'different-request',
      content: 'Wrong response',
    });

    expect(latestState.messages).toHaveLength(1);
    expect(latestState.messages[0].role).toBe('user');
    expect(latestState.isLoading).toBe(true);
  });

  it('should reset the conversation', () => {
    service.sendMessage('Hello');

    const requestId =
      websocketService.sentChats[0].requestId;

    websocketService.emit({
      type: 'started',
      request_id: requestId,
      model: 'test-model',
    });

    websocketService.emit({
      type: 'chunk',
      request_id: requestId,
      content: 'Response',
    });

    service.resetConversation();

    expect(latestState.messages).toHaveLength(0);
    expect(latestState.error).toBeNull();
    expect(latestState.lastModel).toBeNull();
    expect(latestState.lastUsage).toBeNull();

    expect(
      websocketService.cancelledRequestIds,
    ).toEqual([requestId]);
  });
});
