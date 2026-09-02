import { Routes } from '@angular/router';

import { AppShell } from './layout/app-shell/app-shell';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Orbyntiq',
    loadComponent: () =>
      import(
        './features/overview/pages/overview-page/overview-page'
      ).then(
        (component) =>
          component.OverviewPage,
      ),
  },
  {
    path: '',
    component: AppShell,
    children: [
      {
        path: 'workspace',
        title: 'Ask | Orbyntiq',
        loadComponent: () =>
          import(
            './features/workspace/pages/workspace-page/workspace-page'
          ).then(
            (component) =>
              component.WorkspacePage,
          ),
      },
      {
        path: 'knowledge',
        title: 'Knowledge | Orbyntiq',
        loadComponent: () =>
          import(
            './features/knowledge/pages/knowledge-page/knowledge-page'
          ).then(
            (component) =>
              component.KnowledgePage,
          ),
      },
      {
        path: 'agents',
        title: 'Agents | Orbyntiq',
        loadComponent: () =>
          import(
            './features/agents/pages/agents-page/agents-page'
          ).then(
            (component) =>
              component.AgentsPage,
          ),
      },
      {
        path: 'executions',
        title: 'Runs | Orbyntiq',
        loadComponent: () =>
          import(
            './features/executions/pages/executions-page/executions-page'
          ).then(
            (component) =>
              component.ExecutionsPage,
          ),
      },
      {
        path: 'mcp',
        title: 'Integrations | Orbyntiq',
        loadComponent: () =>
          import(
            './features/mcp/pages/mcp-page/mcp-page'
          ).then(
            (component) =>
              component.McpPage,
          ),
      },
      {
        path: 'operations',
        title: 'Settings | Orbyntiq',
        loadComponent: () =>
          import(
            './features/operations/pages/operations-page/operations-page'
          ).then(
            (component) =>
              component.OperationsPage,
          ),
      },
    ],
  },
  {
    path: 'overview',
    redirectTo: '',
    pathMatch: 'full',
  },
  {
    path: '**',
    redirectTo: '',
  },
];
