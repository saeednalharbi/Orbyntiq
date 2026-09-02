import {
  AsyncPipe,
} from '@angular/common';
import {
  Component,
  EventEmitter,
  Output,
  inject,
} from '@angular/core';
import {
  RouterLink,
  RouterLinkActive,
} from '@angular/router';

import {
  PlatformStatusService,
} from '../../core/services/platform-status.service';

interface NavigationItem {
  readonly label: string;
  readonly route: string;
  readonly icon:
    | 'workspace'
    | 'agents'
    | 'knowledge'
    | 'executions'
    | 'mcp'
    | 'operations';
}

@Component({
  selector: 'app-sidebar',
  imports: [
    AsyncPipe,
    RouterLink,
    RouterLinkActive,
  ],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
})
export class Sidebar {
  private readonly platformStatus =
    inject(PlatformStatusService);

  @Output()
  readonly navigationRequested =
    new EventEmitter<void>();

  readonly platformState$ =
    this.platformStatus.state$;

  readonly primaryNavigation:
    readonly NavigationItem[] = [
      {
        label: 'Ask',
        route: '/workspace',
        icon: 'workspace',
      },
      {
        label: 'Knowledge',
        route: '/knowledge',
        icon: 'knowledge',
      },
      {
        label: 'Agents',
        route: '/agents',
        icon: 'agents',
      },
      {
        label: 'Runs',
        route: '/executions',
        icon: 'executions',
      },
    ];

  readonly secondaryNavigation:
    readonly NavigationItem[] = [
      {
        label: 'Integrations',
        route: '/mcp',
        icon: 'mcp',
      },
      {
        label: 'Settings',
        route: '/operations',
        icon: 'operations',
      },
    ];

  onNavigate(): void {
    this.navigationRequested.emit();
  }
}
