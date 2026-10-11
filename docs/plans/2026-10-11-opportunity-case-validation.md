# 连续商机案例验证

## 交付

- 可复用源：opportunity-orchestrator/examples/full_lifecycle.py、scripts/case_study.py、assets/case.css、tests/test_case_study.py；入口及参考文档已关联案例。
- 本地结果：output/opportunity-full-lifecycle-case-20261011/。单商机 opp_e758de6f4548，12个分时输入、9次正式迁移、两版方案/报价/合同及签约交接。每个时间点有亮暗工作台与同时间点运行层详情。
- 评分序列：52、52、62、64、63、75、82、82、79、84、84、84。方案匹配单项65→25→100；低价竞争后综合82→79。赢单仍保留84参考分。

## 实际验证

| 范围 | 命令/证据 | 结果 |
|---|---|---|
| 分析、展示与生命周期回归 | PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=opportunity-analysis-skill/src python3 -m unittest discover -s opportunity-analysis-skill/tests -v | 42通过 |
| 分时案例、分发与原主线 | PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s opportunity-orchestrator/tests -v | 10通过，包含5个新增案例测试 |
| 技能结构 | scripts/validate_suite.py、analysis scripts/validate_skill.py、Skill Creator quick_validate.py | 7个入口/本地引用/编译/原验证通过，修改入口有效 |
| 可移植性 | install.py导出7个同级Skill，再从导出副本运行case_study.py | 12个时点完整跑通，评分一致；副本在output/opportunity-full-case-portability-20261011/ |
| 状态与未来事实隔离 | tests/test_case_study.py | 只有同一ID，证据随时点累积；首访页不提前显示35.8万及V2认可 |
| 评审/竞争回流 | 测试及stages/04至06、08至09/snapshot.json | V1退回与V2复审均留在方案共创；意见关闭及评分下降可回读 |
| 报价与签署 | 测试、requests/reject-unsigned.json及对应CLI失败日志 | Q2单独授权；无签署赢单失败且版本不变；C2绑定358000元，A-09首款待办保留 |
| 页面链接 | 新增测试及独立复核 | 工作台、原始详情、源与成果文件本地链接可解析 |
| 真实浏览器页签 | screenshots/tabs-acceptance.json | 24个时间点/主题页 × 5工作面，共120项；选中状态、单一可见面板和雷达结构通过 |
| 真实浏览器响应式 | screenshots/responsive-acceptance.json | 1366/1440/1920/390px，亮暗×评审/竞争/签署，共24项无页面横向溢出 |
| 键盘、原文回读 | 浏览器ArrowRight/Home；实际点击V2链接回读五需求机制与边界 | 页签选择和焦点一致，V2实际可读 |
| 对比度 | screenshots/contrast.json | 12个关键文字/背景组合最低4.85:1 |
| 截图 | screenshots/review-closed-light.jpg、review-closed-dark.jpg、light/dark-1440-5.jpg、light/dark-390-12.jpg | 企业UI蓝图与亮暗/窄屏已视检；无目标图片逐像素一致性声明 |

初次单独运行analysis测试遗漏PYTHONPATH，产生导入错误；使用上述正确命令后42项全部通过。新增案例初稿存在运行层字段名误用，已按实际回读结构修正并通过完整案例测试。

## 独立复核及整改

独立只读Agent检查了代码、模拟业务一致性、快照、链接及5个案例测试，发现RV-03指责“无条件8周”与V1已有通用前提矛盾。已改为“具体沙箱日期及延期处理不充分”，对应客户原话、评分依据与页面同步；V1、V2及评审形成一致闭环。浏览器复核另修正V1退回页错误的“等待评审”摘要，文件链接使用业务标题。

## 限度

客户、价格、竞争、授权、演示及双方签署全部为模拟。共享CLI执行事实不等于真实客户接受、实际签字、回款、收入、生产ERP联通或交付验收。售前本次为需求和方案工作稿，未制作PPT；业务Skill按Agent指引处理，未宣称独立多Agent自动调用。工作台为本地只读案例页面，未实现在线CRM编辑、审批身份校验或外部同步。

无新增依赖。仓库没有本案例独立的lint/typecheck/build配置；Python结构/编译与回归测试已执行。独立复核的LSP因无tsconfig跳过、ast-grep未安装，不报告Python静态类型检查通过。视觉结论针对企业UI蓝图与实测页面，未提供像素参考图。输出、DB、截图及测试安装副本不进入提交。
