import {
  AsyncPipe,
  TitleCasePipe,
} from '@angular/common';
import {
  Component,
  OnInit,
  inject,
} from '@angular/core';

import {
  PlatformComponentState,
  PlatformStatusViewState,
} from '../../../../core/models/platform-status.model';
import {
  PlatformStatusService,
} from '../../../../core/services/platform-status.service';

@Component({
  selector: 'app-operations-page',
  imports: [
    AsyncPipe,
    TitleCasePipe,
  ],
  templateUrl: './operations-page.html',
  styleUrl: './operations-page.scss',
})
export class OperationsPage
implements OnInit {
  private readonly platform =
    inject(
      PlatformStatusService,
    );

  readonly state$ =
    this.platform.state$;

  ngOnInit(): void {
    this.platform.startPolling();
  }

  isHealthy(
    status:
      PlatformComponentState |
      undefined,
  ): boolean {
    return (
      status === 'healthy' ||
      status === 'configured'
    );
  }

  overallReady(
    state:
      PlatformStatusViewState,
  ): boolean {
    return (
      state.data?.status ===
      'healthy'
    );
  }

  statusText(
    status:
      PlatformComponentState |
      undefined,
    loading: boolean,
  ): string {
    if (loading) {
      return 'Checking';
    }

    if (!status) {
      return 'Unavailable';
    }

    switch (status) {
      case 'healthy':
        return 'Healthy';

      case 'configured':
        return 'Configured';

      case 'degraded':
        return 'Degraded';

      case 'disabled':
        return 'Disabled';

      case 'unavailable':
        return 'Unavailable';
    }
  }
}
