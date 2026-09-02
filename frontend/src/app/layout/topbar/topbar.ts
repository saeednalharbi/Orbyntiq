import { AsyncPipe } from '@angular/common';
import {
  Component,
  EventEmitter,
  Output,
  inject,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import {
  PlatformStatusService,
} from '../../core/services/platform-status.service';

@Component({
  selector: 'app-topbar',
  imports: [
    AsyncPipe,
    RouterLink,
  ],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
})
export class Topbar {
  private readonly platformStatus =
    inject(PlatformStatusService);

  @Output()
  readonly menuRequested =
    new EventEmitter<void>();

  readonly platformState$ =
    this.platformStatus.state$;
}
