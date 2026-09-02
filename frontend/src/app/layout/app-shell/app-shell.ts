import {
  Component,
  OnDestroy,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { RouterOutlet } from '@angular/router';

import {
  PlatformStatusService,
} from '../../core/services/platform-status.service';
import { Sidebar } from '../sidebar/sidebar';
import { Topbar } from '../topbar/topbar';

@Component({
  selector: 'app-shell',
  imports: [
    RouterOutlet,
    Sidebar,
    Topbar,
  ],
  templateUrl: './app-shell.html',
  styleUrl: './app-shell.scss',
})
export class AppShell
  implements OnInit, OnDestroy
{
  private readonly platformStatus =
    inject(PlatformStatusService);

  readonly mobileNavigationOpen =
    signal(false);

  ngOnInit(): void {
    this.platformStatus.startPolling();
  }

  ngOnDestroy(): void {
    this.platformStatus.stopPolling();
  }

  openMobileNavigation(): void {
    this.mobileNavigationOpen.set(true);
  }

  closeMobileNavigation(): void {
    this.mobileNavigationOpen.set(false);
  }
}
