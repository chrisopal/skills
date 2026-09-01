# 验收测试

## 测试 1：证据隔离

给定一条管理层访谈观点和一组相反运营数据，系统必须保留冲突，不得将访谈自动写成事实。

## 测试 2：跨模型追溯

随机选择一个 Initiative，必须能追溯到 Gap、目标能力/流程、现状问题、KPI 和 Evidence。

## 测试 3：As-Is/To-Be 分离

As-Is AA 中不得出现未部署目标平台；目标架构不得伪装成现状。

## 测试 4：Operating Model 与 BA 单一源

同一 Capability、Process 和 KPI 在 Operating Model 与 BA View 中必须使用相同 Node ID；若名称、层级或 Owner 不一致，测试失败。

## 测试 5：4A 纵向追溯

随机选择一个目标 Application Service，必须能追溯到：

- BA Capability / Process / Business Service；
- IA Business Object / Information Flow / Data Product；
- TA Technology Service / Platform；
- Gap、Initiative 和 Roadmap Wave。

缺少任一关键关系时，G4 不得通过。

## 测试 6：IA 不是平台清单

若 IA 仅列出数据湖、数据仓库、主数据平台等产品，而没有信息域、业务对象、标准、责任和信息流，则测试失败。

## 测试 7：AA 不是系统堆叠

若 AA 只有系统盒子，没有 Application Service、能力/流程映射、业务对象和集成语义，则测试失败。

## 测试 8：TA 不是设备清单

若 TA 只有云、服务器、网络和产品清单，没有 Technology Service、NFR、运维、韧性和支撑关系，则测试失败。

## 测试 9：路线图依赖

一个依赖主数据治理、集成平台和 AI Runtime 的 Agent 场景不得排在基础举措之前，除非明确作为隔离 POC 并记录风险。

## 测试 10：Transition Architecture

每个 Roadmap Wave 必须记录阶段性 BA/IA/AA/TA 状态，以及新建、改造、整合、迁移和退役动作。

## 测试 11：商业论证

同一效率收益不能同时完整计入流程优化 Initiative 和 AI Initiative；必须拆分归因或去重。

## 测试 12：PPT 不创造结论

Slide Content Pack 中的每个数字、架构组件和 Initiative 必须存在于已批准 Artifact。

## 测试 13：详细流程范围

快速诊断工作流不得自动把全企业流程下钻到 L5。

## 测试 14：AI 4A 完整性

对一个关键 Agent 场景，必须同时存在 BA+AI、IA+AI、AA+AI、TA+AI 设计，以及阈值、人工升级、审计和回滚。
