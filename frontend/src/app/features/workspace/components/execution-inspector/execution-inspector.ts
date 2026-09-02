import {
  Component,
  Input,
} from '@angular/core';
import {
  TitleCasePipe,
} from '@angular/common';

import {
  WebSocketConnectionState,
} from '../../../../core/models/websocket.model';
import {
  WorkspaceExecution,
  WorkspaceMode,
  WorkspaceWorkflowEvent,
} from '../../models/workspace.model';

@Component({
  selector: 'app-execution-inspector',
  imports: [TitleCasePipe],
  templateUrl: './execution-inspector.html',
  styleUrl: './execution-inspector.scss',
})
export class ExecutionInspector {
  @Input({ required: true })
  mode: WorkspaceMode = 'agent';

  @Input({ required: true })
  connectionState:
    WebSocketConnectionState =
      'disconnected';

  @Input()
  execution:
    WorkspaceExecution | null = null;

  @Input()
  model: string | null = null;

  eventTitle(
    event: WorkspaceWorkflowEvent,
  ): string {
    switch (event.eventType) {
      case 'execution_started':
        return 'Started working';

      case 'routing_completed':
        return 'Chose the best approach';

      case 'agent_started':
        return event.agentName
          ? `${event.agentName} started`
          : 'AI agent started';

      case 'agent_result':
        return event.agentName
          ? `${event.agentName} finished`
          : 'AI agent finished';

      case 'execution_completed':
        return 'Finished';

      case 'execution_failed':
        return 'Could not finish';

      default:
        return event.eventType
          .replaceAll('_', ' ');
    }
  }

  eventDetail(
    event: WorkspaceWorkflowEvent,
  ): string | null {
    const routeReason =
      event.payload['route_reason'];

    if (
      typeof routeReason === 'string'
    ) {
      return routeReason;
    }

    const route =
      event.payload['route'];

    if (typeof route === 'string') {
      return `Assigned to ${route}`;
    }

    const error =
      event.payload['error'];

    if (typeof error === 'string') {
      return error;
    }

    return null;
  }
}
