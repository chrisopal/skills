# 生成前创意简报

每个方案一份，只写会改变生成决策的内容；未命中的条件段直接删除。硬门见 [preflight-gates.md](preflight-gates.md)，提示词见 [image-generation-workflow.md](image-generation-workflow.md)。

## 1. 输出、事实与照片

```text
运行目录：output/yingzao/<run-id>/
数量 / 比例 / 尺寸 / quality：__
对象与地点：__
状态：历史遗存 / 修复 / 迁建 / 复建 / 当代 / 未确认
VERIFIED：__；OBSERVED：__；USER-CONFIRMED：__
必须出现 / 可选 / 不出现：__ / __ / __
高风险字及角色：__

来源与角色：Image 1 __ hero；其他来源 __ support / reject
preflight / rectify 报告：__ / __
身份锚点：__、__、__
真实不可拉平：屋坡 / 飞檐 / 不对称 / 匾额 / 其他 __
```

## 2. 构图诊断与四域命题

```text
原构图意图：正立面 / 仰视 / 对角 / 框景 / 局部巨像 / 环境叙事 / 其他 __
稳定骨架：水平 / 竖直 / 对角 / 三角 / 拱形 / 环形 / 其他 __
策略：preserve / deterministic-rectify-crop / semantic-recompose
一个主问题：preserve / 无意滚转 / 偏重 / 截断 / 死负空间 / 承接断裂 / 无图文空间
唯一修复动作：__
允许补齐：无 / 可连续推断的天空、水面、地面、墙或直柱 __
禁止发明：屋顶、层数、门窗、柱数、雕塑、镜像构件及 __

先于参考检索冻结：
主体域：抠取范围 __；尺度/位置动作 __；分区材料转译 __
背景域：主动色场、色窗、明度切片或重建空间 __
互动域：真实轮廓 __ 与文字/色形 __ 的遮挡、共边、穿插或负形 __
排版动作：偏置 / 越栏 / 竖向 / 断行 / 边缘切入 / 其他 __
缩略图可见结果：1.__ 2.__ 3.__ 4.__
```

## 3. Recipe 与主导参考

```text
Recipe ID / family：__
recipe.json / design-plan.json：__ / __
主导参考实际路径：__
适配：主体占幅 __；负空间拓扑 __；互动边界 __
迁移：主体处理 __；主动背景 __；图文关系 __；材料 __
不迁移：原建筑、地名、人物、品牌、符号及 __
照片主轴 / Recipe 主轴：__ / __
主体容器 / 背景尺度 / 语境材料 / 表现字形：__ / __ / __ / __
依赖与互斥结论：__
外国参考的中文语义、目标几何与地域材料接管（如适用）：__
```

## 4. 画布、字体与空间

```text
画布 / 网格 / 外边距 / 共同轴：__ / __ / __ / __
主体范围、占幅与偏置：__
标题范围、占幅与偏置：__
身份保护区 / 背景重建范围：__ / __

展示模式：literal / reinterpret
展示字形谱系：__
字形可见特征：宽窄 __；重心 __；粗细对比 __；收笔 __；字腔 __；节奏 __；表面 __；建筑对应 __
展示 / 地点对象 / 资料小字的字体角色：__ / __ / __
glyph brief / typeset spec / guide / report：__ / __ / __ / __
generation prompt / call manifest / readback：__ / __ / __
alignment groups / overlap contracts / vertical order：__ / __ / __
语义标记：S1 __；B1 __；T1 __；其他 __

统一边缘语言：硬切 / 羽化 / 纸撕 / 墨蚀 / 落影
主材质 / 辅助材质 / 强调色来源：__ / __ / __
z 轴：背景 __ < 结构色形 __ < 主体辅助层 __ < 主体主层 __ < 标题/资料 __
```

`reinterpret` 另在 `analysis/glyph-brief.md` 逐字填写：`字 / 光学问题 / 轮廓动作 / 不可改变的标准部件`。小字不继承展示字的夸张动作。

## 5. 条件段

多图一体化时，逐来源写：`提取主体 / 身份锚点 / 目标位置和尺度 / 共同光向 / 接触面和阴影 / 跨来源遮挡`，并说明共同连续背景与必须消失的原图边界。

启用语义装饰时写：`母题与事实来源 / 进入的 1–3 个角色 / 同时承担的至少两个构图任务 / 不改变文字与主体拓扑的方法`。正常留白不填满。

## 6. 调用记录

```text
动作 / 模型：edit / gpt-image-2 或内置 imagegen
文字路径：typeset-guide-integrated / model-native-minimal-text / geometry-only / layered-final-type
Image 1：__；Image 2：__；Image 3：__；Image 4..n：__
Image 2 可见机制（主体 / 背景 / 图文）：__ / __ / __；禁项是否掏空参考：否 / 是，换参考
Composition diagnosis：__
Composition repair：__
身份不变量：1.__ 2.__ 3.__
必要短文案：__
灾难性禁项（最多五个）：__
保存路径：__
prepare_generation：READY / 未通过 __；call_signature：__
Token 投递：prompt+guide __；preprocess __；missing 必须为 0
```
