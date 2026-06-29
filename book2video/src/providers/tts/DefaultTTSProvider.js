import { TTSProvider } from './TTSProvider.js';

export class DefaultTTSProvider extends TTSProvider {
  constructor() {
    super('tts_handoff_text');
  }

  async synthesize({ text, outputPath }) {
    return {
      ok: false,
      audioPath: outputPath,
      providerName: this.name,
      metadata: { reason: 'handoff-text-only', text }
    };
  }
}
