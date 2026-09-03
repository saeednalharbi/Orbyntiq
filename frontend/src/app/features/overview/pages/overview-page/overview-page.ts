import {
  Component,
  HostListener,
  inject,
  signal,
} from '@angular/core';

import {
  ProductTransitionService,
} from '../../../../core/services/product-transition.service';

@Component({
  selector: 'app-overview-page',
  imports: [],
  templateUrl: './overview-page.html',
  styleUrl: './overview-page.scss',
})
export class OverviewPage {
  private readonly productTransition =
    inject(ProductTransitionService);

  readonly leaving =
    signal(false);

  @HostListener(
    'document:pointermove',
    ['$event'],
  )
  onPointerMove(
    event: PointerEvent,
  ): void {
    const x =
      event.clientX /
      window.innerWidth;

    const y =
      event.clientY /
      window.innerHeight;

    document.documentElement.style
      .setProperty(
        '--pointer-x',
        `${x * 100}%`,
      );

    document.documentElement.style
      .setProperty(
        '--pointer-y',
        `${y * 100}%`,
      );
  }

  enterWorkspace(): void {
    if (this.leaving()) {
      return;
    }

    this.leaving.set(true);

    void this.productTransition.navigate(
      '/workspace',
    );
  }
}
