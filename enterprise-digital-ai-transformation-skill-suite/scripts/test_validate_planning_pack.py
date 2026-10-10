import copy
import unittest

from validate_planning_pack import validate


def fixture():
    return {
        'artifact_header': {'status': 'assumed'},
        'evidence': [{'id': 'E1', 'status': 'assumed'}],
        'processes': [
            {'id': f'P{i}', 'level': i, 'parent_id': f'P{i-1}' if i > 1 else None,
             'name': '流程', 'owner': '厂长', **({'inputs': ['订单'], 'outputs': ['工单'],
             'control_points': ['审批'], 'information_ids': ['D1'],
             'application_ids': ['A1'], 'kpi_ids': ['K1']} if i == 4 else {})}
            for i in range(1, 5)],
        'information_objects': [{'id': 'D1', 'name': '订单', 'owner': '计划'}],
        'applications': [{'id': 'A1', 'name': '计划', 'process_ids': ['P4'],
                          'information_ids': ['D1'], 'technology_ids': ['T1'], 'lifecycle': '改造'}],
        'technology_services': [{'id': 'T1', 'name': '运行平台', 'application_ids': ['A1'], 'nfr': {'recovery': '待验证'}}],
        'kpis': [{'id': 'K1', 'name': '交付率', 'formula': '准时/全部', 'owner': '运营',
                  'baseline': 0.8, 'target': 0.9, 'aggregation': '分子分母求和'}],
        'initiatives': [{'id': 'I1', 'name': '改善交付', 'process_ids': ['P4'],
                         'application_ids': ['A1'], 'kpi_ids': ['K1'], 'depends_on': [], 'wave_id': 'W1'}],
        'waves': [{'id': 'W1', 'name': '试点', 'initiative_ids': ['I1']}],
        'financials': {'currency': 'CNY', 'unit': '万元',
            'costs': [{'initiative_id': 'I1', 'year': 1, 'amount': 100}],
            'benefits': [{'id': 'B1', 'initiative_ids': ['I1'], 'year': 1, 'amount': 40, 'basis': '假设'}],
            'annual_cash_flow': [{'year': 1, 'cost': 100, 'benefit': 40, 'net': -60, 'cumulative': -60}]}}


class PlanningPackTests(unittest.TestCase):
    def test_connected_pack_passes(self):
        self.assertEqual(validate(fixture()), [])

    def test_l4_cannot_skip_parent_level(self):
        p = fixture(); p['processes'][3]['parent_id'] = 'P1'
        self.assertTrue(any('parent' in x for x in validate(p)))

    def test_application_requires_real_information_reference(self):
        p = fixture(); p['applications'][0]['information_ids'] = ['missing']
        self.assertTrue(any('information_ids' in x for x in validate(p)))

    def test_dependency_cannot_run_after_consumer(self):
        p = fixture(); p['waves'].append({'id': 'W2', 'name': '扩展', 'initiative_ids': ['I2']})
        other = copy.deepcopy(p['initiatives'][0]); other.update(id='I2', wave_id='W2')
        p['initiatives'].append(other); p['initiatives'][0]['depends_on'] = ['I2']
        self.assertTrue(any('dependency' in x for x in validate(p)))

    def test_cash_flow_must_reconcile_to_line_items(self):
        p = fixture(); p['financials']['annual_cash_flow'][0]['net'] = 10
        self.assertTrue(any('cash' in x for x in validate(p)))

    def test_duplicate_benefit_year_rejected(self):
        p = fixture(); p['financials']['benefits'] *= 2
        self.assertTrue(any('duplicate benefit' in x for x in validate(p)))

    def test_assumed_evidence_cannot_support_approved_pack(self):
        p = fixture(); p['artifact_header']['status'] = 'approved'
        self.assertTrue(any('assumed' in x for x in validate(p)))

    def test_empty_pack_rejected(self):
        self.assertTrue(validate({}))


if __name__ == '__main__':
    unittest.main()
