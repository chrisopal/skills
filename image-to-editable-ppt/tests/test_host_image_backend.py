from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

from test_multi_agent_backend import PROMPT_SCRIPT, make_minimal_run, read_json, run_cli, write_json


def host_contract():
    return {
        "schema_version": 1,
        "discovery_evidence": "Current session discovered test fixture tool schemas",
        "observed_tools": {
            "mcp__fixture__generate": {"parameters": ["prompt"], "required_parameters": ["prompt"]},
            "mcp__fixture__edit": {"parameters": ["prompt", "images"], "required_parameters": ["prompt", "images"]},
        },
        "operations": {
            "generate": {"tool_name": "mcp__fixture__generate", "required_parameters": ["prompt"], "prompt_parameter": "prompt"},
            "edit": {"tool_name": "mcp__fixture__edit", "required_parameters": ["prompt", "images"], "prompt_parameter": "prompt", "image_parameter": "images"},
        },
        "input_context_policy": "Inspect local inputs before passing absolute paths in images",
        "save_path_policy": "Read the explicit local file path in output.path",
    }


class HostImageBackendTest(unittest.TestCase):
    def test_contract_propagates_to_all_requests_and_worker_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_minimal_run(Path(tmp) / "run")
            contract_path = Path(tmp) / "host.json"
            write_json(contract_path, host_contract())
            result = run_cli("run", "backend", run, "--mode", "host-tool", "--contract", contract_path)
            self.assertEqual(0, result.returncode, result.stderr)
            backend = read_json(run / "deck_manifest.json")["image_backend"]
            self.assertEqual("host-tool", backend["backend_id"])
            self.assertEqual([], backend["fallback_order"])
            self.assertIn("never", backend["handoff_rule"])
            for page_id in ("page_001", "page_002"):
                page = run / "pages" / page_id
                self.assertEqual(backend, read_json(page / "page_request.json")["image_backend"])
                result = subprocess.run([sys.executable, str(PROMPT_SCRIPT), str(run), "--page", page_id, "--out", "worker-prompt.md"], capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
                prompt = (page / "worker-prompt.md").read_text()
                self.assertIn('"mcp__fixture__edit"', prompt)
                self.assertIn('"fallback_order": []', prompt)

    def test_invalid_contract_is_rejected_without_mutating_run(self):
        mutations = [
            lambda c: c.pop("discovery_evidence"),
            lambda c: c.pop("save_path_policy"),
            lambda c: c["operations"].pop("edit"),
            lambda c: c["operations"]["edit"].update(tool_name="not_observed"),
            lambda c: c["operations"]["edit"].update(required_parameters=["prompt"]),
            lambda c: c["operations"]["edit"].update(image_parameter="unsupported"),
            lambda c: c["observed_tools"]["mcp__fixture__edit"].update(required_parameters=["token"]),
            lambda c: c.update(fallback_order=["openai-compatible-api"]),
            lambda c: c.update(fallback_policy="invalid"),
            lambda c: c["observed_tools"].update({"tool;touch BAD": {"parameters": [], "required_parameters": []}}),
            lambda c: c["operations"]["edit"].update(image_parameter="prompt"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                run = make_minimal_run(Path(tmp) / "run")
                before = (run / "deck_manifest.json").read_bytes()
                contract = host_contract()
                mutate(contract)
                path = Path(tmp) / "host.json"
                write_json(path, contract)
                result = run_cli("run", "backend", run, "--mode", "host-tool", "--contract", path)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("host-tool contract", result.stderr)
                self.assertEqual(before, (run / "deck_manifest.json").read_bytes())

    def test_prepare_validates_contract_before_creating_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "slide.png"
            Image.new("RGB", (100, 100), "white").save(source)
            run = Path(tmp) / "run"
            result = run_cli("prepare", source, "--job-dir", run, "--image-backend", "host-tool", "--no-text-hints")
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(run.exists())
            path = Path(tmp) / "host.json"
            write_json(path, host_contract())
            result = run_cli("prepare", source, "--job-dir", run, "--image-backend", "host-tool", "--image-backend-contract", path, "--no-text-hints")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("host-tool", read_json(run / "deck_manifest.json")["image_backend"]["backend_id"])

    def test_host_import_records_exact_tool_and_rejects_other_producers(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_minimal_run(Path(tmp) / "run")
            contract = host_contract()
            contract["backend_id"] = "host-tool"
            page = run / "pages/page_001"
            write_json(page / "page_request.json", {"image_backend": contract})
            source = Path(tmp) / "returned.png"
            Image.new("RGB", (10, 10), "red").save(source)
            base = ("image", "import", page, "--job-id", "asset-1", "--source-image", source, "--dest", "assets/result.png")
            for producer, name in [("codex-oauth", None), ("host-tool", None), ("host-tool", "unobserved")]:
                result = run_cli(*base, "--backend", producer, *(["--tool-name", name] if name else []))
                self.assertNotEqual(0, result.returncode)
                self.assertFalse((page / "assets/result.png").exists())
            result = run_cli(*base, "--backend", "host-tool", "--tool-name", "mcp__fixture__edit")
            self.assertEqual(0, result.returncode, result.stderr)
            job = read_json(page / "imagegen-jobs.json")["jobs"][0]
            self.assertEqual("host-tool", job["backend"])
            self.assertEqual("mcp__fixture__edit", job["tool_name"])
            self.assertEqual(str(source.resolve()), job["source_image"])

    def test_contract_flag_cannot_silently_select_cli_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_minimal_run(Path(tmp) / "run")
            path = Path(tmp) / "host.json"
            write_json(path, host_contract())
            result = run_cli("run", "backend", run, "--contract", path)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("requires", result.stderr)


    def test_host_import_rejects_fallback_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_minimal_run(Path(tmp) / "run")
            contract = host_contract(); contract["backend_id"] = "host-tool"
            page = run / "pages/page_001"
            write_json(page / "page_request.json", {"image_backend": contract})
            source = Path(tmp) / "returned.png"
            Image.new("RGB", (10, 10), "red").save(source)
            result = run_cli("image", "import", page, "--job-id", "asset-1", "--source-image", source,
                             "--dest", "assets/result.png", "--backend", "host-tool", "--tool-name",
                             "mcp__fixture__edit", "--fallback-reason", "tool-error")
            self.assertNotEqual(0, result.returncode)
            self.assertFalse((page / "assets/result.png").exists())


if __name__ == "__main__":
    unittest.main()
