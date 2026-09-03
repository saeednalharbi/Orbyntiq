import {
  AsyncPipe,
} from '@angular/common';
import {
  Component,
  inject,
} from '@angular/core';
import {
  RouterLink,
} from '@angular/router';

import {
  PlatformStatusService,
} from '../../../../core/services/platform-status.service';

type AgentIdentity =
  | 'supervisor'
  | 'research'
  | 'general'
  | 'mcp'
  | 'synthesizer';

interface AiTeamMember {
  readonly id: AgentIdentity;
  readonly name: string;
  readonly role: string;
  readonly category: string;
  readonly description: string;
  readonly whenUsed: string;
}

@Component({
  selector: 'app-agents-page',
  imports: [
    AsyncPipe,
    RouterLink,
  ],
  templateUrl: './agents-page.html',
  styleUrl: './agents-page.scss',
})
export class AgentsPage {
  private readonly platformStatus =
    inject(PlatformStatusService);

  readonly platformState$ =
    this.platformStatus.state$;

  readonly members:
    readonly AiTeamMember[] = [
      {
        id: 'supervisor',
        name: 'Coordinator',
        role: 'Supervisor',
        category: 'Orchestration',
        description:
          'Understands each Smart mode request and chooses the specialist route that should handle it.',
        whenUsed:
          'Every Smart mode execution begins with the supervisor.',
      },
      {
        id: 'research',
        name: 'Researcher',
        role: 'Research agent',
        category: 'Knowledge',
        description:
          'Handles questions that need information from the indexed Orbyntiq knowledge base.',
        whenUsed:
          'Document research and grounded knowledge questions.',
      },
      {
        id: 'general',
        name: 'Assistant',
        role: 'General agent',
        category: 'Reasoning',
        description:
          'Handles general requests that do not require knowledge retrieval or MCP tools.',
        whenUsed:
          'General reasoning and normal AI requests.',
      },
      {
        id: 'mcp',
        name: 'Tool specialist',
        role: 'MCP agent',
        category: 'Tools',
        description:
          'Selects and uses configured MCP capabilities when a request needs an available tool.',
        whenUsed:
          'Tasks routed to Orbyntiq tools and MCP capabilities.',
      },
      {
        id: 'synthesizer',
        name: 'Response composer',
        role: 'Synthesizer',
        category: 'Composition',
        description:
          'Takes the completed specialist work and prepares the final response returned to the user.',
        whenUsed:
          'The final stage of every successful specialist route.',
      },
    ];
}
