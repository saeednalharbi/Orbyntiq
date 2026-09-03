import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  ViewChild,
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
export class WorkspaceConversation
implements AfterViewInit, OnChanges {
  @ViewChild('messageStream')
  private readonly messageStream?:
    ElementRef<HTMLDivElement>;

  @ViewChild('composerInput')
  private readonly composerInput?:
    ElementRef<HTMLTextAreaElement>;

  @Input({ required: true })
  messages:
    readonly WorkspaceMessage[] = [];

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
  readonly modeRequested =
    new EventEmitter<WorkspaceMode>();

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
    {
      title: 'Summarize my knowledge',
      detail: 'Get the key ideas from your documents',
    },
    {
      title: 'Research my documents',
      detail: 'Find grounded answers with sources',
    },
    {
      title: 'Explain something step by step',
      detail: 'Break a complex topic into clear steps',
    },
  ] as const;

  query = '';

  ngAfterViewInit(): void {
    this.focusComposer();
  }

  ngOnChanges(
    changes: SimpleChanges,
  ): void {
    if (
      changes['messages'] ||
      changes['execution'] ||
      changes['isRunning']
    ) {
      this.scrollToLatest();
    }
  }

  setMode(
    mode: WorkspaceMode,
  ): void {
    if (
      this.isRunning ||
      mode === this.mode
    ) {
      return;
    }

    this.modeRequested.emit(mode);
    this.focusComposer();
  }

  submit(): void {
    const query =
      this.query.trim();

    if (
      query.length === 0 ||
      this.isRunning
    ) {
      return;
    }

    this.querySubmitted.emit(query);
    this.query = '';
    this.scrollToLatest();
  }

  useSuggestion(
    suggestion: string,
  ): void {
    if (this.isRunning) {
      return;
    }

    this.query = suggestion;
    this.focusComposer();
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
        event.payload[
          'route_reason'
        ];

      if (
        typeof routeReason ===
        'string'
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
      return (
        `${sourceCount} ` +
        (
          sourceCount === 1
            ? 'source found'
            : 'sources found'
        )
      );
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
          latest.agentName ===
          'research'
        ) {
          return 'Researching your knowledge';
        }

        if (
          latest.agentName ===
          'mcp'
        ) {
          return 'Using connected tools';
        }

        if (
          latest.agentName ===
          'general'
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

    if (
      execution.sources.length > 0
    ) {
      return (
        `${execution.sources.length} ` +
        (
          execution.sources.length === 1
            ? 'source found'
            : 'sources found'
        )
      );
    }

    if (
      execution.route !== null
    ) {
      return this.routeDescription(
        execution.route,
      );
    }

    return 'Following the live AI workflow';
  }

  completedSummary(): string {
    const execution =
      this.execution;

    if (execution === null) {
      return 'Completed';
    }

    const parts = ['Completed'];

    if (
      execution.route !== null
    ) {
      parts.push(
        this.routeShortLabel(
          execution.route,
        ),
      );
    }

    if (
      execution.sources.length > 0
    ) {
      parts.push(
        `${execution.sources.length} ` +
        (
          execution.sources.length === 1
            ? 'source'
            : 'sources'
        ),
      );
    }

    return parts.join(
      ' \u00B7 ',
    );
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
      parts.push(
        `Page ${page}`,
      );
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

    return parts.join(
      ' \u00B7 ',
    );
  }

  private routeCompletedLabel(
    event: WorkspaceWorkflowEvent,
  ): string {
    const route =
      this.readRoute(
        event.payload['route'],
      ) ??
      this.execution?.route;

    switch (route) {
      case 'research':
        return 'Research selected';

      case 'mcp':
        return 'Connected tools selected';

      case 'general':
        return 'General reasoning selected';

      default:
        return 'Approach selected';
    }
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
          'Searching your indexed knowledge ' +
          'for relevant information'
        );

      case 'mcp':
        return (
          'Working with your connected ' +
          'tools and capabilities'
        );

      case 'general':
        return (
          'Using general AI reasoning ' +
          'for this request'
        );
    }
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
      Readonly<
        Record<string, unknown>
      >,
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

  private focusComposer(): void {
    queueMicrotask(() => {
      this.composerInput
        ?.nativeElement
        .focus();
    });
  }

  private scrollToLatest(): void {
    queueMicrotask(() => {
      const element =
        this.messageStream
          ?.nativeElement;

      if (!element) {
        return;
      }

      element.scrollTop =
        element.scrollHeight;
    });
  }
}
