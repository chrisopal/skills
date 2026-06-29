export class TTSProvider {
  constructor(name) {
    this.name = name;
  }

  async synthesize() {
    throw new Error('TTSProvider.synthesize must be implemented by an adapter.');
  }
}
