#!/usr/bin/env python3
"""Behavior tests for the validated WeChat article case-bundle gate."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_case_bundle.py"


class ValidateCaseBundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tempdir.name)
        self.paths = {}
        for name in [
            "source.md",
            "step.png",
            "artifact.pptx",
            "readback.json",
            "article.md",
            "article.html",
            "cover.png",
            "draft-get.json",
        ]:
            path = self.workdir / name
            path.write_text("fixture", encoding="utf-8")
            self.paths[name] = str(path)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def valid_bundle(self) -> dict:
        return {
            "schema_version": "1.0",
            "topic_id": "WB-001",
            "request": {
                "objective": "写一篇可实战复用的 AI PPT 公众号文章",
                "target_reader": "需要用 AI 交付 PPT 的产品与咨询人员",
                "reader_action": "按 SOP 完成一次真实验证",
                "core_claim": "效果差距首先来自 SOP 和验收，而不只是模型",
            },
            "logic": {
                "methodology": ["主题", "观众", "材料", "大纲", "故事线", "逐页契约", "生产", "验收"],
                "storyline": ["先讲底层逻辑", "再比较公开路线", "最后展示真实案例"],
            },
            "scenario": {
                "name": "在 WorkBuddy 中生成并验证产品介绍 PPT",
                "actual": True,
                "environment": "WorkBuddy 已配置模型的本地桌面环境",
                "steps": [
                    {
                        "id": "S01",
                        "action": "执行真实生成流程并截图",
                        "status": "passed",
                        "evidence_ids": ["E01"],
                    }
                ],
                "acceptance_criteria": [
                    {
                        "id": "A01",
                        "criterion": "输出文件重新打开且关键内容可读",
                        "status": "passed",
                        "evidence_ids": ["E02", "E03"],
                    }
                ],
            },
            "materials": [
                {
                    "id": f"M0{index}",
                    "kind": "source",
                    "path_or_url": self.paths["source.md"] if index == 1 else f"https://example.com/source-{index}",
                    "status": "verified",
                }
                for index in range(1, 6)
            ],
            "evidence": {
                "items": [
                    {
                        "id": "E01",
                        "kind": "screenshot",
                        "path": self.paths["step.png"],
                        "verified": True,
                        "privacy_checked": True,
                        "error_checked": True,
                    },
                    {
                        "id": "E02",
                        "kind": "artifact",
                        "path": self.paths["artifact.pptx"],
                        "verified": True,
                    },
                    {
                        "id": "E03",
                        "kind": "readback",
                        "path": self.paths["readback.json"],
                        "verified": True,
                    },
                ]
            },
            "article": {
                "markdown_path": self.paths["article.md"],
                "html_path": self.paths["article.html"],
                "cover_path": self.paths["cover.png"],
                "inline_image_paths": [self.paths["step.png"]],
                "review_status": "passed",
                "markdown_link_residue": False,
                "local_path_residue": False,
                "privacy_residue": False,
                "error_residue": False,
            },
            "wechat": {
                "save_mode": "draft",
                "publish": False,
                "ip_whitelist_checked": True,
                "media_id": "MEDIA_ID_FIXTURE",
                "draft_get_path": self.paths["draft-get.json"],
                "draft_get_verified": True,
                "status": "DRAFT_SAVED",
            },
        }

    def run_validator(self, bundle: dict, phase: str) -> subprocess.CompletedProcess[str]:
        bundle_path = self.workdir / "bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(bundle_path), "--phase", phase],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_intake_rejects_missing_core_claim(self) -> None:
        bundle = self.valid_bundle()
        del bundle["request"]["core_claim"]

        result = self.run_validator(bundle, "intake")

        self.assertEqual(result.returncode, 1)
        self.assertIn("request.core_claim", result.stderr)

    def test_intake_rejects_any_publish_request(self) -> None:
        bundle = self.valid_bundle()
        bundle["wechat"]["publish"] = True

        result = self.run_validator(bundle, "intake")

        self.assertEqual(result.returncode, 1)
        self.assertIn("wechat.publish must be false", result.stderr)

    def test_evidence_requires_every_step_and_acceptance_item_to_pass(self) -> None:
        bundle = self.valid_bundle()
        bundle["scenario"]["steps"][0]["status"] = "pending"
        bundle["scenario"]["acceptance_criteria"][0]["status"] = "blocked"

        result = self.run_validator(bundle, "evidence")

        self.assertEqual(result.returncode, 1)
        self.assertIn("scenario.steps[0].status must be passed", result.stderr)
        self.assertIn("scenario.acceptance_criteria[0].status must be passed", result.stderr)

    def test_evidence_rejects_unchecked_screenshot_privacy_or_errors(self) -> None:
        bundle = self.valid_bundle()
        screenshot = bundle["evidence"]["items"][0]
        screenshot["privacy_checked"] = False
        screenshot["error_checked"] = False

        result = self.run_validator(bundle, "evidence")

        self.assertEqual(result.returncode, 1)
        self.assertIn("privacy_checked must be true", result.stderr)
        self.assertIn("error_checked must be true", result.stderr)

    def test_evidence_requires_five_verified_materials(self) -> None:
        bundle = self.valid_bundle()
        bundle["materials"][-1]["status"] = "unverified"

        result = self.run_validator(bundle, "evidence")

        self.assertEqual(result.returncode, 1)
        self.assertIn("at least five verified materials", result.stderr)

    def test_evidence_requires_an_artifact_or_readback(self) -> None:
        bundle = self.valid_bundle()
        bundle["evidence"]["items"] = [bundle["evidence"]["items"][0]]

        result = self.run_validator(bundle, "evidence")

        self.assertEqual(result.returncode, 1)
        self.assertIn("at least one artifact or readback", result.stderr)

    def test_draft_rejects_residue_and_missing_verified_readback(self) -> None:
        bundle = self.valid_bundle()
        bundle["article"]["markdown_link_residue"] = True
        bundle["article"]["privacy_residue"] = True
        bundle["wechat"]["draft_get_verified"] = False

        result = self.run_validator(bundle, "draft")

        self.assertEqual(result.returncode, 1)
        self.assertIn("article.markdown_link_residue must be false", result.stderr)
        self.assertIn("article.privacy_residue must be false", result.stderr)
        self.assertIn("wechat.draft_get_verified must be true", result.stderr)

    def test_valid_draft_bundle_passes(self) -> None:
        result = self.run_validator(copy.deepcopy(self.valid_bundle()), "draft")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VALIDATION PASSED: draft", result.stdout)


if __name__ == "__main__":
    unittest.main()
