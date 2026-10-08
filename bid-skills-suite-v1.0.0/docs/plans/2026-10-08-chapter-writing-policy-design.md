# 章节篇幅与界面配图设置

用户已确认：由总控推荐章节篇幅和展开深度，允许逐章覆盖；系统功能章节可要求界面图，缺字数或缺图必须定位。修改 portable Skill 套件，保持真实项目原件和已验收候选稿不变。

## 配置与优先级

继续使用 work/writing-settings.json 和现有 Markdown 写作编辑器，不增加依赖。

- length_mode：auto_scoring（默认）或 fixed。
- target_words：统一基准目标，可留空；自动模式默认基准 1000。
- length_tolerance：0—0.5，默认 0.2。
- chapter_overrides：按稳定 section_id 保存 target_words、detail_level（auto/brief/standard/detailed）、ui_required（null/true/false）和 min_ui_images（1—8）；未填写字段继承推荐。
- visuals.system_ui_policy：auto（任务卡要求）、all_system_sections（识别系统功能章节）或 off。
- visuals.min_ui_images：每个适用章最低界面图数，默认 1。
- visuals.max_images 继续是每次生成上限 1—8；整本任务分批执行，不限制全书图片总量。

明确章目标优先于模式推荐。推荐理由保留评分叶子、原规则及需求复杂度；评分分组不重复累加，继承父章评分需要标记。方案条件决定展开机制、步骤、异常、验收；资质/业绩/数量证明与价格公式不因高分强行增加文字。固定表单保留原格式，不为达到推荐字数填充。自动识别是可改的建议，不能认证专业性或评分满足。

## 运行交接

共享 writing_policy.py 负责设置校验、逐章建议、可见正文字符计数及篇幅/界面图检查；不调用模型。workspace.state 返回 chapter_policy；分章 task.json 保存同一 resolved_policy。图任务仍由 13 驱动宿主真实生图 Skill，技术图保持 SVG/Draw.io 路由。

可见字数剔除 Markdown 图片、链接地址、HTML 属性、代码块与空白，表格正文计入。目标 ± tolerance；自动推荐偏离提示整改，用户明确目标作为配置检查失败。缺失/未渲染/未插入正文/损坏图片，或把架构图当界面图不能满足必配图。图片分类使用 13.kind=interface，生成界面图注必须保留示意属性，不假装真实截图。

草稿允许保存；设置使用既有版本/hash CAS，并阻止未知章节配置。写作检查单独返回 writing_policy，不把结构成功当内容达标；评审/导出检查当前策略，明确字数与必配图缺口阻止正式交付。已修改设置必须冻结新快照，旧审核不能复用。

## UI Blueprint

在现有“写作设置”中增加自动/固定模式、系统功能章配图策略；当前章节下显示推荐目标、评分理由、实际可见字数及缺口，提供逐章目标、详细程度、界面必配覆盖。保留其他章节覆盖、未保存正文、冲突/失败提示。沿用 Enterprise UI Design 和现有深浅色 token，不新建设置页面。

## 验证

回归验证高分方案、证明评分、价格、继承评分、无评分、固定表单、逐章覆盖及未知章节；验证 Unicode 可见计数、字数不足、架构图替代界面图、损坏/未插入图片、关闭生图冲突、批次上下文与 CAS。

复制青草沙真实项目到独立验证目录，展示全部章节建议并做正反例，原完整 217 页测试项目保持只读。真实浏览器检查设置保存刷新、切章、500/1000/2000 覆盖与深浅色/窄屏。独立 forward test 使用原始输入和技能，不把确定性检查称作专业评标。刷新独立安装资源和 ZIP 后运行完整套件门禁。
