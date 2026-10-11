"""Real filesystem integration for profiles, pinned form mappings and local exchange.

All external receipts and projects are synthetic fixtures; no network actions occur.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1] / 'skills/delivery-orchestrator/scripts/runtime.py'


def runtime_module():
    spec = importlib.util.spec_from_file_location('delivery_reuse_runtime', RUNTIME)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ReuseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'
        self.r = runtime_module()
        self.r.init_project(self.project, 'REUSE-001', purpose='simulation')
        self.form = self.json_source('FORM', {'fields': [
            {'id': 'title', 'type': 'string', 'required': True},
            {'id': 'hours', 'type': 'number', 'required': True},
            {'id': 'note', 'type': 'string', 'required': False}]})
        self.data = self.json_source('DATA', {'title': '排程任务', 'hours': '12.5',
                                               'private': {'token': 'synthetic-fixture'}})

    def artifact(self, aid, kind, data, inputs, *, revision=1, visibility='internal', project=None):
        project = project or self.project
        return dict(project_id=self.r.read_project(project)['project_id'], artifact_id=aid,
                    revision=revision, kind=kind, visibility=visibility, status='ready',
                    inputs=inputs, data=data)

    def json_source(self, aid, data, project=None):
        project = project or self.project
        path = self.base / (project.name + '-' + aid + '.json')
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return self.r.source(project, path, aid)

    def mapping(self, *, aid='MAP', source=None, form=None, audience='internal'):
        source, form = source or self.data, form or self.form
        return self.artifact(aid, 'template_mapping', dict(
            form_ref=form, audience=audience, mappings=[
                dict(id='M1', target_field='title', source_ref=source, source_pointer='/title', transform='identity'),
                dict(id='M2', target_field='hours', source_ref=source, source_pointer='/hours', transform='number')],
            omissions=[dict(id='O1', target_field='note', reason='No annotation requested')]), [form, source])

    def register_mapping(self):
        return self.r.register(self.project, self.mapping())

    def exchange(self, mapping, *, revision=1, state='prepared', receipt=None, aid='EX'):
        inputs = [mapping] + ([receipt] if receipt else [])
        return self.artifact(aid, 'exchange', dict(operation_id='OP-1', system='synthetic-task-system',
            entity='task', direction='outbound', record_id='WP1', external_id='TASK-1', mapping_ref=mapping,
            state=state, receipt_ref=receipt, conflicts=[]), inputs, revision=revision)

    def receipt(self, **changes):
        value = dict(operation_id='OP-1', system='synthetic-task-system', entity='task', direction='outbound',
                     record_id='WP1', external_id='TASK-1', payload_sha256=canonical_hash(
            {'title': '排程任务', 'hours': 12.5}), state='applied', origin='simulation')
        value.update(changes)
        return self.json_source('RECEIPT', value)

    def profile(self):
        streams = [
            dict(id='FIX', mode='fixed', scope_ids=['deployment'], currency='CNY', amount=1000,
                 hours=None, rate=None, cap=None, basis='Synthetic contract fixed scope', terms_refs=[self.data]),
            dict(id='TIME', mode='time', scope_ids=['support'], currency='USD', amount=None,
                 hours=5, rate=30, cap=120, basis='Synthetic contract capped support', terms_refs=[self.data])]
        return self.artifact('PROFILE', 'profile', dict(billing_mode='mixed', delivery_mode='mixed',
            streams=streams, terms_refs=[self.data], open_items=[]), [self.data])

    def test_profile_keeps_currencies_and_capped_time_estimate_separate(self):
        ref = self.r.register(self.project, self.profile())
        self.assertEqual(self.r.load_artifact(self.project, ref)['data']['billing_mode'], 'mixed')
        gate = self.r.snapshot(self.project)['gates']['PROFILE']
        self.assertTrue(gate['ready'])
        self.assertEqual(gate['billing']['estimates_by_currency'], {'CNY': '1000.00', 'USD': '120.00'})
        self.assertFalse(gate['billing']['revenue_recognized'])
        self.assertFalse(gate['billing']['invoice_created'])

    def test_profile_unknown_hours_stays_incomplete_and_overlapping_scope_is_rejected(self):
        value = self.profile()
        value['data']['streams'][1]['hours'] = None
        self.r.register(self.project, value)
        gate = self.r.snapshot(self.project)['gates']['PROFILE']
        self.assertFalse(gate['ready'])
        self.assertNotIn('USD', gate['billing']['estimates_by_currency'])
        value = self.profile()
        value['revision'] = 2
        value['data']['streams'][1]['scope_ids'] = ['deployment']
        with self.assertRaises(ValueError):
            self.r.register(self.project, value)

    def test_mapping_prepares_actual_snapshot_values_and_verified_output_hash(self):
        ref = self.register_mapping()
        # Changing the original upload must not change the pinned snapshot.
        (self.base / 'project-DATA.json').write_text('{"title":"changed"}', encoding='utf-8')
        output = self.base / 'mapped.json'
        result = self.r.prepare_mapped(self.project, 'MAP', output)
        saved = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(saved['source_ref'], ref)
        self.assertEqual(saved['payload'], {'title': '排程任务', 'hours': 12.5})
        self.assertEqual(saved['payload_sha256'], canonical_hash(saved['payload']))
        self.assertEqual(result['sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertFalse(saved['sent'])
        self.assertFalse(saved['applied'])
        self.assertFalse(saved['customer_package_eligible'])
        with self.assertRaises(FileExistsError):
            self.r.prepare_mapped(self.project, 'MAP', output)

    def test_mapping_cannot_waive_or_silently_skip_required_target(self):
        for omission in (False, True):
            value = self.mapping()
            value['data']['mappings'].pop()
            if omission:
                value['data']['omissions'].append(dict(id='O2', target_field='hours', reason='Unavailable'))
            with self.subTest(omission=omission), self.assertRaises(ValueError):
                self.r.register(self.project, value)

    def test_mapping_rejects_invalid_pointer_type_and_nonfinite_number(self):
        for pointer, transform in (('hours', 'number'), ('/~2bad', 'identity'),
                                   ('/missing', 'identity'), ('/hours', 'identity')):
            value = self.mapping()
            value['data']['mappings'][1].update(source_pointer=pointer, transform=transform)
            with self.subTest(pointer=pointer, transform=transform), self.assertRaises(ValueError):
                self.r.register(self.project, value)
        for raw in ('NaN', 'Infinity', True):
            source = self.json_source('BADNUMBER', {'title': 'Fixture', 'hours': raw})
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.r.register(self.project, self.mapping(source=source))

    def test_form_must_be_real_json_source_and_all_business_refs_must_be_pinned(self):
        value = self.mapping()
        value['inputs'].remove(self.form)
        with self.assertRaises(ValueError):
            self.r.register(self.project, value)
        ref = self.register_mapping()
        value = self.mapping(aid='BADFORM', form=ref)
        with self.assertRaises(ValueError):
            self.r.register(self.project, value)

    def test_target_spec_change_invalidates_mapping_and_prepare(self):
        self.register_mapping()
        self.json_source('FORM', {'fields': [{'id': 'new-required', 'type': 'string', 'required': True}]})
        self.assertFalse(self.r.validate(self.project)['ok'])
        self.assertFalse(self.r.snapshot(self.project)['gates']['MAP']['ready'])
        with self.assertRaises(ValueError):
            self.r.prepare_mapped(self.project, 'MAP', self.base / 'stale.json')

    def test_customer_mapping_rejects_internal_snapshot_even_with_public_target_name(self):
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.mapping(audience='customer'))

    def test_customer_mapping_checks_sensitive_pointer_and_nested_output(self):
        req = self.artifact('REQ', 'requirements', dict(items=[dict(id='R1', statement='Fixture',
            source_refs=[self.data], acceptance='Read back', priority='must')], open_items=[],
            token='synthetic-fixture', public={'nested': [{'password': 'synthetic-fixture'}]}),
            [self.data], visibility='customer')
        reqref = self.r.register(self.project, req)
        for pointer, fieldtype in (('/token', 'string'), ('/public', 'object')):
            form = self.json_source('PRIVATEFORM', {'fields': [{'id': 'description', 'type': fieldtype, 'required': True}]})
            value = self.artifact('PRIVATEMAP', 'template_mapping', dict(form_ref=form, audience='customer',
                mappings=[dict(id='M1', target_field='description', source_ref=reqref,
                    source_pointer=pointer, transform='identity')], omissions=[]), [form, reqref])
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                self.r.register(self.project, value)

    def test_exchange_prepared_is_not_reconciled_and_local_prepare_does_not_dispatch(self):
        mapping = self.register_mapping()
        self.r.register(self.project, self.exchange(mapping))
        gate = self.r.snapshot(self.project)['gates']['EX']
        self.assertFalse(gate['ready'])
        self.assertFalse(gate['dispatched_by_tool'])
        output = self.base / 'exchange.json'
        self.r.prepare_mapped(self.project, 'EX', output)
        saved = json.loads(output.read_text())
        self.assertEqual(saved['exchange']['operation_id'], 'OP-1')
        self.assertFalse(saved['sent'])
        self.assertFalse(saved['applied'])

    def test_exchange_reconciles_only_matching_actual_source_receipt(self):
        mapping = self.register_mapping()
        self.r.register(self.project, self.exchange(mapping))
        receipt = self.receipt()
        ref = self.r.register(self.project, self.exchange(mapping, revision=2, state='reconciled', receipt=receipt))
        self.assertEqual(self.r.load_artifact(self.project, ref)['data']['receipt_ref'], receipt)
        self.assertTrue(self.r.snapshot(self.project)['gates']['EX']['ready'])
        self.assertEqual(self.r.latest_ref(self.project, 'EX')['revision'], 2)

    def test_exchange_receipt_must_match_operation_external_id_payload_and_state(self):
        mapping = self.register_mapping()
        for change in (dict(operation_id='OTHER'), dict(system='OTHER'), dict(entity='document'),
                       dict(direction='inbound'), dict(record_id='WP2'), dict(external_id='OTHER'),
                       dict(payload_sha256='0' * 64), dict(state='pending'), dict(origin='invented')):
            receipt = self.receipt(**change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.r.register(self.project, self.exchange(mapping, state='reconciled', receipt=receipt))

    def test_exchange_receipt_rejects_non_source_artifact_and_conflicts(self):
        mapping = self.register_mapping()
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.exchange(mapping, state='reconciled', receipt=mapping))
        receipt = self.receipt()
        value = self.exchange(mapping, state='reconciled', receipt=receipt)
        value['data']['conflicts'] = ['Unresolved external edit']
        with self.assertRaises(ValueError):
            self.r.register(self.project, value)
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.exchange(mapping, receipt=receipt))

    def test_exchange_duplicate_operation_and_mutable_operation_are_rejected(self):
        mapping = self.register_mapping()
        self.r.register(self.project, self.exchange(mapping))
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.exchange(mapping, aid='DUPLICATE'))
        for key, replacement in (('operation_id', 'OP-2'), ('external_id', 'TASK-2'),
                                 ('record_id', 'WP2'), ('direction', 'inbound')):
            value = self.exchange(mapping, revision=2)
            value['data'][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.r.register(self.project, value)
        self.assertEqual(self.r.latest_ref(self.project, 'EX')['revision'], 1)

    def test_reconciled_exchange_cannot_rewrite_receipt(self):
        mapping = self.register_mapping()
        receipt = self.receipt()
        self.r.register(self.project, self.exchange(mapping, state='reconciled', receipt=receipt))
        second_receipt = self.json_source('OTHERRECEIPT', self.r.read_source_json(
            self.project, self.r.load_artifact(self.project, receipt)))
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.exchange(mapping, revision=2, state='reconciled', receipt=second_receipt))

    def test_customer_mapping_can_export_selected_public_requirement_field(self):
        value = self.artifact('REQ', 'requirements', dict(items=[dict(id='R1', statement='Create work order',
            source_refs=[self.data], acceptance='Saved order reopens', priority='must')], open_items=[]),
            [self.data], visibility='customer')
        source = self.r.register(self.project, value)
        form = self.json_source('PUBLICFORM', {'fields': [{'id': 'description', 'type': 'string', 'required': True}]})
        mapping = self.artifact('PUBLICMAP', 'template_mapping', dict(form_ref=form, audience='customer',
            mappings=[dict(id='M1', target_field='description', source_ref=source,
                source_pointer='/items/0/statement', transform='identity')], omissions=[]), [form, source])
        self.r.register(self.project, mapping)
        output = self.base / 'public-mapped.json'
        self.r.prepare_mapped(self.project, 'PUBLICMAP', output)
        self.assertEqual(json.loads(output.read_text())['payload'], {'description': 'Create work order'})

    def test_exchange_cannot_launder_sensitive_source_pointer_or_stringified_object(self):
        for aid, pointer in (('TOKENMAP', '/private/token'), ('OBJECTMAP', '/private')):
            value = self.mapping(aid=aid)
            value['data']['mappings'][0].update(source_pointer=pointer, transform='string')
            mapping = self.r.register(self.project, value)
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                self.r.register(self.project, self.exchange(mapping))

    def test_exchange_payload_mapping_is_immutable_after_preparation(self):
        mapping = self.register_mapping()
        self.r.register(self.project, self.exchange(mapping))
        other = self.r.register(self.project, self.mapping(aid='OTHERMAP'))
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.exchange(other, revision=2))
        self.assertEqual(self.r.load_artifact(self.project, self.r.latest_ref(self.project, 'EX'))['data']['mapping_ref'], mapping)

    def test_real_project_rejects_simulated_exchange_receipt_but_accepts_actual_origin(self):
        self.project = self.base / 'real-project'
        self.r.init_project(self.project, 'REAL-001', purpose='internal')
        self.form = self.json_source('FORM', {'fields': [
            {'id': 'title', 'type': 'string', 'required': True},
            {'id': 'hours', 'type': 'number', 'required': True},
            {'id': 'note', 'type': 'string', 'required': False}]})
        self.data = self.json_source('DATA', {'title': '排程任务', 'hours': '12.5'})
        mapping = self.register_mapping()
        simulated = self.receipt()
        with self.assertRaises(ValueError):
            self.r.register(self.project, self.exchange(mapping, state='reconciled', receipt=simulated))
        actual = self.receipt(origin='actual')
        self.r.register(self.project, self.exchange(mapping, state='reconciled', receipt=actual))
        self.assertTrue(self.r.snapshot(self.project)['gates']['EX']['ready'])

    def financial_project(self, pid, currency='CNY', purpose='simulation', forecast=100, planned=10):
        project = self.base / pid
        self.r.init_project(project, pid, purpose=purpose, currency=currency)
        source = self.json_source('BASIS', {'fixture': 'synthetic cost and allocation basis'}, project)
        self.r.register(project, self.artifact('HOURS', 'timesheets', dict(items=[], remaining_labor=0,
            allocations=[dict(id='AL1', person='Developer', period='week1', work_package_id='WP1', planned_hours=planned)]),
            [source], project=project))
        self.r.register(project, self.artifact('COST', 'costs', dict(currency=currency, budget=1000,
            other_remaining=0, items=[dict(id='C1', category='other', work_package_id='WP1', state='incurred',
                amount=forecast, basis='Synthetic expense', payment_status='unpaid')]), [source], project=project))
        return project

    def portfolio(self, projects, **kwargs):
        return self.r.reuse.portfolio(projects, self.r.now()[:10], self.r, **kwargs)

    def test_portfolio_segregates_currencies_and_shared_person_needs_explicit_mapping(self):
        a, b = self.financial_project('A'), self.financial_project('B', currency='USD', forecast=200, planned=20)
        result = self.portfolio([a, b])
        self.assertEqual(result['forecast_by_currency'], {'CNY': '100.00', 'USD': '200.00'})
        self.assertEqual(result['resource_load'], [])
        self.assertFalse(result['complete'])
        self.assertTrue(any('unmapped resource' in gap for gap in result['gaps']))
        self.assertTrue(all(project['source_refs'] for project in result['projects']))
        self.assertFalse(result['historical_reconstruction'])
        self.assertFalse(result['external_actions'])

    def test_portfolio_shared_capacity_is_once_per_identified_person_and_period(self):
        a, b = self.financial_project('A'), self.financial_project('B', planned=20)
        result = self.portfolio([a, b], identity_map={'A': {'Developer': 'PERSON-1'}, 'B': {'Developer': 'PERSON-1'}},
            capacities=[dict(person='PERSON-1', period='week1', available_hours=25)])
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['resource_load']), 1)
        row = result['resource_load'][0]
        self.assertEqual(float(row['planned_hours']), 30)
        self.assertEqual(float(row['available_hours']), 25)
        self.assertTrue(row['overloaded'])
        with self.assertRaises(ValueError):
            self.portfolio([a], identity_map={'A': {'Developer': 'PERSON-1'}}, capacities=[
                dict(person='PERSON-1', period='week1', available_hours=25)] * 2)

    def test_portfolio_unknown_planned_hours_does_not_assert_known_total_or_overload(self):
        a, b = self.financial_project('A', planned=10), self.financial_project('B', planned=None)
        result = self.portfolio([a, b], identity_map={'A': {'Developer': 'PERSON-1'}, 'B': {'Developer': 'PERSON-1'}},
            capacities=[dict(person='PERSON-1', period='week1', available_hours=25)])
        self.assertFalse(result['complete'])
        self.assertTrue(any('planned hours unknown' in gap for gap in result['gaps']))
        row = result['resource_load'][0]
        self.assertIsNone(row['planned_hours'])
        self.assertIsNone(row['overloaded'])

    def test_portfolio_rejects_simulation_real_mix_duplicate_projects_and_historical_date(self):
        a, b = self.financial_project('A'), self.financial_project('B', purpose='internal')
        with self.assertRaises(ValueError):
            self.portfolio([a, b])
        with self.assertRaises(ValueError):
            self.portfolio([a, a])
        with self.assertRaises(ValueError):
            self.r.reuse.portfolio([a], '2000-01-01', self.r)


if __name__ == '__main__':
    unittest.main()
