"""Authored fictional case. Dates are scenario dates, not runtime audit timestamps."""

CASE = {
    "customer": "华辰装备有限公司", "supplier": "启程数字科技有限公司",
    "name": "售后工单平台一期", "owner": "顾宁", "amount": 358000,
    "roles": [
        ["王敏", "售后业务负责人", "需求与业务评审", "2026-07-06 首访"],
        ["李工", "IT负责人", "接口、安全、技术评估", "2026-07-13 调研"],
        ["陈经理", "采购经理", "询价与商务条件", "2026-07-20 资格确认"],
        ["赵总", "运营副总", "预算与最终采购决定", "2026-07-20 资格确认"],
    ],
}

DOCUMENTS = {
    "requirements.md": """# 客户需求工作稿 R1（模拟）

来源：EV-02，2026-07-13 调研。以下优先级由模拟业务负责人王敏明确。

| ID | 需求与原话 | 优先级 | 成功标准 | 范围与待澄清 |
|---|---|---|---|---|
| REQ-01 | 王敏：报修后必须有编号，接单、派工、完工和回访能追踪 | 必须 | 五个模拟场景状态及操作人、提交时间可追溯 | 一期仅国内售后团队30账号 |
| REQ-02 | 王敏：派工超过两小时要提醒主管 | 必须 | 工作时段内到期提醒；测试跨班次及节假日 | 工作日09:00–18:00；非工作时段暂停计时 |
| REQ-03 | 李工：从ERP取得客户和设备档案 | 必须 | 测试100条；重复、缺字段、接口失败可识别与重试 | ERP接口文档及沙箱尚未交付 |
| REQ-04 | 王敏：现场网络不稳也要记录，恢复后不能重复 | 必须 | 断网创建20单，恢复后单号不重复、图片完整 | 同一工单双端修改冲突规则待评审 |
| REQ-05 | 李工：区域人员只能看本区域工单 | 必须 | 跨区域访问拒绝，操作日志可导出 | 客户部署；保留期180天为建议，待确认 |

业务目标：减少漏单并建立响应时长基线。客户没有给出现状漏单率和节省金额，不生成收益百分比。范围外：ERP写回、备件库存核算、海外语言、历史纸档清洗。
""",
    "solution-v1.md": """# 售后工单平台方案 V1（模拟候选稿）

关联：需求R1 / EV-02、EV-03。用途：2026-08-03客户评审，未获客户认可。

## 业务机制
REQ-01：服务台登记报修生成编号，主管分配工程师，工程师提交处理记录，王敏团队回访关闭。状态变更保存操作人和时间。
REQ-02：初版按自然时间计时，两小时未派工通知主管；工作日规则尚未设计。
REQ-03：ERP→接口适配→客户/设备主档→工单引用。仅设计读取接口，文档、沙箱和实际连通性未知，不宣称已打通。
REQ-04：在线移动表单上传照片并保存；离线及双端冲突尚未覆盖，列为关键缺口。
REQ-05：按组织区域过滤查询和下载，服务端再次校验权限；日志180天待IT确认。

## 系统边界与非功能
服务台网页、工程师移动网页、业务服务、关系数据存储与文件存储；部署在客户提供环境。目标并发30账号，备份每日一次、恢复目标8小时均为候选，需验证后锁定。无外部认证已接入的声明。

## 实施与验证
建议8周：需求/接口确认2周，配置开发3周，联调1周，业务测试1周，上线准备1周。起算依赖接口资料、环境和关键用户到位。用五场景脚本验证需求；此时尚未执行客户POC。

## 决策记录
选择一期只读ERP，降低双方改造及回滚复杂度；拒绝一期双向同步，因为客户未授权ERP写回。离线能力属于待评审定制，不能以标准功能承诺。
""",
    "customer-review-v1.md": """# 2026-08-03 客户评审记录（模拟）

对象：方案V1。王敏与李工参加；结论：有条件退回修订，不能报价。

| 问题 | 来源/需求 | 客户意见 | 责任人 | 关闭要求 |
|---|---|---|---|---|
| RV-01 | 王敏 / REQ-02 | 夜间两小时提醒不合理，须按工作时段计时 | 售前林工 | V2规则及跨班次测试 |
| RV-02 | 王敏 / REQ-04 | 没有离线记录不能用于现场，双端修改不能静默覆盖 | 技术周工 | 明确离线队列、去重和冲突处理，演示20单 |
| RV-03 | 李工 / REQ-03 | ERP沙箱交付要到8月17日，现有起算前提不够具体，需写明日期与延期影响 | 销售顾宁 | 起算前提和延期影响写入V2 |

采购陈经理：预算暂不批复，先完成这三项；此为模拟案例意见，不是真实客户确认。
""",
    "solution-v2.md": """# 售后工单平台方案 V2（模拟修订稿）

关联：需求R1、评审RV-01至03、EV-05/06；替代V1。客户模拟演示认可只覆盖下述验证范围，不等同上线验收。

## 范围与机制
REQ-01：保留服务台→主管→工程师→回访流程及编号、操作人、提交时间。
REQ-02 / RV-01：日历定义工作日09:00–18:00。非工作时段暂停计时，节假日由主管维护。到累计两工作小时仍未派工，发送主管站内提醒；不含短信费用。
REQ-04 / RV-02：移动端本地队列使用请求UUID幂等去重，恢复网络后逐项同步照片/表单。版本号不一致转冲突队列，由主管选择保留内容，禁止静默覆盖。试演20单同步完整且无重复；现场长时断网、终端兼容及容量压力尚未验证。
REQ-03 / RV-03：只读ERP客户和设备档案。接口文档/沙箱由李工在8月17日提供，延期按实际影响共同调整；示例接口演示不代表生产ERP已联通。
REQ-05：区域权限同时限制查询、下载和附件；日志180天。客户IT模拟确认部署边界与每天备份，实际恢复演练留待交付。

## 交付与验收候选
一期30账号，服务台/派工/移动记录/回访/只读ERP/区域权限；排除ERP写回、库存核算、海外语言和历史纸档清洗。8周从首款到账、客户环境及接口资料三项齐备后起算。五场景用例均需正式业务测试，离线20单及跨区域拒绝为验收样例，指标不能被采购总价覆盖。

## 价值验证与决策
上线前采集连续两周漏单与响应时长，试运行用相同口径比较；不承诺未经测量的降幅。只读ERP仍优于双向同步的一期风险与成本；离线定制纳入本版范围，额外终端许可由客户自备。工期依赖写入最终合同而非放在演示口头说明。
""",
    "customer-review-v2.md": """# 2026-08-20 V2复审及验证记录（模拟）

对象：方案V2。王敏、李工在模拟会议中逐项确认。
RV-01：跨班次及节假日三组计时演示符合规则，关闭。
RV-02：断网20单重连后无重复，冲突转人工队列演示符合预期，关闭本次演示意见；现场压力/兼容测试转交付阶段，不声明已验收。
RV-03：8周起算依赖写入V2，李工提供模拟接口沙箱资料，关闭方案措辞问题；生产联通仍未验证。
结论：认可V2作为一期报价范围；不含生产上线、客户UAT或最终验收。
""",
    "quote-v1.md": """# 报价 Q1（模拟，2026-08-28）

供方：启程数字科技有限公司；客户：华辰装备有限公司；关联方案V2。
含税总额388000元，税率6%，30账号；软件许可及配置238000元、离线/ERP定制100000元、实施培训50000元。总额包含上述三项，无其他许可费。
付款40%签约、50%阶段验收、10%最终验收。8周起算条件同V2。有效期至2026-09-27。一年质保，不含客户新增范围及自备设备。
模拟内部授权人：商务负责人刘总，2026-08-28仅授权本文件Q1；模拟提交对象陈经理，提交不代表接受。
""",
    "competition.md": """# 2026-09-04 竞争反馈（模拟）

来源：采购陈经理EV-09口头反馈。迅达软件报价约320000元，含税及离线范围未说明；启维系统约360000元，客户认为其ERP经验较多，实际方案未取得。
客户提到我方388000元价格偏高，尚未选择供方。竞争报价仅为转述，不当作已核验同范围对价。
行动：顾宁与陈经理核对范围口径；林工补齐离线价值/接口责任对照；不得宣称对手缺能力或虚构底价。
""",
    "negotiation-v1.md": """# 2026-09-15 谈判结果 N1（模拟）

关联方案V2、报价Q1。客户诉求：35万元以内、付款20/70/10、工期8周无条件。
模拟内部授权：刘总允许最低358000元、首款不少于30%；不得删除离线和权限需求；其他责任条款交法务。
模拟双方讨论结果：358000元、30/60/10，保留一期完整范围；8周按首款/环境/接口资料齐备起算。客户在会议中同意作为合同起草依据，尚未签署。
未决项：主体信息、违约责任和签署授权由双方合同审阅确认。让价30000元换取首款和标准范围，不能把会议共识直接登记为签单。
""",
    "quote-v2.md": """# 报价 Q2（模拟，2026-09-15）

关联方案V2、谈判N1；取代Q1。含税358000元，税率6%，30账号；软件许可及配置208000元、离线/ERP定制100000元、实施培训50000元，合计358000元。
付款30/60/10，对应107400元、214800元、35800元。8周从首款、环境、接口资料三项齐备起算。有效期至2026-10-15，一年质保。范围与排除项同方案V2。
模拟内部授权：刘总2026-09-15批准本版358000元及30/60/10。Q1授权不能沿用至本版；本版单独登记授权。
""",
    "contract-draft.md": """# 合同 C1 待签稿（模拟）

编号HC-2026-SVC-01；双方华辰装备有限公司、启程数字科技有限公司。金额358000元含税6%，范围方案V2，报价Q2，付款30/60/10，8周起算依赖同Q2，一年质保。
双方模拟合同审阅完成，但本文件没有任何实际签署。客户签署：未完成；供方签署：未完成。不得登记赢单。
""",
    "contract-signed.md": """# 合同 C2 签署场景样本（纯模拟，无真实签署）

编号HC-2026-SVC-01；客户华辰装备有限公司；供方启程数字科技有限公司。
模拟签署日期2026-10-09；模拟双方签署状态均为完成。此为测试文本，不包含真实签字/印章，不构成合同或法律效力。
含税总额358000元，税率6%。30账号，一期范围引用方案V2与报价Q2；付款30/60/10，即107400/214800/35800元。8周从首款到账、环境和接口资料齐备起算；一年质保；范围外事项同V2。
模拟签署核对：双方主体、编号、金额、日期、范围版本、签署状态一致。实际首款、上线、客户验收、收入均未发生或未核验。
""",
    "handoff.md": """# 签约交接 H1（模拟）

绑定C2、Q2、方案V2；项目经理何工。合同358000元，不记作回款或收入。
待办：顾宁10月12日核实107400元首款；何工10月14日前确认人员、环境、ERP接口资料和启动会。
移交：30账号范围、四项排除、30/60/10付款、8周起算条件、一年质保、王敏/李工/陈经理职责，以及现场离线压力和ERP生产联通两个待验证项。
客户POC/演示认可只限EV-06，交付UAT与最终验收重新执行。后续由delivery-contract-handover/delivery-orchestrator接管交付。
""",
}

# rating patches are explicitly authored simulation judgments, never inferred approvals.
STEPS = [
    dict(date="2026-07-06", title="首次拜访", stage="customer_contacted", page="拜访记录 / 客户与商机概览",
         skills=["opportunity-analysis-skill", "opportunity-pursuit"],
         note="客户：华辰装备有限公司。首次拜访王敏，售后业务负责人。当前报修靠微信群，派工和回访容易漏记，客户希望统一工单；仅同意下一次调研，预算、采购与竞争者未知。",
         decision="建立商机；安排需求调研，不判断已经立项。", inputs="拜访纪要EV-01、王敏原话、销售顾宁的待确认回答", outputs="客户画像、痛点假设、首版18维评估、调研行动",
         scores={"customer_purchase_intent": ("medium", "王敏同意调研，但未立项"), "customer_relationship": ("medium", "已接触业务负责人，尚无决策承诺"), "sales_team": ("medium", "顾宁负责跟进，售前人员待安排")},
         facts={"contact_established": True}, action=("A-01", "完成业务/IT联合调研", "顾宁", "2026-07-13")),
    dict(date="2026-07-13", title="需求调研", stage="needs_discovery", page="需求矩阵 / 澄清清单",
         skills=["opportunity-analysis-skill", "opportunity-solution-validation", "presales-orchestrator", "presales-requirements"],
         note="王敏和IT李工确认五项需求：工单追踪、工作时段提醒、只读ERP主档、离线记录、区域权限。国内30账号，优先一期上线。ERP沙箱、离线冲突规则、预算尚未明确。",
         decision="需求成立；先澄清接口、离线与决策流程。", inputs="EV-02调研纪要、业务流程、账号规模与接口未知项", outputs="需求R1（REQ-01至05）、澄清问题、需求负责人候选",
         scores={"customer_insight": ("medium", "五项需求已明确，采购和决策链仍不完整"), "asset_reuse": ("medium", "工单框架可复用，离线/ERP尚待评估"), "delivery_risk": ("weak", "ERP接口与离线规则未确定")},
         facts={"need_confirmed": True}, complete="A-01", docs=["requirements.md"], action=("A-02", "确认采购路径、预算审批者和推进意愿", "顾宁", "2026-07-20")),
    dict(date="2026-07-20", title="商机资格判断", stage="opportunity_confirmed", page="商机判断 / 雷达 / 决策链",
         skills=["opportunity-analysis-skill", "opportunity-pursuit"],
         note="王敏为需求负责人，明确继续推进方案。采购陈经理确认直销询价；赵总决定预算和最终采购。客户希望10月签约，预算只是35至40万元意向，尚未获批。对手只听说迅达软件，价格和范围未知。销售顾宁、售前林工、技术周工组成团队。",
         decision="值得投入售前；预算仍是信号，暂不报价。", inputs="EV-03资格访谈、决策角色、采购路径与时间窗口", outputs="追单策略、角色责任、投入建议、方案任务书",
         scores={"customer_purchase_intent": ("medium", "有10月目标和继续推进意愿，预算未批"), "customer_insight": ("strong", "需求、采购及最终决策角色均明确"), "sales_team": ("strong", "销售、售前、技术人员已安排"), "partner_team": ("medium", "客户业务/IT可配合，接口责任未锁定"), "strategic_customer": ("medium", "可作售后场景参考，未获案例公开授权"), "contract_scale_type": ("medium", "35至40万预算意向，非批准额")},
         facts={"requirement_owner": "王敏", "continue_intent": True}, complete="A-02", competitors=[["迅达软件", "存在接触线索", "价格/范围/关系未知", "EV-03 王敏转述"]], action=("A-03", "提交方案V1并组织客户评审", "林工", "2026-08-03")),
    dict(date="2026-07-30", title="方案 V1", stage="solution_cocreation", page="方案版本 / 需求响应",
         skills=["opportunity-solution-validation", "presales-orchestrator", "presales-solution-design"],
         note="林工形成方案V1，覆盖在线工单与区域权限；工作时段计时、离线冲突和ERP延期处理仍未解决。已预约8月3日客户评审，方案文件生成不表示认可。",
         decision="进入方案共创，带着三项缺口评审。", inputs="需求R1、EV-03推进意见、接口及离线未知项", outputs="方案V1、逐项响应、验证计划和范围外清单",
         scores={"solution_fit": ("medium", "方案覆盖主流程，离线与计时存在缺口"), "value_proposition": ("medium", "统一闭环价值待客户评审"), "delivery_skill": ("medium", "项目经理资源未最终锁定")},
         facts={"solution_scope": "一期30账号工单、离线、ERP只读和区域权限；三项细节待评审"}, docs=["solution-v1.md"], artifacts=[("SOL-1", "solution", 1, "solution-v1.md")]),
    dict(date="2026-08-03", title="客户评审退回", stage=None, page="客户意见 / 整改闭环",
         skills=["opportunity-solution-validation", "opportunity-analysis-skill", "opportunity-pursuit"],
         note="客户评审方案V1未通过：RV-01须按工作时段提醒；RV-02必须离线20单及双端冲突保护；RV-03须把ERP资料延期和8周起算条件写清。王敏要求修订后再报价；预算尚未批准。",
         decision="停留方案共创；匹配度下降，禁止把评审召开记作通过。", inputs="EV-05评审原话、V1、REQ-02/03/04", outputs="客户评审R1、三项整改、评分下调和V2任务",
         scores={"solution_fit": ("weak", "EV-05客户退回V1，离线与计时未满足"), "presentation_visit": ("weak", "演示暴露关键缺口，尚未通过"), "delivery_risk": ("weak", "ERP具体延期影响尚未澄清")},
         docs=["customer-review-v1.md"], complete="A-03", review_status="open", action=("A-04", "完成V2及三项验证，邀请客户逐项复审", "林工", "2026-08-20")),
    dict(date="2026-08-20", title="方案 V2 复审", stage=None, page="方案对比 / 验证记录 / 意见关闭",
         skills=["opportunity-solution-validation", "presales-solution-design", "opportunity-analysis-skill"],
         note="方案V2完成工作日计时、离线去重/冲突队列、工期依赖。王敏和李工模拟复审：RV-01至03逐项关闭，认可V2作为报价范围；离线20单演示通过。现场压力测试、生产ERP联通及正式验收仍未执行。",
         decision="本轮方案意见关闭，准备预算确认；客户演示认可限于V2场景。", inputs="EV-06复审记录、V2、三个问题及验证结果", outputs="方案V2、评审R2、意见关闭证据、更新范围",
         scores={"solution_fit": ("strong", "客户认可V2报价范围，三项意见关闭"), "presentation_visit": ("strong", "20单离线与计时/冲突演示通过，非生产验收"), "value_proposition": ("strong", "客户重视现场离线与可追溯闭环"), "partner_team": ("strong", "李工提供沙箱资料，业务/IT责任落实"), "delivery_risk": ("medium", "生产ERP及现场压力仍待交付验证"), "asset_reuse": ("strong", "标准工单框架加明确的离线/接口定制")},
         facts={"solution_scope": "方案V2：30账号，工作日计时、离线去重/冲突、ERP只读、区域权限；生产验证待交付"}, docs=["solution-v2.md", "customer-review-v2.md"], artifacts=[("SOL-2", "solution", 2, "solution-v2.md")], complete="A-04", review_status="closed", action=("A-05", "取得预算及询价范围确认", "顾宁", "2026-08-25")),
    dict(date="2026-08-25", title="预算与立项", stage="budget_project_confirmed", page="预算 / 采购里程碑",
         skills=["opportunity-commercial", "opportunity-analysis-skill"],
         note="赵总模拟批准一期预算400000元，陈经理按方案V2组织三家询价，目标10月签约。预算批准不等于选择供方。公司内部确认何工可任项目经理，交付成本测算约25万元，仍为估算非实际成本。",
         decision="预算成立，按V2准备授权报价。", inputs="EV-07预算批复场景、V2、采购与内部成本估算", outputs="预算事实、报价任务、资源与成本判断",
         scores={"customer_purchase_intent": ("strong", "已立项，40万元预算及10月采购窗口明确"), "pricing_budget_fit": ("medium", "预算40万，尚无正式我方报价"), "delivery_skill": ("strong", "项目经理何工有可用档期"), "delivery_cost_structure": ("medium", "25万元为内部估算，未形成实际成本"), "margin_deal_shape": ("medium", "毛利和付款仍需按实际报价谈判确认")},
         facts={"budget_confirmed": True}, complete="A-05", action=("A-06", "批准并提交Q1，取得采购反馈", "顾宁", "2026-09-04")),
    dict(date="2026-08-28", title="首次报价", stage="proposal_bidding", page="报价版本 / 授权与提交",
         skills=["opportunity-commercial", "opportunity-pursuit"],
         note="按方案V2准备Q1含税388000元，付款40/50/10。刘总模拟批准Q1后，顾宁模拟提交陈经理。价格未超40万预算，但客户未接受。直销询价无需调用投标技能。",
         decision="进入报价阶段，跟进同范围比较与付款意见。", inputs="EV-08报价与内部授权、方案V2、成本测算", outputs="报价Q1、版本绑定、授权和提交记录",
         scores={"pricing_budget_fit": ("medium", "388000元在预算内，客户接受度尚未确认")},
         docs=["quote-v1.md"], artifacts=[("Q-1", "quote", 1, "quote-v1.md")], authorize="Q-1"),
    dict(date="2026-09-04", title="竞争低价介入", stage=None, page="竞争矩阵 / 评分变化 / 下一行动",
         skills=["opportunity-pursuit", "opportunity-analysis-skill", "opportunity-commercial"],
         note="陈经理转述迅达软件约32万元、启维系统约36万元，含税和离线范围未核实。客户认为我方38.8万元偏高，暂未定供方。竞争信息不能当作同范围报价，需补齐对比。",
         decision="停留报价阶段；竞争与价格评分下降，先对齐范围再谈折扣。", inputs="EV-09采购反馈、Q1、两家对手转述", outputs="竞争矩阵、价格/范围差异、跟进行动",
         scores={"competitors": ("weak", "两家报价更低，我方尚未证明同范围优势"), "pricing_budget_fit": ("weak", "客户认为38.8万偏高，未接受我方报价"), "customer_relationship": ("medium", "王敏支持需求但采购保持多家比较")},
         docs=["competition.md"], competitors=[["迅达软件", "约32万元（采购转述）", "含税/离线/交付范围待核验", "EV-09 陈经理"], ["启维系统", "约36万元（采购转述）；ERP经验受关注", "真实案例/接口范围待核验", "EV-09 陈经理"], ["我方", "Q1 38.8万元含税，离线/接口纳入V2", "价格偏高；需证明同范围价值", "Q1、V2、EV-09"]], complete="A-06", action=("A-07", "核对竞争范围，按授权谈价格与付款交换", "顾宁", "2026-09-15")),
    dict(date="2026-09-15", title="商务谈判", stage="commercial_negotiation", page="条款差异 / 授权底线 / 报价Q2",
         skills=["opportunity-negotiation", "opportunity-commercial", "opportunity-analysis-skill"],
         note="客户提出35万元及20/70/10付款。刘总模拟授权最低35.8万元、首款不少于30%。双方模拟会议同意35.8万元、30/60/10、保留V2完整范围和8周起算条件，作为合同起草依据。Q2单独批准，口头一致未签约。",
         decision="进入谈判；Q2替代Q1并重新授权，准备合同审核。", inputs="EV-10客户诉求、Q1、V2、内部让步授权", outputs="谈判N1、授权差异、Q2 35.8万元、剩余条款",
         scores={"pricing_budget_fit": ("strong", "双方接受35.8万作为合同草拟依据，仍待签署"), "competitors": ("medium", "客户接受我方范围价值，未取得对手完整材料"), "margin_deal_shape": ("medium", "首款30%，总价下降；成本仍是估算"), "customer_relationship": ("strong", "业务/IT与采购共同认可合同起草依据")},
         docs=["negotiation-v1.md", "quote-v2.md"], artifacts=[("N-1", "negotiation", 1, "negotiation-v1.md"), ("Q-2", "quote", 2, "quote-v2.md")], authorize="Q-2", complete="A-07", action=("A-08", "核对合同主体、条款与双方签署", "顾宁", "2026-10-09")),
    dict(date="2026-09-25", title="合同审核待签", stage="contract_signing", page="合同版本 / 签署核验",
         skills=["opportunity-closeout", "opportunity-negotiation"],
         note="合同C1模拟内部及客户条款审阅完成，编号HC-2026-SVC-01，金额35.8万元含税，范围V2和Q2，付款30/60/10。双方尚未签署。高评分和条款认可不能当成赢单。",
         decision="停留合同签署；无签署证据的赢单请求应被拒绝。", inputs="EV-11合同审阅、N1、Q2、V2", outputs="合同C1待签稿、签署缺口、金额范围一致性检查",
         docs=["contract-draft.md"], artifacts=[("C-1", "contract", 1, "contract-draft.md")], reject_unsigned=True),
    dict(date="2026-10-09", title="双方签署与交接", stage="won", page="签单归档 / 交付交接",
         skills=["opportunity-closeout", "opportunity-orchestrator"],
         note="纯模拟签署场景：双方在10月9日完成合同C2签署，主体华辰装备有限公司与启程数字科技有限公司，金额358000元含税。核对C2绑定方案V2、报价Q2及30/60/10付款，登记模拟签单。首款、收入和上线验收尚未核验。",
         decision="签单依据是模拟双方签署记录；评分保持上一轮评估，不改成100%。", inputs="EV-12模拟签署记录、C2、Q2、V2、N1", outputs="签署登记、赢单阶段、交接H1与首款/启动待办",
         docs=["contract-signed.md", "handoff.md"], artifacts=[("C-2", "contract", 2, "contract-signed.md"), ("H-1", "handoff", 1, "handoff.md")], complete="A-08", signed=True,
         action=("A-09", "核实107400元首款并移交启动条件", "顾宁", "2026-10-12")),
]
