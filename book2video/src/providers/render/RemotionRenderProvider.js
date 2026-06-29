import { RenderProvider } from './RenderProvider.js';

export class RemotionRenderProvider extends RenderProvider {
  constructor() {
    super('remotion');
  }

  async render() {
    return { ok: false, providerName: this.name, metadata: { reason: 'remotion-template-only' } };
  }
}
