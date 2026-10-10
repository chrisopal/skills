import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import bidkit
import quality_checks
from core_review_fixture import populate


class QualityChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        bidkit.init_project(self.project, "TEST-QUALITY")
        populate(self.project)
        writing_path = self.project / "artifacts/11-technical-content.json"
        writing = bidkit.read(writing_path)
        writing["data"]["chapters"][0]["body"] += " 工期30日。"
        bidkit.atomic(writing_path, writing)
        tender = bidkit.read(self.project / "artifacts/04-scoring.json")["data"]["items"][0]["sources"][0]
        body = {
            "relative_path": "artifacts/11-technical-content.json",
            "sha256": bidkit.digest(writing_path),
            "location": "/data/chapters/0/body",
            "quote": "测试主体提交营业执照。类似业绩附合同A和合同B。 工期30日。",
        }
        self.plan = {
            "schema_version": "1.0", "project_id": "TEST-QUALITY",
            "plan_id": "QP-TEST", "revision": 1,
            "inputs": [{"relative_path": rel, "sha256": bidkit.digest(self.project / rel)}
                        for rel in ("artifacts/04-scoring.json", "artifacts/05-compliance.json",
                                    "artifacts/09-evidence-selection.json")],
            "conditions": [{"condition_id": "S1-C1", "scoring_id": "S1", "kind": "phrase",
                            "description": "TEST ONLY score condition", "source_refs": [tender],
                            "section_ids": ["CH-1"]}],
            "facts": [{"fact_id": "F-DAYS", "kind": "numeric", "expected": 30,
                       "unit": "日", "source_refs": [tender], "body_refs": [body],
                       "section_ids": ["CH-1"]}],
        }
        bidkit.atomic(self.project / "profiles/quality-plan.json", self.plan)
        self.review = quality_checks.prepare(self.project)
        self.review["conditions"][0].update(
            conclusion="satisfied", rationale="TEST ONLY condition read back", body_refs=[body])
        self.review["facts"][0].update(conclusion="consistent", rationale="TEST ONLY fact read back")

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return quality_checks.check(self.project, self.review, self.project / "profiles/quality-plan.json")

    def test_no_plan_is_explicitly_not_run(self):
        (self.project / "profiles/quality-plan.json").unlink()
        result = quality_checks.check(self.project)
        self.assertEqual(result["quality_gate"], "NOT_RUN")
        self.assertFalse(result["binding_ready"])

    def test_prepare_creates_unknown_rows(self):
        scaffold = quality_checks.prepare(self.project)
        self.assertEqual(scaffold["conditions"][0]["conclusion"], "unknown")
        self.assertEqual(scaffold["facts"][0]["conclusion"], "unknown")
        self.assertNotEqual(scaffold["semantic_acceptance"], "PASS")

    def test_complete_bound_quality_review_passes_mechanical_gate(self):
        result = self.check()
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["quality_gate"], "PASSED")
        self.assertFalse(result["semantic_acceptance_certified"])

    def test_omitted_condition_blocks_and_reports_target_sections(self):
        self.review["conditions"] = []
        result = self.check()
        self.assertTrue(any("漏条件" in item for item in result["blockers"]))
        self.assertEqual(result["actions"][0]["target_id"], "S1")
        self.assertEqual(result["actions"][0]["section_ids"], ["CH-1"])
        self.assertTrue(result["actions"][0]["blocking"])

    def test_wrong_response_quote_is_error_and_self_proof_is_rejected(self):
        self.review["conditions"][0]["body_refs"][0]["quote"] = "不存在的正文"
        result = self.check()
        self.assertTrue(any("正文引用文字不在指定位置" in item for item in result["errors"]))
        self.review["conditions"][0]["body_refs"][0] = {
            "relative_path": "reviews/quality-review.json",
            "sha256": "0" * 64, "location": "/conditions/0/rationale", "quote": "TEST ONLY",
        }
        result = self.check()
        self.assertTrue(any("不能引用评审自证" in item for item in result["errors"]))

    def test_parameter_conflict_is_reported_from_registered_body_reference(self):
        path = self.project / "artifacts/11-technical-content.json"
        writing = bidkit.read(path)
        writing["data"]["chapters"][0]["body"] += " 调整为45日。"
        bidkit.atomic(path, writing)
        digest = bidkit.digest(path)
        body_ref = self.plan["facts"][0]["body_refs"][0]
        body_ref["sha256"] = digest
        body_ref["quote"] = writing["data"]["chapters"][0]["body"]
        self.plan["facts"][0]["body_refs"][0] = body_ref
        self.review["plan_ref"] = {"relative_path": "profiles/quality-plan.json",
                                    "sha256": bidkit.digest(self.project / "profiles/quality-plan.json")}
        bidkit.atomic(self.project / "profiles/quality-plan.json", self.plan)
        self.review["facts"][0]["conclusion"] = "conflict"
        result = self.check()
        self.assertTrue(any("未登记参数值" in item for item in result["errors"]))
        self.assertTrue(any(item["row_id"] == "F-DAYS" and item["blocking"]
                            for item in result["actions"]))

    def test_narrow_fact_quote_does_not_treat_other_chapter_numbers_as_conflicts(self):
        path = self.project / 'artifacts/11-technical-content.json'
        value = bidkit.read(path)
        value['data']['chapters'][0]['body'] += '\n另外有5名测试人员。'
        bidkit.atomic(path, value)
        digest = bidkit.digest(path)
        self.plan['facts'][0]['body_refs'][0]['sha256'] = digest
        self.plan['facts'][0]['body_refs'][0]['quote'] = '工期30日。'
        self.review['facts'][0]['body_refs'][0].update(sha256=digest, quote='工期30日。')
        self.review['conditions'][0]['body_refs'][0]['sha256'] = digest
        bidkit.atomic(self.project / 'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project / 'profiles/quality-plan.json')
        result = self.check()
        self.assertEqual(result['errors'], [])

    def test_condition_cannot_use_other_readable_source(self):
        other = bidkit.read(self.project / 'artifacts/09-evidence-selection.json')['data']['materials'][0]['sources'][0]
        self.plan['conditions'][0]['source_refs'] = [other]
        bidkit.atomic(self.project / 'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project / 'profiles/quality-plan.json')
        result = self.check()
        self.assertTrue(any('对应评分叶子' in item for item in result['errors']))

    def test_same_source_location_unrelated_quote_is_rejected(self):
        self.plan['conditions'][0]['source_refs'][0]['quote'] = 'TEST ONLY 招标样例'
        original = bidkit.read(self.project / 'artifacts/04-scoring.json')
        original['data']['items'][0]['sources'][0]['quote'] = '类似合同每项1分，最多2项。'
        bidkit.atomic(self.project / 'artifacts/04-scoring.json', original)
        self.plan['inputs'][0]['sha256'] = bidkit.digest(self.project / 'artifacts/04-scoring.json')
        bidkit.atomic(self.project / 'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project / 'profiles/quality-plan.json')
        self.assertTrue(any('对应评分叶子' in item for item in self.check()['errors']))

    def test_empty_atomic_description_is_rejected(self):
        self.plan['conditions'][0]['description'] = ''
        bidkit.atomic(self.project / 'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project / 'profiles/quality-plan.json')
        self.assertTrue(any('description' in item for item in self.check()['errors']))

    def test_evaluation_condition_cannot_be_claimed_satisfied(self):
        self.plan['conditions'][0]['phase'] = 'evaluation'
        bidkit.atomic(self.project/'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project/'profiles/quality-plan.json')
        result = self.check()
        self.assertFalse(result['binding_ready'])
        self.assertTrue(any('评标阶段' in error for error in result['errors']))

    def test_deferred_is_only_allowed_for_explicit_evaluation_phase(self):
        self.review['conditions'][0]['conclusion'] = 'deferred'
        self.assertTrue(any('评标阶段' in item for item in self.check()['errors']))
        self.plan['conditions'][0]['phase'] = 'evaluation'
        bidkit.atomic(self.project / 'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project / 'profiles/quality-plan.json')
        result = self.check()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['blockers'], [])
        self.assertTrue(any('外部条件' in item for item in result['warnings']))
        self.assertFalse(result['semantic_acceptance_certified'])

    def test_not_applicable_cannot_skip_scoring_condition(self):
        self.review['conditions'][0].update(conclusion='not_applicable', body_refs=[])
        self.assertTrue(any('结论无效' in item for item in self.check()['errors']))

    def test_plan_input_drift_is_error(self):
        path = self.project / "artifacts/04-scoring.json"
        value = bidkit.read(path)
        value["data"]["items"][0]["title"] = "changed TEST ONLY"
        bidkit.atomic(path, value)
        result = self.check()
        self.assertTrue(any("未绑定当前上游" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
