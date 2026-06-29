import { ImageProvider } from './ImageProvider.js';

export class CodexImagePluginProvider extends ImageProvider {
  constructor() {
    super('codex_image_plugin');
  }

  async generateOrSearch() {
    return { ok: false, providerName: this.name, metadata: { reason: 'adapter-not-configured' } };
  }
}
