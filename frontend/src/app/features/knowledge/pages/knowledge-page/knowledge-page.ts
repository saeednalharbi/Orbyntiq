import {
  AsyncPipe,
  DecimalPipe,
} from '@angular/common';
import {
  Component,
  OnInit,
  inject,
} from '@angular/core';
import {
  FormsModule,
} from '@angular/forms';

import {
  KnowledgeDocument,
  KnowledgeSearchResult,
} from '../../models/knowledge.model';
import {
  KnowledgeStateService,
} from '../../services/knowledge-state.service';

@Component({
  selector: 'app-knowledge-page',
  imports: [
    AsyncPipe,
    DecimalPipe,
    FormsModule,
  ],
  templateUrl: './knowledge-page.html',
  styleUrl: './knowledge-page.scss',
})
export class KnowledgePage
implements OnInit {
  private readonly knowledge =
    inject(KnowledgeStateService);

  readonly state$ =
    this.knowledge.state$;

  query = '';
  limit = 5;
  scoreThreshold:
    number | null = null;

  ngOnInit(): void {
    this.knowledge.load();
  }

  refresh(): void {
    this.knowledge.load();
  }

  search(): void {
    this.knowledge.search(
      this.query,
      this.limit,
      this.scoreThreshold,
    );
  }

  clearSearch(): void {
    this.query = '';
    this.knowledge.clearSearch();
  }

  selectDocument(
    rawDocumentId: string,
  ): void {
    this.knowledge.selectDocument(
      rawDocumentId || null,
    );
  }

  upload(
    event: Event,
  ): void {
    const input =
      event.target as HTMLInputElement;

    const file =
      input.files?.[0];

    if (!file) {
      return;
    }

    this.knowledge.ingest(file);
    input.value = '';
  }

  clearError(): void {
    this.knowledge.clearError();
  }

  previewText(
    text: string,
    maxLength = 320,
  ): string {
    const normalized = text
      .replace(/\s+/g, ' ')
      .trim();

    if (normalized.length <= maxLength) {
      return normalized;
    }

    return `${normalized.slice(0, maxLength).trimEnd()}?`;
  }

  scorePercent(
    result: KnowledgeSearchResult,
  ): number {
    return Math.round(
      Math.max(
        0,
        Math.min(
          1,
          result.score,
        ),
      ) * 100,
    );
  }

  fileType(
    document: KnowledgeDocument,
  ): string {
    const extension =
      document.file_name
        .split('.')
        .at(-1);

    return extension
      ? extension.toUpperCase()
      : 'DOC';
  }

  documentDescription(
    document: KnowledgeDocument,
  ): string {
    const sections =
      `${document.chunk_count} ${
        document.chunk_count === 1
          ? 'section'
          : 'sections'
      }`;

    if (document.page_count > 0) {
      const pages =
        `${document.page_count} ${
          document.page_count === 1
            ? 'page'
            : 'pages'
        }`;

      return `${sections} · ${pages}`;
    }

    return sections;
  }
}
