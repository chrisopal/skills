---
name: wechat-validated-article-pipeline
description: Use when a WeChat article must turn user-supplied requirements, logic, source materials, and a real-world validation scenario into an evidence-backed Official Account draft, especially when operational screenshots, artifact verification, privacy masking, editorial review, and draft readback are required.
---

# 微信公众号实证成稿流水线

把“观点写得像真的”改成“先做真的，再按证据写”。把真实场景验证作为写作前置条件，再调用现有公众号技能完成选题、写作、配图、排版、审核和草稿保存。

## 核心原则

只把已经由材料或真实操作证明的内容写成事实。文件存在不等于结果可用，接口返回成功不等于草稿可回读，截图存在不等于适合公开。

终点固定为：

> 已通过 `draft/get` 回读的微信公众号草稿，未发布。

本 Skill 永远不调用发布、群发或 `freepublish`。用户之后明确要求发布时，结束本流程并交给独立的人工确认流程。

## 需要调用的现有能力

按阶段加载，不要把所有 Skill 一次性塞进上下文。

- **REQUIRED SUB-SKILL:** Use `wechat-topic-planner` for topic identity, duplicate screening, title candidates, and article brief.
- **REQUIRED SUB-SKILL:** Use `wechat-article-writer` for the evidence-backed Markdown draft and illustration brief.
- **REQUIRED SUB-SKILL:** Use `wechat-article-human-tone-reviewer` before final review.
- **REQUIRED SUB-SKILL:** Use `wechat-article-layout` for cover, inline visuals, HTML, and mobile visual QA.
- **REQUIRED SUB-SKILL:** Use `wechat-article-reviewer` as the final editorial and risk gate.
- **REQUIRED SUB-SKILL:** Use `wechat-account-operator` for topic-pool and operational status updates.
- **REQUIRED BACKGROUND:** Understand `wechat-daily-pipeline` and reuse its workspace, draft-save, readback, and audit conventions. Do not invoke it again as a nested duplicate workflow after running the component skills above.
- Use the host `imagegen` capability for generated cover and explanatory visuals. Keep actual operation screenshots as actual screenshots.

## 输入合同

先读取 `references/intake-and-case-bundle.md`，把用户输入整理成八项：

1. 文章目标
2. 目标读者
3. 读完后的动作
4. 核心观点
5. 底层逻辑或 SOP
6. 要实际验证的场景
7. 可用材料、工具与环境
8. 验收证据与微信草稿边界

缺少不改变方向的字段时，做保守推断并记录。缺少真实场景、关键材料、操作环境或验收定义时，只补齐这些关键项；不要凭想象启动“实战复盘”。

在内容工作区创建：

`operations/<slug>-case-bundle.json`

然后运行：

```bash
python3 <skill-dir>/scripts/validate_case_bundle.py \
  operations/<slug>-case-bundle.json \
  --phase intake
```

修到 `VALIDATION PASSED: intake` 再继续。

## 工作流

### 1. 建立选题身份

调用 `wechat-topic-planner`：

1. 查重本地选题池、Get笔记主索引、近期标题和近四篇结构。
2. 解析或创建唯一 `topic_id`。
3. 写明目标读者、业务问题、核心观点、证据要求和转化动作。
4. 产出三个标题候选，但只把它们视为候选；真实验证结束后再定最终标题。
5. 把选题推进到 `SELECTED`，开始收集证据时推进到 `RESEARCHING`。

### 2. 建立方法线与证据线

同时维护两条线：

| 线 | 必须回答的问题 | 产物 |
|---|---|---|
| 方法线 | 这件事的底层步骤、判断点和验收标准是什么？ | SOP、比较维度、故事线 |
| 证据线 | 哪一步真实做过，结果由什么证明，哪些仍未知？ | 步骤记录、截图、产物、回读 |

不要先写长文再寻找能配上结论的截图。先把方法线变成可执行步骤，再逐步收证据。

### 3. 执行真实场景

读取 `references/evidence-and-draft-gates.md`，然后：

1. 在用户指定的真实工具和环境中执行，不用概念图代替实际操作。
2. 用户要求使用中文交互时，全程用中文与目标工具对话。
3. 每个关键步骤保留一张能独立说明动作和结果的截图。
4. 为每个步骤写 `evidence_ids`，为每条验收标准写对应证据。
5. 对生成物做真实回读：例如重新打开 PPTX、读取 API 结果、检查可编辑对象或验证最终文件，而不是只检查文件名存在。
6. 对截图逐张检查个人昵称、头像、账号、路径、令牌、错误提示和无关窗口。
7. 若错误影响结果，先修复并重做该步骤；不得通过裁掉报错把失败包装成成功。
8. 若错误与最终结果无关且只影响公开展示，保留内部原图，另存脱敏后的公开图，并在审计包记录处理。
9. 检查每个箭头、框线和标注是否指向正确对象；无法确认时删除标注。

把步骤、验收和证据写入 case bundle，然后运行：

```bash
python3 <skill-dir>/scripts/validate_case_bundle.py \
  operations/<slug>-case-bundle.json \
  --phase evidence
```

只有 `VALIDATION PASSED: evidence` 才能把场景写成“实测”“已验证”或“端到端完成”。

### 4. 用证据驱动成稿

调用 `wechat-article-writer`。把 case bundle、来源清单、限制和证据路径一起交给它。

优先采用下面的内容骨架；若用户的逻辑不同，保留“方法先于工具、证据支撑结论”的原则并调整章节：

1. 从一个真实工作冲突或结果切入。
2. 讲清底层 SOP：主题、读者、材料、大纲、故事线、内容契约、生产、验收。
3. 比较公开路线：输入、中间表示、输出、可编辑性、适用场景、限制。
4. 展开端到端实战：每一步做了什么、看见什么、如何验收。
5. 抽象成读者可复用的 brief、SOP 或检查表。
6. 说明仍未验证的边界，不补写“合理但没发生”的细节。

正文中的公开项目和工具优先引用官方文档、官方仓库或原始材料。把事实、推断、目标和个人判断分开表达。

### 5. 配图与排版

调用 `wechat-article-layout`：

1. 使用账号 `style-system.md`，默认保持明亮白底、墨绿主色、少量暖色强调；不要继承蓝紫赛博风。
2. 封面只讲一个主画面或 3–5 个模块，不把封面做成缩小版白皮书。
3. 真实步骤使用已脱敏的操作截图；流程、比较和抽象机制再用 `imagegen`。
4. 每张图必须有文章中的明确用途、放置位置、公开版本路径和简短说明。
5. 在移动端检查标题、箭头、标注、裁切和中文可读性。
6. 确认 HTML 中没有原生 `<ul>/<li>`，没有本地路径，没有 Markdown 链接残留。
7. 外部链接无法在微信正文稳定保留时，正文使用干净的项目名；完整 URL 留在本地来源清单和审计包，不把原始 `[标题](URL)` 放进草稿。

### 6. 两轮审核

先调用 `wechat-article-human-tone-reviewer`，再调用 `wechat-article-reviewer`。

每次修改正文后重新渲染 HTML。最终必须满足：

- 结论由证据推出，不由语气推出
- 至少五条已验证具体材料支撑长文
- 真实场景贯穿正文，不只出现在开头
- 截图无个人信息、无未解释报错、无错位箭头
- 标题、摘要、封面和正文承诺一致
- 无 Markdown 链接、本地路径、占位符和敏感凭据
- 人味审稿与最终审稿均为 `通过`

未通过时保留 `DRAFTING` 或 `READY_LOCAL`，不要保存微信草稿。

### 7. 保存并回读微信草稿

1. 先检查当前出口 IP 是否已在白名单。
2. 若已有同一文章的 `media_id`，更新原草稿；不要新建近重复草稿。
3. 只调用草稿新增或草稿更新接口。
4. 等待异步命令结束后再决定是否重试；在确认草稿列表前不要重复提交。
5. 用 `draft/get` 回读标题、摘要、封面、正文和图片。
6. 把回读结果保存到 `drafts/<slug>-draft-get.json`。
7. 只有回读成功后，才把 topic pool 状态从 `READY_LOCAL` 更新为 `DRAFT_SAVED`，记录 `media_id`、回读时间和审计路径，并同步 Get笔记主索引。
8. 补齐 case bundle 的 `article` 与 `wechat` 字段，运行：

```bash
python3 <skill-dir>/scripts/validate_case_bundle.py \
  operations/<slug>-case-bundle.json \
  --phase draft
```

只有 `VALIDATION PASSED: draft` 才能汇报“已保存草稿，未发布”。

## 失败处理

| 失败点 | 正确状态 | 继续动作 |
|---|---|---|
| 材料或验收定义不足 | `SELECTED` / `RESEARCHING` | 补材料、缩小场景或降低文章范围 |
| 真实操作或产物回读失败 | `RESEARCHING` | 修复并重跑，不写成成功案例 |
| 审核未通过 | `DRAFTING` / `READY_LOCAL` | 修改 Markdown、重排版、重审 |
| IP 白名单或凭据失败 | `READY_LOCAL` | 保留本地产物并报告阻塞 |
| 草稿写入返回但无法回读 | `READY_LOCAL` | 查草稿列表与任务终态，不重复提交 |

不要用截止时间降低证据标准。时间不够时，缩短文章或停在本地交付；不要把“差不多完成”改写成“已验证并保存”。

## 常见误判

| 误判 | 纠正 |
|---|---|
| 文件生成了，所以结果已验证 | 重新打开或通过目标应用/API回读 |
| 有截图，所以可以公开 | 逐图检查隐私、错误、箭头和可读性 |
| 报错裁掉就不影响文章 | 先判断是否影响结论；影响结论必须修复重跑 |
| API 返回 `media_id`，所以草稿已保存 | 必须 `draft/get` 回读 |
| 截止时间紧，先保存再补证据 | 保持 `READY_LOCAL`，缩短范围或补证据 |
| 原始 Markdown 链接会自动变成微信链接 | 检查最终 HTML 与回读正文，清除残留 |

## 审计包

最终报告必须包含：

- 标题、摘要、目标读者、核心观点
- `topic_id` 与最终状态
- 来源和材料清单
- 真实场景、步骤、验收结果和限制
- 原始证据与公开脱敏图路径
- Markdown、HTML、封面和正文图路径
- 两轮审核结论
- 微信 `media_id`、`draft/get` 路径和回读时间
- 明确结论：`已保存草稿，未发布`

若任何一项未完成，按真实状态汇报，不输出这句完成结论。

## 资源

- `references/intake-and-case-bundle.md`：八项输入、case bundle 字段和示例
- `references/evidence-and-draft-gates.md`：证据、截图、产物回读和微信草稿门
- `references/orchestration-map.md`：现有公众号 Skill 的阶段映射与交接物
- `scripts/validate_case_bundle.py`：三阶段确定性校验器
- `scripts/test_validate_case_bundle.py`：校验器行为回归测试
