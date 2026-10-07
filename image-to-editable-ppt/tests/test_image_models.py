import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/image-to-editable-ppt/cli"))
from editppt.runtime import image_gen, runtime_env
from test_multi_agent_backend import make_minimal_run, read_json, run_cli


class ImageModelTests(unittest.TestCase):
    def test_default_and_explicit_configuration(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(image_gen._default_model(), "gpt-image-2.5-sunburst")
            self.assertEqual(runtime_env.DEFAULT_IMAGE_MODEL, image_gen._default_model())
        with mock.patch.dict(os.environ, {"IMAGE_TO_EDITABLE_PPT_IMAGE_MODEL": "gpt-image-2"}):
            self.assertEqual(image_gen._default_model(), "gpt-image-2")

    def test_quality_and_size_for_both_models_and_snapshots(self):
        for name in ("flare", "sunburst"):
            for prefix in ("", "openai/"):
                for suffix in ("", "-2026-09-08"):
                    model = f"{prefix}gpt-image-2.5-{name}{suffix}"
                    with self.subTest(model=model):
                        for quality in ("auto", "high", "xhigh", "max"):
                            image_gen._validate_quality(quality, model)
                        image_gen._validate_size("2560x1440", model)
                        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                            image_gen._validate_size("2561x1440", model)

    def test_new_quality_rejected_for_legacy_and_lookalike_models(self):
        for model in ("gpt-image-1.5", "gpt-image-2", "gpt-image-2-2026-04-21",
                      "gpt-image-2.5", "gpt-image-2.5-flare-invalid", "gpt-image-20"):
            for quality in ("xhigh", "max"):
                with self.subTest(model=model, quality=quality):
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        image_gen._validate_quality(quality, model)
            image_gen._validate_quality("high", model)

    def test_size_rules_do_not_match_lookalike_model_names(self):
        for model in ("gpt-image-2", "openai/gpt-image-2-2026-04-21"):
            image_gen._validate_size("2560x1440", model)
        for model in ("gpt-image-20", "gpt-image-2.5", "gpt-image-2.5-flare-invalid"):
            with self.subTest(model=model), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                image_gen._validate_size("2560x1440", model)

    def test_oauth_body_preserves_requested_model_and_quality(self):
        for model in (image_gen.DEFAULT_MODEL, "gpt-image-2.5-flare"):
            body = image_gen._codex_image_body(
                prompt="test", image_paths=[], mask_path=None,
                model=model, size="auto", quality="xhigh",
            )
            self.assertEqual(body["model"], model)
            self.assertEqual(body["quality"], "xhigh")
        self.assertEqual(image_gen.DEFAULT_QUALITY, "auto")

    def test_dry_run_preserves_model_and_quality_for_generate_and_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            Image.new("RGB", (16, 16)).save(source)
            self._check_dry_runs(source)

    def _check_dry_runs(self, source):
        for operation in ("generate", "edit"):
            argv = ["editppt image", operation, "--prompt", "test", "--model",
                    "gpt-image-2.5-flare", "--quality", "max", "--dry-run"]
            if operation == "edit":
                argv += ["--image", str(source)]
            output = io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 mock.patch.object(image_gen, "_load_runtime_env"), \
                 mock.patch.object(image_gen, "_codex_available", return_value=False), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(image_gen.main(), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["model"], "gpt-image-2.5-flare")
            self.assertEqual(payload["quality"], "max")

    def test_cli_model_precedence_preserves_saved_and_environment_overrides(self):
        cases = (
            (None, None, None, "gpt-image-2.5-sunburst"),
            ("gpt-image-2", None, None, "gpt-image-2"),
            ("gpt-image-2", "openai/gpt-image-2-2026-04-21", None,
             "openai/gpt-image-2-2026-04-21"),
            ("gpt-image-2", "gpt-image-2", "gpt-image-2.5-flare", "gpt-image-2.5-flare"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            Image.new("RGB", (16, 16)).save(source)
            config = Path(tmp) / "config.yaml"
            for saved, environment, explicit, expected in cases:
                config.write_text(f"IMAGE_TO_EDITABLE_PPT_IMAGE_MODEL: {saved}\n" if saved else "{}\n")
                before = config.read_bytes()
                for operation in ("generate", "edit"):
                    with self.subTest(saved=saved, environment=environment, explicit=explicit, operation=operation):
                        env = {"EDITPPT_CONFIG_HOME": tmp}
                        if environment:
                            env["IMAGE_TO_EDITABLE_PPT_IMAGE_MODEL"] = environment
                        argv = ["editppt image", operation, "--prompt", "test", "--dry-run"]
                        if explicit:
                            argv += ["--model", explicit]
                        if operation == "edit":
                            argv += ["--image", str(source)]
                        output = io.StringIO()
                        with mock.patch.dict(os.environ, env, clear=True), \
                             mock.patch.object(sys, "argv", argv), \
                             mock.patch.object(image_gen, "_codex_available", return_value=False), \
                             contextlib.redirect_stdout(output):
                            self.assertEqual(0, image_gen.main())
                        payload = json.loads(output.getvalue())
                        self.assertEqual(expected, payload["model"])
                        self.assertEqual("auto", payload["quality"])
                        self.assertEqual(before, config.read_bytes())

    def test_mocked_api_generate_and_edit_preserve_model_quality_and_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            Image.new("RGB", (16, 16)).save(source)
            for operation in ("generate", "edit"):
                with self.subTest(operation=operation):
                    client = mock.Mock()
                    request_method = getattr(client.images, operation)
                    request_method.return_value.data = []
                    argv = ["editppt image", operation, "--prompt", "test", "--model",
                            "openai/gpt-image-2.5-sunburst-2026-09-08", "--quality", "xhigh",
                            "--size", "2560x1440", "--out", str(Path(tmp) / "output.png")]
                    if operation == "edit":
                        argv += ["--image", str(source)]
                    with mock.patch.object(sys, "argv", argv), \
                         mock.patch.object(image_gen, "_load_runtime_env"), \
                         mock.patch.object(image_gen, "_ensure_api_key"), \
                         mock.patch.object(image_gen, "_codex_available", return_value=False), \
                         mock.patch.object(image_gen, "_create_client", return_value=client), \
                         contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(0, image_gen.main())
                    request_method.assert_called_once()
                    payload = request_method.call_args.kwargs
                    self.assertEqual("openai/gpt-image-2.5-sunburst-2026-09-08", payload["model"])
                    self.assertEqual("xhigh", payload["quality"])
                    self.assertEqual("2560x1440", payload["size"])
                    self.assertEqual({"model", "prompt", "size", "quality"} |
                                     ({"image"} if operation == "edit" else set()), set(payload))
                    if operation == "edit":
                        self.assertEqual(str(source), payload["image"].name)

    def test_run_backend_defaults_propagate_without_changing_native_producer(self):
        for mode in ("editppt-image-cli", "openai-compatible-api", "builtin-imagegen", "agent-image-tool"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                run_dir = make_minimal_run(tmp)
                flags = ("--model", "native-provider-model") if mode == "agent-image-tool" else ()
                result = run_cli("run", "backend", run_dir, "--mode", mode, *flags)
                self.assertEqual(0, result.returncode, result.stderr)
                backend = read_json(run_dir / "deck_manifest.json")["image_backend"]
                for page in ("page_001", "page_002"):
                    self.assertEqual(backend, read_json(run_dir / f"pages/{page}/page_request.json")["image_backend"])
                if mode in ("builtin-imagegen", "agent-image-tool"):
                    self.assertEqual("gpt-image-2.5-sunburst", backend["fallback_model"])
                    self.assertEqual("native-provider-model" if mode == "agent-image-tool" else None,
                                     backend["model"])
                    self.assertEqual(["codex-oauth", "openai-compatible-api"], backend["fallback_order"])
                    if mode == "agent-image-tool":
                        self.assertEqual("editppt image generate/edit --model gpt-image-2.5-sunburst",
                                         backend["fallback_command"])
                    else:
                        self.assertNotIn("model", backend["required_parameters"]["generate"])
                        self.assertNotIn("model", backend["required_parameters"]["edit"])
                else:
                    self.assertEqual("gpt-image-2.5-sunburst", backend["model"])


if __name__ == "__main__":
    unittest.main()
