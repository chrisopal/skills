# 规划验证底稿JSON约定

这是跨成果的轻量核验投影，不替代各Skill的完整Artifact。真实项目仍需证据、审批及专业评审。生成实例放项目输出目录，不混入源代码。

顶层 `artifact_header` 使用共享Header；`evidence` 为带id、来源类型及status的证据列表。模拟数据使用assumed，整体不能伪装approved。

| 集合 | 必需字段 |
|---|---|
| processes | id, name, level(1—4), parent_id(L1为null), owner；L4另含inputs, outputs, control_points, information_ids, application_ids, kpi_ids |
| information_objects | id, name, owner |
| applications | id, name, process_ids, information_ids, technology_ids, lifecycle |
| technology_services | id, name, application_ids, nfr |
| kpis | id, name, formula, owner, baseline, target, aggregation |
| initiatives | id, name, process_ids, application_ids, kpi_ids, depends_on, wave_id |
| waves | id, name, initiative_ids；按实施先后排列 |

未知基线用带status和采集计划的对象，禁止伪造数值。所有引用必须解析到本底稿对象。父节点恰好上一级；每个范围内的L1—L3至少有一个子节点。举措强依赖在此前波次完成；同波次存在强依赖时在投影中拆为先后子波次，防止日期顺序不明。

`financials` 含currency、unit、costs、benefits、annual_cash_flow。成本行含initiative_id/year/amount；收益行含唯一归因id/initiative_ids/year/amount/basis；现金流行含year/cost/benefit/net/cumulative。相同收益可跨年，不能同年重复。amount非负有限数，年为整数且现金流按年排序；net=benefit-cost，cumulative逐年累加。成本和收益均需列零金额年份以保留整个评价期。

工具不计算业务因果，不解析自由文本公式，不自动确定折现率或批准投资。收益basis另附基线×改善率×兑现率×爬坡明细；情景、折现、回收期与可行性由独立Reviewer复核。状态检查保守：包含assumed证据的模拟底稿不接受validated/approved；真实项目如需保留已批准估算，应在单独真实项目规范中标明批准对象与假设，不使用本模拟投影升级状态。
