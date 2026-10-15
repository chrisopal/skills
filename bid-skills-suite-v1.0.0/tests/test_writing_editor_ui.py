from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "assets" / "ui"


class WritingEditorUiContractTest(unittest.TestCase):
    def test_scoring_workspace_is_inside_settings_panel(self):
        html = (UI / "writing-editor.html").read_text(encoding="utf-8")
        self.assertIn('id="settings-panel"', html)
        self.assertIn('id="ai-score-button"', html)
        self.assertIn('id="ai-report-button"', html)
        self.assertIn('id="ai-refresh-button"', html)
        self.assertIn('id="ai-improve-button"', html)
        self.assertIn('id="ai-show-all-scoring"', html)
        self.assertLess(html.index('id="settings-panel"'), html.index('id="ai-score-button"'))
        self.assertIn("查看评分依据与宿主交接", html)

    def test_scoring_client_uses_cas_contract_and_keeps_refresh_separate(self):
        script = (UI / "writing-editor.js").read_text(encoding="utf-8")
        self.assertIn('fetch("/api/ai-scoring"', script)
        self.assertIn('return report && report.report_url || ""', script)
        self.assertNotIn('"/api/ai-scoring/report?path=" + encodeURIComponent(report.relative_path)', script)
        self.assertIn("expected_revision: state.writing.revision", script)
        self.assertIn("expected_sha256: state.writing.sha256", script)
        self.assertIn("payload.scoring_sha256 = report.sha256", script)
        self.assertIn("payload.target_ids = targetIds", script)
        self.assertIn("var showAllScoringRows = false", script)
        self.assertIn("rowNeedsAttention", script)
        self.assertIn(' : "无扣分"', script)
        self.assertIn('unknown: "待核验"', script)
        self.assertIn("var settingsDirty = false", script)
        self.assertIn("function hasUnsavedWork()", script)
        self.assertIn("hasUnsaved || !view.available", script)
        self.assertRegex(script, r"function refreshAiScoring\(\)[\s\S]*?fetch\(\"/api/ai-scoring\"")
        refresh_body = script.split("function refreshAiScoring()", 1)[1].split("function createAiScoringTask", 1)[0]
        self.assertNotIn('fetch("/api/state"', refresh_body)

    def test_ui_has_responsive_and_theme_specific_scoring_styles(self):
        css = (UI / "writing-editor.css").read_text(encoding="utf-8")
        self.assertIn("--ui-surface-sunken", css)
        self.assertIn(".ai-scoring-table-wrap", css)
        self.assertIn("@media (max-width: 700px)", css)
        self.assertIn(".ai-scoring-metrics { grid-template-columns: repeat(2", css)


if __name__ == "__main__":
    unittest.main()
