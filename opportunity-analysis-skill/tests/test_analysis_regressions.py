import unittest
from opportunity_skill.extractor import analyze
from opportunity_skill.assessment import build_commercial_assessment
from opportunity_skill.stage_management import infer_opportunity_stage


class AnalysisRegressions(unittest.TestCase):
    def test_future_quote_is_not_quote_stage(self):
        text = '客户希望先安排技术交流，再决定是否进入报价。'
        self.assertEqual(infer_opportunity_stage({'text': text})['stage_id'], 'solution_cocreation')

    def test_po_template_is_not_won(self):
        self.assertNotEqual(infer_opportunity_stage({'text': '请提供 PO 模板供参考'})['stage_id'], 'won')

    def test_historic_cancelled_does_not_override_current_signed(self):
        self.assertEqual(infer_opportunity_stage({'text': '去年项目取消。今年合同已签。'})['stage_id'], 'won')

    def test_unknown_answer_is_not_confirmation(self):
        context = {'text': '', 'sales_confirmation_answers': [{'dimension_id': 'customer_relationship', 'rating': 'unknown', 'answer_text': '不知道'}]}
        result = build_commercial_assessment(context)
        dimension = next(d for d in result['dimensions'] if d['dimension_id'] == 'customer_relationship')
        self.assertEqual(dimension['evidence_status'], 'needs_sales_confirmation')
        self.assertEqual(result['assessment_confidence_score'], build_commercial_assessment({'text': ''})['assessment_confidence_score'])

    def test_high_inferred_rating_still_asks_confirmation(self):
        result = build_commercial_assessment({'text': '', 'budget_amount': 100000})
        self.assertIn('pricing_budget_fit', {q['dimension_id'] for q in result['questions']})

    def test_analysis_only_suggests(self):
        result = analyze({'materials': [{'content': '客户合同已签。'}]})
        self.assertEqual(result['structured_data']['opportunity']['stage_id'], 'won')

    def test_confirmation_flag_retains_high_rating_question(self):
        result = build_commercial_assessment({'text': '客户支持我们', 'evidence_list': [{'evidence_id': 'ev1', 'requires_human_confirmation': True}]})
        dimension = next(d for d in result['dimensions'] if d['dimension_id'] == 'customer_relationship')
        self.assertEqual(dimension['rating'], 'strong')
        self.assertEqual(dimension['evidence_status'], 'needs_sales_confirmation')
        self.assertIn('customer_relationship', {q['dimension_id'] for q in result['questions']})

    def test_unknown_answer_text_cannot_confirm_with_strong_rating(self):
        result = build_commercial_assessment({'text': '', 'sales_confirmation_answers': [{'dimension_id': 'customer_relationship', 'rating': 'strong', 'answer_text': '不知道'}]})
        dimension = next(d for d in result['dimensions'] if d['dimension_id'] == 'customer_relationship')
        self.assertEqual(dimension['evidence_status'], 'needs_sales_confirmation')
