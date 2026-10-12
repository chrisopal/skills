# 从首次拜访到合同签订：一个连续案例

案例客户为虚构的华辰装备，购买售后工单平台一期，30个账号。销售顾宁、售前林工与技术周工推进，王敏负责业务、李工负责IT、陈经理负责采购、赵总决定预算和最终采购。所有人物、意见、竞争报价、授权与签署均为模拟。案例中的分析、增量存储、阶段核验、版本登记及回读真实运行。

总控始终是 opportunity-orchestrator；下表列出本次业务能力。Skill 是 Agent 执行指引，运行日志记录共享 CLI 的实际调用，不将其描述为七个独立 Agent 自动协同。

| 时间点 | 主 Skill | 输入 | 输出 | 管理页面与正式阶段 |
|---|---|---|---|---|
| 7月6日首访 | opportunity-analysis-skill / opportunity-pursuit | 拜访纪要、王敏原话 | 画像、痛点假设、18维评估、调研行动 | 拜访/概览；客户接触 |
| 7月13日调研 | opportunity-solution-validation → presales-orchestrator / presales-requirements | 联合访谈、账号及接口材料 | REQ-01至05、成功标准、未知项 | 需求矩阵；需求澄清 |
| 7月20日资格 | opportunity-analysis-skill / opportunity-pursuit | 决策链、直销路径、继续推进意愿 | 投入判断、策略及方案任务 | 商机判断/雷达/决策链；商机确认 |
| 7月30日V1 | opportunity-solution-validation → presales-solution-design | 需求R1、接口及离线未知项 | 方案V1、范围及验证计划 | 方案版本/响应；方案共创 |
| 8月3日评审 | opportunity-solution-validation / opportunity-analysis-skill / opportunity-pursuit | 客户退回V1的三条原话 | RV-01至03、责任、整改与评分下调 | 客户意见/整改；仍在方案共创 |
| 8月20日V2 | opportunity-solution-validation / presales-solution-design | V1评审意见、修订及模拟演示结果 | V2、逐项复审与关闭依据 | 方案对比/验证；仍在方案共创 |
| 8月25日预算 | opportunity-commercial / opportunity-analysis-skill | 40万元预算批复、范围V2 | 预算事实、报价任务与资源判断 | 预算/采购里程碑；预算/立项确认 |
| 8月28日报价 | opportunity-commercial / opportunity-pursuit | V2、成本估算、Q1授权 | 38.8万元Q1、授权与提交记录 | 报价版本/提交；报价/投标 |
| 9月4日竞争 | opportunity-pursuit / opportunity-analysis-skill | 两家低价转述、客户异议、Q1 | 有来源的竞争矩阵、评分下调、跟进行动 | 竞争/价格差异；仍在报价/投标 |
| 9月15日谈判 | opportunity-negotiation / opportunity-commercial | 客户诉求、Q1、内部让步范围 | N1、35.8万元Q2及新授权、30/60/10付款 | 条款差异/授权；商务谈判 |
| 9月25日待签 | opportunity-closeout / opportunity-negotiation | C1、N1、Q2、V2 | 主体/金额/范围核对、签署缺口 | 合同/签署核验；合同签署 |
| 10月9日签署 | opportunity-closeout | C2模拟双方签署及版本核对 | 模拟赢单、H1交接、首款与启动待办 | 签单归档/交接；已签单 |

## 两次回流和签单条件

V1的问题不另建商机：RV-01工作时段计时关联REQ-02，RV-02离线/冲突关联REQ-04，RV-03工期依赖关联REQ-03。修订成V2后，以客户模拟复审EV-06逐项关闭本轮意见，生产联通、现场压力与最终验收继续保留待验证。方案文件存在与客户认可分开，开过评审会不会自动推进阶段。

迅达约32万元、启维约36万元为采购转述，范围和含税口径未知；不能宣称对方缺少离线能力。9月4日竞争与价格评分下降，先核对同范围价值，再把报价/付款/范围一起谈。Q2保留V2完整范围，单独登记35.8万元授权，旧Q1批准不自动转移。

合同C1没有双方签署时，实际尝试赢单会失败，正式版本不变。C2是明确标为纯模拟的签署场景文件，运行层据模拟记录完成赢单；不能据此宣称真实法律签署。35.8万元签单额不记成回款、收入或验收；交接保留首款10.74万元、ERP生产联通与现场压力测试待办。

## 页面与复现

从本 Skill 的 scripts/case_study.py 运行，output 必须是新的空目录：

```bash
python3 /absolute/skills/opportunity-orchestrator/scripts/case_study.py --output /absolute/project/full-case
```

生成 index.html、light/01.html至12.html、dark/01.html至12.html、case-report.md，以及 sources、documents、stages 和 requests。每个时间点立即回读并冻结当时数据，页面不提前展示后续预算、报价或签署。业务日期是场景时间，审计时间是实际执行时间。

每页五个工作面为「概览与评估」「方案与客户评审」「竞争与决策链」「商务与合同」「Skill交接」。时间点、页签、主题、原文下载和商机详情链接实际可用；这是本地只读案例工作台。方案交付本次限定为需求与两版方案工作稿，不宣称PPT、真实POC、生产验收、客户外发或CRM在线编辑已经实现。

雷达复用既有18维分组渲染，按同一时点的commercial_assessment生成。参考分序列52→52→62→64→63→75→82→82→79→84→84→84；未知项按既有引擎40分占位，不代表已证实。正式阶段与签署依据独立登记，最终评分保留84，不机械改成100%成交概率。

## 评审和版本依赖回读

RV-01至03通过manage实际登记并绑定SOL-1，复审时逐条绑定SOL-2和EV-06关闭，页面只读取lifecycle.reviews。Q2依赖SOL-2，N1依赖Q2，C2依赖Q2/N1，H1依赖C2；均保留具体摘要。上游替代或文件变化会触发意见复核和下游失效，不能靠高评分继续推进。
