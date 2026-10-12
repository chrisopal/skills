#!/usr/bin/env python3
"""Rehearse a simulated opportunity through the public CLI; keep outputs local."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def rehearse(output: Path) -> dict:
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new empty output directory; rehearsal never overwrites an existing project.")
    output.mkdir(parents=True, exist_ok=True)
    run = Path(__file__).with_name("run.py")
    db = output / "opportunity.db"
    logs = output / "requests"
    logs.mkdir()
    sequence = 0
    checks = []

    def write_json(path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def cli(command, *args, expect_failure=False):
        nonlocal sequence
        sequence += 1
        result = subprocess.run([sys.executable, str(run), command, "--db", str(db), *map(str, args)], capture_output=True, text=True)
        (logs / f"{sequence:02d}-{command}.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (logs / f"{sequence:02d}-{command}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        if expect_failure:
            if result.returncode == 0:
                raise AssertionError("Invalid business mutation unexpectedly succeeded")
            return None
        if result.returncode:
            raise RuntimeError(result.stderr)
        return json.loads(result.stdout)

    contact = output / "01-customer-note.md"
    contact.write_text("# 模拟客户交流记录\n客户：示例工业服务有限公司。联系人：王敏，业务负责人。客户需要设备服务工单管理；先讨论方案，再决定是否报价。此文件为功能演练素材，不是真实客户记录。\n", encoding="utf-8")
    seed = {"request_id": "demo-create", "owner": "模拟销售负责人", "evidence_list": [{"evidence_id": "EV-CONTACT", "source_type": "meeting_note", "source_name": "模拟初次交流", "content": contact.read_text(), "file_path": str(contact), "confidence": 0.9}]}
    source = output / "seed.json"
    write_json(source, seed)
    first = cli("analyze", "--input", source, "--template", "opportunity_detail", "--output-dir", output / "initial")
    oid = first["storage_result"]["opportunity_id"]

    def state():
        return cli("lifecycle", "--opportunity-id", oid)["lifecycle"]

    def manage(label, operations, expect_failure=False):
        envelope = {"request_id": label, "opportunity_id": oid, "expected_revision": state()["revision"], "actor": "模拟业务负责人", "operations": operations}
        path = logs / f"{label}.json"
        write_json(path, envelope)
        return cli("manage", "--input", path, expect_failure=expect_failure)

    def fact(key, value=True, artifact_id=None):
        op = {"type": "confirm_fact", "fact_id": key, "value": value, "evidence": ["EV-FOLLOWUP"]}
        if artifact_id:
            op["artifact_id"] = artifact_id
        return op

    def transition(stage):
        return {"type": "transition", "to_stage": stage, "reason": "已核验对应模拟材料", "evidence": ["EV-FOLLOWUP"]}

    def artifact(aid, kind, version=1):
        path = output / f"{aid}.md"
        descriptions = {
            "solution": "范围：设备服务工单、客户响应及状态追踪；演示验证通过。",
            "quote": "正式模拟报价：人民币120000元；范围对应方案；有效期30天。修订版保留相同金额并明确培训范围。",
            "negotiation": "模拟谈判结果：范围、金额、交付和付款条件已逐项记录；此素材不构成对外承诺。",
            "contract": "模拟合同编号 DEMO-2026-001。双方：示例工业服务有限公司、示例服务供应商有限公司。金额CNY120000。双方签署于2026-10-11。此文件仅用于软件功能演练，不具实际签署或法律效力。",
            "handoff": "模拟交付交接：工单管理范围、联系人、付款安排、验收口径、待办及资源安排。未记录实际回款或客户验收。",
        }
        path.write_text(f"# 模拟{kind}文件\n\n{descriptions[kind]}\n", encoding="utf-8")
        required = {"quote": ["solution"], "negotiation": ["quote"], "contract": ["quote", "negotiation"], "handoff": ["contract"]}.get(kind, [])
        current = state()["artifacts"]
        dependencies = []
        for upstream_kind in required:
            upstream = next(a for a in reversed(current) if a["kind"] == upstream_kind and a["validity"] == "valid")
            dependencies.append({"artifact_id": upstream["id"], "sha256": upstream["sha256"]})
        return {"type": "register_artifact", "dependencies": dependencies, "artifact_id": aid, "document_id": kind, "kind": kind, "version": version, "file_path": str(path), "evidence": ["EV-FOLLOWUP"], "metadata": {"simulated": True, "use_scope": "internal-rehearsal", "contract_number": "DEMO-2026-001" if kind == "contract" else None}}

    initial = state()
    assert initial["current_stage_id"] == "lead_identified" and not initial["history"]
    checks.append("分析建议不伪造正式阶段及历史")
    followup = output / "02-followup.md"
    followup.write_text("# 模拟跟进与结果\n业务负责人王敏确认需求并安排持续推进。方案演示通过。报价和修订报价由模拟负责人批准。谈判范围、价格、付款、交付已记录；双方模拟签署文件齐备。本文件所有陈述仅为软件测试素材。\n", encoding="utf-8")
    incremental = {"request_id": "demo-followup", "opportunity_id": oid, "expected_revision": initial["revision"], "evidence_list": [{"evidence_id": "EV-FOLLOWUP", "source_type": "meeting_note", "source_name": "模拟跟进与签署记录", "content": followup.read_text(), "file_path": str(followup), "confidence": 0.9}]}
    update = output / "update.json"
    write_json(update, incremental)
    cli("analyze", "--input", update, "--output-dir", output / "updated")
    assert cli("query")["count"] == 1
    checks.append("新材料更新同一商机且保留旧证据")

    manage("contact", [fact("contact_established"), transition("customer_contacted")])
    manage("needs", [fact("need_confirmed"), transition("needs_discovery")])
    manage("qualified", [fact("requirement_owner", "王敏"), fact("continue_intent"), transition("opportunity_confirmed")])
    manage("plan", [{"type": "add_action", "action_id": "ACT-DEMO", "title": "完成方案演示并记录客户反馈", "owner": "模拟售前负责人", "due_date": "2026-10-20"}])
    manage("validated", [artifact("solution-v1", "solution"), fact("solution_scope", "设备服务工单及状态追踪", "solution-v1"), {"type": "complete_action", "action_id": "ACT-DEMO", "result": "模拟演示完成，客户反馈范围符合需求", "evidence": ["EV-FOLLOWUP"]}, transition("solution_cocreation")])
    manage("quoted", [artifact("quote-v1", "quote"), fact("quote_authorized", True, "quote-v1"), transition("proposal_bidding")])
    manage("quote-revised", [artifact("quote-v2", "quote", 2), fact("quote_authorized", True, "quote-v2")])
    manage("negotiated", [artifact("negotiation-v1", "negotiation"), transition("commercial_negotiation")])
    before = state()
    manage("reject-no-signature", [transition("won")], expect_failure=True)
    assert state()["revision"] == before["revision"]
    checks.append("缺签署记录拒绝赢单且事务未改变版本")
    manage("contract-prepared", [artifact("contract-v1", "contract"), transition("contract_signing")])
    signed = {"type": "record_contract", "contract_id": "CON-DEMO", "artifact_id": "contract-v1", "signing_date": "2026-10-11", "parties": ["示例工业服务有限公司", "示例服务供应商有限公司"], "amount": 120000, "currency": "CNY", "signature_facts": {"customer_signed": True, "supplier_signed": True}, "evidence": ["EV-FOLLOWUP"]}
    manage("signed", [signed, transition("won")])
    manage("handoff", [artifact("handoff-v1", "handoff")])
    final = state()
    assert final["status"] == "won" and final["current_stage_id"] == "won"
    assert len(final["contracts"]) == 1 and final["actions"][0]["status"] == "completed"
    assert final["history"][-1]["to_stage"] == "won"
    checks.append("行动完成、报价版本、实际阶段历史、模拟签署及交接回读")
    for theme in ("light", "dark"):
        cli("detail", "--opportunity-id", oid, "--theme", theme, "--output-dir", output / theme)
        cli("query", "--render-html", "--theme", theme, "--output-dir", output / theme)
        cli("query", "--render-html", "--template", "opportunity_kanban", "--theme", theme, "--output-dir", output / theme)
    report = {"simulated": True, "opportunity_id": oid, "checks": checks, "final_lifecycle": final, "limits": "CLI integration with simulated materials; not real customer approval, legally valid signature, CRM sync or calibrated forecast."}
    write_json(output / "acceptance.json", report)
    return {"output": str(output), "opportunity_id": oid, "revision": final["revision"], "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    print(json.dumps(rehearse(parser.parse_args().output), ensure_ascii=False, indent=2))
