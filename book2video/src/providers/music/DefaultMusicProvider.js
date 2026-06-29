import { MusicProvider } from './MusicProvider.js';

export class DefaultMusicProvider extends MusicProvider {
  constructor() {
    super('music_handoff_text');
  }

  async generate({ durationSec, outputPath }) {
    return {
      ok: false,
      musicPath: outputPath,
      durationSec,
      providerName: this.name,
      metadata: { reason: 'handoff-text-only' }
    };
  }
}
