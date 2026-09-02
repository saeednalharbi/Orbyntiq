import {
  DestroyRef,
  Injectable,
  inject,
} from '@angular/core';
import {
  takeUntilDestroyed,
} from '@angular/core/rxjs-interop';
import {
  HttpErrorResponse,
  HttpEventType,
} from '@angular/common/http';
import {
  BehaviorSubject,
  forkJoin,
} from 'rxjs';

import {
  KnowledgeSearchRequest,
  KnowledgeState,
} from '../models/knowledge.model';
import {
  KnowledgeService,
} from './knowledge.service';

const INITIAL_STATE: KnowledgeState = {
  status: null,
  documents: [],
  searchResults: [],
  searchQuery: '',
  selectedDocumentId: null,
  loading: false,
  searching: false,
  uploading: false,
  uploadProgress: null,
  error: null,
  lastIngestion: null,
};

@Injectable({
  providedIn: 'root',
})
export class KnowledgeStateService {
  private readonly api =
    inject(KnowledgeService);

  private readonly destroyRef =
    inject(DestroyRef);

  private readonly stateSubject =
    new BehaviorSubject<KnowledgeState>(
      INITIAL_STATE,
    );

  readonly state$ =
    this.stateSubject.asObservable();

  load(): void {
    if (this.stateSubject.value.loading) {
      return;
    }

    this.patchState({
      loading: true,
      error: null,
    });

    forkJoin({
      status: this.api.getStatus(),
      documents: this.api.getDocuments(),
    })
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({
        next: ({
          status,
          documents,
        }) => {
          this.patchState({
            status,
            documents:
              documents.documents,
            loading: false,
            error: null,
          });
        },

        error: (error: unknown) => {
          this.patchState({
            loading: false,
            error:
              this.errorMessage(
                error,
                'Unable to load the knowledge collection.',
              ),
          });
        },
      });
  }

  search(
    rawQuery: string,
    limit = 5,
    scoreThreshold:
      number | null = null,
  ): void {
    const query =
      rawQuery.trim();

    if (
      !query ||
      this.stateSubject.value.searching
    ) {
      return;
    }

    const request:
      KnowledgeSearchRequest = {
        query,
        limit,
        score_threshold:
          scoreThreshold,
    };

    const selectedDocumentId =
      this.stateSubject.value
        .selectedDocumentId;

    if (selectedDocumentId) {
      request.document_id =
        selectedDocumentId;
    }

    this.patchState({
      searching: true,
      searchQuery: query,
      searchResults: [],
      error: null,
    });

    this.api.search(request)
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({
        next: (response) => {
          this.patchState({
            searching: false,
            searchResults:
              response.results,
          });
        },

        error: (error: unknown) => {
          this.patchState({
            searching: false,
            error:
              this.errorMessage(
                error,
                'Semantic search failed.',
              ),
          });
        },
      });
  }

  ingest(file: File): void {
    if (
      this.stateSubject.value.uploading
    ) {
      return;
    }

    this.patchState({
      uploading: true,
      uploadProgress: 0,
      error: null,
      lastIngestion: null,
    });

    this.api.ingest(file)
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({
        next: (event) => {
          if (
            event.type ===
            HttpEventType.UploadProgress
          ) {
            const total =
              event.total;

            this.patchState({
              uploadProgress:
                total && total > 0
                  ? Math.round(
                      100 *
                      event.loaded /
                      total,
                    )
                  : null,
            });

            return;
          }

          if (
            event.type ===
            HttpEventType.Response
          ) {
            this.patchState({
              uploading: false,
              uploadProgress: 100,
              lastIngestion:
                event.body,
            });

            this.load();
          }
        },

        error: (error: unknown) => {
          this.patchState({
            uploading: false,
            uploadProgress: null,
            error:
              this.errorMessage(
                error,
                'Document ingestion failed.',
              ),
          });
        },
      });
  }

  selectDocument(
    documentId: string | null,
  ): void {
    this.patchState({
      selectedDocumentId:
        documentId,
    });
  }

  clearSearch(): void {
    this.patchState({
      searchQuery: '',
      searchResults: [],
    });
  }

  clearError(): void {
    this.patchState({
      error: null,
    });
  }

  private errorMessage(
    error: unknown,
    fallback: string,
  ): string {
    if (
      error instanceof
        HttpErrorResponse &&
      typeof error.error === 'object' &&
      error.error !== null &&
      'detail' in error.error &&
      typeof error.error.detail ===
        'string'
    ) {
      return error.error.detail;
    }

    return fallback;
  }

  private patchState(
    changes: Partial<KnowledgeState>,
  ): void {
    this.stateSubject.next({
      ...this.stateSubject.value,
      ...changes,
    });
  }
}
