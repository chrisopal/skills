import { srtTime } from './duration.js';

export function sceneToSrt(scene) {
  return `1\n${srtTime(0)} --> ${srtTime(scene.durationSec)}\n${scene.subtitle}\n`;
}
