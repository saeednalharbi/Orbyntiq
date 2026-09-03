import {
  Component,
  inject,
} from '@angular/core';
import { RouterOutlet } from '@angular/router';

import {
  ProductTransitionService,
} from './core/services/product-transition.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  readonly productTransition =
    inject(ProductTransitionService);
}
