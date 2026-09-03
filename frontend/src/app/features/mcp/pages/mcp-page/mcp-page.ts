import {
  AsyncPipe,
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
  PlatformStatusViewState,
} from '../../../../core/models/platform-status.model';
import {
  PlatformStatusService,
} from '../../../../core/services/platform-status.service';

type McpRequirement =
  | 'platform'
  | 'retriever'
  | 'rag';

interface McpTool {
  readonly name: string;
  readonly technicalName: string;
  readonly category: string;
  readonly description: string;
  readonly requirement: McpRequirement;
  readonly inputs: readonly string[];
}

interface McpPrimitive {
  readonly type: 'Resource' | 'Prompt';
  readonly name: string;
  readonly technicalName: string;
  readonly description: string;
}

@Component({
  selector: 'app-mcp-page',
  imports: [
    AsyncPipe,
    RouterLink,
  ],
  templateUrl: './mcp-page.html',
  styleUrl: './mcp-page.scss',
})
export class McpPage
implements OnInit {
  private readonly platform =
    inject(
      PlatformStatusService,
    );

  readonly state$ =
    this.platform.state$;

  readonly tools:
    readonly McpTool[] = [
      {
        name: 'Platform status',
        technicalName:
          'platform_status',
        category: 'System',
        description:
          'Returns the current Orbyntiq MCP service state and reports whether retrieval and RAG are configured.',
        requirement: 'platform',
        inputs: [],
      },
      {
        name: 'Search knowledge',
        technicalName:
          'search_knowledge',
        category: 'Retrieval',
        description:
          'Searches the indexed Qdrant knowledge base for semantically relevant document sections.',
        requirement: 'retriever',
        inputs: [
          'query',
          'limit',
          'score threshold',
          'document filter',
        ],
      },
      {
        name: 'Answer with RAG',
        technicalName:
          'answer_with_rag',
        category: 'RAG',
        description:
          'Retrieves relevant knowledge and generates a grounded answer with source metadata.',
        requirement: 'rag',
        inputs: [
          'question',
          'limit',
          'score threshold',
          'document filter',
        ],
      },
    ];

  readonly primitives:
    readonly McpPrimitive[] = [
      {
        type: 'Resource',
        name: 'Platform information',
        technicalName:
          'orbyntiq://platform/info',
        description:
          'Exposes basic information about the Orbyntiq multi-agent platform to MCP clients.',
      },
      {
        type: 'Prompt',
        name: 'RAG assistant',
        technicalName:
          'rag_assistant',
        description:
          'Creates a grounded assistant prompt that instructs the model to answer from retrieved Orbyntiq knowledge.',
      },
    ];

  ngOnInit(): void {
    this.platform.startPolling();
  }

  mcpReady(
    state:
      PlatformStatusViewState,
  ): boolean {
    return (
      state.data?.components
        .mcp.status ===
      'healthy'
    );
  }

  retrieverReady(
    state:
      PlatformStatusViewState,
  ): boolean {
    return (
      state.data?.components
        .mcp
        .retriever_configured ??
      false
    );
  }

  ragReady(
    state:
      PlatformStatusViewState,
  ): boolean {
    return (
      state.data?.components
        .mcp
        .rag_configured ??
      false
    );
  }

  toolReady(
    tool: McpTool,
    state:
      PlatformStatusViewState,
  ): boolean {
    switch (
      tool.requirement
    ) {
      case 'platform':
        return (
          state.data !== null &&
          !state.error
        );

      case 'retriever':
        return this
          .retrieverReady(
            state,
          );

      case 'rag':
        return this.ragReady(
          state,
        );
    }
  }

  statusLabel(
    ready: boolean,
    loading: boolean,
  ): string {
    if (loading) {
      return 'Checking';
    }

    return ready
      ? 'Ready'
      : 'Unavailable';
  }
}
