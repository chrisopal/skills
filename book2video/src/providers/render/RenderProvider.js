export class RenderProvider {
  constructor(name) {
    this.name = name;
  }

  async render() {
    throw new Error('RenderProvider.render must be implemented by an adapter.');
  }
}
