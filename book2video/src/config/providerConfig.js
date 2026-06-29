export function resolveProviderConfig(env = process.env) {
  return {
    imageProvider: env.BOOK2VIDEO_IMAGE_PROVIDER || 'component_svg_fallback',
    ttsProvider: env.BOOK2VIDEO_TTS_PROVIDER || 'tts_handoff_text',
    musicProvider: env.BOOK2VIDEO_MUSIC_PROVIDER || 'music_handoff_text',
    renderProvider: env.BOOK2VIDEO_RENDER_PROVIDER || 'remotion'
  };
}
