import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { API_CONFIG } from '../config/api.config';
import {
  PlatformStatusResponse,
  PlatformStatusViewState,
} from '../models/platform-status.model';
import {
  PlatformStatusService,
} from './platform-status.service';

const MOCK_STATUS: PlatformStatusResponse = {
  status: 'healthy',
  service: 'Orbyntiq',
  environment: 'development',
  components: {
    api: {
      status: 'healthy',
      detail: 'FastAPI application is responding.',
    },
    redis: {
      status: 'healthy',
      detail: 'Redis is connected.',
    },
    mongodb: {
      status: 'healthy',
      detail: 'MongoDB is connected.',
    },
    qdrant: {
      status: 'healthy',
      detail: 'Qdrant is connected.',
    },
    multi_agent: {
      status: 'healthy',
      detail:
        'Multi-agent orchestration is configured.',
    },
    mcp: {
      status: 'healthy',
      detail:
        'MCP retrieval and RAG services are configured.',
      retriever_configured: true,
      rag_configured: true,
    },
    llm: {
      status: 'configured',
      detail:
        'Local LLM runtime is configured.',
      provider: 'ollama',
      model: 'qwen3:4b-instruct',
    },
    observability: {
      status: 'configured',
      detail: 'Observability is enabled.',
      metrics_enabled: true,
      tracing_enabled: true,
    },
  },
};

describe('PlatformStatusService', () => {
  let service: PlatformStatusService;
  let httpTesting: HttpTestingController;
  let latestState: PlatformStatusViewState;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        PlatformStatusService,
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(
      PlatformStatusService,
    );

    httpTesting = TestBed.inject(
      HttpTestingController,
    );

    service.state$.subscribe((state) => {
      latestState = state;
    });
  });

  afterEach(() => {
    service.stopPolling();
    httpTesting.verify();
  });

  it('should expose the initial loading state', () => {
    expect(latestState.loading).toBe(true);
    expect(latestState.data).toBeNull();
    expect(latestState.error).toBeNull();
  });

  it('should load real platform status', () => {
    service.startPolling();

    const request = httpTesting.expectOne(
      `${API_CONFIG.baseUrl}/platform/status`,
    );

    expect(request.request.method).toBe('GET');

    request.flush(MOCK_STATUS);

    expect(latestState.loading).toBe(false);
    expect(latestState.error).toBeNull();
    expect(latestState.data).toEqual(
      MOCK_STATUS,
    );
    expect(latestState.lastUpdated).not.toBeNull();
  });

  it('should expose an API connectivity error', () => {
    service.startPolling();

    const request = httpTesting.expectOne(
      `${API_CONFIG.baseUrl}/platform/status`,
    );

    request.error(
      new ProgressEvent('error'),
    );

    expect(latestState.loading).toBe(false);
    expect(latestState.data).toBeNull();
    expect(latestState.error).toBe(
      'Unable to reach the Orbyntiq platform API.',
    );
  });

  it('should not start duplicate polling loops', () => {
    service.startPolling();
    service.startPolling();

    httpTesting.expectOne(
      `${API_CONFIG.baseUrl}/platform/status`,
    );
  });
});
