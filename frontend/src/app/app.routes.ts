import { Routes } from '@angular/router';

import { ChatPage } from './features/chat/components/chat-page/chat-page';
import { AppShell } from './layout/app-shell/app-shell';

export const routes: Routes = [
  {
    path: '',
    component: AppShell,
    children: [
      {
        path: '',
        component: ChatPage,
      },
    ],
  },
  {
    path: '**',
    redirectTo: '',
  },
];
