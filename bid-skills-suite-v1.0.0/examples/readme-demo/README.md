# 模拟招标 · 输出示例

这是一份可分享的模拟案例快照，用来查看投标 Skill 的实际输出形式。项目为“青禾园区事件闭环平台”，编号 `SIM-WB-20261011`，采购内容、金额和事件记录全部为模拟数据；不含真实招标原件或企业资质。

## 看什么

| 阶段 | 示例内容 | 文件 |
|---|---|---|
| 输入 | 软件集成 + 一年运维；单一标包 | [Markdown 原文](inputs/tender.md)、[DOCX 原件](inputs/SRC-001-模拟招标文件.docx) |
| 理解 | 基础信息、组合模板、12 条原子需求、评分规则、资格否决、强制格式 | [HTML 报告](reports/tender-report.html)、[需求 JSON](artifacts/03-requirements.json)、[评分 JSON](artifacts/04-scoring.json) |
| 目录 | 9 个目录节点；需求、评分、材料和图的章节关联 | [目录展示](outline.html)、[目录 JSON](artifacts/08-outline.json) |
| 写作 | 仅 4.1 事件闭环管理候选稿，未正式采纳 | [正文展示](writing.html)、[Markdown 草稿](artifacts/11-chapter-4.1.md) |
| 配图 | SVG 六状态流程；宿主实际生成的界面示意图 | [配图展示](visuals.html)、[SVG](assets/fig-4.1-event-flow.svg)、[JSON 图源](assets/fig-4.1-event-flow.diagram.json)、[界面原图](assets/fig-4.1-ui.r3.png) |
| 评审 | 17 项逐项结论、9 项未关闭问题、4 项阻塞问题 | [HTML 评审报告](reports/repair-review-report.html)、[评审 JSON](reviews/15-review.json) |
| 导出 | 6 页单章样稿；9 条目录链接；2 张实际嵌入图片 | [Word](deliverables/chapter-4.1-sample.docx)、[PDF](deliverables/chapter-4.1-sample.pdf)、[校验值](deliverables/SHA256SUMS) |

GitHub 会展示 Markdown、JSON 与截图，但 HTML 通常显示源码。下载仓库后双击 [index.html](index.html) 即可离线查看，或从套件目录启动只读文件服务：

```bash
python3 -m http.server 8780 --bind 127.0.0.1
```

然后打开 `http://127.0.0.1:8780/examples/readme-demo/`。查看示例不需要启动 Bid Agent 后端、安装办公软件或提供模型 Key。

## 演示边界

- 本例实际运行了原件解析、分类、需求、评分、合规、格式、目录、材料缺口、单章候选写作、配图和限定范围评审。没有把未执行的响应策略、完整技术设计、商务填报或整本编写伪装成已完成。
- 原文原生提取的覆盖状态仍为 `partial`；DOCX 的文本框、修订等复杂内容未在这份原件上验证。原文没提供的字段保留缺失。
- 100 分是规则满分；4.1 关联评分的 25 分是原文最高分，均非实际得分。营业执照、签署盖章、合同与验收证明未提供，评审保持阻塞，不能真实递交。
- 界面图由 WorkBuddy 原生 ImageGen 生成；SVG 由绘图 Skill 渲染。两者都为响应设计示意，不是系统实现或企业能力证据。
- Word 样稿在 Mac Word 更新目录、保存重开并实测跳转；对应 PDF 经 LibreOffice 转换并逐页检查。分享版 Word 仅移除了修改者元数据，其他 ZIP 条目（包括文档 XML、目录与媒体）均与已检查版本一致；PDF 字节与已检查版本一致。Windows Word、整本与复杂附件不在此验收范围。
- `artifacts/`、`reviews/`、`work/` 保留既有版本与追溯信息，不把历史提醒改写成新结论。例如正文中的旧版 r2 配图提醒仍保留，实际展示的是 r3 图；不应只凭这份文档展示页宣布完整项目通过。此目录是展示快照，不是可恢复的全部工作目录或完整审计证据包。
- 五个示例 HTML 展示页由 `render_demo.py` 读取保存的 JSON 与草稿生成。招标理解和逐项评审 HTML 是套件报告的实际输出。页面本身不调用模型、不执行修改、不自动关闭评审问题。

## 自己试一次

先按[套件 README](../../README.md#通用-npx-安装)安装 17 个投标 Skill 和绘图 Skill。在自己的独立项目中新建 `inputs/`，复制模拟原件，再向宿主发送：

> 调用 bid-orchestrator，项目目录为【我的项目绝对路径】。这是完全模拟的功能测试，不做真实投标。先解析 inputs 中的招标文件，识别标包和类别，提取需求、评分、资格否决与强制格式，保存原文追溯并生成 HTML 报告。之后基于已确认范围规划目录，编写 4.1 事件闭环管理候选稿，输出 SVG 流程图和宿主实际生成的界面设计示意，运行限定范围评审并导出 Word/PDF 样稿。缺失材料保留阻塞，不把设计描述视为实际能力。

新结果写入自己的项目，不覆盖这个展示快照。需要重建五个文档展示页时，从套件目录执行：

```bash
python3 examples/readme-demo/render_demo.py
```

该命令只重建展示页，不重新解析原件、运行 Agent、生成图片、刷新 Word 目录或审核标书。
