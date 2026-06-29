import { sumSceneDuration } from './duration.js';

export function validateProjectData({ bookCore, styleBible, coverPosterPlan, storyboard }) {
  const errors = [];
  const scenes = storyboard.scenes || [];
  if (!bookCore?.bookTitle) errors.push('bookCore.bookTitle is required');
  if (!bookCore?.visualModel) errors.push('bookCore.visualModel is required');
  if (!styleBible?.visualStyle?.palette) errors.push('styleBible.visualStyle.palette is required');
  if (styleBible?.visualStyle?.palette?.primary !== '#F97316') errors.push('orange primary #F97316 is required');
  if (styleBible?.visualStyle?.palette?.secondary !== '#0B5D3B') errors.push('green secondary #0B5D3B is required');
  if (coverPosterPlan?.aspectRatio !== '4:5') errors.push('coverPosterPlan.aspectRatio must be 4:5');
  if (scenes.length < 6 || scenes.length > 8) errors.push(`storyboard scenes must be 6-8, got ${scenes.length}`);
  if (sumSceneDuration(scenes) > Number(storyboard.durationLimitSec || 300)) errors.push('storyboard duration exceeds limit');
  return errors;
}
