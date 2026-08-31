---
name: ppt-review-refinement
description: Review and refine an existing PPTX through a controlled workflow: understand topic/audience/objective, audit narrative and visual quality, obtain change approval, build pilot slides, normalize theme/color/typography/layout, refine individual slides and imagery, then render and validate the result while protecting content and editability.
version: 1.1.0
language: zh-CN
---

# PPT Review & Refinement Skill

用于对**已经创建好的 PPTX**进行系统化评审、规范化和精修。重点不是“一键换模板”，而是先理解业务目标，再通过受控流程提高叙事清晰度、视觉一致性、专业度和可读性。

## 适用场景

- 公司介绍、售前解决方案、项目汇报、战略规划、投标汇报、产品介绍、培训课件。
- 需要统一主题风格、配色、字体、字号、布局、间距、图表、架构图和配图。
- 需要在不误改数据、名称、页面顺序和业务含义的前提下优化现有演示文稿。

## 不适用场景

- 从零创作完整 PPT：应改用专门的演示文稿创作流程。
- 旧 `.ppt` 二进制格式：先转换为 `.pptx`。
- 需要完整保留复杂 VBA、ActiveX、嵌入对象或高度复杂动画的文件：必须采用保守模式并人工复核。

## 不可违反的原则

1. **先评审，后修改。** 未进入 `APPROVED` 状态，不执行内容重构或深度视觉修改。
2. **先统一系统，再逐页美化。** 顺序固定为：主题 → 配色 → 字体 → 网格与间距 → 组件 → 单页精修 → 配图。
3. **内容修改与视觉修改分开授权。** 标题改写、正文改写、页面重排、页面拆分合并、配图替换必须由 `change_manifest.json` 明确授权。
4. **保护业务事实。** 金额、日期、百分比、单位、型号、客户名称、产品名称、指标、来源不得无授权改变。
5. **保持可编辑。** 优先保留文本、表格、图表、流程图和架构图的可编辑性，避免整页栅格化。
6. **样板确认后再批量执行。** L2/L3 优化先制作 2–3 页样板。
7. **每轮编辑后必须渲染检查。** 结构检查不能替代视觉检查。
8. **配图替换遵循授权边界。** 工厂实景、产品照片、真实案例、技术架构和数据图表不得用泛化 AI 图片替代。

## 状态机

```text
INGESTED   已读取源文件
REVIEWED   已完成定位、叙事和视觉评审
APPROVED   已确认优化范围和保护边界
PILOTED    已完成并确认样板页
EXECUTED   已完成全稿优化
VALIDATED  已完成内容、视觉和技术校验
DELIVERED  已交付优化版和报告
```

状态不得跳跃，但有两个例外：

- L0 仅评审：`INGESTED → REVIEWED → DELIVERED`
- 已提供完整 `change_manifest.json` 且仅执行 L1：允许 `REVIEWED → APPROVED → EXECUTED`

## 优化等级

| 等级 | 名称 | 允许动作 |
|---|---|---|
| L0 | 仅评审 | 输出定位判断、叙事问题、视觉问题、逐页清单，不修改文件 |
| L1 | 规范化 | 统一主题、颜色映射、字体、标题位置、基础间距和组件样式；不改正文、不重排页面 |
| L2 | 结构优化 | 在 L1 基础上调整布局、信息层级、图文关系、图表样式、架构表达；先做样板 |
| L3 | 深度精修 | 允许按授权改写标题、重构部分页面、调整叙事顺序、替换配图、重画复杂图形；先做样板 |

默认：**L0 先行；L1 可在明确授权后执行；L2/L3 必须样板确认。**

## 标准工作流

### 1. 建立评审资料包

```bash
python scripts/create_review_bundle.py input.pptx --out work/review_bundle
```

输出：

- `analysis.json`：结构、字体、字号、颜色、版式、图片和几何问题。
- `structural_audit.md`：可读的结构审计摘要。
- `slides/`：逐页渲染图。
- `montage.png`：整稿缩略图总览。
- `deck_context.json`、`change_manifest.json`、`style_tokens.json` 模板。

若无法渲染，仍可完成结构审计，但不得宣称视觉检查已完成。

### 2. 判断定位

读取源文件文本、页面缩略图和用户上下文，生成 `deck_context.json`：

- PPT 类型、主题、目标观众、使用场景、沟通目标。
- 希望观众记住的一句话。
- 建议表达气质和品牌约束。
- 每项推断的置信度及待确认假设。

使用 `prompts/profile_analyzer.md`。

### 3. 双线评审

**叙事评审**：使用 `prompts/narrative_reviewer.md` 和 `rules/narrative_rules.yaml`。

- 整体故事线、章节顺序、论据链、重复、跳跃、结论缺失。
- 每页角色、核心结论、信息密度、是否需要删减/拆分/合并/前移。

**视觉评审**：使用 `prompts/visual_auditor.md` 和 `rules/visual_audit_rules.yaml`。

- 主题、配色、字体、信息层级、布局、间距、图形、图表、配图、技术质量。
- 每个问题必须包含页码、类别、严重级别、风险、建议动作和是否需要授权。

评审输出必须符合 `schemas/review_report.schema.json`。

### 4. 生成并确认变更授权

根据评审结果填写 `change_manifest.json`。至少明确：

- 正文、标题、页面顺序、拆分合并是否允许修改。
- 主题、配色、字体、布局、图表、架构图、配图的处理权限。
- 是否保留动画、链接、备注、母版、图表可编辑性。
- 受保护术语、数字和页面。

未经授权的动作只能列为建议，不能执行。

### 5. 建立设计系统

生成 `style_tokens.json`，内容至少包括：

- 主色、辅助色、强调色、背景、表面色、主文字、次文字、语义色。
- 中英文字体、封面标题、章节标题、页面标题、正文、数据、注释、页脚字号与字重。
- 页面安全边距、标题区、内容区、页脚区、标准栏宽和间距标尺。
- 卡片圆角、描边、阴影、箭头、图标、图片蒙版、页码等组件规则。
- 适用的页面原型。

使用 `prompts/style_system_builder.md`。

### 6. 制作样板页

L2/L3 从以下页面中选择 2–3 页：

- 封面或章节页。
- 普通图文页。
- 架构图、流程图、表格或数据页。

样板必须覆盖主要设计语言，并生成前后对比。用户确认后状态进入 `PILOTED`。

### 7. 执行优化

执行顺序不可更改：

1. 主题一致性。
2. 配色一致性。
3. 字体与字号体系。
4. 页面网格、页边距、标题区和基础间距。
5. 卡片、线条、箭头、图标、页脚等组件。
6. 逐页信息层级和布局。
7. 图表、表格、流程和架构图。
8. 配图裁切、色调、替换或生成。

L1 可使用：

```bash
python scripts/normalize_pptx.py input.pptx output.pptx \
  --tokens work/style_tokens.json \
  --manifest work/change_manifest.json \
  --log work/normalization_log.json
```

此脚本只执行低风险、明确配置的规范化动作。L2/L3 由 `scripts/execute_refinement_plan.py` 按 `refinement_plan.json` 逐页实施。执行器只接受已批准的 `change_manifest.json`、已确认的 `pilot_confirmation.json`，并只执行白名单动作：几何位置、标题框、字体角色、填充色、线条色和明确授权的标题文本。图表、SmartArt、动画、嵌入对象、图片替换和 `.pptm` 仍必须转交具备相应 PowerPoint/OOXML/Office API 能力的外部执行器。

叙事和视觉输入可由外部 Agent 生成，再使用 `scripts/compose_review_report.py` 合并为并通过 Schema 校验的 `review_report.json`。该脚本不替代叙事判断或视觉判断，只负责结构化编排和契约校验。

### 8. 渲染与验证

```bash
python scripts/validate_pptx.py \
  --original input.pptx \
  --candidate output.pptx \
  --manifest work/change_manifest.json \
  --out work/validation
```

最终验证必须提供人工创建并批准的 `visual_signoff.json`：

```bash
python scripts/confirm_visual_review.py \
  --signoff work/visual_signoff.json \
  --source input.pptx \
  --candidate output.pptx

python scripts/validate_pptx.py \
  --original input.pptx \
  --candidate output.pptx \
  --manifest work/change_manifest.json \
  --visual-signoff work/visual_signoff.json \
  --out work/validation
```

校验包括：

- 页数、顺序、正文、数字、日期、单位和受保护术语。
- 文本溢出、重叠、越界、异常字体、颜色漂移、低分辨率图片。
- 标题位置、页边距和设计 Token 一致性。
- 文件可打开、对象可编辑、图表/链接/动画保留情况。

最终文件必须再次渲染，逐页检查，并由人工填写 `templates/visual_signoff.template.json`。发现问题则回到 `EXECUTED` 修正，直至 `VAL-VISUAL-SIGNOFF` 通过。

## 页面原型

优先从 `rules/page_archetypes.yaml` 选择，不要把所有页面机械改成卡片：

- 封面、目录、章节、观点、图文、双栏、三栏。
- 对比、流程、时间轴、架构、数据图表、案例、路线图、总结、结束页。

## 配图决策

按四级处理：

1. 保留：语义和质量均合适，仅对齐。
2. 优化：裁切、比例、圆角、蒙版、明暗和色调统一。
3. 替换：低清、无关、风格冲突、带水印或不符合场景，且已授权。
4. 重绘/生成：适合封面概念图和抽象场景；流程、架构、数据图表应优先重绘为可编辑矢量对象。

详见 `rules/image_policy.md`。

## 输出契约

一次完整交付至少包含：

```text
optimized.pptx
review_report.json
review_report.md
change_manifest.json
style_tokens.json
validation_report.json
validation_report.md
change_log.json
before_after/（L2/L3）
```

## 失败与降级策略

- PPTX 损坏：停止编辑，报告具体解析错误并保留原文件。
- 渲染失败：只输出结构审计，并明确“视觉审计未完成”。
- SmartArt、复杂图表、嵌入对象、VBA：默认保守处理，不擅自重建。
- 字体缺失：记录替代风险，不打包或分发字体文件。
- 找不到合适配图：保留原图并标注建议，不用低相关图片凑数。
- 无法验证某类对象：标记为 `manual_review_required`，不得声明全部通过。

## 推荐阅读顺序

1. `workflows/00_orchestration.md`
2. `workflows/01_intake_profile.md`
3. `workflows/02_review.md`
4. `workflows/03_approval_pilot.md`
5. `workflows/04_normalize.md`
6. `workflows/05_refine_images.md`
7. `workflows/06_validate_deliver.md`
8. 相关 `rules/`、`prompts/` 和 `schemas/`
