import { TestBed } from '@angular/core/testing';

import {
  WorkspaceConversation,
} from './workspace-conversation';

describe('WorkspaceConversation', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkspaceConversation],
    }).compileComponents();
  });

  it('should emit a trimmed query', () => {
    const fixture =
      TestBed.createComponent(
        WorkspaceConversation,
      );

    const component =
      fixture.componentInstance;

    let emitted: string | undefined;

    component.querySubmitted.subscribe(
      (query) => {
        emitted = query;
      },
    );

    component.query =
      '  Research Orbyntiq  ';

    component.submit();

    expect(emitted).toBe(
      'Research Orbyntiq',
    );

    expect(component.query).toBe('');
  });

  it('should not submit while running', () => {
    const fixture =
      TestBed.createComponent(
        WorkspaceConversation,
      );

    const component =
      fixture.componentInstance;

    let count = 0;

    component.querySubmitted.subscribe(
      () => {
        count += 1;
      },
    );

    component.query = 'Test';
    component.isRunning = true;

    component.submit();

    expect(count).toBe(0);
  });
});
