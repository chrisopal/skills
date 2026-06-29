export class ImageProvider {
  constructor(name) {
    this.name = name;
  }

  async generateOrSearch() {
    throw new Error('ImageProvider.generateOrSearch must be implemented by an adapter.');
  }
}
