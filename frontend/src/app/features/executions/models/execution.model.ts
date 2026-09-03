export type ExecutionStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

export interface ExecutionSummary {
  readonly execution_id: string;
  readonly conversation_id: string;
  readonly agent_name: string;
  readonly status: ExecutionStatus;

  readonly request_id: string | null;
  readonly query: string | null;

  readonly route: string | null;
  readonly route_reason: string | null;
  readonly hop_count: number | null;

  readonly source_count: number;
  readonly error: string | null;

  readonly created_at: string;
  readonly started_at: string | null;
  readonly completed_at: string | null;

  readonly duration_ms: number | null;
}

export interface ExecutionListResponse {
  readonly total: number;
  readonly count: number;
  readonly limit: number;
  readonly offset: number;
  readonly executions:
    readonly ExecutionSummary[];
}

export interface WorkflowEvent {
  readonly id: string;
  readonly sequence: number;
  readonly event_type: string;
  readonly agent_name: string | null;
  readonly payload:
    Readonly<Record<string, unknown>>;
  readonly created_at: string;
}

export interface ExecutionDetail {
  readonly execution: ExecutionSummary;
  readonly input:
    Readonly<Record<string, unknown>>;
  readonly output:
    Readonly<Record<string, unknown>>;
  readonly events:
    readonly WorkflowEvent[];
}

export interface ExecutionsState {
  readonly total: number;
  readonly executions:
    readonly ExecutionSummary[];

  readonly selectedExecutionId:
    string | null;

  readonly selected:
    ExecutionDetail | null;

  readonly loading: boolean;
  readonly detailLoading: boolean;

  readonly error: string | null;
}
