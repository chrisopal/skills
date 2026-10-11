import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_suite.py"
spec = importlib.util.spec_from_file_location("validate_suite", VALIDATOR_PATH)
assert spec and spec.loader
validate_suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_suite)


class SuiteTests(unittest.TestCase):
    def test_installed_batches_roster_and_metadata(self):
        self.assertEqual(validate_suite.validate(), [])

    def test_index_has_markdown_and_csv_templates(self):
        index = json.loads((validate_suite.TEMPLATES / "index.json").read_text(encoding="utf-8"))
        formats = {entry["format"] for entry in index["templates"]}
        self.assertEqual(formats, {"markdown", "csv"})
        self.assertGreaterEqual(sum(entry["format"] == "markdown" for entry in index["templates"]), 12)
        self.assertGreaterEqual(sum(entry["format"] == "csv" for entry in index["templates"]), 10)

    def test_future_skills_are_not_routed(self):
        text = (validate_suite.SKILLS / "delivery-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        for name in validate_suite.FUTURE_SKILLS:
            self.assertNotIn(f"`{name}`", text)

    def test_csv_templates_have_no_fictional_data(self):
        for path in validate_suite.TEMPLATES.glob("*.csv"):
            data = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(data), 2, path.name)
            self.assertTrue(all(not value.strip() for value in data[1].split(",")), path.name)


if __name__ == "__main__":
    unittest.main()
