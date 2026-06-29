export function srtTime(seconds) {
  const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
  const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
  const s = String(seconds % 60).padStart(2, '0');
  return `${h}:${m}:${s},000`;
}

export function sumSceneDuration(scenes) {
  return scenes.reduce((total, scene) => total + Number(scene.durationSec || 0), 0);
}
