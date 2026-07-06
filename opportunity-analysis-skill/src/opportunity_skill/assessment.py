from __future__ import annotations

from typing import Any

from .utils import new_id

RATING_SCORE = {
    "strong": 100,
    "medium": 65,
    "weak": 25,
    "unknown": 40,
}

CATEGORY_WEIGHTS = {
    "win_likelihood": 0.55,
    "deal_attractiveness": 0.25,
    "delivery_confidence": 0.20,
}

DIMENSIONS: list[dict[str, Any]] = [
    {
        "id": "customer_purchase_intent",
        "category": "win_likelihood",
        "label": "客户购买意向",
        "priority": "P0",
        "critical": True,
        "question": "客户是否已经正式立项或进入采购流程？是否有明确决策截止时间或强制事件？",
    },
    {
        "id": "customer_insight",
        "category": "win_likelihood",
        "label": "客户洞察力",
        "priority": "P0",
        "critical": True,
        "question": "我们是否清楚客户业务需求、买方价值观、决策流程和关键干系人权力图？缺哪一块？",
    },
    {
        "id": "customer_relationship",
        "category": "win_likelihood",
        "label": "客户关系",
        "priority": "P0",
        "critical": True,
        "question": "客户内部是否有人明确支持我方？他/她能否影响评审、技术路线或采购决策？",
    },
    {
        "id": "reputation",
        "category": "win_likelihood",
        "label": "我方业绩和声誉",
        "priority": "P1",
        "critical": False,
        "question": "客户是否认可我们在类似解决方案领域的交付能力、案例和可信度？",
    },
    {
        "id": "competitors",
        "category": "win_likelihood",
        "label": "竞争对手",
        "priority": "P0",
        "critical": True,
        "question": "已知竞争对手是谁？他们在客户侧的关系、方案和价格位置分别如何？",
    },
    {
        "id": "solution_fit",
        "category": "win_likelihood",
        "label": "解决方案匹配度",
        "priority": "P0",
        "critical": True,
        "question": "客户是否认为我们的方案适合其具体需求？还有哪些检测点位、接口或节拍要求未满足？",
    },
    {
        "id": "value_proposition",
        "category": "win_likelihood",
        "label": "价值主张/双赢主题",
        "priority": "P1",
        "critical": False,
        "question": "客户最认可我们的哪一个差异化价值？这个价值是否足以支撑选择我们？",
    },
    {
        "id": "pricing_budget_fit",
        "category": "win_likelihood",
        "label": "报价和业务交易形态",
        "priority": "P0",
        "critical": True,
        "question": "客户预算区间、价格预期和我们预期方案范围是否匹配？如果不匹配，差距在哪里？",
    },
    {
        "id": "partner_team",
        "category": "win_likelihood",
        "label": "团队合作",
        "priority": "P2",
        "critical": False,
        "question": "是否已确定合作方、内部关键成员和客户侧配合团队？",
    },
    {
        "id": "presentation_visit",
        "category": "win_likelihood",
        "label": "演示/现场参观",
        "priority": "P2",
        "critical": False,
        "question": "是否需要演示、样板线参观或客户现场验证？准备程度如何？",
    },
    {
        "id": "sales_team",
        "category": "win_likelihood",
        "label": "销售团队",
        "priority": "P1",
        "critical": False,
        "question": "销售、售前、方案、技术和交付角色是否齐备？缺哪个关键角色？",
    },
    {
        "id": "strategic_customer",
        "category": "deal_attractiveness",
        "label": "战略客户",
        "priority": "P1",
        "critical": True,
        "question": "该客户对我们是否具有战略价值或标杆价值？优先级是什么？",
    },
    {
        "id": "contract_scale_type",
        "category": "deal_attractiveness",
        "label": "合同规模/类型",
        "priority": "P1",
        "critical": True,
        "question": "预计合同金额、当前价值和后续合作空间大概在哪个区间？是否属于战略性工作？",
    },
    {
        "id": "margin_deal_shape",
        "category": "deal_attractiveness",
        "label": "利润和交易形态",
        "priority": "P1",
        "critical": True,
        "question": "预计毛利、付款条件、验收方式和风险条款是否健康？是否可能低于利润目标？",
    },
    {
        "id": "asset_reuse",
        "category": "deal_attractiveness",
        "label": "复用现有产品/方案",
        "priority": "P1",
        "critical": False,
        "question": "方案能否复用现有产品、算法、设备选型、MES接口或行业模板？需要多少定制？",
    },
    {
        "id": "delivery_skill",
        "category": "delivery_confidence",
        "label": "交付技巧/资源",
        "priority": "P1",
        "critical": True,
        "question": "交付所需的项目经理、方案架构师、视觉检测、软件集成和现场实施资源是否可用？",
    },
    {
        "id": "delivery_cost_structure",
        "category": "delivery_confidence",
        "label": "交付成本结构",
        "priority": "P2",
        "critical": False,
        "question": "当前方案、交付方式和人员配置能否支撑目标利润？成本风险在哪里？",
    },
    {
        "id": "delivery_risk",
        "category": "delivery_confidence",
        "label": "交付风险",
        "priority": "P1",
        "critical": True,
        "question": "项目复杂度、现场节拍、接口、验收和上线风险是什么？是否有不可控风险？",
    },
]


def build_commercial_assessment(context: dict[str, Any]) -> dict[str, Any]:
    answer_map = _answer_map(context.get("sales_confirmation_answers", []))
    dimensions = []
    for spec in DIMENSIONS:
        inferred = _infer_dimension(spec["id"], context)
        answer = answer_map.get(spec["id"])
        if answer:
            rating = normalize_rating(answer.get("rating")) or inferred["rating"]
            evidence_status = "sales_confirmed"
            answer_text = answer.get("answer_text") or answer.get("answer")
            rationale = answer_text or inferred["rationale"]
        else:
            rating = inferred["rating"]
            evidence_status = inferred["evidence_status"]
            answer_text = None
            rationale = inferred["rationale"]
        dimensions.append({
            "id": new_id("dim"),
            "dimension_id": spec["id"],
            "category": spec["category"],
            "label": spec["label"],
            "priority": spec["priority"],
            "critical": bool(spec["critical"]),
            "rating": rating,
            "score": RATING_SCORE.get(rating, RATING_SCORE["unknown"]),
            "weight": 1,
            "evidence_status": evidence_status,
            "rationale": rationale,
            "question": spec["question"],
            "answer": answer_text,
            "evidence_refs": inferred.get("evidence_refs", []),
        })

    category_scores = _category_scores(dimensions)
    raw_overall = round(sum(category_scores[k] * CATEGORY_WEIGHTS[k] for k in CATEGORY_WEIGHTS))
    baseline_score = context.get("baseline_score")
    if baseline_score is not None:
        overall = round(raw_overall * 0.75 + int(baseline_score) * 0.25)
    else:
        overall = raw_overall
    assessment_confidence = _assessment_confidence(dimensions)
    unanswered_critical = sum(1 for d in dimensions if d["critical"] and d["evidence_status"] == "needs_sales_confirmation")
    win_probability = _win_probability(category_scores["win_likelihood"], overall, assessment_confidence)
    questions = _questions_from_dimensions(dimensions)
    return {
        "id": new_id("assess"),
        "win_likelihood_score": category_scores["win_likelihood"],
        "deal_attractiveness_score": category_scores["deal_attractiveness"],
        "delivery_confidence_score": category_scores["delivery_confidence"],
        "overall_opportunity_score": overall,
        "win_probability": win_probability,
        "confidence_level": _confidence_level(assessment_confidence),
        "assessment_confidence_score": assessment_confidence,
        "unanswered_critical_count": unanswered_critical,
        "dimensions": dimensions,
        "questions": questions,
        "answers": list(answer_map.values()),
    }


def normalize_rating(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    mapping = {
        "强": "strong",
        "高": "strong",
        "strong": "strong",
        "中": "medium",
        "medium": "medium",
        "一般": "medium",
        "弱": "weak",
        "低": "weak",
        "weak": "weak",
        "未知": "unknown",
        "unknown": "unknown",
        "不知道": "unknown",
        "不确定": "unknown",
        "待确定": "unknown",
        "待确认": "unknown",
        "确认中": "unknown",
        "不清楚": "unknown",
        "uncertain": "unknown",
        "pending": "unknown",
        "tbd": "unknown",
    }
    return mapping.get(text)


def _answer_map(answers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped = {}
    for answer in answers or []:
        key = answer.get("dimension_id") or answer.get("question_id")
        if key:
            item = dict(answer)
            item["rating"] = normalize_rating(item.get("rating")) or "unknown"
            mapped[key] = item
    return mapped


def _infer_dimension(dimension_id: str, context: dict[str, Any]) -> dict[str, Any]:
    text = context.get("text", "")
    stage = context.get("stage", "")
    core_need = context.get("core_need", "")
    budget_signal = context.get("budget_signal", "")
    budget_amount = context.get("budget_amount")
    timeline = context.get("timeline", "")
    contacts = context.get("contacts", [])
    decision_chain = context.get("decision_chain", [])
    competitors = context.get("competitors", [])
    systems = context.get("current_systems", [])
    pains = context.get("pain_points", [])
    evidence_refs = [ev.get("evidence_id") for ev in context.get("evidence_list", [])[:2] if ev.get("evidence_id")]
    confirmed_chain = sum(1 for n in decision_chain if n.get("status") == "confirmed")
    has_requirement_owner = any(c.get("is_requirement_owner") for c in contacts)
    has_decision_maker = any(n.get("decision_role") == "最终决策人/关键拍板人" and n.get("status") == "confirmed" for n in decision_chain)

    def out(rating: str, status: str, rationale: str) -> dict[str, Any]:
        return {"rating": rating, "evidence_status": status, "rationale": rationale, "evidence_refs": evidence_refs}

    if dimension_id == "customer_purchase_intent":
        if budget_signal != "预算信息未明确" and timeline != "时间节点未明确" and stage in {"方案交流", "投标/报价", "商务谈判"}:
            return out("strong", "inferred", "材料显示有预算/立项信号、明确时间窗口，并已进入方案或更后阶段。")
        if budget_signal != "预算信息未明确" or timeline != "时间节点未明确":
            return out("medium", "inferred", "材料显示购买兴趣、预算或时间信号，但采购流程和决策截止点仍需商务确认。")
        return out("unknown", "needs_sales_confirmation", "缺少正式采购流程、强制事件和决策时限信息。")
    if dimension_id == "customer_insight":
        if has_requirement_owner and has_decision_maker and confirmed_chain >= 4:
            return out("strong", "inferred", "需求负责人、决策人和主要链路节点较完整。")
        if has_requirement_owner and confirmed_chain >= 2:
            return out("medium", "inferred", "已识别需求/项目负责人和部分链路，但权力图仍不完整。")
        return out("unknown", "needs_sales_confirmation", "客户业务需求、买方价值观或决策链仍缺关键洞察。")
    if dimension_id == "customer_relationship":
        if any(k in text for k in ["支持我们", "认可我们", "内部推荐", "倾向我们", "导师"]):
            return out("strong", "inferred", "材料出现客户内部支持或倾向我方信号。")
        if contacts:
            return out("medium", "needs_sales_confirmation", "已有客户联系人，但是否存在支持我方的内部导师仍需确认。")
        return out("unknown", "needs_sales_confirmation", "缺少客户关系强度和内部支持者信息。")
    if dimension_id == "reputation":
        if any(k in text for k in ["信任", "认可", "案例", "标杆", "合作经验"]):
            return out("medium", "inferred", "材料出现案例、认可或合作相关信号。")
        return out("unknown", "needs_sales_confirmation", "客户对我方声誉和类似项目交付能力的看法未知。")
    if dimension_id == "competitors":
        if competitors:
            return out("medium", "inferred", "已识别部分竞争对手，但其客户侧定位和优劣势仍需确认。")
        return out("unknown", "needs_sales_confirmation", "竞争对手和客户已接触供应商情况未知。")
    if dimension_id == "solution_fit":
        if core_need != "客户需求待进一步澄清" and systems:
            return out("medium", "inferred", "需求和系统集成边界初步明确，但具体检测点位、节拍和方案适配仍需确认。")
        if core_need != "客户需求待进一步澄清":
            return out("medium", "needs_sales_confirmation", "需求方向明确，但方案适配度仍需商务/售前确认。")
        return out("unknown", "needs_sales_confirmation", "客户是否认可方案匹配度尚不明确。")
    if dimension_id == "value_proposition":
        if any(k in text for k in ["差异化", "价值", "效率", "稳定性", "追溯"]):
            return out("medium", "needs_sales_confirmation", "材料有业务价值线索，但客户是否认为足够差异化仍需确认。")
        return out("unknown", "needs_sales_confirmation", "缺少客户认可的差异化价值主张。")
    if dimension_id == "pricing_budget_fit":
        if budget_amount:
            return out("strong", "needs_sales_confirmation", "识别到预算金额，但仍需确认是否匹配方案范围和报价预期。")
        if budget_signal != "预算信息未明确":
            return out("medium", "needs_sales_confirmation", "有预算/立项信号，但预算区间和价格预期未明确。")
        return out("unknown", "needs_sales_confirmation", "预算和报价匹配度未知。")
    if dimension_id == "partner_team":
        if any(k in text for k in ["合作方", "团队", "同事一起参与", "方案、视觉检测和软件集成"]):
            return out("medium", "inferred", "材料出现内部/合作团队协同信号。")
        return out("unknown", "needs_sales_confirmation", "合作方和关键团队成员尚未确认。")
    if dimension_id == "presentation_visit":
        if any(k in text for k in ["演示", "参观", "现场", "样板", "技术交流"]):
            return out("medium", "inferred", "材料出现技术交流、演示或参观相关动作。")
        return out("unknown", "needs_sales_confirmation", "演示、现场参观或验证计划尚未确认。")
    if dimension_id == "sales_team":
        if any(k in text for k in ["售前", "方案", "视觉检测", "软件集成", "技术团队"]):
            return out("medium", "inferred", "销售/售前/技术角色有初步参与线索。")
        return out("unknown", "needs_sales_confirmation", "销售团队关键角色是否齐备未知。")
    if dimension_id == "strategic_customer":
        if any(k in text for k in ["战略客户", "标杆", "重点客户", "集团"]):
            return out("strong", "inferred", "材料出现战略或标杆价值信号。")
        return out("unknown", "needs_sales_confirmation", "客户战略重要性尚未确认。")
    if dimension_id == "contract_scale_type":
        if budget_amount:
            return out("medium", "needs_sales_confirmation", "已有预算金额线索，但合同规模、后续合作空间和工作类型仍需确认。")
        return out("unknown", "needs_sales_confirmation", "合同规模、工作类型和后续合作空间未知。")
    if dimension_id == "margin_deal_shape":
        return out("unknown", "needs_sales_confirmation", "利润目标、付款条件、验收方式和交易风险条款尚未确认。")
    if dimension_id == "asset_reuse":
        if systems or any(k in text for k in ["现有", "MES", "标准", "复用"]):
            return out("medium", "needs_sales_confirmation", "可能复用现有系统集成或产品能力，但定制比例需要确认。")
        return out("unknown", "needs_sales_confirmation", "是否复用现有产品/方案能力未知。")
    if dimension_id == "delivery_skill":
        if any(k in text for k in ["方案", "视觉检测", "软件集成", "技术团队", "项目经理"]):
            return out("medium", "needs_sales_confirmation", "交付相关角色有参与线索，但资源排期和能力确认仍缺失。")
        return out("unknown", "needs_sales_confirmation", "交付所需资源和技能是否可用未知。")
    if dimension_id == "delivery_cost_structure":
        return out("unknown", "needs_sales_confirmation", "交付方式、人员配置和成本结构尚未确认。")
    if dimension_id == "delivery_risk":
        if any(k in text for k in ["节拍", "接口", "MES", "检测点位", "takt", "复杂"]):
            return out("medium", "needs_sales_confirmation", "材料显示存在节拍、接口或检测点位等交付复杂性。")
        if len(pains) > 3:
            return out("medium", "needs_sales_confirmation", "痛点较多，交付复杂度需要进一步评估。")
        return out("unknown", "needs_sales_confirmation", "交付复杂度和风险尚未确认。")
    return out("unknown", "needs_sales_confirmation", "该评估项缺少判断信息。")


def _category_scores(dimensions: list[dict[str, Any]]) -> dict[str, int]:
    scores = {}
    for category in CATEGORY_WEIGHTS:
        items = [d for d in dimensions if d["category"] == category]
        if not items:
            scores[category] = 0
            continue
        scores[category] = round(sum(d["score"] for d in items) / len(items))
    return scores


def _assessment_confidence(dimensions: list[dict[str, Any]]) -> int:
    if not dimensions:
        return 0
    status_score = {
        "sales_confirmed": 100,
        "inferred": 65,
        "needs_sales_confirmation": 25,
    }
    return round(sum(status_score.get(d["evidence_status"], 25) for d in dimensions) / len(dimensions))


def _confidence_level(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _win_probability(win_likelihood: int, overall: int, confidence: int) -> float:
    calibrated = (win_likelihood * 0.7 + overall * 0.2 + confidence * 0.1) / 100
    return round(max(0.05, min(0.9, calibrated * 0.85)), 2)


def _questions_from_dimensions(dimensions: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    candidates = [
        d for d in dimensions
        if d["evidence_status"] == "needs_sales_confirmation" and d["rating"] in {"unknown", "weak", "medium"}
    ]
    candidates.sort(key=lambda d: (priority_order.get(d["priority"], 9), 0 if d["critical"] else 1, d["category"], d["dimension_id"]))
    questions = []
    for d in candidates[:limit]:
        questions.append({
            "id": new_id("q"),
            "dimension_id": d["dimension_id"],
            "category": d["category"],
            "label": d["label"],
            "question": d["question"],
            "priority": d["priority"],
            "status": "open",
            "current_rating": d["rating"],
            "impact": _question_impact(d),
        })
    return questions


def _question_impact(dimension: dict[str, Any]) -> str:
    if dimension["critical"]:
        return "直接影响赢单率、商机有效性或是否值得进入下一阶段"
    return "用于提升评估可信度和后续行动质量"
