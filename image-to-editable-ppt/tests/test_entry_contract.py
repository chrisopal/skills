"""Offline checks for the selective contract sync and preserved fork boundaries.

Documentation checks protect agent instructions, not a runtime egress firewall.
No OCR or image service is contacted by these tests.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from test_multi_agent_backend import (
    ROOT, make_minimal_run, read_json, run_cli, valid_page_manifest,
    write_json, write_page_outputs,
)
from editppt.runtime import image_gen, runtime_env


SKILL = ROOT / "skills/image-to-editable-ppt"
READMES = [ROOT / name for name in ("README.md", "README_en.md", "README_ko.md")]
DOC_DIRS = [ROOT / name for name in ("docs", "docs/en", "docs/ko")]


class EntryContractTest(unittest.TestCase):
    def test_authorization_keeps_data_scope_and_local_only_exceptions(self):
        skill = (SKILL / "SKILL.md").read_text()
        entry = skill.split("## Entry Contract", 1)[1].split("### Image Backend Selection", 1)[0]
        for boundary in (
            "local-only", "confidential/no-external-processing",
            "Only send task-local page images", "Never send unrelated local files",
            "API keys, auth tokens, credentials",
            "already configured by the user or explicitly specified for this run",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, entry)

    def test_network_approval_covers_prepare_hints_and_cli_fallback(self):
        skill = (SKILL / "SKILL.md").read_text()
        entry = skill.split("## Entry Contract", 1)[1].split("### Image Backend Selection", 1)[0]
        for boundary in (
            "approval required by the current runtime", "editppt prepare",
            "editppt run hints", "PADDLE_OCR_TOKEN", "editppt image generate/edit",
            "approval system explicitly rejects", "Do not add confirmation gates",
            "retain the OCR choices in Phase 1",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, entry)

    def test_updates_use_scoped_fork_source_and_refresh_local_cli(self):
        paths = [SKILL / "SKILL.md", *READMES, *(d / "installation.md" for d in DOC_DIRS)]
        expected = 'npx -y skills@latest add "https://github.com/chrisopal/skills/tree/<fork-commit>/image-to-editable-ppt/skills/image-to-editable-ppt"'
        for path in paths:
            with self.subTest(path=path):
                text = path.read_text()
                self.assertIn(expected, text)
                for step in (
                    "--skill image-to-editable-ppt", "--agent <agent-id>", "--global",
                    "pipx install --force --editable <skill-root>/cli", "editppt doctor",
                    "editppt page visual-qa --help", "editppt image extract-source --help",
                    "editppt run backend --help", "agent-image-tool",
                ):
                    self.assertIn(step, text)
                self.assertNotIn("npx -y skills@latest add ningzimu/", text)

    def test_lightweight_example_is_separate_from_the_fork_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual("gpt-image-2", image_gen._default_model())
            self.assertEqual(runtime_env.DEFAULT_IMAGE_MODEL, image_gen._default_model())
        paths = [*READMES, *(d / "README.md" for d in DOC_DIRS), *(d / "faq.md" for d in DOC_DIRS)]
        for path in paths:
            with self.subTest(path=path):
                examples = [line for line in path.read_text().splitlines() if "gpt-image-2.5-sunburst" in line]
                self.assertEqual(1, len(examples))
                self.assertIn("`gpt-image-2`", examples[0])

    def test_portable_backend_and_visual_qa_stay_in_worker_contract(self):
        prompt = (SKILL / "prompts/page-worker.md").read_text()
        schema = (SKILL / "references/manifest-schema.md").read_text()
        for required in ("agent-image-tool", "producer_id", "source-faithful-extraction", "visual_qa_passed"):
            with self.subTest(required=required):
                self.assertIn(required, schema)
        for required in ("--producer-id", "visual-qa.json", "visual-diff.png", "extract-source"):
            with self.subTest(required=required):
                self.assertIn(required, prompt)


class PreservedRuntimeContractTest(unittest.TestCase):
    def test_slow_dispatch_uses_active_lease_without_mutating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_minimal_run(tmp)
            backend = run_cli("run", "backend", run_dir)
            self.assertEqual(0, backend.returncode, backend.stderr)
            jobs = read_json(run_dir / "page_jobs.json")
            jobs["max_concurrent_pages"] = 1
            jobs["pages"][0].update(status="dispatched", dispatch={
                "agent_id": "slow-worker", "dispatched_at": "2000-01-01T00:00:00Z",
            })
            write_json(run_dir / "page_jobs.json", jobs)
            before = {p: p.read_bytes() for p in run_dir.rglob("*") if p.is_file()}
            for command in ("next", "status", "next"):
                result = run_cli("run", command, run_dir, "--json")
                self.assertEqual(0, result.returncode, result.stderr)
                import json
                payload = json.loads(result.stdout)
                if command == "next":
                    self.assertEqual("wait", payload["stage"])
                else:
                    self.assertEqual(["page_001"], payload["active_dispatches"])
                    self.assertEqual(0, payload["dispatch_slots_available"])
            for flags in (("--agent-id", "slow-worker"), ("--confirm-lost",),
                          ("--agent-id", "wrong-worker", "--confirm-lost")):
                reset = run_cli("run", "reset", run_dir, "--page", "page_001", *flags)
                self.assertNotEqual(0, reset.returncode, reset.stdout)
            self.assertEqual(before, {p: p.read_bytes() for p in run_dir.rglob("*") if p.is_file()})

    def test_run_hints_refresh_preserves_backend_source_and_orchestration(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_minimal_run(tmp)
            backend = run_cli("run", "backend", run_dir, "--mode", "agent-image-tool",
                              "--runtime-id", "test-runtime", "--tool-name", "test-image-tool",
                              "--tool-call", "test.image.edit", "--model", "test-model")
            self.assertEqual(0, backend.returncode, backend.stderr)
            for page in ("page_001", "page_002"):
                Image.new("RGB", (100, 60), "white").save(run_dir / "pages" / page / "source.png")
            before = {p: p.read_bytes() for p in run_dir.rglob("*") if p.is_file()}
            with mock.patch.dict(os.environ, {"PADDLE_OCR_TOKEN": "", "EDITPPT_CONFIG_HOME": str(run_dir / "empty-config")}):
                for _ in range(2):
                    result = run_cli("run", "hints", run_dir)
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            for path, contents in before.items():
                self.assertEqual(contents, path.read_bytes(), str(path))
            for page in ("page_001", "page_002"):
                page_dir = run_dir / "pages" / page
                self.assertEqual("builtin-ink", read_json(page_dir / "text_hints.json")["backend"])
                self.assertTrue((page_dir / "text_hints.png").is_file())

    def test_record_recomputes_visual_qa_instead_of_trusting_passed_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_minimal_run(tmp)
            jobs = read_json(run_dir / "page_jobs.json")
            jobs["pages"][1].update(status="dispatched", dispatch={"agent_id": "worker-1"})
            write_json(run_dir / "page_jobs.json", jobs)
            before = (run_dir / "page_jobs.json").read_bytes()
            page_dir = run_dir / "pages/page_002"
            manifest = valid_page_manifest("First overlapping text")
            manifest["text_boxes"].append({"text": "Second overlapping text", "box_px": [100, 100, 500, 80]})
            write_page_outputs(page_dir, manifest=manifest)
            write_json(page_dir / "visual-qa.json", {"passed": True})
            write_json(page_dir / "validation.json", {"passed": True, "visual_qa_passed": True})
            result = run_cli("run", "record", run_dir, "--page", "page_002", "--agent-id", "worker-1")
            self.assertNotEqual(0, result.returncode)
            self.assertIs(read_json(page_dir / "visual-qa.json")["passed"], False)
            self.assertIs(read_json(page_dir / "validation.json")["visual_qa_passed"], False)
            self.assertEqual(before, (run_dir / "page_jobs.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
