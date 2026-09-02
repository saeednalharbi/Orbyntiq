import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface AiTeamMember {
  readonly name: string;
  readonly role: string;
  readonly description: string;
  readonly whenUsed: string;
  readonly symbol: string;
}

@Component({
  selector: 'app-agents-page',
  imports: [RouterLink],
  templateUrl: './agents-page.html',
  styleUrl: './agents-page.scss',
})
export class AgentsPage {
  readonly members:
    readonly AiTeamMember[] = [
      {
        name: 'Coordinator',
        role: 'Supervisor',
        symbol: '◎',
        description:
          'Understands your request and decides the best way for Orbyntiq to handle it.',
        whenUsed:
          'Every Smart mode task starts here.',
      },
      {
        name: 'Researcher',
        role: 'Research agent',
        symbol: '⌕',
        description:
          'Investigates questions that need information from your indexed knowledge.',
        whenUsed:
          'Used for research and document-grounded questions.',
      },
      {
        name: 'Assistant',
        role: 'General agent',
        symbol: '✦',
        description:
          'Handles general reasoning and requests that do not require specialist tools.',
        whenUsed:
          'Used for normal questions and reasoning tasks.',
      },
      {
        name: 'Tool specialist',
        role: 'MCP agent',
        symbol: '⌘',
        description:
          'Uses Orbyntiq tools and retrieval capabilities when a task needs external actions or knowledge.',
        whenUsed:
          'Used when the coordinator decides tools are required.',
      },
      {
        name: 'Response composer',
        role: 'Synthesizer',
        symbol: '◇',
        description:
          'Combines the work of the AI team into one clear final response.',
        whenUsed:
          'Finishes multi-step AI workflows.',
      },
    ];
}
