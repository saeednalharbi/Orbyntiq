import {
  HttpEventType,
  provideHttpClient,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import {
  TestBed,
} from '@angular/core/testing';

import {
  API_CONFIG,
} from '../../../core/config/api.config';
import {
  KnowledgeService,
} from './knowledge.service';

describe('KnowledgeService', () => {
  let service: KnowledgeService;
  let httpTesting:
    HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        KnowledgeService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service =
      TestBed.inject(KnowledgeService);

    httpTesting =
      TestBed.inject(
        HttpTestingController,
      );
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should load collection status', () => {
    service.getStatus()
      .subscribe((status) => {
        expect(
          status.collection,
        ).toBe(
          'orbyntiq_documents',
        );
      });

    const request =
      httpTesting.expectOne(
        API_CONFIG.knowledge.status,
      );

    expect(
      request.request.method,
    ).toBe('GET');

    request.flush({
      status: 'green',
      collection:
        'orbyntiq_documents',
      points_count: 4,
      indexed_vectors_count: 0,
      document_count: 2,
      vector_size: 1024,
      distance: 'Cosine',
      embedding_provider:
        'ollama',
      embedding_model:
        'qwen3-embedding:0.6b',
      embedding_dimension: 1024,
      supported_file_types: [
        '.md',
        '.pdf',
        '.txt',
      ],
    });
  });

  it('should perform semantic search', () => {
    service.search({
      query: 'Orbyntiq',
      limit: 5,
      score_threshold: 0.25,
    }).subscribe((response) => {
      expect(response.count).toBe(1);
    });

    const request =
      httpTesting.expectOne(
        API_CONFIG.knowledge.search,
      );

    expect(
      request.request.method,
    ).toBe('POST');

    expect(
      request.request.body.query,
    ).toBe('Orbyntiq');

    request.flush({
      query: 'Orbyntiq',
      count: 1,
      results: [],
    });
  });

  it('should upload raw document bytes', () => {
    const file = new File(
      ['hello'],
      'knowledge.txt',
      {
        type: 'text/plain',
      },
    );

    const eventTypes: number[] = [];

    service.ingest(file)
      .subscribe((event) => {
        eventTypes.push(
          event.type,
        );
      });

    const request =
      httpTesting.expectOne(
        (candidate) =>
          candidate.url ===
            API_CONFIG.knowledge.ingest &&
          candidate.params.get(
            'file_name',
          ) === 'knowledge.txt',
      );

    expect(
      request.request.method,
    ).toBe('POST');

    expect(
      request.request.body,
    ).toBe(file);

    request.flush(
      {
        document_id: 'doc-1',
        file_name:
          'knowledge.txt',
        checksum: 'abc',
        chunks_indexed: 1,
      },
    );

    expect(eventTypes).toContain(
      HttpEventType.Response,
    );
  });
});
