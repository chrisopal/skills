from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from opportunity_skill.renderer import SkillDisplayRenderer


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.renderer = SkillDisplayRenderer()
        self.data = {
            "account": {"company_name": "长名称制造企业", "industry": "制造", "region": "湖北"},
            "opportunity": {"name": "生产质量项目", "stage_id": "won", "stage": "赢单", "score": 71,
                            "risk_level": "high", "core_need": "生产质量追溯", "missing_information": ["采购范围待确认"]},
            "lifecycle": {"current_stage_id": "solution_cocreation", "suggested_stage_id": "proposal_bidding",
                          "status": "active", "revision": 3, "owner": "王经理", "verification_status": "verified",
                          "actions": [{"action_id": "a1", "title": "核验现场", "owner": "李工", "due_date": "2026-10-20", "status": "completed", "result": "现场已核验", "evidence": ["ev1"]},
                                      {"title": "确认接口", "owner": "赵工", "due_date": "2026-10-22", "status": "open"}],
                          "history": [{"from_stage": "needs_discovery", "to_stage": "solution_cocreation", "actor": "王经理", "time": "2026-10-11", "reason": "客户确认范围", "evidence": ["ev1"]}],
                          "facts": [{"name": "客户反馈", "value": "接口方案通过", "evidence_ids": ["ev2"]}],
                          "artifacts": [{"artifact_id": "art1", "kind": "proposal", "version": 2, "file_path": "proposal-v2.md", "validity": "stale_or_missing", "metadata": {"feedback": "待复核"}, "sha256": "hash1", "evidence": ["ev2"]}],
                          "contracts": [{"id": "c1", "version": 1, "signed_file": "contract.pdf", "signed_at": "2026-10-30", "status": "signed", "evidence": ["ev3"]}],
                          "status_history": [{"status": "paused", "reason": "客户排期", "actor": "王经理"}]},
            "contacts": [{"name": "陈总", "title": "总经理", "department": "管理", "role_in_opportunity": "决策人"}],
            "decision_chain": [{"decision_role": "最终决策人/关键拍板人", "person_name": "陈总", "status": "confirmed", "influence_level": "high"}],
            "commercial_assessment": {"deal_attractiveness_score": 80, "dimensions": [{"category": "deal_attractiveness", "label": "项目价值", "score": 80, "rationale": "真实依据", "question": "是否确认预算", "answer": "预算已确认"}]},
            "evidence": [{"source_name": "现场纪要", "content": "客户确认方案范围和验收指标"}],
            "archived_files": [{"id": "f1", "relative_path": "attachments/现场纪要.pdf", "file_name": "现场纪要.pdf"}],
        }

    def body(self, result):
        return result["html"].split("<body", 1)[1]

    def test_detail_preserves_business_content_and_lifecycle(self):
        result = self.renderer.render("opportunity_detail", self.data)
        for marker in ["当前阶段", "方案共创", "建议阶段", "报价/投标", "王经理", "确认接口", "2026-10-22", "采购范围待确认", "阶段历史", "客户确认范围", "现场已核验", "ev1", "版本成果", "art1", "文件已变更或缺失", "ql-record-invalid", "合同与签署", "2026-10-30", "陈总", "现场纪要", "商机价值", "预算已确认", "状态变更", "客户排期"]:
            self.assertIn(marker, result["html"], marker)
        self.assertNotIn("成交意向", result["html"])
        for marker in ["阶段历史", "客户确认范围", "art1", "ev3", "当前阶段：方案共创", "商机价值", "现场已核验", "陈总"]:
            self.assertIn(marker, result["markdown"], marker)

    def test_legacy_stage_is_suggestion_without_fabricated_history(self):
        data = copy.deepcopy(self.data)
        del data["lifecycle"]
        body = self.body(self.renderer.render("opportunity_detail", data))
        self.assertIn("暂无正式阶段变更", body)
        self.assertIn("建议阶段", body)
        self.assertIn("待确认", body)
        self.assertNotIn("ql-stage-step-done", body)
        self.assertNotIn("✓", body)
        self.assertNotIn("ql-stage-step-current", body)
        self.assertNotIn("已确认商机", body)

    def test_reviews_and_dependency_revalidation_are_visible_and_escaped(self):
        self.data["lifecycle"]["reviews"] = [{"id": "RV-01", "title": "<客户意见>",
            "requirement_ids": ["REQ-02"], "owner": "林工", "due_date": "2026-10-22",
            "artifact_id": "s1", "blocking": True, "status": "resolved", "verification_status": "needs_review",
            "verification_reasons": ["review closure solution is superseded"],
            "closure": {"artifact_id": "s2", "resolution": "<整改结果>", "evidence": ["ev3"]}, "history": []}]
        self.data["lifecycle"]["artifacts"] = [
            {"id": "s1", "kind": "solution", "version": 1, "validity": "superseded"},
            {"id": "s2", "kind": "solution", "version": 2, "validity": "superseded"},
            {"id": "q1", "kind": "quote", "version": 1, "validity": "dependency_invalid",
             "dependencies": [{"artifact_id": "s2", "sha256": "abc"}], "verification_reasons": ["dependency invalid: s2 (superseded)"]}]
        result = self.renderer.render("opportunity_detail", self.data)
        for marker in ["客户评审与整改", "需复核 · 阻塞推进", "REQ-02", "2026-10-22", "评审 V1", "关闭 V2", "解决方案 V2", "依据版本需复核", "上游成果需复核：s2", "ev3", "&lt;客户意见&gt;"]:
            self.assertIn(marker, result["html"])
        self.assertNotIn("<整改结果>", result["html"])
        self.assertIn("RV-01", result["markdown"])

    def test_current_stage_is_authoritative_and_results_not_pipeline_steps(self):
        body = self.body(self.renderer.render("opportunity_detail", self.data))
        self.assertIn("ql-stage-step-current", body)
        self.assertNotIn("ql-stage-step-done", body)
        self.assertNotIn("<strong>丢单</strong>", body)
        self.assertNotIn("<strong>暂停</strong>", body)
        self.assertIn("合同签署", body)

    def test_list_populated_and_empty(self):
        record = {**self.data, "detail_url": "details/one.html"}
        result = self.renderer.render("opportunity_list", {"opportunities": [record]})
        self.assertIn("details/one.html", result["html"])
        for marker in ["商机列表", "长名称制造企业", "王经理", "方案共创", "确认接口", "2026-10-22", "采购范围待确认"]:
            self.assertIn(marker, result["html"])
        self.assertIn("生产质量项目", result["markdown"])
        self.assertIn("暂无商机", self.renderer.render("opportunity_list", {"opportunities": []})["html"])

    def test_kanban_populated_empty_and_outcomes(self):
        paused = copy.deepcopy(self.data)
        paused["lifecycle"]["status"] = "paused"
        html = self.renderer.render("opportunity_kanban", {"opportunities": [self.data, paused]})["html"]
        self.assertIn("生产质量项目", html)
        self.assertIn("暂停", html)
        self.assertIn("确认接口", html)
        self.assertIn("暂无商机", self.renderer.render("opportunity_kanban", {"opportunities": []})["html"])

    def test_safe_urls_and_escaped_data(self):
        data = copy.deepcopy(self.data)
        data["opportunity"]["name"] = '<script>alert(1)</script>{{opportunity.stage}}'
        data["lifecycle"]["facts"] = [{"value": '<img onerror="evil()">'}]
        data["archived_files"] = [{"id": "bad", "relative_path": "javascript:evil()", "file_name": "bad"}]
        result = self.renderer.render("opportunity_detail", data)
        self.assertIn("&lt;script&gt;", result["html"])
        self.assertIn("{{opportunity.stage}}", result["html"])
        self.assertNotIn("<script", result["html"])
        self.assertNotIn("<img onerror", result["html"])
        self.assertNotIn("href='javascript", result["html"])
        for url in ["javascript:evil()", "//evil.test", "data:text/html,bad", "java\nscript:evil()", "\\\\evil.test"]:
            row = {**self.data, "detail_url": url}
            self.assertNotIn("<a", self.body(self.renderer.render("opportunity_list", {"opportunities": [row]})).split("<tbody>", 1)[1])

    def test_static_templates_have_no_fake_controls_or_scripts(self):
        for template in ["opportunity_detail", "opportunity_card", "customer_profile", "risk_table", "next_action_list", "opportunity_list", "opportunity_kanban"]:
            data = {"opportunities": [self.data]} if template in {"opportunity_list", "opportunity_kanban"} else self.data
            body = self.body(self.renderer.render(template, data))
            self.assertNotRegex(body, r"<script|\son\w+\s*=")
            self.assertNotIn("ql-command", body)
            self.assertNotIn("<button", body)
            self.assertNotIn("{{", body)

    def test_theme_scope_focus_and_narrow_content_rules(self):
        html = self.renderer.render("opportunity_detail", self.data, theme="dark")["html"]
        self.assertIn("data-theme='dark'", html)
        self.assertIn("--ui-action-text: #80B5FF", html)
        self.assertIn("--ui-action-solid: #1558B0", html)
        self.assertIn("focus-visible", html)
        self.assertIn("@media (max-width: 767px)", html)
        self.assertIn("overflow-wrap: anywhere", html)
        css = self.renderer.css
        self.assertNotRegex(css, r"(?m)^\s*(?:svg|button|div)\s*[,{]")
        self.assertNotIn("https://", css)
        self.assertNotIn("gradient", css)
        self.assertIn("data-ui='legacy'", self.renderer.render("opportunity_detail", self.data, profile="legacy")["html"])

    def test_missing_values_and_file_integrity_are_not_business_claims(self):
        body = self.body(self.renderer.render("opportunity_detail", self.data))
        self.assertIn("待评估", body)
        self.assertNotIn("<strong>0%</strong>", body)
        self.assertNotIn("待确认级商机", body)
        self.assertNotIn("结束原因", body)
        self.assertIn("文件状态", body)
        self.assertIn("需复核", body)
        self.assertNotIn("已核验", body.split("</dl>", 1)[0])
        self.assertIn("编号与证据", body)
        data = copy.deepcopy(self.data)
        data["lifecycle"]["artifacts"] = []
        data["lifecycle"]["verification_status"] = "current"
        self.assertEqual(self.renderer._file_status(data["lifecycle"]), "未登记")
        data["lifecycle"]["artifacts"] = [{"validity": "valid"}]
        self.assertEqual(self.renderer._file_status(data["lifecycle"]), "文件未变更")

    def test_lifecycle_empty_blockers_and_selected_action_are_authoritative(self):
        data = copy.deepcopy(self.data)
        life = data["lifecycle"]
        life["blockers"] = []
        life["next_action"] = {"title": "运行层选定动作", "due_date": "2026-10-12"}
        summary = self.renderer._lifecycle_summary(data)
        self.assertIn("暂无已登记阻塞", summary)
        self.assertNotIn("采购范围待确认", summary)
        self.assertIn("运行层选定动作", summary)
        life["next_action"] = None
        self.assertEqual(self.renderer._next_action(life), {})
        del life["next_action"]
        life["actions"] = [{"title": "较晚", "due_date": "2026-11-20"}, {"title": "最早", "due_date": "2026-10-11"}]
        self.assertEqual(self.renderer._next_action(life)["title"], "最早")

    def test_runtime_labels_and_archived_artifact_link(self):
        data = copy.deepcopy(self.data)
        life = data["lifecycle"]
        life["status"] = "won"
        life["facts"] = [{"fact_id": "contact_established", "value": True, "status": "confirmed"}]
        life["artifacts"] = [{"id": "solution-v1", "kind": "solution", "file_path": "/Users/private/solution.md", "archive_path": "attachments/solution.md", "status": "registered"}]
        life["contracts"] = [{"signing_date": "2026-10-11", "amount": 120000, "currency": "CNY", "parties": ["客户甲", "供应商乙"], "signature_facts": {"customer_signed": True, "supplier_signed": True}, "verification_scope": "Recorded signature facts; no legal or signature authenticity verification."}]
        body = self.body(self.renderer.render("opportunity_detail", data))
        for marker in ["已签单", "客户接触已建立", "解决方案", "已登记", "签署日期", "合同金额", "人民币（CNY）", "客户甲；供应商乙", "客户：已登记签署", "真实性与法律效力未核验", "href=\'attachments/solution.md\'"]:
            self.assertIn(marker, body)
        self.assertNotIn("href='/Users", body)
        self.assertNotIn("<dd>True</dd>", body)
        del life["artifacts"][0]["archive_path"]
        body = self.body(self.renderer.render("opportunity_detail", data))
        self.assertNotIn("href='/Users", body)
        self.assertIn("solution.md", body)

    def test_long_data_is_retained(self):
        data = copy.deepcopy(self.data)
        long_value = "很长的客户反馈" * 80 + "final-marker"
        data["lifecycle"]["facts"][0]["value"] = long_value
        data["evidence"][0]["content"] = long_value
        html = self.renderer.render("opportunity_detail", data)["html"]
        self.assertIn(long_value, html)
        self.assertIn("<details", html)


if __name__ == "__main__":
    unittest.main()
