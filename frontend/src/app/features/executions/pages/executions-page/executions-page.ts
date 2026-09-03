import {
  AsyncPipe,
  DatePipe,
} from '@angular/common';
import {
  Component,
  OnInit,
  inject,
} from '@angular/core';
import {
  RouterLink,
} from '@angular/router';

import {
  ExecutionDetail,
  ExecutionSummary,
  WorkflowEvent,
} from '../../models/execution.model';
import {
  ExecutionStateService,
} from '../../services/execution-state.service';

@Component({
  selector: 'app-executions-page',
  imports: [
    AsyncPipe,
    DatePipe,
    RouterLink,
  ],
  templateUrl:
    './executions-page.html',
  styleUrl:
    './executions-page.scss',
})
export class ExecutionsPage
implements OnInit {
  private readonly executions =
    inject(
      ExecutionStateService,
    );

  readonly state$ =
    this.executions.state$;

  ngOnInit(): void {
    this.executions.load();
  }

  refresh(): void {
    this.executions.load();
  }

  select(
    executionId: string,
  ): void {
    this.executions.select(
      executionId,
    );
  }

  closeDetail(): void {
    this.executions
      .clearSelection();
  }

  clearError(): void {
    this.executions.clearError();
  }

  completedCount(
    executions:
      readonly ExecutionSummary[],
  ): number {
    return executions.filter(
      (execution) =>
        execution.status ===
        'completed',
    ).length;
  }

  failedCount(
    executions:
      readonly ExecutionSummary[],
  ): number {
    return executions.filter(
      (execution) =>
        execution.status ===
        'failed',
    ).length;
  }

  activeCount(
    executions:
      readonly ExecutionSummary[],
  ): number {
    return executions.filter(
      (execution) =>
        execution.status ===
          'running' ||
        execution.status ===
          'queued',
    ).length;
  }

  statusLabel(
    status:
      ExecutionSummary['status'],
  ): string {
    switch (status) {
      case 'completed':
        return 'Completed';

      case 'failed':
        return 'Failed';

      case 'running':
        return 'Running';

      case 'queued':
        return 'Queued';
    }
  }

  routeLabel(
    route: string | null,
  ): string {
    if (!route) {
      return 'No route';
    }

    switch (route) {
      case 'research':
        return 'Research';

      case 'general':
        return 'General';

      case 'mcp':
        return 'Tools';

      default:
        return route;
    }
  }

  queryLabel(
    execution:
      ExecutionSummary,
  ): string {
    return (
      execution.query?.trim() ||
      'Untitled execution'
    );
  }

  durationLabel(
    durationMs: number | null,
  ): string {
    if (
      durationMs === null ||
      !Number.isFinite(
        durationMs,
      )
    ) {
      return '—';
    }

    if (durationMs < 1000) {
      return `${Math.round(
        durationMs,
      )} ms`;
    }

    const seconds =
      durationMs / 1000;

    if (seconds < 60) {
      return `${seconds.toFixed(
        seconds >= 10
          ? 1
          : 2,
      )} s`;
    }

    const minutes =
      Math.floor(
        seconds / 60,
      );

    const remainder =
      Math.round(
        seconds % 60,
      );

    return `${minutes}m ${remainder}s`;
  }

  eventLabel(
    event: WorkflowEvent,
  ): string {
    switch (event.event_type) {
      case 'execution_started':
        return 'Execution started';

      case 'routing_completed':
        return 'Route selected';

      case 'agent_started':
        return 'Agent started';

      case 'agent_result':
        return 'Agent completed';

      case 'execution_completed':
        return 'Execution completed';

      case 'execution_failed':
        return 'Execution failed';

      default:
        return event.event_type
          .replaceAll(
            '_',
            ' ',
          );
    }
  }

  agentLabel(
    agent: string | null,
  ): string {
    if (!agent) {
      return 'System';
    }

    switch (agent) {
      case 'supervisor':
        return 'Supervisor';

      case 'research':
        return 'Research';

      case 'general':
        return 'General';

      case 'mcp':
        return 'MCP';

      case 'synthesizer':
        return 'Synthesizer';

      default:
        return agent;
    }
  }

  finalResponse(
    detail: ExecutionDetail,
  ): string | null {
    return this.stringValue(
      detail.output[
        'final_response'
      ],
    );
  }

  sources(
    detail: ExecutionDetail,
  ): readonly Readonly<
    Record<string, unknown>
  >[] {
    const value =
      detail.output['sources'];

    if (!Array.isArray(value)) {
      return [];
    }

    return value.filter(
      (
        source,
      ): source is Readonly<
        Record<string, unknown>
      > =>
        typeof source ===
          'object' &&
        source !== null &&
        !Array.isArray(
          source,
        ),
    );
  }

  sourceName(
    source:
      Readonly<
        Record<string, unknown>
      >,
  ): string {
    return (
      this.stringValue(
        source['file_name'],
      ) ??
      this.stringValue(
        source['source_path'],
      ) ??
      this.stringValue(
        source['document_id'],
      ) ??
      'Knowledge source'
    );
  }

  sourceMeta(
    source:
      Readonly<
        Record<string, unknown>
      >,
  ): string {
    const parts: string[] = [];

    const page =
      source['page_number'];

    const score =
      source['score'];

    if (
      typeof page === 'number'
    ) {
      parts.push(
        `Page ${page}`,
      );
    }

    if (
      typeof score === 'number'
    ) {
      parts.push(
        `${Math.round(
          score * 100,
        )}% match`,
      );
    }

    return parts.join(' · ');
  }

  routingReason(
    detail: ExecutionDetail,
  ): string | null {
    return (
      detail.execution
        .route_reason ??
      null
    );
  }

  technicalJson(
    value: unknown,
  ): string {
    return JSON.stringify(
      value,
      null,
      2,
    );
  }

  private stringValue(
    value: unknown,
  ): string | null {
    if (
      typeof value !==
      'string'
    ) {
      return null;
    }

    const normalized =
      value.trim();

    return normalized ||
      null;
  }
}
