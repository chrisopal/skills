from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_human_tone.py"


class CheckHumanToneTest(unittest.TestCase):
    def run_checker(self, text: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), "-"],
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_reports_rhetorical_shapes(self) -> None:
        result = self.run_checker(
            "你以为企业买的是模型，其实真正值钱的是工作流。\n\n"
            "团队完成了对流程的优化。\n\n"
            "谁在审批，谁在部署，谁在验收。\n"
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("疑似动作级翻案", result.stdout)
        self.assertIn("疑似名词化动作", result.stdout)
        self.assertIn("疑似三项同构排比", result.stdout)

    def test_masks_code_and_links(self) -> None:
        result = self.run_checker(
            "这段正文只说明系统已经接入工单流程。\n\n"
            "`你以为 A，其实 B`\n\n"
            "[查看来源](https://example.com/你以为其实)\n"
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("提示 0 项", result.stdout)

    def test_missing_file_is_an_input_error(self) -> None:
        missing = ROOT / "tests" / "does-not-exist.md"
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(missing)],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("无法读取稿件", result.stderr)


if __name__ == "__main__":
    unittest.main()
