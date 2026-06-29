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

## BookResearch

`Book2StoryboardTool` must generate `book_research.json` before final shot design.

Recommended fields:

- `bookTitle`
- `bookSubtitle`
- `bookAuthor`
- `publishedYear`
- `publisher`
- `researchSummary[]`
- `visualFacts[]`
- `sourceNotes[]` with `label`, `url`, `note`

Use this research to design imagegen prompts for book-object shots, author/context shots, real-world scenarios, and visual metaphors.

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

## Imagegen Defaults

The default image provider is the built-in `imagegen` plugin.

Every full project should include:

- `imagegen_prompts.json`
- `imagegen_sources/`
- `asset_manifest.json.imageProvider.default = "imagegen"`
- project-bound image target paths for selected imagegen outputs

Do not leave project-referenced imagegen assets only under `$CODEX_HOME/generated_images/...`. Copy selected outputs into the book project directory. Component-rendered PNGs may remain as deterministic fallback frames.

Imagegen should generate the visual subject for every storyboard scene. It should not be asked to render reliable long Chinese copy; final Chinese titles, captions, and labels are applied by the composition layer.

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

## Project Output Directory

Each book must have one durable project directory. Default root:

```text
book2videoskill/projects/<book-slug>/
```

Do not create book projects under `/tmp`. Generated project folders are local artifacts and are excluded from git by default.

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

## Principles Rules

When `bookTitle` is `原则` or contains `Principles`, include:

- `极度求真`: 把现实看清楚，比维护面子更重要。
- `极度透明`: 让关键事实和分歧被看见。
- `创意择优`: 让最好想法胜出。
- `痛苦 + 反思 = 进步`: 把挫败感变成下一次行动规则。
- `可信度加权决策`: 更重视有经验、有记录、能解释判断的人。

Visual model:

- Name: `原则操作系统反馈环`
- Type: `flywheel`
- Layers:
  - `目标与现实`
  - `问题与根因`
  - `原则与决策`
  - `执行与复盘`

AI Skill candidate:

- Name: `AI原则复盘教练`
- Goal: 把失败记录、项目复盘或决策分歧转成可执行的个人/团队原则。

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
