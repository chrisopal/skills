import { RenderProvider } from './RenderProvider.js';

export class HyperframeRenderProvider extends RenderProvider {
  constructor() {
    super('hyperframe');
  }

  async render() {
    throw new Error('Hyperframe renderer not implemented yet.');
  }
}
