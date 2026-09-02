import {
  HttpEventType,
  HttpResponse,
} from '@angular/common/http';
import {
  TestBed,
} from '@angular/core/testing';
import {
  of,
} from 'rxjs';
import {
  vi,
} from 'vitest';

import {
  KnowledgeService,
} from './knowledge.service';
import {
  KnowledgeStateService,
} from './knowledge-state.service';

class FakeKnowledgeService {
  getStatus = vi.fn(() =>
    of({
      status: 'green',
      collection:
        'orbyntiq_documents',
      points_count: 4,
      indexed_vectors_count: 0,
      document_count: 1,
      vector_size: 1024,
      distance: 'Cosine',
      embedding_provider:
        'ollama',
      embedding_model:
        'qwen3-embedding:0.6b',
      embedding_dimension: 1024,
      supported_file_types: [
        '.txt',
      ],
    }),
  );

  getDocuments = vi.fn(() =>
    of({
      count: 1,
      documents: [
        {
          document_id: 'doc-1',
          file_name:
            'knowledge.txt',
          source_path:
            'data/knowledge/knowledge.txt',
          checksum: 'abc',
          chunk_count: 2,
          page_count: 0,
        },
      ],
    }),
  );

  search = vi.fn(() =>
    of({
      query: 'architecture',
      count: 1,
      results: [
        {
          id: 'chunk-1',
          score: 0.9,
          document_id:
            'doc-1',
          chunk_index: 0,
          text: 'Orbyntiq architecture',
          source_path:
            'data/knowledge/knowledge.txt',
          file_name:
            'knowledge.txt',
          checksum: 'abc',
          page_number: null,
        },
      ],
    }),
  );

  ingest = vi.fn(() =>
    of(
      {
        type:
          HttpEventType
            .UploadProgress,
        loaded: 5,
        total: 10,
      },
      new HttpResponse({
        body: {
          document_id:
            'doc-2',
          file_name:
            'new.txt',
          checksum: 'def',
          chunks_indexed: 1,
        },
      }),
    ),
  );
}

describe(
  'KnowledgeStateService',
  () => {
    let service:
      KnowledgeStateService;

    let api:
      FakeKnowledgeService;

    beforeEach(() => {
      TestBed.configureTestingModule({
        providers: [
          KnowledgeStateService,
          {
            provide:
              KnowledgeService,
            useClass:
              FakeKnowledgeService,
          },
        ],
      });

      service =
        TestBed.inject(
          KnowledgeStateService,
        );

      api =
        TestBed.inject(
          KnowledgeService,
        ) as unknown as
          FakeKnowledgeService;
    });

    it('should load status and documents', () => {
      let latest:
        any = null;

      service.state$
        .subscribe((state) => {
          latest = state;
        });

      service.load();

      expect(
        latest.status.collection,
      ).toBe(
        'orbyntiq_documents',
      );

      expect(
        latest.documents,
      ).toHaveLength(1);

      expect(latest.loading)
        .toBe(false);
    });

    it('should run semantic search', () => {
      let latest:
        any = null;

      service.state$
        .subscribe((state) => {
          latest = state;
        });

      service.search(
        ' architecture ',
        5,
        0.25,
      );

      expect(api.search)
        .toHaveBeenCalledWith({
          query: 'architecture',
          limit: 5,
          score_threshold: 0.25,
        });

      expect(
        latest.searchResults,
      ).toHaveLength(1);

      expect(latest.searching)
        .toBe(false);
    });

    it('should ingest and refresh collection data', () => {
      const file = new File(
        ['test'],
        'new.txt',
      );

      service.ingest(file);

      expect(api.ingest)
        .toHaveBeenCalledWith(file);

      expect(api.getStatus)
        .toHaveBeenCalledTimes(1);

      expect(api.getDocuments)
        .toHaveBeenCalledTimes(1);
    });
  },
);
