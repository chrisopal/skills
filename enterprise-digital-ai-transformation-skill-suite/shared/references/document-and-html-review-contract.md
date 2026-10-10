# 文档写作与HTML审阅契约

## 分工与调用

本能力作为17个业务Skill之外的表现层接入，不增加咨询专业Skill，也不赋予总控写作或分析职责。

| 工作 | 唯一主Skill | 输入 | 输出 |
|---|---|---|---|
| 阶段结论和底稿 | 当前阶段专业Skill | 证据、模型和已批准前置成果 | 版本化候选Artifact |
| 过程报告的语言组织 | 项目指定的文档写作Skill | 锁定版本的候选成果、读者和决策问题 | 可读报告草案与来源映射 |
| 正式汇报内容编排 | transformation-storyline-builder | 已批准成果；或明确simulation草案入口 | 故事线和PPT内容包 |
| HTML审阅面 | enterprise-ui-design | 报告、流程与架构模型、PPT内容包 | HTML、来源清单、审阅意见文件 |
| 可编辑图示 | drawio 或项目已选图示Skill | 已确定的节点和关系 | 图源及HTML可读图示 |
| Word文件 | documents 或项目已选Word写作Skill | 已审核报告、图示、版式要求 | DOCX及逐页渲染核验记录 |
| 图片PPT | consulting-ppt-image（用户指定时） | 经实际确认的内容与样式版本 | 图片型PPT及回读结果 |

真实执行前必须读取所选外部Skill完整入口及适用参考，不把名称写进提示词视为已经调用。文档路由必须解析到当前宿主实际可用的Skill位置并记录版本；没有工具或依赖时明确blocked，只保留可读HTML/Markdown，不声称Word已生成。不得以云端文档服务为默认降级而上传客户资料。此仓库提供SOP和本地渲染器，不宣称实现WorkBuddy自动事件调度。

## 阶段触发

每阶段专业成果保存后，总控依次下发独立任务卡：文档写作 → HTML派生视图 → consulting-quality-review → 人工Gate。每张卡只有一个主Skill，并传递输入ID/版本/状态、输出版本和验收条件。没有报告写作需求的模型阶段可直接渲染结构化模型，不生成无意义的长文。

HTML审阅必须允许显示候选draft，否则无法支持审批前阅读。这不改变真实项目各阶段的前置Gate要求；未经批准的前置成果不能借展示链路继续开展下游咨询。simulation可按现有模拟入口推演，全部假设/草案标签保留。

S8在图片生成前显示逐页标题、核心结论、正文、关键数字、证据、图示意图及版式样例。HTML排版示意不是最终图片，最终成图仍须审校。用户对内容/样式的实际确认单独记录，不与业务投资批准混淆。用户未确认时可以生成HTML审阅草案，不得伪造approval_ref或启动受确认门槛约束的PPT正式生产。

## 单一来源与写作约束

- 报告先说明本阶段结论、范围和待决策事项，正文说明依据、原因、选择及约束；术语首次出现用中文解释。文档写作只能改善表达，不能补造访谈、成熟度、收益或客户承诺。
- 源文件保持不可变；派生物独立版本。记录artifact-header、源ID/版本/状态、SHA-256、生成Skill/版本、主题版本及Reviewer。HTML显示的源状态不等同于页面已获批准。
- L1—L4从模型生成，不按排版重新归类；同一节点ID在报告、BA、图示、表格和PPT中保持一致。As-Is、To-Be、Transition各自可辨，不把目标系统放进现状。
- 4A除了四域总览还必须能查域间关系：AA→BA流程/能力、AA→IA对象、TA→AA/IA。总览省略的关系必须可在明细或来源中查看，禁止用四排系统名代替架构。
- 数字始终保留单位、周期、口径、假设和来源。改动语义须退回上游生成新版本并重审，不能只改HTML或PPT。

## 展示与交互

HTML遵循enterprise-ui-design的tokens.json与检查清单：蓝灰主色、浅深主题、扁平布局、正文可读密度、可识别操作、可见键盘焦点、响应式。样式适用于过程报告与PPT审阅外壳；最终PPT遵守已确认的主题，不把审阅外壳截图冒充成稿。

最低视图为报告正文、可展开四级流程、4A关系与明细、组织/KPI、投资路线图、逐页PPT审阅。没有源数据的视图显示缺失，不填装饰性统计。过程阶段可只提供当期可用视图。必要表格在容器内滚动；长ID放可键盘展开的详情。保留本地原始文档访问或来源下载。

无后端时，审阅意见只在当前浏览器内编辑并导出文件，明确保存范围；不要出现会伪造批准的“通过Gate”按钮。意见文件记录源版本/哈希和逐页意见，不自动回写approved。源变更后旧意见不能被当作新版本确认。

## 本地渲染与验收

`scripts/render_review_workbench.py`读取显式指定的规划底稿、报告和PPT内容包，生成离线HTML。当前适配的是`planning-pack-contract.md`数据结构；不能宣称支持任意Markdown扩展或完整企业架构仓库。调用示例：

```sh
python3 scripts/render_review_workbench.py \
  --pack /absolute/project/planning-pack.json \
  --report /absolute/project/report.md \
  --slides /absolute/project/slide-content-pack.json \
  --tokens /absolute/enterprise-ui-design/assets/tokens.json \
  --out /absolute/project/review-v1/index.html
```

验收分开记录：源数字/引用一致性、HTML构建、真实浏览器交互、浅深主题与1366/1440/1920/390宽度截图、键盘和长内容、Word逐页渲染、PPT复开回读、WorkBuddy实际调用、客户人工批准。未执行项目标未验证，不以脚本成功替代其他项目。
