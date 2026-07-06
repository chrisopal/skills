from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    name: str
    order: int
    description: str
    signals: tuple[str, ...]
    is_terminal: bool = False
    is_opportunity_confirmed: bool = False


STAGE_DEFINITIONS: list[StageDefinition] = [
    StageDefinition("lead_identified", "线索识别", 1, "只有客户、行业、潜在方向或零散线索。", ("线索", "潜在客户", "客户名单")),
    StageDefinition("customer_contacted", "客户接触", 2, "已经发生初步沟通或识别到客户联系人。", ("沟通", "拜访", "客户交流", "联系人", "名片")),
    StageDefinition("needs_discovery", "需求澄清", 3, "已有需求方向和痛点，但推进意愿或负责人仍不完整。", ("需求", "痛点", "现状", "问题", "希望", "需要")),
    StageDefinition("opportunity_confirmed", "商机确认", 4, "客户、需求、负责人和继续推进意愿基本成立。", ("继续推进", "安排交流", "资料清单", "需求负责人", "项目负责人"), is_opportunity_confirmed=True),
    StageDefinition("solution_cocreation", "方案共创", 5, "正在进行方案、技术、范围、POC 或接口讨论。", ("方案", "技术交流", "演示", "接口", "POC", "设备选型", "检测点位", "MES对接", "范围讨论"), is_opportunity_confirmed=True),
    StageDefinition(
        "budget_project_confirmed",
        "预算/立项确认",
        6,
        "预算、立项、采购计划、审批或时间窗口已有明确的正向确认。",
        ("预算已批", "预算获批", "预算已立项", "立项通过", "已立项", "采购计划已确认", "审批通过", "内部审批通过", "时间窗口已确认", "技改预算已批"),
        is_opportunity_confirmed=True,
    ),
    StageDefinition("proposal_bidding", "报价/投标", 7, "进入报价、招投标、比选、询价或 RFP 阶段。", ("报价", "投标", "招标", "比选", "询价", "RFP"), is_opportunity_confirmed=True),
    StageDefinition("commercial_negotiation", "商务谈判", 8, "正在围绕价格、合同、付款、交付边界或法务条款谈判。", ("合同条款", "价格谈判", "付款方式", "交付边界", "法务", "采购谈判", "商务谈判"), is_opportunity_confirmed=True),
    StageDefinition("won", "赢单", 9, "商机已经中标、签约或成交。", ("中标", "已签约", "合同已签", "PO", "成交", "赢单"), is_terminal=True, is_opportunity_confirmed=True),
    StageDefinition("lost", "丢单", 10, "商机已失败、暂停、取消或客户选择其他供应商。", ("未中标", "选择其他供应商", "项目暂停", "项目取消", "预算取消", "丢单"), is_terminal=True, is_opportunity_confirmed=True),
]


LEGACY_STAGE_NAME_TO_ID = {
    "线索": "lead_identified",
    "初步沟通": "customer_contacted",
    "需求确认": "needs_discovery",
    "方案交流": "solution_cocreation",
    "投标/报价": "proposal_bidding",
}

GUARDED_SIGNALS = frozenset(
    next(stage.signals for stage in STAGE_DEFINITIONS if stage.stage_id == "budget_project_confirmed")
)
GUARDED_PREFIX_MARKERS = ("如果", "若", "待", "未", "尚未", "还未", "暂未", "正在", "走流程")
GUARDED_SUFFIX_MARKERS = ("后", "再", "将", "才能", "才", "前")
CONTEXT_WINDOW = 6
_PUNCTUATION = " \t\r\n,，.。;；:：!！?？、"


def stage_names() -> list[str]:
    return [stage.name for stage in STAGE_DEFINITIONS]


def stage_by_id(stage_id: str) -> StageDefinition | None:
    for stage in STAGE_DEFINITIONS:
        if stage.stage_id == stage_id:
            return stage
    return None


def stage_from_name(stage_name: str | None) -> StageDefinition | None:
    if not stage_name:
        return None
    normalized = stage_name.strip()
    for stage in STAGE_DEFINITIONS:
        if stage.name == normalized:
            return stage
    legacy_stage_id = LEGACY_STAGE_NAME_TO_ID.get(normalized)
    if legacy_stage_id:
        return stage_by_id(legacy_stage_id)
    return None


def _normalize_context_snippet(snippet: str, *, strip_left: bool) -> str:
    return snippet.lstrip(_PUNCTUATION) if strip_left else snippet.rstrip(_PUNCTUATION)


def _signal_is_blocked(text: str, signal: str, start: int) -> bool:
    if signal not in GUARDED_SIGNALS:
        return False

    prefix = _normalize_context_snippet(text[max(0, start - CONTEXT_WINDOW):start], strip_left=False)
    suffix = _normalize_context_snippet(text[start + len(signal):start + len(signal) + CONTEXT_WINDOW], strip_left=True)

    if any(prefix.endswith(marker) or marker in prefix for marker in GUARDED_PREFIX_MARKERS):
        return True
    return any(suffix.startswith(marker) for marker in GUARDED_SUFFIX_MARKERS)


def _text_has_any(text: str, signals: tuple[str, ...]) -> list[str]:
    text_lower = text.lower()
    matched: list[str] = []
    for signal in signals:
        if not signal:
            continue
        signal_lower = signal.lower()
        search_from = 0
        while True:
            start = text_lower.find(signal_lower, search_from)
            if start == -1:
                break
            if not _signal_is_blocked(text, signal, start):
                matched.append(signal)
                break
            search_from = start + 1
    return matched


def _confirmed_contact(context: dict[str, Any]) -> bool:
    contacts = context.get("contacts") or []
    decision_chain = context.get("decision_chain") or []
    if any(item.get("is_requirement_owner") or item.get("role_in_opportunity") for item in contacts):
        return True
    return any(item.get("status") == "confirmed" for item in decision_chain)


def _need_is_clear(context: dict[str, Any]) -> bool:
    core_need = str(context.get("core_need") or "")
    return bool(core_need and core_need != "客户需求待进一步澄清")


def infer_opportunity_stage(context: dict[str, Any]) -> dict[str, Any]:
    text = str(context.get("text") or "")
    hits_by_stage: dict[str, list[str]] = {}
    for stage in STAGE_DEFINITIONS:
        hits = _text_has_any(text, stage.signals)
        if hits:
            hits_by_stage[stage.stage_id] = hits

    selected = stage_by_id("lead_identified")
    signal_hits: list[str] = []
    for stage in reversed(STAGE_DEFINITIONS):
        hits = hits_by_stage.get(stage.stage_id, [])
        if hits:
            selected = stage
            signal_hits = [f"{stage.name}:{hit}" for hit in hits]
            break

    if selected and selected.stage_id in {"lead_identified", "customer_contacted", "needs_discovery"}:
        has_contact = bool(context.get("contacts"))
        has_confirmed_contact = _confirmed_contact(context)
        clear_need = _need_is_clear(context)
        wants_more = bool(_text_has_any(text, ("安排", "资料清单", "继续", "方案", "技术交流", "确认时间")))
        if clear_need and has_confirmed_contact and wants_more:
            selected = stage_by_id("opportunity_confirmed")
            signal_hits = ["商机确认:明确需求", "商机确认:客户负责人", "商机确认:继续推进意愿"]
        elif clear_need:
            selected = stage_by_id("needs_discovery")
            signal_hits = signal_hits or ["需求澄清:明确需求方向"]
        elif has_contact:
            selected = stage_by_id("customer_contacted")
            signal_hits = signal_hits or ["客户接触:已识别客户联系人"]

    selected = selected or STAGE_DEFINITIONS[0]
    confidence = "high" if len(signal_hits) >= 2 else "medium" if signal_hits else "low"
    reason = "、".join(signal_hits) if signal_hits else "材料中阶段信号较少，默认作为线索识别。"
    return {
        "stage_id": selected.stage_id,
        "stage": selected.name,
        "stage_reason": reason,
        "stage_confidence": confidence,
        "stage_signal_hits": signal_hits,
        "opportunity_confirmed": selected.is_opportunity_confirmed,
    }
