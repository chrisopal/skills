# 主题与页面组合

每个主题是完整的配色、字体、布局、材质与可编辑策略，不是套一个颜色。
七主题共享微软雅黑（`Microsoft YaHei`）及显式pt目标：普通正文/图内节点/图表与表格标签14pt，副标题16pt，模块短标题18pt，内容标题28pt，页脚12pt；封面保留各主题设定。常规字重为主，短标签不放大填空间。用户品牌/大屏规范可覆盖；字体未安装不得静默替换。
主题用独立名称，不附麦肯锡、BCG、埃森哲等企业 Logo，也不宣称官方模板。
用户提供品牌规范/参考图时，以其授权参考为准；新建项目主题版本保留来源。

| 主题文件 | 特点 | 适用场景 |
|---|---|---|
| [consulting-blue](../assets/themes/consulting-blue.json) | 白底深蓝、观点先行、直接标注图表 | 战略、经营汇报 |
| [consulting-red](../assets/themes/consulting-red.json) | 白底朱红、重点对比、行动导向 | 变革、决策 |
| [consulting-purple](../assets/themes/consulting-purple.json) | 白底紫色、局部光带、清楚架构层级 | AI、数字化 |
| [consulting-green](../assets/themes/consulting-green.json) | 白底墨绿、细线、稳重留白 | 产业与规划 |
| [product-solution](../assets/themes/product-solution.json) | 产品主视觉、场景与能力边界 | 售前、方案 |
| [marketing-editorial](../assets/themes/marketing-editorial.json) | 暖白黑橙、非对称大标题、强主视觉 | 发布、营销 |
| [annual-gala](../assets/themes/annual-gala.json) | 深紫黑、香槟金、舞台光影 | 年会、庆典 |

[页面配方](../assets/layouts.json) 覆盖封面、章节、观点、数据、架构、流程、案例、对比、路线图、甘特图、行动计划和结束页。按内容关系选结构；连续三页同一结构时查看是否单调，但不为变化破坏逻辑。

主题里的 preferred_pixels 是设计目标，不是强制传给工具的参数。只使用工具实际支持的原生尺寸。现有登记检查默认要求接近16:9且宽度至少1600；若宿主原生尺寸不同，先明确裁剪/留边/自定义画布方案，并在 init 前建立适用的主题 profile，记录真实分辨率。不要静默拉伸或放大。

对密集方案保留足够字级和图例；营销/年会可增加视觉主导面积，仍要保留正文对比度。先核对图片生成后的实际文字大小，再核对重建后的字体与换行。

这些文件是可复用主题规格和页面配方，不是固定成品。2026-10-11 的通用演示测试使用旧默认（正文20pt等），记录保留原始实测事实，不证明新版微软雅黑/14pt已经实际渲染。历史覆盖：

| 主题 | 已完成的真实样稿验证 |
|---|---|
| consulting-purple | 三页生图、可编辑重建、LibreOffice 渲染、macOS PowerPoint 编辑保存重开 |
| consulting-blue / consulting-red / consulting-green | 各一页生图、图片版及可编辑版；正文20pt、标题32pt、模块标签24pt；最终文件内容/备注审计、LibreOffice渲染、PowerPoint副本编辑保存重开 |
| product-solution / marketing-editorial / annual-gala | 各一页生图、图片版及可编辑版；正文20pt、封面标题44/48/44pt；最终文件内容/备注审计、LibreOffice渲染、PowerPoint副本编辑保存重开 |

六套可编辑样稿包含44个原生文本框；复杂视觉保留独立位图，年会使用去字后的舞台背景，未用原始带字整图覆盖。最终六页合集和六个单页文件均已实际渲染。PowerPoint测试副本的六页正文从20pt改为21pt、红色页容器移动后，保存重开并回读，修改和全部备注均保留；交付原稿仍为20pt。字号缩小是用户授权修订，图形渐变、阴影和素材边缘仍有轻微差异。

本次只覆盖Codex和上述通用样稿，不代表所有内容、宿主或客户品牌均已验收；Windows及Claude实际运行未测；WorkBuddy只补测了一页蓝色咨询样稿的两种输出，其他主题、复杂素材编辑和多页派发未测，见[宿主实测边界](host-tools.md)。跨平台字体替代仍需检查。生成物留在本地，不随技能发布。新增主题或密集内容仍需按所选模式完成代表页验证；详细字号依据见[字号规则](typography.md)。
