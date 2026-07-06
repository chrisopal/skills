# Opportunity Stage Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standard opportunity stage model, explainable current-stage judgment, confirmed-opportunity state, refreshed top metrics, and static HTML stage visualization to `opportunity-analysis-skill`.

**Architecture:** Add a focused `stage_management.py` module under the existing `opportunity_skill` package. The opportunity analysis stage will consume that module, SQLite will persist nullable metadata for compatibility, and the renderer will use the metadata to build a static detail-page stage path and kanban columns.

**Tech Stack:** Python 3.12 standard library, SQLite, static HTML templates, CSS, existing `scripts/validate_skill.py`.

## Global Constraints

- Keep the skill portable and dependency-free.
- Do not implement stage history, stage duration, manual stage movement, rollback, drag-and-drop, or strict stage gate validation.
- Do not add JavaScript, a frontend framework, or an interactive CRM UI.
- Do not break existing `stage` queries or stored opportunity rows.
- Keep `stage` as the Chinese stage name for backward compatibility.
- Add nullable metadata fields so old rows can still render.
- Continue to escape user-controlled values and keep templates script-free.
- Only stage files related to `opportunity-analysis-skill`, `docs/superpowers/plans`, and `STATUS.md`; leave unrelated workspace changes untouched.

---

### Task 1: Stage Model and Judgment Helper

**Files:**
- Create: `opportunity-analysis-skill/src/opportunity_skill/stage_management.py`
- Modify: `opportunity-analysis-skill/scripts/validate_skill.py`

**Interfaces:**
- Produces: `STAGE_DEFINITIONS: list[StageDefinition]`
- Produces: `stage_names() -> list[str]`
- Produces: `stage_by_id(stage_id: str) -> StageDefinition | None`
- Produces: `stage_from_name(stage_name: str | None) -> StageDefinition | None`
- Produces: `infer_opportunity_stage(context: dict[str, Any]) -> dict[str, Any]`
- Later tasks consume the returned keys: `stage_id`, `stage`, `stage_reason`, `stage_confidence`, `stage_signal_hits`, `opportunity_confirmed`.

- [ ] **Step 1: Add failing validator checks for the stage model**

Add imports near the existing stage imports in `opportunity-analysis-skill/scripts/validate_skill.py`:

```python
from opportunity_skill.stage_management import infer_opportunity_stage, stage_names  # noqa: E402
```

Add this function after `check_stage_modules()`:

```python
def check_stage_management() -> None:
    expected = [
        "线索识别",
        "客户接触",
        "需求澄清",
        "商机确认",
        "方案共创",
        "预算/立项确认",
        "报价/投标",
        "商务谈判",
        "赢单",
        "丢单",
    ]
    if stage_names() != expected:
        fail(f"stage model order mismatch: {stage_names()}")
    result = infer_opportunity_stage({
        "text": "客户希望Q3前完成方案确认，安排技术交流，讨论检测点位和MES对接。",
        "core_need": "质检自动化升级",
        "contacts": [{"name": "王总", "is_requirement_owner": True}],
        "decision_chain": [{"decision_role": "业务需求负责人", "status": "confirmed"}],
        "budget_signal": "预算信息未明确",
        "timeline": "Q3",
    })
    if result["stage_id"] != "solution_cocreation":
        fail(f"solution signals should infer solution_cocreation, got {result}")
    if result["stage"] != "方案共创":
        fail("stage result should keep Chinese stage name")
    if not result["opportunity_confirmed"]:
        fail("solution_cocreation should be a confirmed opportunity")
    if "技术交流" not in "".join(result["stage_signal_hits"]):
        fail("stage signal hits should explain matched signals")
    early = infer_opportunity_stage({
        "text": "客户名片已获取，后续再沟通。",
        "core_need": "客户需求待进一步澄清",
        "contacts": [{"name": "张三"}],
        "decision_chain": [],
        "budget_signal": "预算信息未明确",
        "timeline": "时间节点未明确",
    })
    if early["stage_id"] != "customer_contacted" or early["opportunity_confirmed"]:
        fail(f"early contact should not be confirmed opportunity, got {early}")
    print("ok stage management")
```

Call it in `main()` immediately after `check_stage_modules()`:

```python
    check_stage_modules()
    check_stage_management()
    check_confirmation_loop()
```

- [ ] **Step 2: Run validator to verify the import fails**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'opportunity_skill.stage_management'`.

- [ ] **Step 3: Create the stage management module**

Create `opportunity-analysis-skill/src/opportunity_skill/stage_management.py`:

```python
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
    StageDefinition("budget_project_confirmed", "预算/立项确认", 6, "预算、立项、采购计划、审批或时间窗口逐步明确。", ("预算已批", "预算", "立项", "采购计划", "审批", "时间窗口", "技改"), is_opportunity_confirmed=True),
    StageDefinition("proposal_bidding", "报价/投标", 7, "进入报价、招投标、比选、询价或 RFP 阶段。", ("报价", "投标", "招标", "比选", "询价", "RFP"), is_opportunity_confirmed=True),
    StageDefinition("commercial_negotiation", "商务谈判", 8, "正在围绕价格、合同、付款、交付边界或法务条款谈判。", ("合同条款", "价格谈判", "付款方式", "交付边界", "法务", "采购谈判", "商务谈判"), is_opportunity_confirmed=True),
    StageDefinition("won", "赢单", 9, "商机已经中标、签约或成交。", ("中标", "已签约", "合同已签", "PO", "成交", "赢单"), is_terminal=True, is_opportunity_confirmed=True),
    StageDefinition("lost", "丢单", 10, "商机已失败、暂停、取消或客户选择其他供应商。", ("未中标", "选择其他供应商", "项目暂停", "项目取消", "预算取消", "丢单"), is_terminal=True, is_opportunity_confirmed=True),
]


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
    for stage in STAGE_DEFINITIONS:
        if stage.name == stage_name:
            return stage
    return None


def _text_has_any(text: str, signals: tuple[str, ...]) -> list[str]:
    return [signal for signal in signals if signal and signal.lower() in text.lower()]


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
```

- [ ] **Step 4: Run validator to verify the stage model passes**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: PASS through `ok stage management`.

- [ ] **Step 5: Commit Task 1**

```bash
cd /Users/guojiexie/Development/skills
git add opportunity-analysis-skill/src/opportunity_skill/stage_management.py opportunity-analysis-skill/scripts/validate_skill.py
git commit -m "Add opportunity stage model"
```

---

### Task 2: Wire Stage Judgment into Opportunity Analysis

**Files:**
- Modify: `opportunity-analysis-skill/src/opportunity_skill/stages/opportunity_analysis.py`
- Modify: `opportunity-analysis-skill/schemas/opportunity.schema.json`
- Modify: `opportunity-analysis-skill/scripts/validate_skill.py`

**Interfaces:**
- Consumes: `infer_opportunity_stage(context: dict[str, Any]) -> dict[str, Any]`
- Produces in opportunity payload: `stage_id: str`, `stage_confidence: str`, `stage_signal_hits: list[str]`, `opportunity_confirmed: bool`.
- Later storage and renderer tasks rely on these keys.

- [ ] **Step 1: Add failing output contract checks**

In `assert_output_contract()` in `opportunity-analysis-skill/scripts/validate_skill.py`, after the existing `opportunity = result["structured_data"]["opportunity"]` use pattern is not present, add this block after the assessment contract checks:

```python
    opportunity = structured["opportunity"]
    for key in ["stage_id", "stage_reason", "stage_confidence", "stage_signal_hits", "opportunity_confirmed"]:
        if key not in opportunity:
            fail(f"{source} missing opportunity.{key}")
```

In the archive case after `opportunity = archive_result["structured_data"]["opportunity"]` is not currently assigned, add this before `assessment = ...`:

```python
        archive_opportunity = archive_result["structured_data"].get("opportunity", {})
        if archive_opportunity.get("stage_id") not in {"opportunity_confirmed", "solution_cocreation", "budget_project_confirmed"}:
            fail(f"archive case stage_id did not reflect confirmed opportunity flow: {archive_opportunity}")
        if not archive_opportunity.get("opportunity_confirmed"):
            fail("archive case should be marked as confirmed opportunity")
```

- [ ] **Step 2: Run validator to verify new contract fails**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: FAIL with `missing opportunity.stage_id`.

- [ ] **Step 3: Replace local stage inference call**

In `opportunity-analysis-skill/src/opportunity_skill/stages/opportunity_analysis.py`, add the import:

```python
from ..stage_management import infer_opportunity_stage
```

Keep the existing `infer_stage()` function for backward import compatibility, but stop using it in `analyze_opportunity()`. Replace:

```python
    stage, stage_reason = infer_stage(text, core_need, budget_signal)
```

with:

```python
    stage_result = infer_opportunity_stage({
        "text": text,
        "core_need": core_need,
        "budget_signal": budget_signal,
        "budget_amount": budget_amount,
        "timeline": timeline,
        "contacts": contacts,
        "decision_chain": decision_chain,
    })
    stage = stage_result["stage"]
    stage_reason = stage_result["stage_reason"]
```

Extend the `opportunity` dict with:

```python
        "stage_id": stage_result["stage_id"],
        "stage_confidence": stage_result["stage_confidence"],
        "stage_signal_hits": stage_result["stage_signal_hits"],
        "opportunity_confirmed": stage_result["opportunity_confirmed"],
```

- [ ] **Step 4: Extend opportunity schema**

In `opportunity-analysis-skill/schemas/opportunity.schema.json`, add these properties after `stage_status`:

```json
    "stage_id": {
      "type": ["string", "null"]
    },
    "stage_confidence": {
      "enum": ["high", "medium", "low", null]
    },
    "stage_signal_hits": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "opportunity_confirmed": {
      "type": ["boolean", "null"]
    },
```

- [ ] **Step 5: Run validator to verify output contract passes**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: PASS through `ok evaluation cases`.

- [ ] **Step 6: Commit Task 2**

```bash
cd /Users/guojiexie/Development/skills
git add opportunity-analysis-skill/src/opportunity_skill/stages/opportunity_analysis.py opportunity-analysis-skill/schemas/opportunity.schema.json opportunity-analysis-skill/scripts/validate_skill.py
git commit -m "Infer explainable opportunity stages"
```

---

### Task 3: Persist Stage Metadata with Backward Compatibility

**Files:**
- Modify: `opportunity-analysis-skill/storage/sqlite/schema.sql`
- Modify: `opportunity-analysis-skill/src/opportunity_skill/storage.py`
- Modify: `opportunity-analysis-skill/scripts/validate_skill.py`

**Interfaces:**
- Consumes opportunity payload keys from Task 2.
- Produces stored/reloaded opportunity rows with `stage_id`, `stage_confidence`, `stage_signal_hits`, and `opportunity_confirmed`.
- Renderer tasks consume those keys from both analyze results and detail results.

- [ ] **Step 1: Add failing detail persistence check**

In `check_evaluation_cases()` after:

```python
        detail_result = run_detail(first_db, first_result["storage_result"]["opportunity_id"], temp_root / "detail")
```

add:

```python
        detail_opp = detail_result["detail"].get("opportunity", {})
        if not detail_opp.get("stage_id"):
            fail("detail result did not reload persisted stage_id")
        if "opportunity_confirmed" not in detail_opp:
            fail("detail result did not reload opportunity_confirmed")
```

- [ ] **Step 2: Run validator to verify persistence fails**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: FAIL with `detail result did not reload persisted stage_id`.

- [ ] **Step 3: Extend SQLite schema**

In `opportunity-analysis-skill/storage/sqlite/schema.sql`, add nullable columns after `stage_status TEXT,`:

```sql
    stage_id TEXT,
    stage_confidence TEXT,
    stage_signal_hits TEXT,
    opportunity_confirmed INTEGER,
```

- [ ] **Step 4: Add automatic column migration**

In `OpportunitySQLiteAdapter.__init__()` or the existing schema initialization path in `opportunity-analysis-skill/src/opportunity_skill/storage.py`, after schema execution, add:

```python
        self._ensure_opportunity_stage_columns()
```

Add this method to `OpportunitySQLiteAdapter`:

```python
    def _ensure_opportunity_stage_columns(self) -> None:
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(opportunities)").fetchall()}
        additions = {
            "stage_id": "TEXT",
            "stage_confidence": "TEXT",
            "stage_signal_hits": "TEXT",
            "opportunity_confirmed": "INTEGER",
        }
        for name, sql_type in additions.items():
            if name not in columns:
                self.conn.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {sql_type}")
        self.conn.commit()
```

- [ ] **Step 5: Persist and reload new fields**

In `upsert_opportunity()`, extend the INSERT column list:

```sql
stage_id, stage_confidence, stage_signal_hits, opportunity_confirmed,
```

Extend the SQL `VALUES` list by four `?` entries and the UPDATE clause:

```sql
stage_id=excluded.stage_id, stage_confidence=excluded.stage_confidence,
stage_signal_hits=excluded.stage_signal_hits, opportunity_confirmed=excluded.opportunity_confirmed,
```

Extend the parameter tuple after `opportunity.get("stage_status")`:

```python
                opportunity.get("stage_id"), opportunity.get("stage_confidence"),
                to_json(opportunity.get("stage_signal_hits", [])),
                int(bool(opportunity.get("opportunity_confirmed", False))),
```

In `_row_to_opportunity_summary()`, add:

```python
            "stage_id": row["stage_id"] if "stage_id" in row.keys() else None,
            "stage_confidence": row["stage_confidence"] if "stage_confidence" in row.keys() else None,
            "stage_signal_hits": from_json(row["stage_signal_hits"]) if "stage_signal_hits" in row.keys() else [],
            "opportunity_confirmed": bool(row["opportunity_confirmed"]) if "opportunity_confirmed" in row.keys() and row["opportunity_confirmed"] is not None else None,
```

- [ ] **Step 6: Run validator to verify persistence passes**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: PASS through `ok evaluation cases`.

- [ ] **Step 7: Commit Task 3**

```bash
cd /Users/guojiexie/Development/skills
git add opportunity-analysis-skill/storage/sqlite/schema.sql opportunity-analysis-skill/src/opportunity_skill/storage.py opportunity-analysis-skill/scripts/validate_skill.py
git commit -m "Persist opportunity stage metadata"
```

---

### Task 4: Detail Page Stage Module and Top Metrics

**Files:**
- Modify: `opportunity-analysis-skill/display/templates/opportunity_card.html`
- Modify: `opportunity-analysis-skill/display/templates/opportunity_detail.html`
- Modify: `opportunity-analysis-skill/display/css/default.css`
- Modify: `opportunity-analysis-skill/src/opportunity_skill/renderer.py`
- Modify: `opportunity-analysis-skill/scripts/validate_skill.py`

**Interfaces:**
- Consumes `opportunity.stage_id`, `opportunity.stage`, `opportunity.stage_reason`, `opportunity.stage_confidence`, `opportunity.stage_signal_hits`, `opportunity.opportunity_confirmed`.
- Produces detail HTML classes: `ql-stage-panel`, `ql-stage-step-current`, `ql-stage-confirmed-marker`, `ql-hero-metrics`.

- [ ] **Step 1: Add failing detail HTML assertions**

In `check_evaluation_cases()` archive HTML checks, add after the radar panel assertion:

```python
        for marker in ["ql-stage-panel", "商机阶段", "已确认商机", "ql-hero-metrics", "商机评分", "赢单概率", "风险等级"]:
            if marker not in html:
                fail(f"archive case did not render stage or top metric marker {marker}")
```

- [ ] **Step 2: Run validator to verify UI markers fail**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: FAIL with `archive case did not render stage or top metric marker ql-stage-panel`.

- [ ] **Step 3: Update card template for top metrics**

Replace the metric area in `opportunity-analysis-skill/display/templates/opportunity_card.html` with:

```html
    <div class="ql-hero-metrics">
      <div class="ql-hero-metric">
        <span>商机评分</span>
        <strong>{{opportunity.score}}</strong>
        <em>{{opportunity.score_level}}级商机</em>
      </div>
      <div class="ql-hero-metric">
        <span>赢单概率</span>
        <strong>{{opportunity.win_probability_percent}}%</strong>
        <em>{{assessment.confidence_level}}可信度</em>
      </div>
      <div class="ql-hero-metric risk-{{opportunity.risk_level}}">
        <span>风险等级</span>
        <strong>{{opportunity.risk_label}}</strong>
        <em>{{opportunity.stage}}</em>
      </div>
    </div>
```

- [ ] **Step 4: Add stage module to detail template**

In `opportunity-analysis-skill/display/templates/opportunity_detail.html`, insert this after `{{opportunity_card}}`:

```html
    <section class="ql-panel ql-stage-panel">
      <div class="ql-panel-header">
        <h2 class="ql-panel-title">商机阶段</h2>
        <span class="ql-panel-subtitle">{{opportunity.stage_confirmed_label}}</span>
      </div>
      <div class="ql-panel-body">
        <div class="ql-stage-path">{{opportunity.stage_path}}</div>
        <div class="ql-stage-facts">
          <div><span>当前阶段</span><strong>{{opportunity.stage}}</strong></div>
          <div><span>判断依据</span><strong>{{opportunity.stage_reason}}</strong></div>
          <div><span>阶段可信度</span><strong>{{opportunity.stage_confidence_label}}</strong></div>
          <div><span>商机状态</span><strong>{{opportunity.stage_confirmed_label}}</strong></div>
        </div>
      </div>
    </section>
```

- [ ] **Step 5: Add renderer helpers**

In `opportunity-analysis-skill/src/opportunity_skill/renderer.py`, import:

```python
from .stage_management import STAGE_DEFINITIONS, stage_from_name
```

Add mapping keys to `_render_opportunity_card()` and `_render_opportunity_detail()`:

```python
            "opportunity.stage_confidence_label": esc(self._confidence_label(opp.get("stage_confidence"))),
            "opportunity.stage_confirmed_label": esc(self._opportunity_confirmed_label(opp)),
            "opportunity.stage_path": self._stage_path(opp),
```

Add helpers:

```python
    def _opportunity_confirmed_label(self, opportunity: dict[str, Any]) -> str:
        value = opportunity.get("opportunity_confirmed")
        if value is None:
            stage = stage_from_name(opportunity.get("stage"))
            value = bool(stage and stage.is_opportunity_confirmed)
        return "已确认商机" if value else "尚未确认商机"

    def _stage_path(self, opportunity: dict[str, Any]) -> str:
        current_id = opportunity.get("stage_id")
        if not current_id:
            stage = stage_from_name(opportunity.get("stage"))
            current_id = stage.stage_id if stage else None
        current_order = 0
        for stage in STAGE_DEFINITIONS:
            if stage.stage_id == current_id:
                current_order = stage.order
                break
        parts = []
        for stage in STAGE_DEFINITIONS:
            classes = ["ql-stage-step"]
            if stage.order < current_order:
                classes.append("ql-stage-step-done")
            if stage.stage_id == current_id:
                classes.append("ql-stage-step-current")
            if stage.stage_id == "opportunity_confirmed":
                classes.append("ql-stage-confirmed-marker")
            marker = "关键节点" if stage.stage_id == "opportunity_confirmed" else str(stage.order)
            parts.append(
                "<div class='" + " ".join(classes) + "'>"
                f"<span>{esc(marker)}</span>"
                f"<strong>{esc(stage.name)}</strong>"
                "</div>"
            )
        if current_order == 0 and opportunity.get("stage"):
            parts.append(
                "<div class='ql-stage-step ql-stage-step-current'>"
                "<span>未归类</span>"
                f"<strong>{esc(opportunity.get('stage'))}</strong>"
                "</div>"
            )
        return "".join(parts)
```

- [ ] **Step 6: Add CSS**

Add to `opportunity-analysis-skill/display/css/default.css` near the existing card and assessment styles:

```css
.ql-hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.ql-hero-metric {
  min-width: 0;
  border: 1px solid var(--ql-line);
  border-radius: 6px;
  background: var(--ql-surface);
  padding: 12px;
}

.ql-hero-metric span,
.ql-stage-facts span {
  display: block;
  color: var(--ql-muted);
  font-size: 12px;
  line-height: 18px;
}

.ql-hero-metric strong {
  display: block;
  color: var(--ql-strong);
  font-size: 28px;
  line-height: 34px;
}

.ql-hero-metric em {
  display: block;
  margin-top: 4px;
  color: var(--ql-muted);
  font-style: normal;
  font-size: 12px;
  line-height: 18px;
}

.ql-stage-path {
  display: grid;
  grid-template-columns: repeat(10, minmax(86px, 1fr));
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.ql-stage-step {
  position: relative;
  min-height: 68px;
  border: 1px solid var(--ql-line);
  border-radius: 6px;
  background: var(--ql-gray-soft);
  padding: 9px;
}

.ql-stage-step span {
  display: inline-flex;
  color: var(--ql-muted);
  font-size: 11px;
  line-height: 16px;
}

.ql-stage-step strong {
  display: block;
  margin-top: 7px;
  color: var(--ql-muted);
  font-size: 13px;
  line-height: 18px;
}

.ql-stage-step-done {
  background: #f2f8f5;
  border-color: #c8ddd4;
}

.ql-stage-step-current {
  background: #e8f3ee;
  border-color: var(--ql-green);
  box-shadow: inset 0 0 0 1px var(--ql-green);
}

.ql-stage-step-current strong {
  color: var(--ql-strong);
}

.ql-stage-confirmed-marker span {
  color: var(--ql-orange);
  font-weight: 700;
}

.ql-stage-facts {
  display: grid;
  grid-template-columns: 0.8fr 2fr 0.8fr 0.8fr;
  gap: 10px;
  margin-top: 12px;
}

.ql-stage-facts div {
  min-width: 0;
  border-top: 1px solid var(--ql-line);
  padding-top: 10px;
}

.ql-stage-facts strong {
  display: block;
  color: var(--ql-ink);
  font-size: 13px;
  line-height: 19px;
}
```

Add mobile rules under `@media (max-width: 960px)`:

```css
  .ql-hero-metrics,
  .ql-stage-facts {
    grid-template-columns: 1fr;
  }
```

- [ ] **Step 7: Run validator and browser smoke check**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: PASS.

Then regenerate the Huachen detail:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
PYTHONPATH=src python3.12 -m opportunity_skill.cli detail \
  --db /Users/guojiexie/.codex/skill_data/opportunity-analysis/opportunity.db \
  --opportunity-id opp_184d863276dc \
  --output-dir /Users/guojiexie/.codex/skill_runs/opportunity-analysis/huachen-2026-07-05 \
  --template opportunity_detail
```

Use Node Playwright from the bundled runtime:

```bash
cd /Users/guojiexie/Development/skills
NODE_PATH=/Users/guojiexie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/guojiexie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node - <<'NODE'
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  for (const [name, width, height] of [['desktop', 1440, 1100], ['mobile', 390, 1000]]) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await page.goto('file:///Users/guojiexie/.codex/skill_runs/opportunity-analysis/huachen-2026-07-05/opportunity_detail.html', { waitUntil: 'load' });
    const metrics = await page.evaluate(() => ({
      width: innerWidth,
      stagePanel: document.querySelectorAll('.ql-stage-panel').length,
      currentStage: document.querySelectorAll('.ql-stage-step-current').length,
      metrics: document.querySelectorAll('.ql-hero-metric').length,
      hasScore: document.body.innerText.includes('商机评分'),
      hasWin: document.body.innerText.includes('赢单概率'),
      hasRisk: document.body.innerText.includes('风险等级'),
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
    }));
    console.log(name, JSON.stringify(metrics));
    await page.close();
  }
  await browser.close();
})();
NODE
```

Expected: both outputs have `stagePanel:1`, `currentStage:1`, `metrics:3`, all `has*` values `true`, and `overflow:false`.

- [ ] **Step 8: Commit Task 4**

```bash
cd /Users/guojiexie/Development/skills
git add opportunity-analysis-skill/display/templates/opportunity_card.html opportunity-analysis-skill/display/templates/opportunity_detail.html opportunity-analysis-skill/display/css/default.css opportunity-analysis-skill/src/opportunity_skill/renderer.py opportunity-analysis-skill/scripts/validate_skill.py
git commit -m "Render opportunity stage path"
```

---

### Task 5: Kanban Stage Columns and Confirmed Count

**Files:**
- Modify: `opportunity-analysis-skill/display/templates/opportunity_kanban.html`
- Modify: `opportunity-analysis-skill/src/opportunity_skill/renderer.py`
- Modify: `opportunity-analysis-skill/display/css/default.css`
- Modify: `opportunity-analysis-skill/scripts/validate_skill.py`

**Interfaces:**
- Consumes `STAGE_DEFINITIONS`, `stage_from_name()`, and opportunity `opportunity_confirmed`.
- Produces kanban columns for the new stage model and summary token `summary.confirmed`.

- [ ] **Step 1: Add failing kanban assertions**

In `check_evaluation_cases()` after query rendering:

```python
        kanban_html = query_result.get("display_result", {}).get("html", "")
        for stage_name in ["线索识别", "客户接触", "需求澄清", "商机确认", "方案共创", "预算/立项确认", "报价/投标", "商务谈判", "赢单", "丢单"]:
            if stage_name not in kanban_html:
                fail(f"kanban missing stage column {stage_name}")
        if "已确认商机" not in kanban_html and "未确认商机" not in kanban_html:
            fail("kanban did not render confirmed opportunity status")
```

- [ ] **Step 2: Run validator to verify kanban assertion fails**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: FAIL with `kanban missing stage column 客户接触`.

- [ ] **Step 3: Update kanban renderer stages and card status**

In `_render_kanban()` in `opportunity-analysis-skill/src/opportunity_skill/renderer.py`, replace the fixed `stages` list with:

```python
        stages = [stage.name for stage in STAGE_DEFINITIONS]
```

Add before the card loop:

```python
        confirmed_count = 0
```

Inside the first `for opp in opportunities:` loop, add:

```python
            if self._opportunity_confirmed_label(opp) == "已确认商机":
                confirmed_count += 1
```

Inside each kanban card topline after the risk tag, add:

```python
                    f"<span class='ql-tag stage-confirmed'>{esc(self._opportunity_confirmed_label(opp))}</span>"
```

Add `"summary.confirmed": esc(confirmed_count),` to the template mapping.

- [ ] **Step 4: Update kanban summary template**

In `opportunity-analysis-skill/display/templates/opportunity_kanban.html`, change the fourth mini-stat from `待确认` to:

```html
        <div class="ql-mini-stat">
          <span>已确认商机</span>
          <strong>{{summary.confirmed}}</strong>
        </div>
```

- [ ] **Step 5: Add compact kanban tag CSS**

Add near kanban card styles in `opportunity-analysis-skill/display/css/default.css`:

```css
.ql-tag.stage-confirmed {
  border-color: #c8ddd4;
  background: #f2f8f5;
  color: var(--ql-green-dark);
}
```

- [ ] **Step 6: Run validator**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
cd /Users/guojiexie/Development/skills
git add opportunity-analysis-skill/display/templates/opportunity_kanban.html opportunity-analysis-skill/src/opportunity_skill/renderer.py opportunity-analysis-skill/display/css/default.css opportunity-analysis-skill/scripts/validate_skill.py
git commit -m "Align kanban with opportunity stages"
```

---

### Task 6: Documentation, Examples, Final Verification, and Push

**Files:**
- Modify: `opportunity-analysis-skill/SKILL.md`
- Modify: `opportunity-analysis-skill/README.md`
- Modify: `opportunity-analysis-skill/references/commercial_assessment.md`
- Modify: `opportunity-analysis-skill/display/display_contract.md`
- Modify: `opportunity-analysis-skill/evaluation/test_cases.json`
- Modify: `STATUS.md`

**Interfaces:**
- Consumes all code and rendering behavior from Tasks 1-5.
- Produces complete user-facing documentation and final validation record.

- [ ] **Step 1: Update skill documentation**

In `opportunity-analysis-skill/SKILL.md`, update the Purpose list item about `opportunity_analysis` to include:

```markdown
3. Run `opportunity_analysis`: extract need, standard opportunity stage, confirmed-opportunity state, budget signal, timeline, competitors, risks, next actions, commercial confirmation questions, score, and win probability.
```

Add this paragraph after the commercial dimensions paragraph:

```markdown
The detail renderer must show the standard opportunity stage path and the current-stage judgment. `商机确认` is the point where a lead becomes a real opportunity worth presales or solution resources. Budget confirmation is a later stage and is not required for `opportunity_confirmed=true`.
```

- [ ] **Step 2: Update README stage section**

In `opportunity-analysis-skill/README.md`, add a `## Opportunity Stage Management` section before `## Commercial Assessment`:

```markdown
## Opportunity Stage Management

The skill uses a standard enterprise-service stage model:

`线索识别 -> 客户接触 -> 需求澄清 -> 商机确认 -> 方案共创 -> 预算/立项确认 -> 报价/投标 -> 商务谈判 -> 赢单 / 丢单`

`商机确认` marks the moment a lead becomes a real opportunity. An opportunity can be confirmed before budget is fully clear. The runtime outputs `stage_id`, `stage`, `stage_reason`, `stage_confidence`, `stage_signal_hits`, and `opportunity_confirmed`, while keeping the existing Chinese `stage` field for compatibility.

The detail page renders a static stage path below the opportunity summary card. The kanban uses the same stage model for columns and displays confirmed-opportunity status on each card.
```

- [ ] **Step 3: Update display contract**

In `opportunity-analysis-skill/display/display_contract.md`, add detail-view requirements:

```markdown
- `opportunity_detail` must render the standard opportunity stage path, current-stage reason, stage confidence, and confirmed-opportunity status when those fields are present.
- `opportunity_kanban` must group opportunities by the standard stage model and show confirmed-opportunity status on each card.
```

- [ ] **Step 4: Update evaluation cases**

In `opportunity-analysis-skill/evaluation/test_cases.json`, update expected stage values to the new stage model. For the existing visit-note case that contains方案确认 and technical exchange signals, set:

```json
"expected_stage": "方案共创"
```

Keep `expected_min_score` unchanged unless the implementation changes commercial scoring.

- [ ] **Step 5: Update STATUS**

Run:

```bash
date '+%Y-%m-%d %H:%M:%S %Z'
```

Add a new top entry in `STATUS.md` that starts with the exact timestamp returned by that command and uses this body:

```markdown
- Scope: Implement opportunity stage management in `opportunity-analysis-skill`.
- Changed files:
  - `opportunity-analysis-skill/src/opportunity_skill/stage_management.py`
  - `opportunity-analysis-skill/src/opportunity_skill/stages/opportunity_analysis.py`
  - `opportunity-analysis-skill/src/opportunity_skill/storage.py`
  - `opportunity-analysis-skill/storage/sqlite/schema.sql`
  - `opportunity-analysis-skill/src/opportunity_skill/renderer.py`
  - `opportunity-analysis-skill/display/templates/opportunity_card.html`
  - `opportunity-analysis-skill/display/templates/opportunity_detail.html`
  - `opportunity-analysis-skill/display/templates/opportunity_kanban.html`
  - `opportunity-analysis-skill/display/css/default.css`
  - `opportunity-analysis-skill/scripts/validate_skill.py`
  - `opportunity-analysis-skill/schemas/opportunity.schema.json`
  - `opportunity-analysis-skill/evaluation/test_cases.json`
  - `opportunity-analysis-skill/SKILL.md`
  - `opportunity-analysis-skill/README.md`
  - `opportunity-analysis-skill/display/display_contract.md`
  - `opportunity-analysis-skill/references/commercial_assessment.md`
- Simplifications made:
  - Added static, explainable stage management without stage history, manual movement, drag-and-drop, or stage gate enforcement.
  - Kept the Chinese `stage` field compatible while storing nullable stage metadata.
  - Reused static HTML/CSS instead of adding JavaScript or a frontend framework.
- Validation:
  - `python3.12 scripts/validate_skill.py` passed.
  - `git diff --check -- opportunity-analysis-skill STATUS.md` passed.
  - Regenerated the Huachen detail HTML.
  - Playwright desktop/mobile preview verified one stage panel, one current stage, three top metrics, no overflow, and kanban stage columns.
- Commit/push state: pending commit and push.
- Remaining notes:
  - Stage history and manual stage movement remain out of scope.
```

- [ ] **Step 6: Run full validation**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
python3.12 scripts/validate_skill.py
```

Expected: PASS with:

```text
ok json files
ok python compile
ok template safety
ok stage modules
ok stage management
ok confirmation loop
ok evaluation cases
ok distribution noise
validation passed
```

- [ ] **Step 7: Run diff check**

Run:

```bash
cd /Users/guojiexie/Development/skills
git diff --check -- opportunity-analysis-skill STATUS.md
```

Expected: no output and exit code `0`.

- [ ] **Step 8: Regenerate Huachen detail**

Run:

```bash
cd /Users/guojiexie/Development/skills/opportunity-analysis-skill
PYTHONPATH=src python3.12 -m opportunity_skill.cli detail \
  --db /Users/guojiexie/.codex/skill_data/opportunity-analysis/opportunity.db \
  --opportunity-id opp_184d863276dc \
  --output-dir /Users/guojiexie/.codex/skill_runs/opportunity-analysis/huachen-2026-07-05 \
  --template opportunity_detail
```

Expected: JSON output contains:

```json
{
  "opportunity_id": "opp_184d863276dc",
  "output_dir": "/Users/guojiexie/.codex/skill_runs/opportunity-analysis/huachen-2026-07-05"
}
```

- [ ] **Step 9: Run browser verification**

Run the Node Playwright command from Task 4 and add kanban rendering check:

```bash
cd /Users/guojiexie/Development/skills
NODE_PATH=/Users/guojiexie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
/Users/guojiexie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node - <<'NODE'
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const detail = 'file:///Users/guojiexie/.codex/skill_runs/opportunity-analysis/huachen-2026-07-05/opportunity_detail.html';
  for (const [name, width, height] of [['desktop', 1440, 1100], ['mobile', 390, 1000]]) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await page.goto(detail, { waitUntil: 'load' });
    const metrics = await page.evaluate(() => ({
      stagePanel: document.querySelectorAll('.ql-stage-panel').length,
      currentStage: document.querySelectorAll('.ql-stage-step-current').length,
      topMetrics: document.querySelectorAll('.ql-hero-metric').length,
      confirmed: document.body.innerText.includes('已确认商机') || document.body.innerText.includes('尚未确认商机'),
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
    }));
    console.log(name, JSON.stringify(metrics));
    await page.close();
  }
  await browser.close();
})();
NODE
```

Expected: both viewport outputs have `stagePanel:1`, `currentStage:1`, `topMetrics:3`, `confirmed:true`, and `overflow:false`.

- [ ] **Step 10: Commit final implementation**

```bash
cd /Users/guojiexie/Development/skills
git add STATUS.md opportunity-analysis-skill
git commit -m "Implement opportunity stage management"
```

- [ ] **Step 11: Update STATUS commit state and commit**

After Task 6 Step 10, capture the commit SHA:

```bash
git rev-parse --short HEAD
```

Update the top `STATUS.md` entry from:

```markdown
- Commit/push state: pending commit and push.
```

to a line containing the exact short SHA returned by the command:

```markdown
- Commit/push state: committed as the short SHA returned by `git rev-parse --short HEAD`; push pending with status update commit.
```

The final line should look like `- Commit/push state: committed as \`abc1234\`; push pending with status update commit.` with `abc1234` replaced by the actual command output. Then run:

```bash
git diff --check -- STATUS.md
git add STATUS.md
git commit -m "Record opportunity stage implementation status"
```

- [ ] **Step 12: Push**

```bash
cd /Users/guojiexie/Development/skills
git push origin main
git status --short
```

Expected: push succeeds. `git status --short` may still show pre-existing unrelated `wechat-official-account-skills` changes and untracked local artifacts; it must not show unstaged `opportunity-analysis-skill`, `STATUS.md`, or plan/spec files.
