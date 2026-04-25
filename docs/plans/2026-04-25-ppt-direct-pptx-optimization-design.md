# ppt-maker-direct-pptx 优化设计稿

- 日期：2026-04-25
- 范围：对 `ppt-maker-direct-pptx` 全流程的结构性优化
- 目标：让生成的 PPT 风格、布局更合理；图片按需生成；提示词布局描述更可执行；每一步确认更严格；支持自定义风格

---

## 优化主题（8 项）

1. 图片生成节奏：从一次性批处理改为可中断、可恢复、按页生成
2. 每页提示词详尽度：让 JS 渲染识别布局更稳定
3. 确认流程：现有 4 道闸基础上插入新闸，让目标用户/页数/关键内容/风格逐项强制确认
4. 风格系统：从 5 个固定预设扩展为支持自定义、生成、参考素材抽取
5. 中间预览：让用户在意图阶段就看到布局长什么样
6. 自动质量检查：把静态 checklist 升级为可机检的 lint pipeline
7. 逐页锁定：长 deck 支持局部确认与回滚
8. 风格继承/扩展：基于预设做覆盖修改

---

## §1 新流程 + 7 道闸

```
[1] 需求确认闸           ─ topic / audience / purpose / page_count / key_points 必填
                          每项必须显式逐条复述确认（不接受"嗯""可以"）
                          ↓
[2] 模板/风格选择闸      ─ 3 选 1 入口：
                          ① 选预设（5 个慧新家族 + dark-english）
                          ② 自然语言描述（"深蓝紫色赛博朋克科技风"）
                          ③ 上传参考素材（PPT / 图片 / 网页截图）
                          也支持「预设 + 覆盖字段」的继承模式
                          ↓
[3] 风格预览闸（新）     ─ 按选定风格生成：
                          ① 配色色卡
                          ② 字号示意 4 行
                          ③ Pattern 目录全量预渲染（封面 / 章节 / 双栏 / 矩阵 / KPI / 路径 / 对比 / 总结，8-12 个）
                          ④ 一张代表页真实渲染（首页或 KPI 页）
                          用户可改 master_style 任何字段，重新预览，循环到满意
                          ↓
[4] 大纲确认闸           ─ 整 deck 大纲 + 每页 outline_status，支持逐页锁定
                          locked 的页改 master_style 不会动它，除非显式 reset
                          ↓
[5] 页面意图确认闸       ─ 每页结构化 intent + per-page wireframe 预览
                          每页 intent_status，支持逐页锁定
                          schema lint + 内容 quality judge 自动跑，fail 切 needs_rework
                          ↓
[6] 图片计划闸（新）     ─ 决定每页 image_placeholder 的 status：
                          pending / skipped / placeholder / generated
                          所有页默认 placeholder（即首次渲染就是占位图）
                          ↓
[7] 渲染前总结闸（新）   ─ 全 deck 状态 dashboard + 缩略图 grid
                          布局几何 lint + 风格一致性 lint 自动跑
                          任何 fail 切 needs_rework，闸不放行
                          ↓
渲染 PPTX                ─ 首次输出全占位 deck；用户事后按页触发真图生成
```

关键变化：

- 4 道闸 → 7 道闸；每道闸都有显式触发条件和不放行规则
- 新增 3 道（[3] [6] [7]）专门解决「风格不可控 / 图片节奏不对 / 渲染前没有最后一道把关」
- 所有 per-page 闸（[4] [5] [6]）都由页级状态机驱动，支持逐页锁定 / 局部回滚

---

## §2 风格系统

三个入口都汇入同一个 `master_style.json`。

```
入口 A：选预设              入口 B：自然语言生成          入口 C：参考素材抽取
─────────────              ──────────────────          ─────────────────
template_manifest.json     用户："深蓝紫色赛博朋克"        用户上传：PPT / PNG / 网页截图
中 5 个预设之一             ↓                            ↓
                          调 text_model 生成 brief       调 vision_model：
                          ↓                              · 提取 5 色主调色板
                                                         · 识别字体气质（衬线/无衬线/手写）
                                                         · 抽取版式特征（密度/对称性/卡片化）
                                                         ↓
                          ─────────────────────────────────
                                       ↓
                          统一产出 master_style.json（结构同现有 huixin_master_style_brief.json）
                                       ↓
                          [可选] 继承覆盖：在任何入口产出后，
                          用户可改任意字段（如"主色换成 #1A237E"、"圆角改 8px"）
                                       ↓
                          → 进入 风格预览闸（gate 3）
```

`master_style.json` schema 扩展（在现有字段基础上加）：

- `source`: `preset / nl_generated / reference_extracted / hybrid`
- `parent_template_id`: 继承时记录来源（如 `huixin` + 改色）
- `lock_fields`: 哪些字段是用户手动锁定的，不允许后续 LLM 重写
- `pattern_palette`: 这套风格下 pattern 库渲染需要的额外参数（卡片阴影深浅、连接线粗细、icon 风格）
- `confidence`: NL/参考素材抽取时的置信度，低置信字段在预览闸高亮提醒人工 review

风格预览闸（gate 3）输出：

1. 色卡 panel：5-7 色，每色标注用途（关键数字 / 结构线 / 背景层…）
2. 字号阶梯 panel：4 级（page_title / section_title / body / caption）真实样字
3. Pattern 目录全量预渲染：8-12 个 pattern × 当前 master_style，每个出一张 PNG
4. 代表页真实渲染：首页或一张 KPI 页用真数据完整画一遍

触发重渲染逻辑：用户改 master_style 任何字段 → pattern catalog 全量重渲 + 代表页重渲 → 二次预览，循环到 `style_confirmed=true`。

---

## §3 Pattern 库 + 页面意图 schema

Pattern 库初稿（8-12 个，对齐现有 module_layout_patterns + 扩展）：

| Pattern ID | 用途 | 槽位 |
|---|---|---|
| `cover` | 封面 | title / subtitle / org_block / cover_visual? |
| `section_divider` | 章节分隔 | section_no / section_title / agenda_anchor? |
| `conclusion_top_modules` | 顶部结论条 + 3-4 模块 | headline / module[1-4]:{icon, title, body} |
| `two_column_compare` | 双栏对照 | left:{title, points[]} / right:{title, points[]} / verdict? |
| `four_card_matrix` | 四卡矩阵 | cell[1-4]:{label, value, desc} |
| `three_stage_path` | 三阶段路径 | stage[1-3]:{phase, title, deliverable} |
| `kpi_strip` | KPI 横条 | kpi[1-4]:{value, unit, label, trend?} |
| `architecture_layers` | 架构分层 | layer[1-N]:{name, components[]} |
| `before_after` | 前后对比 | before:{...} / after:{...} / delta_callout |
| `evidence_grid` | 证据/案例墙 | case[1-N]:{logo, headline, metric} |
| `summary_takeaways` | 总结要点 | takeaway[1-5] / next_step |
| `freeform` | 自由式兜底 | 必须填 layout_design + 12×8 栅格坐标 |

每个 pattern 在 `assets/patterns/<pattern_id>.json` 定义：

- `slots`: 槽位列表 + 每槽 `required / max_chars / min_chars / accepts_image`
- `layout_regions`: 默认 content / images / title 三区坐标（占栅格列行）
- `style_hooks`: 哪些 master_style 字段会映射到这个 pattern（卡片圆角 / 阴影 / 连线）
- `wireframe_template`: 用于 per-page wireframe 预览的轻量 SVG 模板
- `js_renderer`: 对应 PptxGenJS 渲染函数路径

页面意图（page_intent）schema 调整：

```json
{
  "page_no": 5,
  "outline_status": "locked",
  "intent_status": "pending_review",
  "pattern_id": "four_card_matrix",
  "layout_mode": "pattern",
  "slots": {
    "cell_1": { "label": "效率提升", "value": "+38%", "desc": "..." },
    "cell_2": { "...": "..." },
    "cell_3": { "...": "..." },
    "cell_4": { "...": "..." }
  },
  "core_message": "...",
  "speaker_notes": "...",
  "image_placeholders": [],
  "compiled_prompt": "..."
}
```

`layout_mode: custom` 的页则不填 `slots`，必须填原来的 `layout_design + key_blocks + grid` 字段（保留兼容）。

自动校验（gate 5 触发）：

- `pattern_id` 必须存在 / `slots` 必须满足 pattern 定义的 required 槽 / `max_chars` 不能超 → 超了切 `needs_rework`
- `compiled_prompt` 由 master_style + pattern.style_hooks + slots 自动生成，不允许人工编辑（避免 drift）

---

## §4 图片生命周期状态机

每个 `image_placeholder` 都是一台状态机：

```
                    用户在 gate 6 决定不要图
                    ┌──────────────────────────┐
                    ↓                          │
[创建 placeholder] ─→ pending ─→ skipped       │
                       │                       │
       默认进入        ↓                       │
                  placeholder ◄────────────────┘
                       │           （首次渲染：只画占位框，不调图模型）
                       ↓ 用户在交付后点"生成真实图"
                  regenerating
                       │
              ┌────────┴────────┐
       成功   ↓                 ↓ 失败
          generated        placeholder + fallback_reason
                       │            ↑
                       │            │ 用户可重试
                       └────────────┘
                       │
                       ↓ 用户对结果不满意
                  regenerating
```

状态字段定义：

```json
"image_placeholders": [
  {
    "id": "page-05-img-1",
    "status": "placeholder",
    "role": "scenario",
    "purpose": "工厂自动化场景图",
    "prompt": "A modern smart factory floor...",
    "placement": { "x": 6.5, "y": 1.2, "w": 5.5, "h": 3.8 },
    "generated_path": null,
    "fallback_reason": null,
    "history": [
      { "ts": "2026-04-25T10:30:00Z", "from": "pending", "to": "placeholder" }
    ]
  }
]
```

渲染时行为分支（`assemble_pptx.py` 改造）：

| status | 渲染动作 |
|---|---|
| `pending` | 不该出现在渲染阶段；闸口拦截 |
| `placeholder` | 画样式化占位框：灰底 + 主色描边 + 中心 icon + 半透明 prompt 文字 + role 标签 |
| `generated` | `slide.addImage(generated_path, placement)` |
| `skipped` | 不画任何东西，content region 自动重排把空间还给文本 |
| `regenerating` | 渲染时按 placeholder 处理；后台异步生成；完成后用户可触发增量替换 |

关键脚本改造：

- `generate_image_assets.py`：默认只扫 `status=pending` 的 placeholder；加 `--ids` 参数支持按页/按 id 触发；成功后状态 → `generated`，失败 → `placeholder` + `fallback_reason`
- `assemble_pptx.py`：按 status 分支渲染；status 变化不需要重新生成 JS 模块，只需要 patch 渲染参数
- 新增 `regenerate_image.py --slide N --img-id ...`：单图重生（对应 `regenerating` 状态），不重渲整 deck
- `slide_specs.json` 的 `layout_regions` 在 `skipped` 时要重计算（content 吃掉 images 的区域）

首次渲染策略：所有 image_placeholder 默认 `status=placeholder` → 用户在 gate 6 把不要图的页改 `skipped` → 渲染产出"全占位 PPTX"立即交付 → 用户事后按页调"生成真图"，不阻塞主流程。

---

## §5 页级状态机 + Dashboard

每页 3 个独立状态字段：

```
outline_status：大纲层（标题/副标题/页角色）
  draft ──→ pending_review ──→ locked
              ↑                   │
              └── needs_rework ←──┘
                  （quality lint fail / 用户主动改）

intent_status：意图层（pattern + slots + speaker_notes）
  同上四态。outline_status 必须 locked 才能进入 pending_review。

image_status：图片层（聚合所有 image_placeholder.status）
  no_image / placeholder_only / partially_generated / fully_generated / has_failures
```

关键转换规则：

| 触发事件 | 影响 |
|---|---|
| 用户改 master_style | 所有 `intent_status=locked` 的页保持 locked；`needs_rework` 的页重渲；新加的 `lock_fields` 阻止 LLM 覆盖 |
| Quality lint 报 fail | 对应页的 outline 或 intent status 自动 → `needs_rework`，附 `lint_failures: [...]` |
| 用户在 dashboard 点"重做这页" | status → `needs_rework`，触发 regenerate_single_slide |
| 用户在 gate 4/5 显式确认这页 | status → `locked` |
| LLM 重新生成一页内容 | status → `pending_review`，等用户确认 |

Dashboard（gate 7 的核心 UI，文本形式输出）：

```
PPT 状态总览（共 18 页）

  Page  Outline           Intent             Image                Lint
  ────  ────────────────  ─────────────────  ──────────────────   ──────
  01    locked            locked             no_image             pass
  02    locked            locked             placeholder_only     pass
  03    locked            locked             fully_generated      pass
  04    locked            needs_rework        placeholder_only     style:fail × 2
  05    locked            locked             has_failures         pass
  ...

风格一致性：pass
布局几何：fail（page 4：title 区与 body 区垂直重叠 0.3 inch）
内容质量：warn（page 7、page 12 核心信息可能重叠）

本闸不放行：page 4、page 7、page 12
建议下一步：
  · python scripts/regenerate_single_slide.py --page-no 4 --instruction "修正 title 与 body 重叠"
  · python scripts/lint_review.py --page 7,12  → 决定是否真要修
  · 若选 ignore，需显式 --override-lint 才放行 gate 7
```

dashboard 数据来源：`outline.json` / `slide_prompts.json` / `slide_specs.json` / `image_manifest.json` / 最新一次 `lint_report.json` 五个文件 join。

新增脚本：

- `scripts/dashboard.py path/to/job.json` —— 任意时刻打印当前 dashboard
- `scripts/lock_pages.py --pages 1,2,3 --layer intent` —— 批量锁页
- `scripts/reset_pages.py --pages 4 --layer intent` —— locked → needs_rework，强制重做

断点续做：所有状态写入 job artifacts，离开会话再回来时 `dashboard.py` 直接给出"上次到哪、还剩什么"。

---

## §6 质量 Lint Pipeline

4 类检查 + 嵌入闸口的触发位置：

```
                         Gate 4 (大纲)         Gate 5 (意图)         Gate 7 (渲染前)
                         ─────────────         ────────────          ───────────────
Schema lint              ✓ outline.schema      ✓ slide_prompts       ✓ slide_specs
                           page_count match      .schema               + image_manifest
                           dup page_no           pattern_id 存在
                           字段齐全              slots 完整 / 不超长
                                                 image_placeholder
                                                 .status 合法

Content quality (LLM)    ✓ 故事线连贯           ✓ 一页一信息
                           覆盖 key_points        内容重复检测
                                                 受众契合度

Layout geometry                                                       ✓ regions 不重叠
                                                                       卡片 ≥1.0 inch
                                                                       字号在 master_style
                                                                       范围内
                                                                       元素不出血 16:9

Style consistency                                                     ✓ 跨 deck 字号分布
                                                                       配色只用 palette
                                                                       title 区域统一
                                                                       forbidden_elements
                                                                       未被违规使用
```

`lint_report.json` 结构：

```json
{
  "ts": "2026-04-25T11:00:00Z",
  "gate": "gate_7",
  "results": [
    {
      "page_no": 4,
      "category": "layout_geometry",
      "rule": "title_body_no_overlap",
      "severity": "fail",
      "detail": "title 区 (y=0.4-1.2) 与 body 区 (y=1.0-3.5) 垂直重叠 0.2 inch",
      "auto_fixable": true
    },
    {
      "page_no": 7,
      "category": "content_quality",
      "rule": "duplicate_core_message",
      "severity": "warn",
      "detail": "core_message 与 page 12 相似度 0.83",
      "auto_fixable": false
    }
  ],
  "deck_level": [
    { "category": "style_consistency", "rule": "font_scale_unified", "severity": "pass" }
  ]
}
```

严重度 → 状态机映射：

- `fail` → 对应页 status 切 `needs_rework`，闸不放行
- `warn` → 闸放行但 dashboard 高亮，用户可显式 `--override-lint` 跳过
- `pass` → 不动

闸的强制性：

- gate 5 / gate 7 不传过 lint 不允许进入下一阶段
- 用户可以 `--override-lint` 强制跳过 warn，但 fail 不允许跳过（除非 `--force-override-lint` 加显式确认）
- 所有 override 写入 `lint_report.json` 的 `overrides` 字段，留痕

关键脚本：

- `scripts/lint_schema.py` —— 跑 schema 类检查，纯 JSON Schema
- `scripts/lint_geometry.py` —— 跑布局几何，纯几何计算（不调任何模型）
- `scripts/lint_style.py` —— 跑风格一致性，纯统计
- `scripts/lint_content.py` —— 跑内容质量，调 text_model 做 LLM judge；可 `--skip-content-judge` 关掉省成本
- `scripts/run_all_lints.py --gate gate_7` —— 闸口编排器

自动修复：`auto_fixable=true` 的 fail（如几何重叠、字号超界）支持 `scripts/auto_fix_lint.py --report lint_report.json` 一键修复，状态切 `pending_review` 等用户重审。

---

## §7 预览系统（Pattern 目录 + Per-page Wireframe）

两层预览解决两个不同的问题：

```
Pattern 目录预览 (deck-level)        Per-page Wireframe (page-level)
─────────────────                    ──────────────────
"这套风格 × 这个 pattern              "我的真实文案塞进 four_card_matrix
 长什么样"                             会不会被截断 / 排得难看"
当 master_style 变 → 整目录重渲     当某页 slots 变 → 那一页重渲
```

Pattern 目录预览：

- 位置：`artifacts/pattern_catalog/<master_style_id>/<pattern_id>.png`
- 生成时机：Gate 3 风格预览闸首次进入 → 全 12 个 pattern 用 lorem-ipsum 占位数据 + 当前 master_style 渲染 → 输出 PNG grid
- 触发重渲染：master_style 任何字段变化 → 整目录失效 → 后台重渲（缓存 key = master_style hash）
- 渲染管线：PptxGenJS 渲染单页 PPTX → LibreOffice headless 转 PNG（已有 Node + npm 依赖，新增 LibreOffice 作为可选依赖；不可用时降级为 SVG 模板预览）
- 用户视角：进入 gate 3 看到一张 4×3 的 grid，每格标 pattern 名 + 缩略图；想看哪个点开看大图

Per-page Wireframe：

- 位置：`artifacts/wireframes/page-<NN>.svg`
- 生成时机：page_intent 进入 pending_review 时 → 用 `pattern.wireframe_template` SVG 模板 + 真实 slots 数据 → 输出低保真 SVG（盒子 + 槽位标签 + 真实文案截断后预览）
- 关键：不调任何渲染引擎、不调 LibreOffice，纯 SVG 字符串拼接，毫秒级生成
- 用户视角：在 gate 5 dashboard 里每页旁边一个 wireframe 缩略图，能看到"卡片 3 的 desc 写了 80 字但槽位最多容纳 60 字"
- 与 lint 联动：wireframe 生成时同步检查 `slots.max_chars` 超限并报到 lint_report

新增脚本：

- `scripts/render_pattern_catalog.py --master-style ...` —— 全量重渲染目录
- `scripts/render_wireframe.py --page-no N` —— 单页 wireframe
- `scripts/preview_dashboard.py` —— 整 deck 的 wireframe 缩略图聚合

与其他系统的协同：

- 风格预览闸（gate 3）= 色卡 + 字号 + Pattern 目录 + 代表页
- 意图确认闸（gate 5）= 结构化 intent + Per-page wireframe + schema/content lint
- 渲染前总结闸（gate 7）= dashboard + 缩略图 grid（这次是 PptxGenJS → 真实 PNG，不是 SVG wireframe）

---

## 决策汇总表

| 主题 | 选项 | 关键产物 |
|---|---|---|
| 3 确认流程 | b | 7 道闸（新增 [3] [6] [7]） |
| 4+8 风格系统 | f | master_style.json schema 扩展 + 三入口（预设/NL/参考素材） |
| 2 提示词详尽度 | c | Pattern 库 12 个 + freeform 兜底 |
| 1 图片节奏 | e | image_placeholder 状态机（5 态） |
| 5 中间预览 | e | Pattern 目录 + Per-page wireframe |
| 7 逐页锁定 | e | 页级状态机（outline/intent/image，4 态） |
| 6 自动质量 | e | 4 类 lint + 闸口强制 + auto-fix |

---

## 新增文件结构

```
ppt-maker-direct-pptx/
├── assets/
│   ├── patterns/                              [新]
│   │   ├── cover.json
│   │   ├── section_divider.json
│   │   ├── conclusion_top_modules.json
│   │   ├── two_column_compare.json
│   │   ├── four_card_matrix.json
│   │   ├── three_stage_path.json
│   │   ├── kpi_strip.json
│   │   ├── architecture_layers.json
│   │   ├── before_after.json
│   │   ├── evidence_grid.json
│   │   ├── summary_takeaways.json
│   │   └── freeform.json
│   └── schemas/
│       ├── master_style.schema.json           [新]
│       ├── pattern.schema.json                [新]
│       └── lint_report.schema.json            [新]
├── scripts/
│   ├── dashboard.py                           [新]
│   ├── lock_pages.py                          [新]
│   ├── reset_pages.py                         [新]
│   ├── regenerate_image.py                    [新]
│   ├── render_pattern_catalog.py              [新]
│   ├── render_wireframe.py                    [新]
│   ├── preview_dashboard.py                   [新]
│   ├── style_from_nl.py                       [新]
│   ├── style_from_reference.py                [新]
│   ├── lint_schema.py                         [新]
│   ├── lint_geometry.py                       [新]
│   ├── lint_style.py                          [新]
│   ├── lint_content.py                        [新]
│   ├── run_all_lints.py                       [新]
│   ├── auto_fix_lint.py                       [新]
│   ├── generate_image_assets.py               [改] 支持状态机 + --ids
│   ├── assemble_pptx.py                       [改] 按 status 分支渲染
│   ├── run_ppt_job.py                         [改] 7 道闸编排
│   ├── sync_job_artifacts.py                  [改] 状态机感知
│   └── regenerate_single_slide.py             [改] 状态机感知
└── artifacts/
    ├── pattern_catalog/<style_hash>/*.png     [新]
    ├── wireframes/page-NN.svg                 [新]
    └── lint_report.json                       [新]
```

---

## 与现有实现的兼容策略

- 旧 `slide_prompts.json`（无 `pattern_id`）默认按 `layout_mode: custom` 处理，不强制迁移
- 旧 `image_placeholders`（无 `status`）默认 `status: placeholder`，不强制迁移
- 新增的 7 道闸默认开启，但 `run_ppt_job.py --legacy-4-gates` 可降级回旧流程
- 所有新 lint 脚本默认 strict，但 `--lint-mode loose` 可关掉新增检查
- 5 个现有预设（慧新家族 + dark-english）仍然是一等公民，作为 `source: preset` 的产物存在
