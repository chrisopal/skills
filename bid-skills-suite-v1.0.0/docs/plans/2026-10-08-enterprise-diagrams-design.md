# 参考版式独立图表Skill及投标集成

用户明确要求：按八张示例生成架构/流程图，可选颜色主题，新增独立Skill、可配置并保留Draw.io，对不同图型测试。

- 源码归属：chrisopal/skills/enterprise-diagrams；bid-skills-suite只分发同源renderer/themes，不另写第二套。
- 表达：纯矢量SVG文字和可编辑JSON，浅色模块/深描边/徽标/菱形/正交连接/虚线分组与反馈；参考、蓝、青、绿、灰、黑白六主题。
- 布局：layered、flow、pipeline、swimlane、network、parallel、sequence、matrix。章节内容是来源，图中不复制示例性能值为项目承诺。长字换行、可变框高；不适合单页的密集图拆为总体与局部。
- 配置：新增blueprint与diagram_theme；既有auto/Draw.io等路由保持；主题仅用于新引擎。层数支持1—12，以包含参考8层，不为满层发明系统。
- 保存与审计：.diagram.json源中保存主题/布局，现有base SHA/CAS不可变快照、排他发布、render_record沿用；实际PNG用宿主已有可选CairoSVG，无安装动作，缺工具保留SVG方案。
- 验证：独立Skill回归、suite设置/路由/审计/ZIP回归、各图型真实SVG/PNG、六主题、长标签/较多节点/回环/自消息/异常输入，真实编辑器保存回读及A4 DOCX/PDF图文核验。
- UI：复用现有enterprise-ui-design编辑器，添加新引擎、主题及布局选项；禁用状态不丢值，四视口与浅深验证。报告只展示真实图、源下载与验证状态。
