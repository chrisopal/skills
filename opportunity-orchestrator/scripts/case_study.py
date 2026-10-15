#!/usr/bin/env python3
"""Run a chronological fictional opportunity through the real shared CLI."""
import argparse
import copy
import html
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "opportunity-analysis-skill" / "src"))
from opportunity_skill.assessment import DIMENSIONS
from opportunity_skill.renderer import SkillDisplayRenderer
from opportunity_skill.stage_management import stage_by_id


def fixture():
    spec = importlib.util.spec_from_file_location("opportunity_case_data", ROOT / "examples" / "full_lifecycle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CASE, module.DOCUMENTS, module.STEPS


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def esc(value):
    return html.escape(str(value), quote=True)


def table(headers, rows, empty="本阶段尚未产生记录"):
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows)
    if not body:
        body = f"<tr><td colspan='{len(headers)}' class='case-empty'>{esc(empty)}</td></tr>"
    return "<div class='case-table-wrap'><table class='case-table'><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>" + body + "</tbody></table></div>"


def document_links(names, documents):
    return "<div class='case-links'>" + "".join(f"<a href='../documents/{esc(name[:-3])}.html'>{esc(documents[name].splitlines()[0].lstrip('# '))} ↗</a>" for name in names) + "</div>"


def workpaper(text):
    """Render the fixture's small heading/paragraph/table subset with escaped text."""
    blocks, paragraph, rows = [], [], []

    def flush():
        if paragraph:
            blocks.append("<p>" + "<br>".join(esc(line) for line in paragraph) + "</p>")
            paragraph.clear()
        if rows:
            blocks.append(table(rows[0], rows[2:]))
            rows.clear()

    for line in text.splitlines():
        if line.startswith("|"):
            if paragraph:
                flush()
            rows.append([c.strip() for c in line.strip("|").split("|")])
        else:
            if rows:
                flush()
            if line.startswith("#"):
                flush()
                level = min(len(line) - len(line.lstrip("#")), 3)
                blocks.append(f"<h{level}>{esc(line.lstrip('#').strip())}</h{level}>")
            elif line.strip():
                paragraph.append(line)
            else:
                flush()
    flush()
    return "".join(blocks)


def render(snapshot, all_steps, theme, css):
    case, documents, _ = fixture()
    step, data, previous = snapshot["step"], snapshot["detail"], snapshot["previous_scores"]
    assessment, lifecycle = data["commercial_assessment"], data["lifecycle"]
    number = snapshot["number"]
    other = "dark" if theme == "light" else "light"
    nav = "".join(f"<a {'aria-current=page' if i == number else ''} href='{i:02d}.html'><span>{i:02d}</span><div>{esc(s['title'])}<small>{s['date']}</small></div></a>" for i, s in enumerate(all_steps, 1))
    score_keys = [("综合参考分", "overall_opportunity_score"), ("赢单可能性", "win_likelihood_score"), ("交易吸引力", "deal_attractiveness_score"), ("交付把握度", "delivery_confidence_score")]
    metrics = "".join(f"<div><span>{label}</span><strong>{assessment[key]}<small> / 100</small></strong></div>" for label, key in score_keys)
    dimensions = assessment["dimensions"]
    changes = [[d["label"], f"{previous.get(d['dimension_id'], '—')} → {d['score']}", d["rationale"]] for d in dimensions if d["dimension_id"] in step.get("scores", {})]
    if not changes:
        changes = [["本次沿用上一轮评估", "未新增评分回答", "阶段推进依据独立事实与文件，不因会议/签署自动加分"]]
    action_rows = [[a["title"], a["owner"], a["due_date"], "已完成" if a["status"] == "completed" else "待处理"] for a in lifecycle["actions"]]
    radar = SkillDisplayRenderer()._assessment_radar_chart(assessment)
    ratings = [[d["label"], d["score"], {"strong": "强", "medium": "中", "weak": "弱", "unknown": "未知"}[d["rating"]], d["rationale"]] for d in dimensions]
    overview = f"<section class='case-panel'><h2>本次判断</h2><p class='case-decision'>{esc(step['decision'])}</p><p>{esc(step['note'])}</p></section><section class='case-panel'><h2>商机评估</h2><div class='case-metrics'>{metrics}</div><details><summary>评分口径与未知项</summary><p>18个维度使用既有运行层评分。强100、中65、弱25、未知40；未知40表示缺信息。综合分含原引擎基线混合，是启发式参考，不是实测成交概率。回答由本案例作者模拟提供；正式阶段、客户评审和签署分别登记。</p></details>{radar}<h3>本次评分变化</h3>{table(['维度','前次 → 本次','本次依据'], changes)}<details><summary>全部18个评分项</summary>{table(['维度','分数','判断','依据'], ratings)}</details></section><section class='case-panel'><h2>跟进行动</h2>{table(['行动','负责人','期限','状态'], action_rows)}</section>"
    reviews = []
    for review in lifecycle.get("reviews", []):
        closure = review.get("closure") or {}
        status = "待整改" if review["status"] == "open" else "需复核" if review.get("verification_status") == "needs_review" else "已关闭"
        basis = closure.get("resolution", "整改后提交客户复审")
        if closure:
            basis += "；" + "、".join(closure["evidence"])
        reviews.append([review["id"] + " / " + "、".join(review["requirement_ids"]), review["title"],
                        review["owner"] + " / " + review["due_date"], status,
                        review["artifact_id"] + (" → " + closure["artifact_id"] if closure else ""), basis])
    solution_docs = [n for n in snapshot["documents"] if n.startswith(("requirements", "solution", "customer-review"))]
    solution = f"<section class='case-panel'><h2>需求与方案版本</h2>{document_links(solution_docs, documents) if solution_docs else '<p class=case-empty>等待需求调研与方案任务。</p>'}<p>{'当前方案 V2；客户认可范围限于演示与报价。生产联通、现场压力及正式验收待交付验证。' if 'solution-v2.md' in solution_docs else '方案 V1 已评审退回，三项意见待整改。' if snapshot['review_status'] == 'open' else '当前方案 V1，等待客户评审。' if 'solution-v1.md' in solution_docs else '已形成需求工作稿，尚未形成可评审方案。' if solution_docs else '需求待进一步调研。'}</p></section><section class='case-panel'><h2>客户评审与整改</h2>{table(['意见 / 需求','客户意见','负责人 / 期限','状态','评审 → 关闭方案','关闭依据 / 下一步'], reviews, '尚未召开客户方案评审')}</section>"
    roles = case["roles"][:1 if number == 1 else 2 if number == 2 else 4]
    competition = f"<section class='case-panel'><h2>决策链</h2>{table(['人员','职责','决策范围','识别来源'], roles)}</section><section class='case-panel'><h2>竞争态势</h2>{table(['供方','已知位置','缺口 / 风险','来源'], snapshot['competitors'], '竞争者未知，列入调研问题')}<p>转述价格保留来源；没有取得原始报价时，不认定为同范围对价。</p></section>"
    renderer = SkillDisplayRenderer()
    artifacts = [[a["id"], renderer._kind_label(a["kind"]), f"V{a['version']}",
                  renderer._dependency_label(lifecycle, a), renderer._status_label(a["validity"]),
                  Path(a["file_path"]).name] for a in lifecycle["artifacts"]]
    contracts = [[c.get("contract_id", c.get("id", "")), c["signing_date"], c["amount"], c["currency"], "双方模拟签署"] for c in lifecycle["contracts"]]
    commercial_docs = [n for n in snapshot["documents"] if n.startswith(("quote", "negotiation", "contract", "handoff", "competition"))]
    commercial = f"<section class='case-panel'><h2>商务与签署</h2>{document_links(commercial_docs, documents)}{table(['合同','签署日期','含税金额','币种','签署状态'], contracts, '没有双方签署登记；当前不能判断已签单')}<p>{'预算未确认。' if number < 7 else '批准预算40万元。' + (' 最终模拟合同35.8万元；首款10.74万元尚未核实，回款/收入/交付验收分别记录。' if lifecycle['status'] == 'won' else ' 预算批准、报价接受和合同签署分别判断。')}</p></section><section class='case-panel'><h2>成果版本台账</h2>{table(['成果','类型','版本','依据版本','核验状态','实际文件'], artifacts)}</section>"
    skill_rows = [["opportunity-orchestrator", "恢复当前版本→任务分派→变更核验→回读正式状态"]] + [[s, "本阶段按对应Skill指引处理，结果见输入/输出与文件"] for s in step["skills"] if s != "opportunity-orchestrator"]
    handoff = f"<section class='case-panel'><h2>本阶段 Skill 调用链</h2>{table(['Skill','责任'], skill_rows)}<h3>输入</h3><p>{esc(step['inputs'])}</p><h3>输出</h3><p>{esc(step['outputs'])}</p><h3>管理页面</h3><p>{esc(step['page'])}</p><details><summary>本次运行证据与执行边界</summary><p>本地CLI实际执行分析、管理和回读。Skill是Agent工作指引，未声称独立多Agent自动调用。方案为需求及方案工作稿；未制作PPT、实际POC或外发。页面是分时只读案例工作台。</p><a href='../stages/{number:02d}/snapshot.json'>本阶段实际回读数据 ↗</a><p>业务日期 {step['date']}；运行层审计时间为真实执行时间，二者分别保留。</p></details></section>"
    panes = [("overview", "概览与评估", overview), ("reviews", "方案与客户评审", solution), ("competition", "竞争与决策链", competition), ("commercial", "商务与合同", commercial), ("skills", "Skill 交接", handoff)]
    tabs = "".join(f"<a role='tab' id='tab-{key}' aria-controls='{key}' aria-selected='{'true' if i == 0 else 'false'}' href='#{key}'>{label}</a>" for i, (key, label, _) in enumerate(panes))
    content = "".join(f"<div role='tabpanel' id='{key}' aria-labelledby='tab-{key}' {'hidden' if i else ''}>{body}</div>" for i, (key, _, body) in enumerate(panes))
    before = f"<a href='{number-1:02d}.html'>← 上一时间点</a>" if number > 1 else ""
    after = f"<a href='{number+1:02d}.html'>下一时间点 →</a>" if number < len(all_steps) else ""
    script = """const tabs=[...document.querySelectorAll('[role=tab]')];function select(){let key=location.hash.slice(1)||'overview';if(!tabs.some(t=>t.getAttribute('href')==='#'+key))key='overview';tabs.forEach(t=>{const active=t.getAttribute('href')==='#'+key;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=!active;});}window.addEventListener('hashchange',select);tabs.forEach((t,i)=>t.addEventListener('keydown',e=>{let j;if(e.key==='ArrowRight')j=(i+1)%tabs.length;else if(e.key==='ArrowLeft')j=(i+tabs.length-1)%tabs.length;else if(e.key==='Home')j=0;else if(e.key==='End')j=tabs.length-1;else return;e.preventDefault();location.hash=tabs[j].getAttribute('href');select();tabs[j].focus();}));select();"""
    return f"""<!doctype html><html lang='zh-CN' data-ui='enterprise' data-theme='{theme}'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{esc(step['title'])} · 华辰商机案例</title><style>{css}</style></head><body class='case-app'><header class='case-topbar'><strong>商机工作台</strong><span>完整案例 · 模拟数据</span><a href='../{other}/{number:02d}.html'>{'深色' if theme == 'light' else '浅色'}模式</a></header><div class='case-shell'><aside class='case-sidebar'><p>华辰装备 / 一期</p><nav aria-label='案例时间点'>{nav}</nav></aside><main class='case-main'><div class='case-heading'><div><p class='case-meta'>{step['date']} · 第 {number} / {len(all_steps)} 个时间点 · 负责人 顾宁</p><h1>{esc(step['title'])}<span class='case-tag'>{esc(stage_by_id(lifecycle['current_stage_id']).name)}</span></h1><p>{esc(case['name'])}</p></div><a class='case-outline' href='../stages/{number:02d}/{theme}/opportunity_detail.html'>查看商机详情 ↗</a></div><div class='case-tabs' role='tablist' aria-label='商机管理页面'>{tabs}</div>{content}<footer class='case-footer'>{before}{after}</footer></main></div><script>{script}</script></body></html>"""


def run_case(output, *, through=12):
    if type(through) is not int or not 1 <= through <= 12:
        raise ValueError('through must be between 1 and 12')
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new empty output directory; existing cases are never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    case, documents, steps = fixture()
    steps = steps[:through]
    for folder in ("documents", "sources", "requests", "stages", "light", "dark"):
        (output / folder).mkdir()
    db, sequence = output / "opportunity.db", 0

    def cli(command, *args, fail=False):
        nonlocal sequence
        sequence += 1
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "run.py"), command, "--db", str(db), *map(str, args)], capture_output=True, text=True)
        for stream in ("stdout", "stderr"):
            (output / "requests" / f"{sequence:03d}-{command}.{stream}.txt").write_text(getattr(result, stream), encoding="utf-8")
        if fail:
            assert result.returncode != 0, "Unsigned contract unexpectedly won"
            return None
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    oid = None
    registered = {}
    snapshots, available_docs, competitors, review_status, previous_scores = [], [], [], None, {}
    answers = {d["id"]: {"dimension_id": d["id"], "rating": "unknown", "answer_text": "未知", "answered_by": "模拟销售顾宁"} for d in DIMENSIONS}
    for number, raw in enumerate(steps, 1):
        step = copy.deepcopy(raw)
        folder = output / "stages" / f"{number:02d}"
        folder.mkdir()
        ev = f"EV-{number:02d}"
        source = output / "sources" / f"{number:02d}.md"
        source.write_text(f"# {step['date']} {step['title']}（模拟）\n\n{step['note']}\n\n仅为完整案例输入，无真实客户或签署。\n", encoding="utf-8")

        def state():
            return cli("lifecycle", "--opportunity-id", oid)["lifecycle"]

        for dimension, (rating, reason) in step.get("scores", {}).items():
            answers[dimension] = {"dimension_id": dimension, "rating": rating, "answer_text": f"{ev}（模拟）：{reason}", "answered_by": "模拟销售顾宁", "evidence_refs": [ev]}
        payload = {"request_id": f"case-analysis-{number}", "account_hint": case["customer"], "owner": case["owner"], "evidence_list": [{"evidence_id": ev, "source_type": "meeting_note", "source_name": f"{step['date']} {step['title']}（模拟）", "content": source.read_text(encoding="utf-8"), "file_path": str(source), "confidence": 0.9}], "sales_confirmation_answers": list(answers.values())}
        if oid:
            payload.update(opportunity_id=oid, expected_revision=state()["revision"])
        request = output / "requests" / f"analysis-{number:02d}.json"
        write_json(request, payload)
        result = cli("analyze", "--input", request, "--output-dir", folder / "analysis")
        oid = result["storage_result"]["opportunity_id"]
        operations = []
        for name, position, gaps, source_note in step.get('competitors', []):
            if name == '我方':
                continue
            operations.append({'type': 'record_competitor', 'competitor_id': 'COMP-' + name,
                'name': name, 'position': position, 'strengths': ['存在客户接触线索；具体优势待核实'],
                'weaknesses': [gaps], 'response': '核验相同范围、税费与交付责任后再比较',
                'status': 'reported', 'evidence': [ev]})
        for name in step.get("docs", []):
            path = output / "documents" / name
            path.write_text(documents[name], encoding="utf-8")
            available_docs.append(name)
        for aid, kind, version, filename in step.get("artifacts", []):
            required = {"quote": ["solution"], "negotiation": ["quote"], "contract": ["quote"], "handoff": ["contract"]}.get(kind, [])
            if kind == "contract" and "negotiation" in registered:
                required.append("negotiation")
            dependencies = [registered[k] for k in required]
            path = output / "documents" / filename
            operations.append({"type": "register_artifact", "artifact_id": aid, "document_id": kind, "kind": kind, "version": version, "file_path": str(path), "dependencies": dependencies, "evidence": [ev], "metadata": {"simulated": True, "scenario_date": step["date"], "source_skill": step["skills"][0]}, **({"scope_review": {"scope_version": max(f["version"] for f in state()["facts"] if f["fact_id"] == "solution_scope"), "summary": "模拟逐项回读：正文对应方案V2、30账号和范围排除；价格付款与有效前提已核对"}} if kind != "solution" else {})})
            registered[kind] = {"artifact_id": aid, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if step.get("review_status") == "open":
            for review in case["reviews"]:
                operations.append({"type": "record_review", **{k: v for k, v in review.items() if k != "resolution"}, "artifact_id": "SOL-1", "blocking": True, "evidence": [ev]})
        if step.get("review_status") == "closed":
            for review in case["reviews"]:
                operations.append({"type": "resolve_review", "review_id": review["review_id"], "artifact_id": "SOL-2", "resolution": review["resolution"], "evidence": [ev]})
        for key, value in step.get("facts", {}).items():
            operations.append({"type": "confirm_fact", "fact_id": key, "value": value, "evidence": [ev], **({"artifact_id": registered["solution"]["artifact_id"]} if key == "solution_scope" else {})})
        if step.get("authorize"):
            operations.append({"type": "confirm_fact", "fact_id": "quote_authorized", "value": True, "artifact_id": step["authorize"], "evidence": [ev]})
        if step.get("complete"):
            operations.append({"type": "complete_action", "action_id": step["complete"], "result": step["note"], "evidence": [ev]})
        if step.get("action"):
            aid, title, owner, due = step["action"]
            operations.append({"type": "add_action", "action_id": aid, "title": title, "owner": owner, "due_date": due})
        if step.get("signed"):
            operations.append({"type": "record_contract", "contract_id": "CON-HC-001", "artifact_id": "C-2", "signing_date": step["date"], "parties": [case["customer"], case["supplier"]], "amount": case["amount"], "currency": "CNY", "signature_facts": {"customer_signed": True, "supplier_signed": True}, "evidence": [ev]})
        if step.get("stage"):
            operations.append({"type": "transition", "to_stage": step["stage"], "reason": step["decision"], "evidence": [ev]})
        envelope = {"request_id": f"case-manage-{number}", "opportunity_id": oid, "expected_revision": state()["revision"], "actor": "案例模拟业务负责人", "operations": operations}
        change = output / "requests" / f"manage-{number:02d}.json"
        write_json(change, envelope)
        if operations:
            cli("manage", "--input", change)
        if step.get("reject_unsigned"):
            revision = state()["revision"]
            envelope.update(request_id="case-reject-unsigned", expected_revision=revision, operations=[{"type": "transition", "to_stage": "won", "reason": "测试未签署保护", "evidence": [ev]}])
            negative = output / "requests" / "reject-unsigned.json"
            write_json(negative, envelope)
            cli("manage", "--input", negative, fail=True)
            assert state()["revision"] == revision
        for theme in ("light", "dark"):
            cli("detail", "--opportunity-id", oid, "--theme", theme, "--output-dir", folder / theme)
        detail = json.loads((folder / "light" / "detail.json").read_text(encoding="utf-8"))
        competitors = [[c['name'], c['position'], '；'.join(c['weaknesses']), '、'.join(c['evidence'])]
                       for c in detail['lifecycle'].get('competitors', [])]
        saved_reviews = detail["lifecycle"].get("reviews", [])
        review_status = ("closed" if all(r["status"] == "resolved" and r["verification_status"] == "current" for r in saved_reviews) else "open") if saved_reviews else None
        snapshot = {"simulated": True, "number": number, "scenario_date": step["date"], "step": step, "detail": detail, "documents": list(available_docs), "competitors": copy.deepcopy(competitors), "review_status": review_status, "previous_scores": previous_scores}
        write_json(folder / "snapshot.json", snapshot)
        snapshots.append(snapshot)
        previous_scores = {d["dimension_id"]: d["score"] for d in detail["commercial_assessment"]["dimensions"]}
    css = (ROOT.parent / "opportunity-analysis-skill" / "display" / "css" / "default.css").read_text(encoding="utf-8") + (ROOT / "assets" / "case.css").read_text(encoding="utf-8")
    for snapshot in snapshots:
        for theme in ("light", "dark"):
            (output / theme / f"{snapshot['number']:02d}.html").write_text(render(snapshot, steps, theme, css), encoding="utf-8")
    for name in available_docs:
        text = (output / "documents" / name).read_text(encoding="utf-8")
        (output / "documents" / f"{name[:-3]}.html").write_text(f"<!doctype html><html lang='zh-CN' data-ui='enterprise'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{esc(name)}</title><style>{css}</style></head><body class='case-app'><main class='case-document'><a class='case-outline' href='{esc(name)}' download>下载方案 / 记录工作稿 ↓</a>{workpaper(text)}</main></body></html>", encoding="utf-8")
    (output / "index.html").write_text("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta http-equiv='refresh' content='0;url=light/01.html'><title>完整商机案例</title></head><body><a href='light/01.html'>从首次拜访开始</a></body></html>", encoding="utf-8")
    rows = []
    for s in snapshots:
        a, l, st = s["detail"]["commercial_assessment"], s["detail"]["lifecycle"], s["step"]
        rows.append([st["date"], st["title"], stage_by_id(l["current_stage_id"]).name, a["overall_opportunity_score"], "、".join(st["skills"]), st["inputs"], st["outputs"], st["page"]])
    markdown = f"# 商机案例：华辰装备售后工单平台一期（截至第{through}次事件）\n\n所有客户、评审、竞争、金额和签署为模拟；CLI实际运行。业务日期与运行时间分开记录。\n\n| 日期 | 事件 | 正式阶段 | 综合分 | Skill（总控始终参与） | 输入 | 输出 | 页面 |\n|---|---|---|---|---|---|---|---|\n" + "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)
    (output / "case-report.md").write_text(markdown + ("\n\n模拟签单35.8万元，不等于回款或收入。" if through == 12 else "\n\n此案例截取尚未记录合同签署。") + "方案工作稿、模拟演示与真实生产验收分别记录。所有页面为本地只读案例视图，写入通过运行层完成。\n", encoding="utf-8")
    result = {"simulated": True, "opportunity_id": oid, "timepoints": len(snapshots), "final_lifecycle": snapshots[-1]["detail"]["lifecycle"], "scores": [s["detail"]["commercial_assessment"]["overall_opportunity_score"] for s in snapshots], "checks": [f"同一商机按{len(snapshots)}份分时证据增量更新", "评分依据与竞争情报实际写入并回读"], "complete_case": through == 12}
    write_json(output / "acceptance.json", result)
    return {"output": str(output), "opportunity_id": oid, "timepoints": len(snapshots), "scores": result["scores"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--through", type=int, default=12, help="Stop at a timepoint for an editable rehearsal")
    args = parser.parse_args()
    print(json.dumps(run_case(args.output, through=args.through), ensure_ascii=False, indent=2))
