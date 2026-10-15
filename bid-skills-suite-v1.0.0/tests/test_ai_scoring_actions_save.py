"""Exercise the actual editor persistence seam, including derived Markdown."""
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import ai_scoring
import bidkit
import test_writing_workspace as fixture
from ai_scoring_actions import AIScoringActionService


class ScoringEditorSaveTest(unittest.TestCase):
    def test_improve_finish_after_actual_editor_save(self):
        source = fixture.WritingWorkspaceTest()
        source.setUp()
        self.addCleanup(source.tearDown)
        project = source.project
        tender = project / "work/tender.txt"
        tender.write_text("TEST ONLY 技术方案质量评审，最高20分。", encoding="utf-8")
        registered = bidkit.register_source(project, tender, "main")
        ref = {key: registered[key] for key in ("source_id", "revision", "sha256")}
        ref.update(location="full_text", quote=tender.read_text(), kind="tender")
        scoring_path = project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0].update(node_type="scored", rule_text="技术方案质量评审", sources=[ref])
        bidkit.atomic(scoring_path, scoring)
        writing_path = project / "artifacts/11-technical-content.json"
        writing = bidkit.read(writing_path)
        for item in writing["inputs"]:
            if item["relative_path"] == "artifacts/04-scoring.json":
                item["sha256"] = bidkit.digest(scoring_path)
        bidkit.atomic(writing_path, writing)
        service = AIScoringActionService(project)
        workspace = source._workspace()

        def request(action, **extra):
            return service.request({"action": action, "request_id": str(uuid.uuid4()),
                                    "expected_revision": bidkit.read(writing_path)["revision"],
                                    "expected_sha256": bidkit.digest(writing_path), **extra})

        def complete(task, score):
            report = ai_scoring.prepare(project, "full")
            report["revision"] = bidkit.read(project / task["report_relative_path"])["revision"]
            report.update(status="completed", semantic_evaluation="COMPLETED",
                          evaluated_at="2026-10-15T00:00:00Z",
                          evaluator={"kind": "host_agent", "host": "test-host", "model": None})
            report["rows"][0].update(status="scored", simulated_score=score,
                range={"low": score, "high": score}, rationale="TEST ONLY 已回读正文。",
                rubric_basis="最高20分。", confidence="high",
                bid_refs=[{"relative_path": "artifacts/11-technical-content.json",
                           "sha256": bidkit.digest(writing_path), "location": "/data/chapters/0/body_markdown",
                           "quote": bidkit.read(writing_path)["data"]["chapters"][0]["body_markdown"]}],
                deductions=[{"points": 20-score, "reason": "方案缺异常机制", "action": "补充异常处理"}] if score < 20 else [])
            report["summary"] = ai_scoring.summarize(report["rows"], scoring, "full", "COMPLETED")
            bidkit.atomic(project / task["report_relative_path"], report)
            bidkit.atomic(project / "work/execution.json", {"project_id": service.project_id,
                "request_id": task["request_id"], "tool_or_agent": "test-host",
                "performed_actions": ["TEST ONLY 实际保存并回读测试正文及评分"]})
            return service.finish(task["request_id"], "work/execution.json")

        first = request("score")
        service.claim(first["request_id"])
        complete(first, 10)
        improve = request("improve", target_ids=["S-1"],
                          scoring_sha256=bidkit.digest(project / first["report_relative_path"]))
        service.claim(improve["request_id"])
        old = workspace.state("CH-1")["writing"]
        workspace.save({"expected_revision": old["revision"], "expected_sha256": old["sha256"],
                        "chapter_id": "CH-1", "body_markdown": "技术方案包含异常检测、重试、回退与复验。"})
        self.assertTrue(writing_path.with_suffix(".md").is_file())
        self.assertEqual(service.view()["latest_request"]["status"], "claimed")
        done = complete(improve, 20)
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["attempts"][0]["changed_section_ids"], ["SEC-1"])


if __name__ == "__main__":
    unittest.main()
