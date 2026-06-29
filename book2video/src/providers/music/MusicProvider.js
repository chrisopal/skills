export class MusicProvider {
  constructor(name) {
    this.name = name;
  }

  async generate() {
    throw new Error('MusicProvider.generate must be implemented by an adapter.');
  }
}
