# 主题与页面组合

每个主题是完整的配色、字体、布局、材质与可编辑策略，不是套一个颜色。
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

这些文件是可复用主题规格和页面配方，不是已经过图像模型实测的成品示例。新增风格应先完成代表页的生成与重建验证。
