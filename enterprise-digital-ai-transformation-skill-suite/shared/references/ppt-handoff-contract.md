# PPT Handoff Contract

## 原则

`transformation-storyline-builder` 负责“讲什么”；外部 PPT Skill 负责“怎么呈现”。

默认推荐渲染器为 `ppt-master-plus` 的 `Generate PPTX` 路线。它是可替换实现，不属于咨询方法论本体；更换渲染器不得改变本契约。

## Slide Content Pack 最小字段

- `deck_id`, `version`, `purpose`, `audience`, `decisions_required`；
- `page_budget`, `language`, `theme_profile`, `output_formats`；
- `story_arc`；
- `slides[]`：
  - `slide_id`；
  - `section`；
  - `title`：结论性标题；
  - `key_message`；
  - `supporting_points[]`；
  - `artifact_ids[]`；
  - `evidence_ids[]`；
  - `architecture_domains[]`；
  - `architecture_view_ids[]`；
  - `visual_type`；
  - `chart_spec` / `diagram_spec`；
  - `layout_hint`；
  - `speaker_notes`；
  - `review_status`；
- `appendix[]`；
- `citation_index[]`。

## PPT Skill 允许修改

- 布局、留白、图形、图标、字体、颜色、动画、页码和母版；
- 文字压缩，但不得改变含义；
- 将 diagram/chart spec 转成可编辑图形。

## PPT Skill 禁止修改

- 数字、公式、范围、状态、架构组件、Initiative 名称、路线图依赖；
- Evidence/Artifact 引用；
- 已批准的核心结论和管理决策请求；
- 4A Node ID、关系、Owner、生命周期和 Transition 状态。

## 交付验证

- 生成前：`slide-content-pack` 已通过 G8 内容审查；
- 生成后：PPTX 可复开，页数与页序符合 Content Pack，关键标题与数字回读一致；
- 视觉层：检查溢出、遮挡、空白页、字体替换和不可编辑的关键图；
- 状态层：PPTX 文件存在只代表渲染完成，不代表内容已获业务批准。

## 华为 4A 页面交接规则

- 所有 BA、IA、AA、TA 页面必须引用已批准的 Architecture View 或 `four-a-architecture-package` Aggregate Package。
- 每个 4A 页面必须提供 `architecture_domains` 与 `architecture_view_ids`。
- 标准 visual type：`4a-overview`、`business-architecture`、`information-architecture`、`application-architecture`、`technology-architecture`、`4a-traceability`、`transition-architecture`、`ai-4a-overlay`。
- 总体架构页应表达 BA 驱动 IA/AA、IA 与 AA 相互约束、TA 提供支撑的关系，不能把四域画成没有语义的技术堆叠。
- Integration、Security & Trust、AI & Knowledge、NFR、Governance 应作为跨域能力或侧向治理表达，不能冒充第五个 A。
- 图中的节点、关系、状态、Owner、利旧/改造/新建/整合/迁移/退役标识必须来自 approved Architecture View。
- IA 页面可按客户习惯显示为“信息架构”“数据架构”或“信息/数据架构”，但内部域代码保持 `IA`，且内容不能退化为数据平台产品图。
- PPT Skill 不得新增、删除、合并或更名架构对象，除非上游 Artifact 已完成版本变更和审批。
