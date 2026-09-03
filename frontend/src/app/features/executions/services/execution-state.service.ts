import {
  HttpErrorResponse,
} from '@angular/common/http';
import {
  DestroyRef,
  Injectable,
  inject,
} from '@angular/core';
import {
  takeUntilDestroyed,
} from '@angular/core/rxjs-interop';
import {
  BehaviorSubject,
} from 'rxjs';

import {
  ExecutionsState,
} from '../models/execution.model';
import {
  ExecutionService,
} from './execution.service';

const INITIAL_STATE:
  ExecutionsState = {
    total: 0,
    executions: [],
    selectedExecutionId: null,
    selected: null,
    loading: false,
    detailLoading: false,
    error: null,
  };

@Injectable({
  providedIn: 'root',
})
export class ExecutionStateService {
  private readonly api =
    inject(ExecutionService);

  private readonly destroyRef =
    inject(DestroyRef);

  private readonly stateSubject =
    new BehaviorSubject<ExecutionsState>(
      INITIAL_STATE,
    );

  readonly state$ =
    this.stateSubject.asObservable();

  load(): void {
    if (
      this.stateSubject.value.loading
    ) {
      return;
    }

    this.patchState({
      loading: true,
      error: null,
    });

    this.api
      .list(
        100,
        0,
      )
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({
        next: (response) => {
          const currentId =
            this.stateSubject.value
              .selectedExecutionId;

          const selectedStillExists =
            currentId !== null &&
            response.executions.some(
              (execution) =>
                execution.execution_id ===
                currentId,
            );

          this.patchState({
            total: response.total,
            executions:
              response.executions,
            loading: false,
            selectedExecutionId:
              selectedStillExists
                ? currentId
                : null,
            selected:
              selectedStillExists
                ? this.stateSubject
                    .value.selected
                : null,
            error: null,
          });
        },

        error: (error: unknown) => {
          this.patchState({
            loading: false,
            error:
              this.errorMessage(
                error,
                'Unable to load execution history.',
              ),
          });
        },
      });
  }

  select(
    executionId: string,
  ): void {
    if (
      !executionId ||
      this.stateSubject.value
        .detailLoading
    ) {
      return;
    }

    if (
      this.stateSubject.value
        .selectedExecutionId ===
        executionId &&
      this.stateSubject.value.selected
    ) {
      return;
    }

    this.patchState({
      selectedExecutionId:
        executionId,
      selected: null,
      detailLoading: true,
      error: null,
    });

    this.api
      .get(executionId)
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({
        next: (detail) => {
          if (
            this.stateSubject.value
              .selectedExecutionId !==
            executionId
          ) {
            return;
          }

          this.patchState({
            selected: detail,
            detailLoading: false,
          });
        },

        error: (error: unknown) => {
          if (
            this.stateSubject.value
              .selectedExecutionId !==
            executionId
          ) {
            return;
          }

          this.patchState({
            selected: null,
            detailLoading: false,
            error:
              this.errorMessage(
                error,
                'Unable to load execution details.',
              ),
          });
        },
      });
  }

  clearSelection(): void {
    this.patchState({
      selectedExecutionId: null,
      selected: null,
      detailLoading: false,
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
      typeof error.error ===
        'object' &&
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
    changes:
      Partial<ExecutionsState>,
  ): void {
    this.stateSubject.next({
      ...this.stateSubject.value,
      ...changes,
    });
  }
}
