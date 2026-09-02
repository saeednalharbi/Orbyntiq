import {
  AsyncPipe,
} from '@angular/common';
import {
  Component,
  inject,
} from '@angular/core';

import {
  ExecutionInspector,
} from '../../components/execution-inspector/execution-inspector';
import {
  WorkspaceConversation,
} from '../../components/workspace-conversation/workspace-conversation';
import {
  WorkspaceMode,
} from '../../models/workspace.model';
import {
  WorkspaceStateService,
} from '../../services/workspace-state.service';

@Component({
  selector: 'app-workspace-page',
  imports: [
    AsyncPipe,
    ExecutionInspector,
    WorkspaceConversation,
  ],
  templateUrl: './workspace-page.html',
  styleUrl: './workspace-page.scss',
})
export class WorkspacePage {
  private readonly workspace =
    inject(WorkspaceStateService);

  readonly state$ =
    this.workspace.state$;

  setMode(mode: WorkspaceMode): void {
    this.workspace.setMode(mode);
  }

  submit(query: string): void {
    this.workspace.submit(query);
  }

  cancel(): void {
    this.workspace.cancel();
  }

  reset(): void {
    this.workspace.resetConversation();
  }

  clearError(): void {
    this.workspace.clearError();
  }
}
