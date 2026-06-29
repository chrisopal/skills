export function buildMusicBrief(storyboard) {
  return [
    'Generate calm structured BGM for a knowledge explainer.',
    `Duration must be >= ${storyboard.targetDurationSec} seconds.`,
    'Loopable: true.',
    'Volume: 0.18.',
    'Ducking: keep narration clear.'
  ].join('\n');
}
