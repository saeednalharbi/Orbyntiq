import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface ToolCapability {
  readonly name: string;
  readonly description: string;
  readonly detail: string;
  readonly icon: string;
}

@Component({
  selector: 'app-mcp-page',
  imports: [RouterLink],
  templateUrl: './mcp-page.html',
  styleUrl: './mcp-page.scss',
})
export class McpPage {
  readonly tools:
    readonly ToolCapability[] = [
      {
        name: 'Knowledge search',
        icon: '⌕',
        description:
          'Finds relevant information from the documents stored in your knowledge base.',
        detail:
          'RAG + Qdrant retrieval',
      },
      {
        name: 'MCP services',
        icon: '⌘',
        description:
          'Lets Orbyntiq agents access configured tools through the Model Context Protocol.',
        detail:
          'MCP transport and tools',
      },
      {
        name: 'Local AI',
        icon: '✦',
        description:
          'Runs language-model inference locally through Ollama.',
        detail:
          'qwen3:4b-instruct',
      },
      {
        name: 'Embeddings',
        icon: '◇',
        description:
          'Converts document sections into searchable semantic representations.',
        detail:
          'qwen3-embedding:0.6b',
      },
    ];
}
