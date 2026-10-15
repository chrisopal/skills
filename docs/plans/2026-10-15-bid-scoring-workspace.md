# 配置页 AI 模拟评分入口

## UI Blueprint

- 保留现有章节导航、正文编辑、依据面板和设置字段；沿用 enterprise-ui-design 的蓝色语义变量、描边次要按钮、键盘焦点与浅深主题。
- 设置面板首部增加 AI 模拟评分工作区：版本状态、已评分/已评上限、待核验上限；紧凑操作组包含模拟评分、查看报告、刷新结果和按选中扣分项提升。
- 扣分项以可选择的表格呈现评分项、失分、原因和建议；原文依据及执行交接放入可键盘访问的详情。资格、材料、价格问题保留补料状态。
- 设置表单按写作、篇幅、配图、章节覆盖分组，长说明移入详情，不改变保存契约。未保存正文或设置时禁止发起任务，刷新评分不重置编辑内容。
- 390px 使用单列和局部表格滚动；1366/1440/1920px 保持三栏工作台与可换行按钮组。

## 执行契约

- state 增加 ai_scoring；GET /api/ai-scoring 仅刷新评分状态；POST /api/ai-scoring 创建任务；GET /api/ai-scoring/report 从当前合法 JSON 动态渲染只读报告。
- POST: action=score|improve, request_id=UUID, expected_revision, expected_sha256；improve 另传 scoring_sha256、target_ids。
- 返回 available/error/latest_report/latest_request/host_execution=manual_handoff；latest_report 包含 relative_path、sha256、revision、valid/current、summary、rows 和 report_url。
- 任务保存于 work/ai-scoring-actions，保留幂等、并发写保护、输入版本绑定和 claim/finish；prepare 只准备评分，host_prompt 才描述实际模型评读。状态不能把交接当评分完成。
- 完成评分必须回读当前完成态评分；提升必须有范围内正文变化和新版本重评分。客观证据、价格及未知项不能靠润色补齐，模拟分不替代原有资格/废标审核。

## 验证

- 单元及 HTTP：无报告、有效/过期/损坏报告、CAS、幂等/重复请求、路径/来源限制、范围外修改、未实际评分不可完成。
- 浏览器：三步入口、交接复制、未保存修改保护、报告、扣分选择、空/错误状态、浅深主题和窄宽屏。
- 独立测试项目执行一次真实宿主评分和一次内容提升/重评；保留无法核验的价格、模拟材料和原审核阻塞。
- 无新增依赖；生成项目、报告和截图只在本地。刷新分发包并运行套件回归后提交推送。
