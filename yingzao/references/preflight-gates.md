# 生成前门控

这是高成本图像调用前的唯一门控真源。它只检查输入与方案是否成立，不评价成图，不触发 proof、评分或重生成，也不作为长负面提示词回灌。

## 八个硬门

1. **依赖与路径**
   - `scripts/check_dependencies.py` 返回 0；运行目录为调用者的 `output/yingzao/<run-id>/`。
   - 输入用副本，Skill 包内没有缓存、测试图或运行产物。

2. **照片、身份与几何**
   - 每张来源已有 preflight 报告和 `hero / support / reject` 角色。
   - 构图策略在 `preserve / deterministic-rectify-crop / semantic-recompose` 中三选一，且只有一个主修复动作。
   - 屋坡、飞檐、不对称、题字等身份锚点不被扶正或重构破坏；只补齐可连续推断的低风险背景、直柱、墙、水面或地面。

3. **事实与文字**
   - 文案只来自 `VERIFIED / OBSERVED / USER-CONFIRMED`；必须出现、可选、不出现和高风险字已分组。
   - 生僻字不承担巨型结构字；历史遗存、修复、迁建、复建与当代建筑没有混淆。

4. **命题与主导参考**
   - 四域命题写在参考检索前；高风格化任务恰好有一张实际输入的主导参考实图。
   - 参考与目标的主轴、身份轮廓、主体占幅、负空间拓扑和互动边界兼容，`requires / conflicts / mutex_groups` 已解析。
   - 参考同时示范主体处理、主动背景和图文互动，而非只提供颜色、纸纹、字体或氛围。

5. **模型增值**
   - 主体域包含语义抠取、尺度/位置重组或分区材质；背景域包含色场、色窗、明度切片或重建空间；互动域包含真实轮廓遮挡、共边、穿插或负形咬合。
   - 三域都能在缩略尺度看见，并有一个偏置、越栏、竖向、断行或边缘切入等非默认排版动作。
   - 原照加居中标题、双居中孤岛、统一滤镜加字、普通渐变、矩形拼版均不通过。只有用户明确要求组照/对照时保留照片矩形。

6. **排版垫图**
   - `typeset_compose.py` 报告 `passed=true`：字体 cmap、fallback、真实字面、碰撞、溢出、对齐组、primitive 禁穿区、遮挡契约与竖排顺序均通过。
   - 每个展示层显式声明 `glyph_design_mode`；`literal` 使用 `guide_render: text`，`reinterpret` 使用 `guide_render: scaffold`，不能把全尺寸普通字体轮廓当作重绘垫图。
   - `text-behind-subject` 使用从 Image 1 轮廓得到的 `subject_front + subject-footprint`；规则线或空原因不能证明遮挡。

7. **展示字形**
   - `literal` 使用常规字体；`reinterpret` 已有 `analysis/glyph-brief.md`，只选一个形制并记录至少五项可见特征。
   - 2–5 字标题逐字写明光学问题、轮廓动作与不可改变的标准部件；资料小字保持常规字形。

8. **调用与输出**
   - 输入顺序、3–5 个身份不变量、必要短文案、方案数量、比例、质量和保存路径均已确定。
   - `recipe.json` 与 `design-plan.json` 已保存；全部启用 Token 恰好投递一次，四域 binding 都有当前对象、模型动作、可见结果与垫图标记，只有确定性校正项进入 `preprocess_tokens`。
   - 手写提示词符合 `image-generation-workflow.md` 的最小合同，没有 Token 列表、失败案例、检查清单或手写 `Mechanism bindings`；主导参考的主体、背景和图文机制没有被禁项掏空。
   - typeset spec/report、design plan 与最终编译提示词中的标记双向一致；没有只在文档出现、未真正进入 Image 3 或 ImageGen prompt 的设计机制。
   - `scripts/prepare_generation.py` 返回 `READY`；随后只使用 `generation-call.json` 中的完整 `tool_arguments` 调用图像模型。

任一硬门失败时在生成前修复或明确降级，不“先生成看看”。门控通过后只生成用户要求的数量。

## 条件门

- 外国/纯外文参考：只迁移机制，由中文语义、目标几何和地域材料接管；删除原地名、人物、品牌、宗教符号与建筑身份。
- 字窗/多窗：容器与主体轴兼容，并完整保留至少一个身份区；宽阔多重檐或高频正立面通常不用字窗。
- 语义装饰：必须来自可见、用户确认或已核实内容，至少承担两项构图任务，最多进入三个角色。
- `layered-final-type`：仅在用户生成前明确选择且字体、蒙版、预留空间都已准备时启用。
- 多方案：Recipe family 与主布局不同，并在主体容器、字形动作、主材质、明度极性或边缘语言中至少另有一项可见差异。
