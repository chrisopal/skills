import importlib.util
from pathlib import Path
import tempfile
import unittest


class WorkflowCLITests(unittest.TestCase):
    def test_full_lifecycle_through_public_cli(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "rehearse.py"
        spec = importlib.util.spec_from_file_location("rehearse_opportunity", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            result = module.rehearse(Path(temp) / "project")
            self.assertGreater(result["revision"], 10)
            self.assertEqual(len(result["checks"]), 4)
            self.assertTrue((Path(result["output"]) / "light" / "opportunity_list.html").is_file())


if __name__ == "__main__":
    unittest.main()
