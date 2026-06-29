# Schemas And Rules

## Defaults

```json
{
  "targetPlatform": "xiaohongshu",
  "durationLimitSec": 300,
  "targetDurationSec": 240,
  "aspectRatio": "9:16",
  "coverAspectRatio": "4:5",
  "outputMode": "remotion",
  "language": "zh-CN",
  "stylePreset": "orange_primary_green_secondary"
}
```

Default palette:

```json
{
  "background": "#FFFDF7",
  "primary": "#F97316",
  "secondary": "#0B5D3B",
  "primaryText": "#111111",
  "secondaryText": "#333333",
  "mutedText": "#666666",
  "cardBg": "#FFFFFF",
  "line": "#F4A261",
  "highlight": "#FF6A00"
}
```

Use orange for titles, section numbers, key arrows, highlighted concepts, flow labels, primary tags, and primary buttons. Use green for secondary icons, small structural labels, secondary lines, mascot leaf accents, and minor charts.

## BookCore

`Book2StoryboardTool` must generate `book_core.json` before the storyboard.

Required fields:

- `bookTitle`
- `bookAuthor`
- `coreProblem`
- `videoCoreQuestion`
- `coreClaim`
- `coreConcepts[]` with `name`, `explanation`, `usage`
- `visualModel` with `name`, `type`, `description`, optional `layers[]`
- `sop[]` with `step`, `title`, `action`, `output`
- `aiSkillCandidate` with `name`, `goal`, `input[]`, `output[]`, `useCases[]`

## CoverPosterPlan

Required fields:

- `projectName`
- `aspectRatio`, default `4:5`
- `title`, `headline`, `subtitle`, `badgeText`, `footerText`
- `theme`
- `layout`
- `mascot`
- `modules[]`
- `diagram`
- `tags[]`

Generate cover text with Remotion/SVG/HTML Canvas components. Use ImageGen only for mascot, texture, or illustration elements.

## Storyboard

Use `6-8` scenes. Total scene duration must be <= `durationLimitSec`.

Each scene must include:

- `sceneId`
- `title`
- `durationSec`
- `goal`
- `visualType`
- `visualDescription`
- `imageSourceStrategy`
- `onscreenText`
- `subtitle`
- `narration`
- `motion`
- `transitionIn`
- `transitionOut`
- `musicCue`
- `tts`

Mainline:

```text
现实痛点 -> 书籍核心内涵 -> 结构模型 -> SOP方法 -> AI Skill转化 -> 真实场景 -> 总结CTA
```

Narration must be short, oral, TTS-friendly, and free of long book quotes.

## Pyramid Principle Rules

When `bookTitle` contains `金字塔原理` or `Pyramid Principle`, include:

- `结论先行`: 先说答案，再展开说明。
- `以上统下`: 上层概括下层，下层支撑上层。
- `归类分组`: 同类信息放在一起，避免交叉重复。
- `逻辑递进`: 组内按照时间顺序、结构顺序或重要性顺序展开。

Visual model:

- Name: `金字塔结构`
- Type: `pyramid`
- Layers:
  - `结论 / 核心观点`
  - `分论点 / 关键理由`
  - `事实 / 数据 / 案例`

SOP:

1. 先写一句话结论
2. 拆成 2-4 个关键理由
3. 每组内容归类分组
4. 用事实、数据、案例支撑

AI Skill candidate:

- Name: `AI汇报结构生成器`
- Goal: 把杂乱材料转成清晰的金字塔汇报结构。

## Mascot Rules

Default mascot style:

- Original anthropomorphic book
- Professional, friendly, mature, minimal
- Upright book outline
- Restrained expression
- Simple line face
- Slight teaching gesture
- Warm-white cover
- Orange bookmark
- Small green leaf accent
- Transparent background when generated

Forbidden:

- Exaggerated eyes
- Children's picture-book style
- Overly cute or childish style
- Complex expression
- Existing character references
- Copied mascots
