import {
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  AgentRoute,
  WorkspaceExecution,
  WorkspaceMessage,
  WorkspaceMode,
  WorkspaceSource,
  WorkspaceWorkflowEvent,
} from '../../models/workspace.model';

@Component({
  selector: 'app-workspace-conversation',
  imports: [FormsModule],
  templateUrl: './workspace-conversation.html',
  styleUrl: './workspace-conversation.scss',
})
export class WorkspaceConversation {
  @Input({ required: true })
  messages: readonly WorkspaceMessage[] = [];

  @Input({ required: true })
  mode: WorkspaceMode = 'agent';

  @Input()
  isRunning = false;

  @Input()
  error: string | null = null;

  @Input()
  execution:
    WorkspaceExecution | null = null;

  @Output()
  readonly querySubmitted =
    new EventEmitter<string>();

  @Output()
  readonly cancelRequested =
    new EventEmitter<void>();

  @Output()
  readonly resetRequested =
    new EventEmitter<void>();

  @Output()
  readonly errorDismissed =
    new EventEmitter<void>();

  readonly suggestions = [
    'Summarize my knowledge',
    'Research my documents',
    'Explain something step by step',
  ] as const;

  query = '';

  submit(): void {
    const query = this.query.trim();

    if (
      query.length === 0 ||
      this.isRunning
    ) {
      return;
    }

    this.querySubmitted.emit(query);
    this.query = '';
  }

  useSuggestion(
    suggestion: string,
  ): void {
    if (this.isRunning) {
      return;
    }

    this.query = suggestion;
  }

  handleKeydown(
    event: KeyboardEvent,
  ): void {
    if (
      event.key === 'Enter' &&
      !event.shiftKey
    ) {
      event.preventDefault();
      this.submit();
    }
  }

  eventLabel(
    event: WorkspaceWorkflowEvent,
  ): string {
    switch (event.eventType) {
      case 'execution_started':
        return 'Request received';

      case 'routing_completed':
        return this.routeCompletedLabel(
          event,
        );

      case 'agent_started':
        return event.agentName
          ? `${this.humanize(
              event.agentName,
            )} started`
          : 'AI agent started';

      case 'agent_result':
        return event.agentName
          ? `${this.humanize(
              event.agentName,
            )} finished`
          : 'Agent step completed';

      case 'execution_completed':
        return 'Answer ready';

      case 'execution_failed':
        return 'Task failed';

      default:
        return this.humanize(
          event.eventType,
        );
    }
  }

  eventDetail(
    event: WorkspaceWorkflowEvent,
  ): string | null {
    if (
      event.eventType ===
      'routing_completed'
    ) {
      const routeReason =
        event.payload['route_reason'];

      if (
        typeof routeReason === 'string'
      ) {
        return routeReason;
      }

      const route =
        this.readRoute(
          event.payload['route'],
        );

      if (route !== null) {
        return this.routeDescription(
          route,
        );
      }
    }

    const sourceCount =
      this.sourceCountFromPayload(
        event.payload,
      );

    if (sourceCount > 0) {
      return `${sourceCount} ${
        sourceCount === 1
          ? 'source'
          : 'sources'
      } found`;
    }

    return null;
  }

  currentActivity(): string {
    const execution =
      this.execution;

    if (
      execution === null ||
      execution.events.length === 0
    ) {
      return 'Starting Orbyntiq';
    }

    const latest =
      execution.events.at(-1);

    if (!latest) {
      return 'Starting Orbyntiq';
    }

    switch (latest.eventType) {
      case 'execution_started':
        return 'Choosing the best approach';

      case 'routing_completed':
        return this.routeActivity(
          execution.route ??
          this.readRoute(
            latest.payload['route'],
          ),
        );

      case 'agent_started':
        if (
          latest.agentName === 'research'
        ) {
          return 'Researching your knowledge';
        }

        if (
          latest.agentName === 'mcp'
        ) {
          return 'Using connected tools';
        }

        if (
          latest.agentName === 'general'
        ) {
          return 'Reasoning through your request';
        }

        return 'AI agent is working';

      case 'agent_result':
        return 'Preparing your answer';

      case 'execution_completed':
        return 'Answer ready';

      case 'execution_failed':
        return 'Could not complete the task';

      default:
        return 'Working on your request';
    }
  }

  currentActivityDetail(): string {
    const execution =
      this.execution;

    if (execution === null) {
      return 'Preparing the request';
    }

    if (execution.sources.length > 0) {
      return (
        `${execution.sources.length} ` +
        `${
          execution.sources.length === 1
            ? 'source'
            : 'sources'
        } found so far`
      );
    }

    if (execution.route !== null) {
      return this.routeDescription(
        execution.route,
      );
    }

    return 'Following the live agent workflow';
  }

  completedSummary(): string {
    const execution =
      this.execution;

    if (execution === null) {
      return 'Completed';
    }

    const parts = [
      'Completed',
    ];

    if (execution.route !== null) {
      parts.push(
        this.routeShortLabel(
          execution.route,
        ),
      );
    }

    if (execution.sources.length > 0) {
      parts.push(
        `${execution.sources.length} ${
          execution.sources.length === 1
            ? 'source'
            : 'sources'
        }`,
      );
    }

    return parts.join(' · ');
  }

  sourceLabel(
    source: WorkspaceSource,
  ): string {
    const fileName =
      source['file_name'];

    if (
      typeof fileName === 'string' &&
      fileName.length > 0
    ) {
      return fileName;
    }

    const citation =
      source['citation'];

    if (
      typeof citation === 'string' &&
      citation.length > 0
    ) {
      return citation;
    }

    return 'Knowledge source';
  }

  sourceMeta(
    source: WorkspaceSource,
  ): string {
    const parts: string[] = [];

    const page =
      source['page_number'];

    if (typeof page === 'number') {
      parts.push(`Page ${page}`);
    }

    const score =
      source['score'];

    if (typeof score === 'number') {
      const percentage =
        Math.round(
          Math.max(
            0,
            Math.min(
              1,
              score,
            ),
          ) * 100,
        );

      parts.push(
        `${percentage}% match`,
      );
    }

    return parts.join(' · ');
  }

  private routeCompletedLabel(
    event: WorkspaceWorkflowEvent,
  ): string {
    const route =
      this.readRoute(
        event.payload['route'],
      ) ?? this.execution?.route;

    if (route === null) {
      return 'Approach selected';
    }

    switch (route) {
      case 'research':
        return 'Research route selected';

      case 'mcp':
        return 'Tool route selected';

      case 'general':
        return 'Direct reasoning selected';
    }

    return 'Approach selected';
  }

  private routeActivity(
    route: AgentRoute | null,
  ): string {
    switch (route) {
      case 'research':
        return 'Researching your knowledge';

      case 'mcp':
        return 'Using connected tools';

      case 'general':
        return 'Reasoning through your request';

      default:
        return 'Starting the selected workflow';
    }
  }

  private routeDescription(
    route: AgentRoute,
  ): string {
    switch (route) {
      case 'research':
        return (
          'Searching indexed knowledge ' +
          'and grounding the response.'
        );

      case 'mcp':
        return (
          'Using configured tools and ' +
          'connected capabilities.'
        );

      case 'general':
        return (
          'Handling the request with ' +
          'general AI reasoning.'
        );
    }

    return 'Handling your request.';
  }

  private routeShortLabel(
    route: AgentRoute,
  ): string {
    switch (route) {
      case 'research':
        return 'Research';

      case 'mcp':
        return 'Tools';

      case 'general':
        return 'General';
    }

    return 'General';
  }

  private readRoute(
    value: unknown,
  ): AgentRoute | null {
    return value === 'research' ||
      value === 'mcp' ||
      value === 'general'
      ? value
      : null;
  }

  private sourceCountFromPayload(
    payload:
      Readonly<Record<string, unknown>>,
  ): number {
    const sources =
      payload['sources'];

    return Array.isArray(sources)
      ? sources.length
      : 0;
  }

  private humanize(
    value: string,
  ): string {
    return value
      .replaceAll('_', ' ')
      .replace(
        /\b\w/g,
        (character) =>
          character.toUpperCase(),
      );
  }
}
