import { TestBed } from '@angular/core/testing';

import {
  ExecutionInspector,
} from './execution-inspector';

describe('ExecutionInspector', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExecutionInspector],
    }).compileComponents();
  });

  it('should render the empty agent state', () => {
    const fixture =
      TestBed.createComponent(
        ExecutionInspector,
      );

    fixture.componentRef.setInput(
      'mode',
      'agent',
    );

    fixture.componentRef.setInput(
      'connectionState',
      'connected',
    );

    fixture.detectChanges();

    const element =
      fixture.nativeElement as HTMLElement;

    expect(element.textContent).toContain(
      'No active execution',
    );
  });

  it('should render execution metadata', () => {
    const fixture =
      TestBed.createComponent(
        ExecutionInspector,
      );

    fixture.componentRef.setInput(
      'mode',
      'agent',
    );

    fixture.componentRef.setInput(
      'connectionState',
      'connected',
    );

    fixture.componentRef.setInput(
      'execution',
      {
        requestId: 'request-1',
        executionId: 'execution-1',
        status: 'completed',
        route: 'research',
        routeReason:
          'Grounded retrieval required.',
        hopCount: 3,
        events: [],
        sources: [],
        errors: [],
      },
    );

    fixture.detectChanges();

    const text =
      (
        fixture.nativeElement as HTMLElement
      ).textContent;

    expect(text).toContain('Research');
    expect(text).toContain('execution-1');
    expect(text).toContain(
      'Grounded retrieval required.',
    );
  });
});
