# 证据采集、冲突与核验闭环

版本1.0.0。用于真实资料到事实底座的交接，不替代制造业访谈题库。
智能工厂沿用 manufacturing-planning-toolkit.md 第1节的角色、问题和材料清单。

## 每条采集任务

记录 request_id、待支持的结论/流程/KPI、受访角色及组织层级、
问题、原始材料要求、期间/样本/排除项、采集Owner、截止日期、
访问权限与脱敏要求、状态和关联Evidence ID。没有材料时保持待采集。
同一关键命题至少设计“怎样支持”和“怎样推翻”的核验路径；
不同工厂、班次、产品族分别采样，不从单一访谈推断集团现状。

## 每条证据

来源必须可定位：文档页/段/表、录音时间戳、文件与行号，或受控查询ID、
筛选条件和数据快照。登记source_owner、source_date、location、
raw_excerpt和scope；摘录遵守访问与脱敏限制，敏感原文可改为受控摘录引用。
问卷答案为观点，原始记录为观察，推导结论为分析，不混用。

升级verified时，按 evidence-item.schema.json 补齐上述字段和verification：
reviewer、checked_at、method、result_evidence_ids。Schema通过仅证明字段齐备，
复核人仍需回读原始材料、重算关键指标，并检查核验引用确实存在。
未知值省略或保持unverified，不用“待补”字符串冒充已核验。

## 冲突与假设

冲突保留双方Evidence ID、不同口径/期间/范围及各方观点；
status=conflicted必须有conflicts_with与verification_plan(owner,due_date,action)。
核验结果新增证据，不覆盖旧证据；未关闭冲突不得以高置信事实进入投资测算。
假设登记提出理由、业务影响、验证人/期限/材料、失败时受影响成果，
并保持assumed/draft，不因PPT排版或技术检查升级状态。

## 关闭采集任务

满足材料已取得、原始定位可打开、Owner核验、冲突处理可追溯后才能完成。
超期/拒绝提供只改变采集状态，不自动生成事实。范围调整需回到G0；
证据变更按 phase-one-planning.md 触发G1—G3及受影响下游重审。
