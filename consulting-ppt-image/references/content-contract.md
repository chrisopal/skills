# 内容交接契约

## 双层状态，不让生成状态污染咨询审批

上游 `slide-content-pack.json` 固定用户批准的内容。下游 `deck-manifest.json` 只管理样式快照、图片版本、审校和最终选版。

内容包保留既有交接字段：`deck_id/version/purpose/audience/decisions_required/page_budget/language/theme_profile/output_formats/story_arc/slides/appendix/citation_index`。新增 `sections`、稳定用途 `purpose_id`、实际顺序 `order`，便于机器检查。

`slide_id` 代表逻辑页面，移动页面时不改ID；`order`代表本次展示位置。图片页码用order/总页数，而不是ID。`purpose_id`标识这一页独有的论证任务，不能让两页用不同标题重复一个任务。

每页必需：
- `title/key_message/supporting_points`：原意明确的结论和支撑。
- `section/visual_type/layout_hint`：章节与视觉关系。
- `evidence_ids`：关联真实证据，或对纯建议页留空并显著标建议。
- `review_status`：draft、needs_review、approved。上游更新此状态，PPT技能不能私自升级。
- `approval_ref`：全稿当前版本的实际确认依据，缺少时不能开始正式生产。

推荐扩展：`protected_terms/protected_values/diagram_spec/chart_spec/visible_qualifier/speaker_notes`。保护字段列出不可改变的对象和数值；最终图中的正确性仍需逐项视觉核对。

## 图形规格

架构/流程用 `diagram_spec.nodes[{id,label}]` 与 `edges[{from,to,label}]`。脚本能发现悬空节点，不会判断组织或架构设计是否正确。严禁为了布局把并行改串行、把共用底座画成多个孤立平台。

甘特图用 `schedule.tasks` 和 `schedule.milestones`。本版日期检查只支持**按天的完成—开始(FS)依赖**；`depends_on`列前置任务ID，`must_finish_before`列里程碑ID。更复杂的SS/FF/SF、时区、工作日、资源平衡必须由上游明确，不能偷偷当FS计算。日期区间在甘特图内的准确位置需要视觉检查。

## 对标案例

`benchmark.entity_id`须与该页证据 `entity_id`逐一一致。外部事实必须有已核验来源，正式渲染还必须有 `type=official_screenshot` 的已核验原始截图。当前版本将文字实体与元数据一致性作为检查项；不能靠它确认截图内真实企业名称。

原案例图暂时无法获取时：标“证据待补”，不生成像截图的假网页、不把别家照片替上去。

## 当前示例的边界

`examples/minimal/` 是虚构的三页建议型演示内容，初始为draft。

`examples/generic-35/` 是35页通用结构示例，只保存页标题和每页作用；刻意设置 `content_complete=false`、`needs_review`。它不包含客户资料，也不是完整可渲染方案。要重用时，先从实际已确认PPT/业务资料提取逐页内容和来源，再确认。

请勿把客户名称、投产日期、产能或经营指标等项目特定事实硬编码进通用生成器。
