import { Injectable, inject } from '@angular/core';
import {
  HttpClient,
  HttpEvent,
  HttpHeaders,
  HttpParams,
} from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/config/api.config';
import {
  KnowledgeDocumentsResponse,
  KnowledgeIngestResponse,
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
  KnowledgeStatus,
} from '../models/knowledge.model';

@Injectable({
  providedIn: 'root',
})
export class KnowledgeService {
  private readonly http =
    inject(HttpClient);

  getStatus(): Observable<KnowledgeStatus> {
    return this.http.get<KnowledgeStatus>(
      API_CONFIG.knowledge.status,
    );
  }

  getDocuments():
    Observable<KnowledgeDocumentsResponse> {
    return this.http.get<KnowledgeDocumentsResponse>(
      API_CONFIG.knowledge.documents,
    );
  }

  search(
    request: KnowledgeSearchRequest,
  ): Observable<KnowledgeSearchResponse> {
    return this.http.post<KnowledgeSearchResponse>(
      API_CONFIG.knowledge.search,
      request,
    );
  }

  ingest(
    file: File,
  ): Observable<HttpEvent<KnowledgeIngestResponse>> {
    const params = new HttpParams().set(
      'file_name',
      file.name,
    );

    return this.http.post<KnowledgeIngestResponse>(
      API_CONFIG.knowledge.ingest,
      file,
      {
        params,
        headers: new HttpHeaders({
          'Content-Type':
            'application/octet-stream',
        }),
        observe: 'events',
        reportProgress: true,
      },
    );
  }
}
