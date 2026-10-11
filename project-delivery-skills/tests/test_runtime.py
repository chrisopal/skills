"""Business-state regression checks; all approval records here are synthetic fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1] / 'skills/delivery-orchestrator/scripts/runtime.py'


def module():
    spec = importlib.util.spec_from_file_location('delivery_runtime', RUNTIME)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'project'
        self.r = module()
        self.r.init_project(self.project, 'TEST-001', purpose='simulation')
        source = self.base / 'contract.txt'
        source.write_text('SIMULATION: contract and synthetic decisions, not customer evidence.')
        self.src = self.r.source(self.project, source, 'SRC')

    def artifact(self, aid='REQ', kind='requirements', revision=1, inputs=None, data=None, **extra):
        value = dict(project_id='TEST-001', artifact_id=aid, revision=revision,
                     kind=kind, visibility='customer', status='ready',
                     inputs=inputs if inputs is not None else [self.src],
                     data=data if data is not None else {'items': [{
                         'id': 'R1', 'statement': 'Create work order',
                         'source_refs': [dict(self.src, locator='line 1')],
                         'acceptance': 'Saved work order is read back', 'priority': 'must'}], 'open_items': []})
        value.update(extra)
        return value

    def register(self, value):
        return self.r.register(self.project, value)

    def req(self, revision=1):
        return self.register(self.artifact(revision=revision))

    def blueprint(self, req=None, revision=1):
        req = req or self.req()
        data = dict(
            processes=[{'id': 'P1', 'title': 'Work order', 'steps': ['create', 'save'], 'requirement_ids': ['R1']}],
            pages=[{'id': 'UI1', 'title': 'Create', 'requirement_ids': ['R1']}],
            fields=[{'id': 'F1', 'page_id': 'UI1', 'name': 'Title', 'type': 'string',
                     'required': True, 'validation': '1-100 chars', 'permission': 'dispatcher writes'}],
            interfaces=[{'id': 'API1', 'title': 'Asset lookup', 'source_system': 'Asset',
                         'target_system': 'Work order', 'field_mappings': ['asset_id'], 'acceptance': 'IDs match'}],
            acceptance_scenarios=[{'id': 'T1', 'requirement_ids': ['R1'], 'steps': ['save', 'reopen'], 'expected': 'same value'}],
            coverage=[{'requirement_id': 'R1', 'design_ids': ['P1', 'UI1', 'F1', 'API1', 'T1']}], open_items=[])
        return self.register(self.artifact('BP', 'blueprint', revision, [req, self.src], data))

    def confirmation(self, target, state='accepted', origin='simulation', aid='CONF'):
        return self.register(self.artifact(aid, 'confirmation', inputs=[target, self.src], data=dict(
            target=target, state=state, actor='Synthetic customer representative', role='test fixture',
            date='2026-10-11', scope=['processes', 'pages', 'fields', 'permissions', 'interfaces', 'data', 'acceptance'],
            evidence_refs=[dict(self.src, locator='line 1')], origin=origin, open_items=[])))

    def review(self, target, verdict='pass', aid='REVIEW', findings=None):
        return self.register(self.artifact(aid, 'review', inputs=[target, self.src], visibility='internal', data=dict(
            targets=[target], verdict=verdict, reviewer='Synthetic reviewer', method='independent-fixture',
            findings=findings or [], unchecked=['identity verification'], scope=['scope', 'fields', 'source'])))

    def change(self, old, new, state='approved'):
        return self.register(self.artifact('CHG', 'change', inputs=[old, new, self.src], visibility='internal', data=dict(
            state=state, reason='Synthetic new approval step', affected_ids=[old['artifact_id']],
            baseline_refs=[old], replacements=[new], decision_refs=[dict(self.src, locator='line 1')],
            impact={'schedule': 'two estimated days', 'cost': 'pending estimate'})))

    def test_init_refuses_overwrite(self):
        with self.assertRaises(ValueError):
            self.r.init_project(self.project, 'OTHER')

    def test_workspace_separates_stage_materials_and_internal_finance(self):
        for directory in ('04-discovery', '05-requirements-blueprint', 'internal-finance', 'customer-deliverables', '11-milestone-acceptance'):
            self.assertTrue((self.project / directory).is_dir())
        self.assertIn('目录名不是权限控制', (self.project / 'README.md').read_text())

    def test_source_snapshot_and_idempotence(self):
        src = self.r.load_artifact(self.project, self.src)
        self.assertEqual(src['kind'], 'source')
        self.assertTrue((self.project / src['data']['path']).is_file())
        self.assertEqual(self.r.source(self.project, self.base / 'contract.txt', 'SRC'), self.src)

    def test_roundtrip_and_idempotence(self):
        a = self.artifact()
        ref = self.register(a)
        self.assertEqual(self.r.load_artifact(self.project, ref), a)
        self.assertEqual(self.register(a), ref)

    def test_wrong_project(self):
        with self.assertRaises(ValueError):
            self.register(self.artifact(project_id='OTHER'))

    def test_path_traversal_id(self):
        with self.assertRaises(ValueError):
            self.register(self.artifact(aid='../outside'))

    def test_missing_dependency(self):
        with self.assertRaises(ValueError):
            self.register(self.artifact(inputs=[dict(self.src, artifact_id='UNKNOWN')]))

    def test_dependency_hash_tamper(self):
        with self.assertRaises(ValueError):
            self.register(self.artifact(inputs=[dict(self.src, sha256='0'*64)]))

    def test_revision_gap(self):
        with self.assertRaises(ValueError):
            self.req(2)

    def test_no_overwrite_same_revision(self):
        self.req()
        a = self.artifact()
        a['data']['items'][0]['statement'] = 'silently changed'
        with self.assertRaises(ValueError):
            self.register(a)

    def test_duplicate_business_id(self):
        a = self.artifact()
        a['data']['items'] *= 2
        with self.assertRaises(ValueError):
            self.register(a)

    def test_ready_placeholders_rejected(self):
        a = self.artifact()
        a['data']['items'][0]['statement'] = '{{requirement}}'
        with self.assertRaises(ValueError):
            self.register(a)

    def test_draft_placeholders_allowed(self):
        a = self.artifact(status='draft')
        a['data']['items'][0]['statement'] = '{{requirement}}'
        self.register(a)

    def test_source_change_invalidates_downstream(self):
        self.req()
        (self.base / 'contract.txt').write_text('updated synthetic source')
        self.r.source(self.project, self.base / 'contract.txt', 'SRC')
        self.assertFalse(self.r.validate(self.project)['ok'])

    def test_artifact_file_tamper_detected(self):
        ref = self.req()
        path = self.r.artifact_path(self.project, ref)
        path.write_text(path.read_text() + ' ')
        self.assertFalse(self.r.validate(self.project)['ok'])

    def test_source_snapshot_tamper_detected(self):
        src = self.r.load_artifact(self.project, self.src)
        (self.project / src['data']['path']).write_text('tamper')
        self.assertFalse(self.r.validate(self.project)['ok'])

    def test_symlink_artifact_rejected(self):
        ref = self.req()
        path = self.r.artifact_path(self.project, ref)
        data = path.read_bytes()
        path.unlink()
        elsewhere = self.base / 'elsewhere.json'
        elsewhere.write_bytes(data)
        path.symlink_to(elsewhere)
        with self.assertRaises(ValueError):
            self.r.load_artifact(self.project, ref)

    def test_candidate_does_not_replace_baseline(self):
        old = self.req()
        self.r.activate(self.project, ['REQ'])
        self.req(2)
        self.assertEqual(self.r.snapshot(self.project)['effective']['REQ'], old)
        self.assertTrue(self.r.validate(self.project)['effective_ok'])

    def test_activate_cannot_bypass_change(self):
        self.req()
        self.r.activate(self.project, ['REQ'])
        self.req(2)
        with self.assertRaises(ValueError):
            self.r.activate(self.project, ['REQ'])

    def test_change_atomic_apply(self):
        old = self.req()
        self.r.activate(self.project, ['REQ'])
        new = self.req(2)
        change = self.change(old, new)
        result = self.r.apply_change(self.project, 'CHG')
        self.assertEqual(result['state'], 'effective')
        self.assertEqual(self.r.snapshot(self.project)['effective']['REQ'], new)
        self.assertEqual(self.r.apply_change(self.project, 'CHG'), result)

    def test_failed_change_preserves_baseline(self):
        old = self.req()
        self.r.activate(self.project, ['REQ'])
        new = self.req(2)
        self.change(old, new)
        self.r.artifact_path(self.project, new).write_text('{}')
        with self.assertRaises(ValueError):
            self.r.apply_change(self.project, 'CHG')
        self.assertEqual(self.r.read_registry(self.project)['effective']['REQ'], old)

    def test_change_cannot_leave_effective_design_on_old_requirements(self):
        old = self.req()
        self.blueprint(old)
        self.r.activate(self.project, ['REQ', 'BP'])
        new = self.req(2)
        self.change(old, new)
        with self.assertRaises(ValueError):
            self.r.apply_change(self.project, 'CHG')
        self.assertEqual(self.r.read_registry(self.project)['effective']['REQ'], old)

    def test_unapproved_change_blocked(self):
        old = self.req()
        self.r.activate(self.project, ['REQ'])
        new = self.req(2)
        self.change(old, new, 'proposed')
        with self.assertRaises(ValueError):
            self.r.apply_change(self.project, 'CHG')

    def test_missing_confirmation_not_ready(self):
        self.blueprint()
        self.assertFalse(self.r.snapshot(self.project)['gates']['blueprint']['ready'])

    def test_exact_blueprint_confirmation(self):
        bp = self.blueprint()
        self.confirmation(bp)
        self.assertTrue(self.r.snapshot(self.project)['gates']['blueprint']['ready'])
        self.blueprint(self.r.latest_ref(self.project, 'REQ'), revision=2)
        self.assertFalse(self.r.snapshot(self.project)['gates']['blueprint']['ready'])

    def test_conditional_not_full_confirmation(self):
        bp = self.blueprint()
        self.confirmation(bp, state='conditional')
        self.assertFalse(self.r.snapshot(self.project)['gates']['blueprint']['ready'])

    def test_new_confirmation_id_cannot_hide_rejection(self):
        bp = self.blueprint()
        self.confirmation(bp, state='rejected', aid='REJECTED')
        self.confirmation(bp, aid='ACCEPTED')
        self.assertFalse(self.r.snapshot(self.project)['gates']['blueprint']['ready'])

    def test_simulation_confirmation_cannot_enter_real_project(self):
        self.req()
        self.r.project_path(self.project).write_text(json.dumps({'project_id': 'TEST-001', 'purpose': 'internal', 'currency': 'CNY'}))
        with self.assertRaises(ValueError):
            self.confirmation(self.r.latest_ref(self.project, 'REQ'))

    def test_confirm_unbound_target_rejected(self):
        target = self.req()
        ref = self.confirmation(target)
        value = self.r.load_artifact(self.project, ref)
        value['artifact_id'] = 'OTHERCONF'
        value['inputs'] = [self.src]
        with self.assertRaises(ValueError):
            self.register(value)

    def test_blueprint_unmapped_requirement_rejected(self):
        bp = self.blueprint()
        a = self.r.load_artifact(self.project, bp)
        a['revision'] = 2
        a['data']['coverage'][0]['design_ids'] = ['MISSING']
        with self.assertRaises(ValueError):
            self.register(a)

    def financials(self, rate=100, status='approved', revision=1, expense_state='incurred'):
        timesheets = self.artifact('HOURS', 'timesheets', revision, visibility='internal', data={
            'items': [{'id': 'H1', 'person': 'Developer', 'date': '2026-10-11', 'work_package_id': 'WP1',
                       'hours': 5, 'rate': rate, 'resource_type': 'internal', 'status': status},
                      {'id': 'H2', 'person': 'Vendor', 'date': '2026-10-11', 'work_package_id': 'WP1',
                       'hours': 8, 'rate': 200, 'resource_type': 'outsourced', 'status': 'approved'}],
            'remaining_labor': 200})
        self.register(timesheets)
        self.register(self.artifact('COST', 'costs', revision, visibility='internal', data={
            'currency': 'CNY', 'budget': 3000, 'other_remaining': 0,
            'items': [{'id': 'TRIP1', 'category': 'travel', 'work_package_id': 'WP1',
                       'state': expense_state, 'amount': 100, 'basis': 'test travel', 'payment_status': 'unpaid', 'travel_or_expense_ref': 'TRAVEL-001'},
                      {'id': 'VENDOR1', 'category': 'outsourcing', 'work_package_id': 'WP1',
                       'state': expense_state, 'amount': 1600, 'basis': 'settlement fixture', 'payment_status': 'unpaid'}]}))

    def test_cost_outsource_not_double_counted(self):
        self.financials()
        s = self.r.snapshot(self.project)['cost_summary']
        self.assertEqual(s['internal_labor'], '500.00')
        self.assertEqual(s['other_incurred'], '1700.00')
        self.assertEqual(s['forecast'], '2400.00')
        self.assertTrue(s['complete'])

    def test_unknown_rate_not_zero_complete(self):
        self.financials(rate=None)
        self.assertFalse(self.r.snapshot(self.project)['cost_summary']['complete'])

    def test_missing_outsourcing_amount_and_explicit_evidence_gaps(self):
        self.financials()
        value = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        value['revision'] = 2
        value['data']['items'][1]['work_package_id'] = 'UNLINKED'
        value['data']['evidence_status'] = 'incomplete_business_evidence'
        self.register(value)
        summary = self.r.cost_summary(self.project)
        self.assertFalse(summary['complete'])
        self.assertTrue(any('outsourced' in gap for gap in summary['gaps']))
        self.assertTrue(any('business evidence' in gap for gap in summary['gaps']))

    def test_unapproved_hours_are_provisional(self):
        self.financials(status='submitted')
        s = self.r.snapshot(self.project)['cost_summary']
        self.assertEqual(s['provisional_labor'], '500.00')
        self.assertFalse(s['complete'])

    def test_expense_payment_does_not_add_cost(self):
        self.financials()
        before = self.r.snapshot(self.project)['cost_summary']['forecast']
        v = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        v['revision'] = 2
        for item in v['data']['items']:
            item['payment_status'] = 'paid'
        self.register(v)
        self.assertEqual(self.r.snapshot(self.project)['cost_summary']['forecast'], before)

    def test_current_expense_observation_not_frozen_by_budget_baseline(self):
        self.financials()
        self.r.activate(self.project, ['COST', 'HOURS'])
        value = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        value['revision'] = 2
        value['data']['items'][0]['amount'] = 150
        value['data']['budget'] = 9999
        self.register(value)
        summary = self.r.snapshot(self.project)['cost_summary']
        self.assertEqual(summary['forecast'], '2450.00')
        self.assertEqual(summary['budget'], '3000.00')
        self.assertFalse(summary['complete'])

    def test_estimate_settlement_replaces_not_adds(self):
        self.financials(expense_state='estimate')
        before = self.r.snapshot(self.project)['cost_summary']['forecast']
        self.financials(revision=2)
        self.assertEqual(self.r.snapshot(self.project)['cost_summary']['forecast'], before)

    def test_duplicate_expense_rejected(self):
        self.financials()
        v = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        v['revision'] = 2
        v['data']['items'] *= 2
        with self.assertRaises(ValueError):
            self.register(v)

    def test_cost_alias_duplicates_and_conflicts_rejected(self):
        self.financials()
        base = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        import copy
        for alias in ('travel_or_expense_ref', 'procurement_ref', 'external_ref'):
            v = copy.deepcopy(base)
            v['revision'] = 2
            v['data']['items'][0]['travel_or_expense_ref'] = 'TRAVEL-001'
            duplicate = dict(v['data']['items'][0], id='TRIP2')
            duplicate.pop('travel_or_expense_ref')
            duplicate[alias] = 'TRAVEL-001'
            v['data']['items'].append(duplicate)
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                self.register(v)
        v = copy.deepcopy(base)
        v['revision'] = 2
        v['data']['items'][0].update(travel_or_expense_ref='A', external_ref='B')
        with self.assertRaises(ValueError):
            self.register(v)

    def test_stable_cost_lifecycle_and_id_across_revisions(self):
        self.financials(expense_state='estimate')
        original = self.r.snapshot(self.project)['cost_summary']['forecast']
        v = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        for revision, state, payment in ((2, 'committed', 'unpaid'), (3, 'incurred', 'reimbursed'), (4, 'incurred', 'paid')):
            v['revision'] = revision
            v['data']['items'][0].update(state=state, payment_status=payment, travel_or_expense_ref='TRAVEL-001')
            self.register(v)
            self.assertEqual(self.r.snapshot(self.project)['cost_summary']['forecast'], original)
        v['revision'] = 5
        v['data']['items'][0]['id'] = 'NEW-TRIP'
        with self.assertRaises(ValueError):
            self.register(v)

    def test_cost_row_or_logical_reference_cannot_disappear(self):
        self.financials()
        import copy
        base = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        for mutation in ('remove-row', 'remove-ref', 'change-ref', 'unaliased-new-id'):
            value = copy.deepcopy(base)
            value['revision'] = 2
            if mutation == 'remove-row':
                value['data']['items'].pop()
            elif mutation == 'remove-ref':
                value['data']['items'][0].pop('travel_or_expense_ref')
            elif mutation == 'change-ref':
                value['data']['items'][0]['travel_or_expense_ref'] = 'TRAVEL-OTHER'
            else:
                value['data']['items'][1]['id'] = 'VENDOR-NEW'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.register(value)

    def test_customer_shared_boundary_rejects_nested_credentials(self):
        for key in self.r.CUSTOMER_FORBIDDEN_KEYS:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.r.customer_fields({'nested': [{key.upper(): 'value'}]}, reject=True)
            self.assertEqual(self.r.customer_fields({'nested': [{key.upper(): 'value'}]}), {'nested': [{}]})

    def test_over_24_hours_rejected(self):
        self.financials()
        v = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'HOURS'))
        v['revision'] = 2
        v['data']['items'][0]['hours'] = 25
        with self.assertRaises(ValueError):
            self.register(v)

    def test_mixed_currency_rejected(self):
        self.financials()
        v = self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'COST'))
        v['revision'] = 2
        v['data']['currency'] = 'USD'
        with self.assertRaises(ValueError):
            self.register(v)

    def test_prepare_requires_review(self):
        self.req()
        with self.assertRaises(ValueError):
            self.r.prepare_customer(self.project, ['REQ'], self.base/'pack')

    def test_prepare_discussion_and_manifest_readback(self):
        target = self.req()
        self.review(target)
        result = self.r.prepare_customer(self.project, ['REQ'], self.base/'pack')
        self.assertEqual(result['purpose'], 'simulation')
        self.assertIn('模拟', (self.base/'pack/README.md').read_text())
        self.assertEqual(len(list((self.base/'pack').glob('*.json'))), 2)
        self.assertFalse((self.base/'pack/00-control').exists())

    def test_prepare_confirmed_requires_customer_confirmation(self):
        target = self.req()
        self.review(target)
        with self.assertRaises(ValueError):
            self.r.prepare_customer(self.project, ['REQ'], self.base/'pack', mode='confirmed')
        self.confirmation(target)
        self.r.prepare_customer(self.project, ['REQ'], self.base/'pack', mode='confirmed')

    def test_customer_pack_rejects_internal_even_mislabeled_kind(self):
        self.financials()
        target = self.r.latest_ref(self.project, 'COST')
        self.review(target)
        with self.assertRaises(ValueError):
            self.r.prepare_customer(self.project, ['COST'], self.base/'pack')

    def test_review_blocking_finding_cannot_pass(self):
        target = self.req()
        with self.assertRaises(ValueError):
            self.review(target, findings=[{'id': 'F1', 'severity': 'blocking', 'status': 'open', 'resolution_evidence': ''}])

    def test_new_review_id_cannot_hide_failure(self):
        target = self.req()
        self.review(target, verdict='fail', aid='FAILED')
        self.review(target, aid='PASSED')
        with self.assertRaises(ValueError):
            self.r.prepare_customer(self.project, ['REQ'], self.base/'pack')

    def test_pack_no_overwrite(self):
        target = self.req()
        self.review(target)
        self.r.prepare_customer(self.project, ['REQ'], self.base/'pack')
        with self.assertRaises(ValueError):
            self.r.prepare_customer(self.project, ['REQ'], self.base/'pack')


if __name__ == '__main__':
    unittest.main()
