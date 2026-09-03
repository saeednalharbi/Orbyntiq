import {
  HttpClient,
  HttpParams,
} from '@angular/common/http';
import {
  Injectable,
  inject,
} from '@angular/core';
import {
  Observable,
} from 'rxjs';

import {
  API_CONFIG,
} from '../../../core/config/api.config';
import {
  ExecutionDetail,
  ExecutionListResponse,
} from '../models/execution.model';

@Injectable({
  providedIn: 'root',
})
export class ExecutionService {
  private readonly http =
    inject(HttpClient);

  list(
    limit = 100,
    offset = 0,
  ): Observable<ExecutionListResponse> {
    const params =
      new HttpParams()
        .set(
          'limit',
          limit,
        )
        .set(
          'offset',
          offset,
        );

    return this.http
      .get<ExecutionListResponse>(
        API_CONFIG.executions.list,
        {
          params,
        },
      );
  }

  get(
    executionId: string,
  ): Observable<ExecutionDetail> {
    return this.http.get<ExecutionDetail>(
      API_CONFIG.executions.detail(
        executionId,
      ),
    );
  }
}
