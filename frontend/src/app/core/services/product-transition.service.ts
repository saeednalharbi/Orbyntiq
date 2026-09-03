import {
  Injectable,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';

export type ProductTransitionPhase =
  | 'idle'
  | 'entering'
  | 'switching'
  | 'revealing';

@Injectable({
  providedIn: 'root',
})
export class ProductTransitionService {
  readonly phase =
    signal<ProductTransitionPhase>(
      'idle',
    );

  private running = false;

  constructor(
    private readonly router: Router,
  ) {}

  async navigate(
    url: string,
  ): Promise<void> {
    if (this.running) {
      return;
    }

    const reducedMotion =
      window.matchMedia(
        '(prefers-reduced-motion: reduce)',
      ).matches;

    if (reducedMotion) {
      await this.router.navigateByUrl(url);
      return;
    }

    this.running = true;

    this.phase.set('entering');

    await this.wait(240);

    this.phase.set('switching');

    await this.wait(120);

    await this.router.navigateByUrl(url);

    this.phase.set('revealing');

    await this.wait(430);

    this.phase.set('idle');
    this.running = false;
  }

  private wait(
    milliseconds: number,
  ): Promise<void> {
    return new Promise((resolve) => {
      window.setTimeout(
        resolve,
        milliseconds,
      );
    });
  }
}
