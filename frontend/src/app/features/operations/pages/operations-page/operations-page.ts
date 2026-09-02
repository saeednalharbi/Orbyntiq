import { Component } from '@angular/core';

interface SystemCapability {
  readonly name: string;
  readonly purpose: string;
  readonly technology: string;
  readonly status: string;
}

@Component({
  selector: 'app-operations-page',
  imports: [],
  templateUrl: './operations-page.html',
  styleUrl: './operations-page.scss',
})
export class OperationsPage {
  readonly capabilities:
    readonly SystemCapability[] = [
      {
        name: 'AI runtime',
        purpose:
          'Runs Orbyntiq language-model responses locally.',
        technology:
          'Ollama · qwen3:4b-instruct',
        status:
          'Managed locally',
      },
      {
        name: 'Knowledge search',
        purpose:
          'Stores and retrieves semantic document knowledge.',
        technology:
          'Qdrant · qwen3-embedding:0.6b',
        status:
          'Vector storage',
      },
      {
        name: 'Fast memory',
        purpose:
          'Stores temporary sessions, state, and cached data.',
        technology:
          'Redis',
        status:
          'Runtime state',
      },
      {
        name: 'Persistent data',
        purpose:
          'Stores users, conversations, executions, and workflow history.',
        technology:
          'MongoDB',
        status:
          'Persistent storage',
      },
      {
        name: 'Monitoring',
        purpose:
          'Collects metrics and distributed tracing data.',
        technology:
          'Prometheus · Grafana · Tempo · OpenTelemetry',
        status:
          'Observability',
      },
    ];
}
