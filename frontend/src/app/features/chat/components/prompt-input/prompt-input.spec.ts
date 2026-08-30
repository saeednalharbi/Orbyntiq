import { TestBed } from '@angular/core/testing';

import { PromptInput } from './prompt-input';

describe('PromptInput', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PromptInput],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(PromptInput);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should emit a trimmed prompt and clear the input', () => {
    const fixture = TestBed.createComponent(PromptInput);
    const component = fixture.componentInstance;

    let emittedPrompt: string | undefined;

    component.promptSubmit.subscribe((prompt) => {
      emittedPrompt = prompt;
    });

    component.prompt = '  Hello Orbyntiq  ';
    component.submitPrompt();

    expect(emittedPrompt).toBe('Hello Orbyntiq');
    expect(component.prompt).toBe('');
  });

  it('should not emit an empty prompt', () => {
    const fixture = TestBed.createComponent(PromptInput);
    const component = fixture.componentInstance;

    let emissionCount = 0;

    component.promptSubmit.subscribe(() => {
      emissionCount += 1;
    });

    component.prompt = '   ';
    component.submitPrompt();

    expect(emissionCount).toBe(0);
  });

  it('should not emit while disabled', () => {
    const fixture = TestBed.createComponent(PromptInput);
    const component = fixture.componentInstance;

    let emissionCount = 0;

    component.promptSubmit.subscribe(() => {
      emissionCount += 1;
    });

    component.prompt = 'Hello';
    component.disabled = true;
    component.submitPrompt();

    expect(emissionCount).toBe(0);
  });
});
