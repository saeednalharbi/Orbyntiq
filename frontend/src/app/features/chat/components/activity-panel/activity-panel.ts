import { Component, Input } from '@angular/core';

import { TokenUsage } from '../../../../core/models/llm.model';

@Component({
  selector: 'app-activity-panel',
  templateUrl: './activity-panel.html',
  styleUrl: './activity-panel.scss',
})
export class ActivityPanel {
  @Input()
  model: string | null = null;

  @Input()
  usage: TokenUsage | null = null;

  @Input()
  isLoading = false;

  @Input()
  messageCount = 0;
}
