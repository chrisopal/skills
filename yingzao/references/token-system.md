# 建筑海报 Design Token 系统

本系统把 [art-direction.md](art-direction.md) 中的设计判断编码成稳定、可检索的 Token。它借用 Design System 的分层思想：Token 先帮助找到一套完整风格和真实参考证据，随后必须被编译成针对当前照片的少量模型动作与垫图区域，而不是把几十条通用句子机械串成提示词。具体尺寸、字形与构图仍由目标照片决定。

好看的参考图包含难以完整文字化的高维共生关系：构图、材质、色彩、尺度、边缘和排版相互制约。拆解用于检索与解释，生成时必须重新回到一张主导参考实图；“更多 Token 的安全交集”通常只会得到平庸公约数。

机器可读清单位于 [design-tokens.json](design-tokens.json)，逐图来源证据仍保留在参考编码文档中。

## 四层模型

1. **Primitive**：可计算的基础尺度，例如栏数、外边距、沟槽、字级比例、遮挡比例和 z 值。Primitive 不单独决定风格。
2. **Semantic**：回答“它在画面里负责什么”，例如中文展示标题、资料字、背景尺度、身份保护、地域强调色。
3. **Component**：可复用的视觉机制，例如字窗纪念碑、连续竖窗、来源正文场、纹样边缘遮罩和细网点建筑。
4. **Recipe**：已经过兼容检查的一组 Token；它是起点而非模板，仍需根据照片替换主体范围、文案、取色和材质参数。

Token ID 使用 `cap.<category>.<name>`：

```text
cap.primitive.grid-6
cap.type.display-cn
cap.layout.type-window
cap.material.arch-halftone-fine
cap.depth.arch-over-ghost-type
cap.policy.functional-dividers
```

ID 是稳定接口。可以扩写描述和标签，但不要因措辞变化重命名；确需废弃时增加别名或迁移记录。

## Token 契约

每个 Token 至少包含：

```json
{
  "id": "cap.layout.type-window",
  "tier": "component",
  "category": "layout",
  "label": "字窗纪念碑",
  "intent": "让短标题同时成为图像容器和背景尺度",
  "value": { "subject_inside": "60-75%", "identity_breakout": "25-40%" },
  "tags": ["塔", "门楼", "短标题", "字窗"],
  "requires": ["cap.type.display-cn", "cap.subject.identity-protection"],
  "compatible": ["cap.material.arch-duotone", "cap.depth.identity-breakout"],
  "conflicts": ["cap.layout.multi-image-collage"],
  "constraints": ["标题限 2-5 个汉字", "至少一个身份锚点越出蒙版"],
  "prompt": "Use the verified short Chinese title as an image mask...",
  "visual": { "glyph": "字", "swatch": "linear-gradient(...)" },
  "sources": ["127c...jpg", "7a760...jpg"]
}
```

- `intent` 解释视觉任务，禁止只写风格形容词。
- `value` 存放可视化和前端可消费的参数；范围优先于伪精确值。
- `requires` 是硬依赖；解析后若缺失，方案无效。
- `compatible` 是加分关系，不代表必须同时选择。
- `conflicts` 是硬冲突，任何方向声明都视为双向冲突。
- `constraints` 是必须在生成前简报或门控中得到处理的自然语言边界。
- `prompt` 是该机制的候选动作描述，不包含具体建筑名、虚构事实或外国文化内容。它不能与同一 Recipe 中其他 Token 的 `prompt` 自动串接；执行者要把全部启用 Token 按兼容关系合并为主体、背景、字体、互动四域的少量当前照片动作，并写入 `design-plan.json`。
- `visual` 只用于目录预览，不参与生成判断。
- `sources` 提供参考图证据；它不是复制许可。

## 受控照片标签

`design-tokens.json.controlled_tags` 是照片分析进入 `suggest` 的唯一标签入口。当前词表：

```text
单体 建筑群 中轴 偏侧 横向 竖向 低机位 正立面 天空留白 留白
高密度 低密度 夜景 暖光 木作 石构 水面 花木 室内 食物 饮品 店铺
桥 塔 城墙 城门 院落 街巷 屋檐 门洞 券洞 山寺 多图 多图合一
档案 修缮 旧照 当代 建筑 摄影随笔 复杂排版
```

词表优先描述可观察的几何、光线、材料、密度和画面角色。常见自由词通过 alias 归一化，例如 `寺庙 / 寺院 / 古寺 -> 山寺`、`桥梁 / 古桥 / 石桥 -> 桥`、`园林 -> 院落`、`横图 -> 横向`。使用：

```bash
python3 scripts/design_tokens.py tags
python3 scripts/design_tokens.py tags --search 寺庙
```

`suggest` 的 JSON 输出包含 `normalized_tags / matched_tags / unmatched_tags`。若全部标签未命中，命令返回状态 2；不得用字母序候选继续生成。

## 风格轴与历史指纹

Recipe 会由所含 Token 推导六轴指纹：`ground / polarity / era / texture / saturation / image_behavior`。Token 可在 `value.style_axes` 中显式覆盖推断。多方案和跨会话去同质化使用：

```bash
python3 scripts/design_tokens.py suggest \
  --tag 夜景 --tag 中轴 --count 3 --maximize-distance \
  --history output/yingzao/<run-id>/recipe-history.json \
  --record-history
```

历史文件属于用户运行目录，不属于 Skill 包。风格距离只负责扩大候选差异，不能覆盖身份、事实、几何和冲突硬门。

## 互斥槽位

`design-tokens.json` 中的 `mutex_groups` 是 Recipe 的主要骨架：

| 槽位 | 上限 | 说明 |
| --- | --- | --- |
| `slot.layout-primary` | 1 | 中心、中轴、侧边、对角、分割、字窗、多窗、门洞套层、连续模块、模块拼贴、一体化蒙太奇、局部巨像或密集标题场只能有一个主布局 |
| `slot.subject-container` | 1 | 字窗、连续竖窗、同轴多窗、模块拼贴、一体化蒙太奇、门洞套层、连续模块只能选一种 |
| `slot.background-scale` | 1 | 来源正文场、重复短地名、同字号地点语义序列、尺度数字只能选一种 |
| `slot.context-material` | 1 | 地形频率场、地域纹样、可信档案层只能选一种 |
| `slot.expressive-type` | 1 | 书写标题、随形文字、巨型几何字、语义拆字、互锁标题、全幅等宽标题只能选一种 |
| `slot.glyph-morphology` | 1 | 刊刻楔脚宋、碑额篆刻、构架几何变体、横张隶意、民艺拙笔、理性明体只能选一个展示字形形制 |
| `slot.line-policy` | 1 | 显式禁线、主题功能分割线与解释注释线只能选一种 |

互斥只限制同类主机制。基础纸纹、资料字体、身份保护、区域材质和 z 轴关系可作为依赖加入。

## 基础质量 Token

以下 Token 不决定海报风格，但负责阻止构图和排版在进入风格混搭前失真：

- `cap.subject.preflight-rectification`：抠图前检查相机滚转、梯形透视、主体居中和校正后裁切；保护真实屋坡、飞檐、匾额和建筑不对称。
- `cap.primitive.optical-alignment`：同时检查文本框与可见字面；一个标题组至少共享两个边界或基线。
- `cap.type.vertical-title-lockup`：需要竖排时，把拼音微字、重字重对象名和地点限定词编译为一个父级组件，不允许三段文字分别漂移。
- `cap.type.full-width-cn-row`：将 2–5 个标题字锁为全幅等宽行；建筑可遮挡字形，但不能让某个字为了避让主体而缩小、错位或离开共同基线。
- `cap.background.semantic-place-sequence`：把 2–4 个真实地点、水系或构造词锁为同字体、同字号、同字重的语义序列；层级只由顺序、位置、明度、z 轴和遮挡产生。
- `cap.policy.functional-dividers`：主题模式允许最多两条有任务的规则线/分割线；必须服务信息分组、共同轴线或资料基线，不是默认装饰。
- `cap.policy.typeset-guide-gated`：字体加载、字面测量、碰撞、溢出、共享轴和竖排顺序全部通过时，默认使用不含目标照片像素的真实字体排版垫图；任一失败才回退到 geometry-only 或纯提示词。
- `cap.policy.recipe-geometry-gate`：在占槽前比较照片主轴、Recipe 要求轴、主体容器和闭合身份轮廓；不适配时直接淘汰 Recipe，而不是在提示词阶段补救。
- `cap.policy.mask-compatibility-gate`：字窗专用质量门；检查主体是否细长单轴、是否只保留一个窄越界区、字形缩略图是否可读，以及标题带/主体/负空间比例是否延续主导参考。宽阔多重檐正立面和“完整主体 + 字窗主体”视觉复读直接淘汰。
- `cap.policy.glyph-scale-risk-gate`：把模型低置信度生僻字限制在小资料层，巨型结构字改用已核实的常用地点、形制或构件词；正式专名不得被擅自改字。
- `cap.policy.multi-scheme-material-distance`：多方案比较建筑本身的明度极性、表达方式、边缘语言、纹理频率与颜色行为，至少两轴不同；只换背景不算新方案。
- `cap.policy.typography-context-fit-gate`：在占用表现型字体槽位前先记录照片的光线、材料、尺度、叙事速度和场所类型。粗黑体、全幅宽体或巨型几何字必须由纪念碑体量、坚硬中轴、现代商业或夜游语气触发；暖光木作、手作、饮食与文化室内优先使用宋/明体与衬线微字。
- `cap.type.glyph-*`：字体类别之后再选一个展示字形形制，把参考图的气质语义与骨架、重心、粗细、收笔、字腔、连接和表面证据一起编码。垫图中的普通字体只锁定字面范围；资料字不参与形制重绘。详见 [display-glyph-morphology.md](display-glyph-morphology.md)。
- `cap.type.serif-editorial-hierarchy`：为同址文化店铺、室内和食物摄影随笔提供中文展示、地点/品类、资料微字三角色，阻止多图海报退化成一组大字和等权图片块。
- `cap.layout.integrated-subject-montage`：把同址多图中的真实主体逐一抠取，重组进一个连续环境；原图矩形、分栏缝和卡片全部消失，主体共享尺度、透视、光线、接触阴影与边缘材质。
- `cap.policy.image-model-value-gate`：调用图像模型前先声明不可由裁图、统一滤镜和打字复现的语义增值动作；无法给出这些动作时换方向或不用图像模型。

### 可选语义母题机制

`cap.context.semantic-motif-propagation` 把照片中可见、用户确认或已核实的一个物件/材料母题，最多传播到主体实物、展示字微结构和一处边缘切入三个角色。它只在修复死负空间、连接视觉路径、回收孤立强调色或建立在地字形时启用，并至少承担两项任务；不得把正常留白填满，不能改变汉字标准拓扑，也不能成为悬浮贴纸或第二主体。

该 Token 不占 `slot.context-material`：它不引入第二套独立背景材料，而是让同一个真实内容来源跨层回声。若母题发展成重复纹样、档案层或地形频率场，应改用对应的语境材料 Token 并遵守该槽位互斥。Recipe 中只把它列为可选机制，不能默认激活。

主体校正、字面对齐和文字垫图门控已进入基础 Recipe。三轨标题只在照片负空间和标题长度适合时选择，不能把所有海报都强制变成同一种标题模板。门控通过时 `typeset-guide` 是首选参考模式且不含目标照片像素；门控失败才使用 `geometry-only`，后者不含文字、伪字、文字框或空卡片。

## Token 解析顺序

这里仅规定候选组合怎样形成；照片处理、排版门控和图像调用分别以对应参考文档为唯一真源。

1. **检索并记录历史**：从受控标签调用 `suggest --maximize-distance --history ... --record-history`；零命中立即停止。
2. **锁定主导参考**：每个方案只选一张实际可读取的 `reference_asset`，记录其 family、主轴、主体容器和可见字体证据。
3. **筛几何与语域**：比较照片主轴、身份轮廓、光线、材料、尺度、叙事速度和画面密度；只写宽泛风格词、复用上一张字体动作或破坏闭合身份轮廓的候选直接淘汰。
4. **占槽并解析依赖**：每个互斥槽位只留一个主机制，展开 `requires`，命中任一 `conflicts` 即淘汰；展示字需要重绘时，字形形制槽必须且只能占一个。
5. **执行条件门**：只在命中时检查字窗兼容、高风险字、多图语义增值、语义母题和多方案材质距离；不存在的 JSON 字段不参与筛选。
6. **编译设计计划**：保留 Token ID 供追踪，把全部启用 Token 恰好分配一次；确定性校正进入 `preprocess_tokens`，其余按布局、主体、材质/颜色、字体与图文关系合并为四域可见动作。每个动作必须写 `target / prompt_instruction / visible_result / guide_markers`，由 `prepare_generation.py` 写进最终模型提示词并与垫图标记核验；Token 自带的通用 `prompt` 和 `constraints` 仍不逐条串接。
7. **交给执行文档**：按 [creative-brief.md](creative-brief.md) 完成生成前简报，再按 [image-generation-workflow.md](image-generation-workflow.md) 的固定输入顺序调用图像模型。

建议评分：目标几何直接匹配 `+3`，显式兼容 `+2`，同一真实内容来源 `+1`；弱适配 `-2`，文化来源不明 `-3`，显式冲突或身份锚点风险直接淘汰。分数只用于排序，不能覆盖硬约束。

## Recipe 解析

Recipe 由来源、可见特征和 Token 组合共同组成：

- `family` 是方案的结构族；多方案不能重复。
- `signature` 描述缩略图中必须能看到的布局/字体/主体容器/z 轴特征，不能只写配色和质感。
- `sources` 指向产生该机制的参考证据；不是复制许可。`design_tokens.py recipe <id> --json` 会把它们解析为 `reference_assets`，优先返回 `assets/reference-plates/` 的较大图，缺失时才回退到缩略图。
- 高风格化任务必须从 `reference_assets` 中选择一张并作为实际图像输入。若 Recipe 没有可读取的参考资产，它只能用于目录浏览，不能进入生成。
- 每个方案从 `sources` 中明确一个且仅一个主导参考，由它决定主要轴线和主体容器；次要参考不得再引入竞争主轴或容器。

- `tokens` 不是需要逐条注入提示词的文本包，但也不能只停留在检索结果里。Recipe 展开后的每个启用 Token 都必须在 `generation-call.json.token_delivery` 中显示为 `prompt+guide` 或允许的 `preprocess`；没有投递路径即停止生成。
- `optional` 只有命中照片与事实条件时才能加入。
- `forbidden` 防止常见模板残留。
- `invariants` 是该组合成立的最小条件。

使用 Recipe 时先把它展开为 Token ID，再根据当前照片删除不适用的可选项；不要把 Recipe 名直接写进图像提示词。

每个方案在生成前保留内部追踪链：`实际输入的 reference_asset -> family -> 创意命题 -> 4–6 个合并后的可见动作 -> prompt+guide 标记`。没有附带主导参考实图时，Recipe 不得进入生成。

## 可视化与命令行检索

使用 [scripts/design_tokens.py](../scripts/design_tokens.py)：

```bash
python3 scripts/design_tokens.py validate
python3 scripts/design_tokens.py query --category layout --tag 塔
python3 scripts/design_tokens.py query --compatible-with cap.layout.type-window
python3 scripts/design_tokens.py tags --search 天空
python3 scripts/design_tokens.py suggest --tag 屋檐 --tag 天空留白 --count 3 --maximize-distance
python3 scripts/design_tokens.py recipe cap.recipe.tower-type-window
python3 scripts/design_tokens.py render --output /tmp/cap-token-catalog.html
```

`suggest` 按受控照片标签给 Recipe 排序，报告未命中词，并可按风格轴扩大距离；它只生成候选，不绕过硬冲突。HTML 目录按层级和类别显示色片、ID、标签、意图、依赖、兼容、冲突、风格指纹、来源缩略图和 Recipe 可见特征。若 `assets/reference-thumbnails/` 存在则自动加载；不存在时来源文字仍可检索，绝不回退到 Skill 目录之外的 `参考/参考新/`。它是检索界面，不是网页式海报模板。

## 扩展规则

新增参考图时：

1. 先逐图编码事实观察和中式转译。
2. 搜索现有 Token；同一视觉任务优先补 `sources`、标签或约束，不新建同义 Token。
3. 只有出现新的可复用视觉任务时才新增 Token。
4. 新 Token 必须至少加入一个检索标签，声明互斥槽位或说明为何不互斥，并有一条可在生成前判断的约束。
5. 新 Recipe 必须声明 `family`、`signature` 与 `sources`；`signature` 必须是缩略图可见的结构特征。多方案用 family 和 `slot.layout-primary` 控制真正差异。
6. 修改后运行 `design_tokens.py validate`，渲染带 `Reference coverage` 的目录并确认没有意外 `unmapped`；随后从当前环境的 `skill-creator` 目录运行 `scripts/quick_validate.py yingzao`。该脚本不在本 Skill 内，不得假定本地存在同名文件。

不要为每张参考图创建一个 Token，也不要把“高级、复古、东方、氛围感”这类不可执行形容词当 Token。
