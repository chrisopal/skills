import { ImageProvider } from './ImageProvider.js';

export class ImageGenProvider extends ImageProvider {
  constructor() {
    super('imagegen');
  }

  async generateOrSearch() {
    return { ok: false, providerName: this.name, metadata: { reason: 'adapter-not-configured' } };
  }
}
