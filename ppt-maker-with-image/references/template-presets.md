# Template Presets

## 慧新

When the user selects `慧新`, use the following style block in Chinese as a deck-level template constraint and propagate it into every per-slide prompt.

```text
慧新这套模版的提示词，语言：中文。严格使用以下风格与配色（白底、绿色主色、Teal辅色、灰中性），信息密度高但清晰可读。

================================================
全局风格（必须严格遵守）
================================================
- 画布：16:9 横版
- 背景：纯白 #FFFFFF（允许极浅灰分区底 #F5F7FA）
- 主色（Primary Green）：#A8D86B
- 辅色（Secondary Teal）：#0F95B6
- 中性色（Neutral Gray）：#D9D9D9
- 文字主色：#1E1E1E；辅助文字：#6B7280
- 线条/分割：#E5E7EB
- 强调规则：绿色用于“关键数字/关键词/核心模块”；Teal用于“结构线/二级标题/按钮”；灰用于“背景层/分区底”
- 圆角矩形 R=14px；线条 1–1.25pt；轻阴影 5–8%黑
- 图标：线性图标统一笔画（不要3D拟物）
```

### Usage Rules

- Use this block as a deck-level style preset, not as a one-off slide note.
- Keep the whole deck in Chinese unless the user explicitly asks for another language.
- Inject the preset into:
  - master style generation
  - per-slide prompt batch generation
  - single-slide regeneration
- Preserve the color-role mapping strictly:
  - green for key numbers / keywords / core modules
  - teal for structural lines / secondary headings / buttons
  - gray for neutral backgrounds and sections
- Maintain high information density, but keep hierarchy and readability stable.

### Suggested Metadata

- template_id: `huixin`
- template_name: `慧新`
- primary_color: `#A8D86B`
- secondary_color: `#0F95B6`
- neutral_color: `#D9D9D9`
- background_color: `#FFFFFF`
- language: `zh-CN`

### Master Style Brief Template

Use the following structure as the default `master_style_brief` for `慧新`.

```json
{
  "template_id": "huixin",
  "template_name": "慧新",
  "language": "zh-CN",
  "status": "confirmed",
  "visual_positioning": "正式商务、科技咨询、白底高密度信息表达",
  "deck_voice": "理性、克制、专业、结构化，强调解决方案与管理价值",
  "color_strategy": {
    "primary_green": "#A8D86B",
    "secondary_teal": "#0F95B6",
    "neutral_gray": "#D9D9D9",
    "background": "#FFFFFF",
    "section_background": "#F5F7FA",
    "text_primary": "#1E1E1E",
    "text_secondary": "#6B7280",
    "divider": "#E5E7EB"
  },
  "typography": {
    "title_font": "Microsoft YaHei",
    "body_font": "Microsoft YaHei",
    "page_title": "36-44px, bold",
    "section_title": "24-30px, bold, teal",
    "subtitle": "18-22px, medium, gray",
    "body_text": "16-18px, regular",
    "caption": "12-14px, gray"
  },
  "title_hierarchy_rules": [
    "每页只允许一个主标题",
    "副标题只补充场景或结论，不重复主标题",
    "二级标题用于分区，不超过 2 种视觉样式",
    "关键词和数字优先用绿色强调"
  ],
  "layout_system": {
    "grid": "12-column",
    "margins": "左右 56-72px，上下 40-56px",
    "module_spacing": "20-28px",
    "module_shapes": "圆角矩形，R=14px",
    "stroke": "1-1.25pt",
    "shadow": "5-8% black"
  },
  "module_layout_patterns": [
    "单页结论 + 3-4个核心模块",
    "双栏对照",
    "四卡片矩阵",
    "三阶段路径/路线图",
    "顶部结论条 + 下方内容模块"
  ],
  "chart_rules": [
    "图表统一使用扁平化 2D 风格",
    "优先使用柱状图、折线图、矩阵图、流程图、里程碑图",
    "禁止 3D 图表、复杂渐变、重装饰背景",
    "图表主强调使用绿色，结构辅助使用 teal，网格和底层使用浅灰"
  ],
  "icon_rules": [
    "统一线性图标",
    "线条粗细一致",
    "禁止 3D 拟物图标",
    "图标仅作为信息辅助，不喧宾夺主"
  ],
  "forbidden_elements": [
    "深色大背景",
    "大面积高饱和渐变",
    "页边角随机小字",
    "花哨装饰线",
    "厚重投影",
    "3D 图表",
    "3D 拟物图标",
    "无意义纹理背景"
  ]
}
```
