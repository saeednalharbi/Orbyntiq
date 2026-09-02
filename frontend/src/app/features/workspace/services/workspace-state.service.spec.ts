import { TestBed } from '@angular/core/testing';
import {
  BehaviorSubject,
  Subject,
} from 'rxjs';
import { vi } from 'vitest';

import {
  ServerWebSocketEvent,
  WebSocketConnectionState,
} from '../../../core/models/websocket.model';
import {
  WebSocketService,
} from '../../../core/services/websocket.service';
import {
  WorkspaceState,
} from '../models/workspace.model';
import {
  WorkspaceStateService,
} from './workspace-state.service';

class FakeWebSocketService {
  readonly connectionStateSubject =
    new BehaviorSubject<WebSocketConnectionState>(
      'disconnected',
    );

  readonly eventSubject =
    new Subject<ServerWebSocketEvent>();

  readonly connectionState$ =
    this.connectionStateSubject.asObservable();

  readonly events$ =
    this.eventSubject.asObservable();

  connect = vi.fn();

  disconnect = vi.fn();

  sendChat = vi.fn();

  sendAgentExecution = vi.fn();

  cancel = vi.fn();
}

describe('WorkspaceStateService', () => {
  let service: WorkspaceStateService;
  let websocket: FakeWebSocketService;
  let latestState: WorkspaceState;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        WorkspaceStateService,
        {
          provide: WebSocketService,
          useClass: FakeWebSocketService,
        },
      ],
    });

    service = TestBed.inject(
      WorkspaceStateService,
    );

    websocket = TestBed.inject(
      WebSocketService,
    ) as unknown as FakeWebSocketService;

    service.state$.subscribe((state) => {
      latestState = state;
    });
  });

  it('should default to agent mode', () => {
    expect(latestState.mode).toBe('agent');
    expect(latestState.isRunning).toBe(false);
    expect(latestState.execution).toBeNull();
    expect(latestState.messages).toEqual([]);
  });

  it('should queue an agent request until connected', () => {
    service.submit(
      'Research the architecture.',
    );

    expect(websocket.connect).toHaveBeenCalledOnce();

    expect(
      websocket.sendAgentExecution,
    ).not.toHaveBeenCalled();

    websocket.connectionStateSubject.next(
      'connected',
    );

    expect(
      websocket.sendAgentExecution,
    ).toHaveBeenCalledOnce();

    const call =
      websocket.sendAgentExecution.mock.calls[0];

    expect(call[1]).toBe(
      'Research the architecture.',
    );

    expect(call[2]).toBe(
      latestState.conversationId,
    );

    expect(call[3]).toBe(4);

    expect(latestState.isRunning).toBe(true);
    expect(latestState.execution?.status).toBe(
      'running',
    );
  });

  it('should capture live routing metadata', () => {
    websocket.connectionStateSubject.next(
      'connected',
    );

    service.submit('Research Orbyntiq.');

    const requestId =
      latestState.activeRequestId!;

    websocket.eventSubject.next({
      type: 'agent_event',
      request_id: requestId,
      execution_id: 'execution-1',
      sequence: 0,
      event_type: 'execution_started',
      agent_name: 'supervisor',
      payload: {},
    });

    websocket.eventSubject.next({
      type: 'agent_event',
      request_id: requestId,
      execution_id: 'execution-1',
      sequence: 1,
      event_type: 'routing_completed',
      agent_name: 'supervisor',
      payload: {
        route: 'research',
        route_reason:
          'Grounded retrieval is required.',
      },
    });

    expect(
      latestState.execution?.executionId,
    ).toBe('execution-1');

    expect(
      latestState.execution?.route,
    ).toBe('research');

    expect(
      latestState.execution?.routeReason,
    ).toBe(
      'Grounded retrieval is required.',
    );

    expect(
      latestState.execution?.events,
    ).toHaveLength(2);
  });

  it('should complete a multi-agent execution', () => {
    websocket.connectionStateSubject.next(
      'connected',
    );

    service.submit('Use research.');

    const requestId =
      latestState.activeRequestId!;

    websocket.eventSubject.next({
      type: 'agent_event',
      request_id: requestId,
      execution_id: 'execution-2',
      sequence: 0,
      event_type: 'execution_started',
      agent_name: 'supervisor',
      payload: {},
    });

    websocket.eventSubject.next({
      type: 'agent_event',
      request_id: requestId,
      execution_id: 'execution-2',
      sequence: 1,
      event_type: 'execution_completed',
      agent_name: 'synthesizer',
      payload: {
        route: 'research',
        hop_count: 3,
        final_response:
          'Grounded final response.',
        errors: [],
        sources: [
          {
            file_name: 'architecture.pdf',
            score: 0.91,
          },
        ],
      },
    });

    expect(latestState.isRunning).toBe(false);

    expect(
      latestState.execution?.status,
    ).toBe('completed');

    expect(
      latestState.execution?.hopCount,
    ).toBe(3);

    expect(
      latestState.execution?.sources,
    ).toHaveLength(1);

    expect(latestState.messages).toHaveLength(
      2,
    );

    expect(
      latestState.messages[1].content,
    ).toBe('Grounded final response.');
  });

  it('should stream direct LLM responses', () => {
    websocket.connectionStateSubject.next(
      'connected',
    );

    service.setMode('direct');
    service.submit('Hello');

    const requestId =
      latestState.activeRequestId!;

    expect(
      websocket.sendChat,
    ).toHaveBeenCalledOnce();

    websocket.eventSubject.next({
      type: 'started',
      request_id: requestId,
      model: 'qwen3:4b-instruct',
    });

    websocket.eventSubject.next({
      type: 'chunk',
      request_id: requestId,
      content: 'Hello ',
    });

    websocket.eventSubject.next({
      type: 'chunk',
      request_id: requestId,
      content: 'world',
    });

    websocket.eventSubject.next({
      type: 'completed',
      request_id: requestId,
      model: 'qwen3:4b-instruct',
    });

    expect(latestState.isRunning).toBe(false);

    expect(latestState.lastModel).toBe(
      'qwen3:4b-instruct',
    );

    expect(
      latestState.messages[1].content,
    ).toBe('Hello world');
  });

  it('should cancel an active request', () => {
    websocket.connectionStateSubject.next(
      'connected',
    );

    service.submit('Long request');

    const requestId =
      latestState.activeRequestId!;

    service.cancel();

    expect(
      websocket.cancel,
    ).toHaveBeenCalledWith(requestId);

    websocket.eventSubject.next({
      type: 'cancelled',
      request_id: requestId,
    });

    expect(latestState.isRunning).toBe(false);

    expect(
      latestState.execution?.status,
    ).toBe('cancelled');
  });

  it('should ignore unrelated request events', () => {
    websocket.connectionStateSubject.next(
      'connected',
    );

    service.submit('My request');

    websocket.eventSubject.next({
      type: 'agent_event',
      request_id: 'another-request',
      execution_id: 'execution-other',
      sequence: 0,
      event_type: 'execution_completed',
      agent_name: 'synthesizer',
      payload: {
        final_response: 'Wrong response',
      },
    });

    expect(latestState.isRunning).toBe(true);
    expect(latestState.messages).toHaveLength(
      1,
    );
  });

  it('should preserve the selected mode after reset', () => {
    service.setMode('direct');

    const oldConversationId =
      latestState.conversationId;

    service.resetConversation();

    expect(latestState.mode).toBe('direct');
    expect(latestState.messages).toEqual([]);
    expect(latestState.execution).toBeNull();

    expect(latestState.conversationId).not.toBe(
      oldConversationId,
    );
  });
});
