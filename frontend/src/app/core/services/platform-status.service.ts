import {
  HttpClient,
  HttpErrorResponse,
} from '@angular/common/http';
import {
  Injectable,
  OnDestroy,
  inject,
} from '@angular/core';
import {
  BehaviorSubject,
  Subscription,
  catchError,
  concat,
  exhaustMap,
  interval,
  of,
} from 'rxjs';

import { API_CONFIG } from '../config/api.config';
import {
  PlatformStatusResponse,
  PlatformStatusViewState,
} from '../models/platform-status.model';

export const PLATFORM_STATUS_POLL_INTERVAL_MS =
  15_000;

const INITIAL_STATE: PlatformStatusViewState = {
  data: null,
  loading: true,
  error: null,
  lastUpdated: null,
};

@Injectable({
  providedIn: 'root',
})
export class PlatformStatusService
  implements OnDestroy
{
  private readonly http = inject(HttpClient);

  private readonly stateSubject =
    new BehaviorSubject<PlatformStatusViewState>(
      INITIAL_STATE,
    );

  private pollingSubscription: Subscription | null =
    null;

  readonly state$ =
    this.stateSubject.asObservable();

  startPolling(): void {
    if (this.pollingSubscription !== null) {
      return;
    }

    const pollingTrigger$ = concat(
      of(0),
      interval(
        PLATFORM_STATUS_POLL_INTERVAL_MS,
      ),
    );

    this.pollingSubscription = pollingTrigger$
      .pipe(
        exhaustMap(() =>
          this.http
            .get<PlatformStatusResponse>(
              `${API_CONFIG.baseUrl}/platform/status`,
            )
            .pipe(
              catchError((error: unknown) => {
                this.handleError(error);
                return of(null);
              }),
            ),
        ),
      )
      .subscribe((status) => {
        if (status === null) {
          return;
        }

        this.stateSubject.next({
          data: status,
          loading: false,
          error: null,
          lastUpdated: new Date().toISOString(),
        });
      });
  }

  stopPolling(): void {
    this.pollingSubscription?.unsubscribe();
    this.pollingSubscription = null;
  }

  ngOnDestroy(): void {
    this.stopPolling();
    this.stateSubject.complete();
  }

  private handleError(
    error: unknown,
  ): void {
    let message =
      'Unable to reach the Orbyntiq platform API.';

    if (
      error instanceof HttpErrorResponse &&
      error.status !== 0
    ) {
      message =
        `Platform status request failed ` +
        `with HTTP ${error.status}.`;
    }

    this.stateSubject.next({
      ...this.stateSubject.value,
      loading: false,
      error: message,
    });
  }
}
