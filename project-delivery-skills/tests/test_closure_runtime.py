"""Closure integration with real registered upstreams and independent gate states."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1] / 'skills/delivery-orchestrator/scripts/runtime.py'


class ClosureRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'
        spec = importlib.util.spec_from_file_location('delivery_closure_runtime', RUNTIME)
        self.r = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.r)
        self.r.init_project(self.project, 'CLOSURE-001', purpose='internal')
        path = self.base / 'basis.txt'
        path.write_text('Synthetic registered closure terms and decisions. No genuine customer evidence.')
        self.source = self.r.source(self.project, path, 'SRC')
        self.contract = self.register('CONTRACT', 'contract', dict(obligations=[dict(id='O1',
            statement='Warranty excluded by synthetic contract', source_id='SRC', locator='line 1',
            acceptance='Closure evidence retained')], scope_in=['Synthetic delivery'], scope_out=['Warranty'],
            customer_dependencies=[]), [self.source])
        self.decision = self.register('DECISION', 'minutes', dict(meeting_date=self.r.now()[:10],
            participants=['Synthetic representative'], decisions=['Administrative closure recorded'],
            actions=[], open_items=[]), [self.source])
        self.evidence = self.register('EVIDENCE', 'evidence', dict(items=[dict(id='E1', source_id='SRC',
            locator='line 1', content='Synthetic release receipt', read_status='read')], unread_scope=[]), [self.source])
        self.requirements = self.register('REQ', 'requirements', dict(items=[dict(id='R1',
            statement='Maintain closure record', source_refs=[self.source], acceptance='Record reopens', priority='must')],
            open_items=[]), [self.source])
        self.receipt = self.register('RECEIPT', 'confirmation', dict(target=self.requirements, state='accepted',
            actor='Synthetic representative', role='fixture', date=self.r.now()[:10], scope=['record'],
            evidence_refs=[self.source], origin='actual', open_items=[]), [self.requirements, self.source])

    def register(self, aid, kind, data, inputs, revision=1):
        return self.r.register(self.project, dict(project_id='CLOSURE-001', artifact_id=aid, revision=revision,
            kind=kind, visibility='internal', status='ready', inputs=inputs, data=data))

    def closure(self):
        return dict(origin='actual', as_of=self.r.now()[:10], obligations=[dict(id='O1', title='Return access',
            category='handover', owner='Delivery owner', state='closed', due_date='2020-01-01',
            evidence_refs=[self.evidence], recipient=None, receipt_refs=[])],
            warranty=dict(applicable=False, reason='Excluded by contract', owner=None, start_date=None, end_date=None,
                terms_refs=[self.contract], transfer_refs=[], items=[]),
            administration=dict(state='closed', decision_refs=[self.decision]),
            settlement=dict(state='reconciled', evidence_refs=[self.evidence]),
            resources=[dict(id='RES1', owner='Delivery owner', state='released', reason='', evidence_refs=[self.evidence])],
            archive=[dict(id='ARC1', artifact_ref=self.requirements, owner='Records owner',
                classification='internal project record', retention_until='2099-01-01')],
            lessons=[dict(id='L1', observation='Synthetic test records retain provenance',
                action='Keep source references', owner='Delivery owner')])

    def save_closure(self, data=None, revision=1, inputs=None):
        return self.register('CLOSE', 'closure', data if data is not None else self.closure(),
            inputs if inputs is not None else [self.contract, self.decision, self.evidence, self.requirements, self.receipt], revision)

    def gate(self):
        return self.r.snapshot(self.project)['gates']['CLOSE']

    def test_complete_closure_roundtrips_with_real_pinned_upstreams(self):
        ref = self.save_closure()
        loaded = self.r.load_artifact(self.project, ref)
        self.assertEqual(loaded['data']['archive'][0]['artifact_ref'], self.requirements)
        self.assertTrue(self.r.validate(self.project)['ok'])
        self.assertTrue(all(self.gate()[key] for key in ('administrative_closed', 'warranty_transferred',
            'warranty_ended', 'fully_discharged', 'ready')))

    def test_future_actual_date_cannot_force_warranty_end(self):
        data = self.closure()
        data.update(as_of='2099-01-01')
        data['warranty'].update(applicable=True, reason='Contract warranty', owner='Support owner',
            start_date='2020-01-01', end_date='2090-01-01', transfer_refs=[self.receipt])
        with self.assertRaises(ValueError):
            self.save_closure(data)
        self.assertIsNone(self.r.read_registry(self.project)['artifacts'].get('CLOSE'))

    def test_warranty_in_progress_allows_admin_close_but_not_discharge(self):
        data = self.closure()
        data['warranty'].update(applicable=True, reason='Contract warranty', owner='Support owner',
            start_date='2020-01-01', end_date='2090-01-01', transfer_refs=[self.receipt])
        self.save_closure(data)
        gate = self.gate()
        self.assertTrue(gate['administrative_closed'])
        self.assertTrue(gate['warranty_transferred'])
        self.assertFalse(gate['warranty_ended'])
        self.assertFalse(gate['fully_discharged'])
        self.assertFalse(gate['ready'])

    def test_transferred_obligation_is_administrative_not_full_discharge(self):
        data = self.closure()
        data['obligations'][0].update(state='transferred', recipient='Customer owner', receipt_refs=[self.receipt])
        self.save_closure(data)
        self.assertTrue(self.gate()['administrative_closed'])
        self.assertFalse(self.gate()['fully_discharged'])

    def test_actual_warranty_ended_still_requires_transfer_and_product_archive(self):
        for missing in ('transfer', 'archive'):
            data = self.closure()
            data['warranty'].update(applicable=True, reason='Contract warranty', owner='Support owner',
                start_date='2000-01-01', end_date='2001-01-01', transfer_refs=[self.receipt])
            if missing == 'transfer':
                data['warranty']['transfer_refs'] = []
            else:
                data['archive'] = []
            with self.subTest(missing=missing):
                if missing == 'archive':
                    with self.assertRaises(ValueError):
                        self.save_closure(data, revision=2)
                else:
                    self.save_closure(data)
                    self.assertFalse(self.gate()['fully_discharged'])
                    self.assertFalse(self.gate()['ready'])

    def test_empty_initial_archive_cannot_fully_discharge(self):
        data = self.closure()
        data['archive'] = []
        self.save_closure(data)
        self.assertFalse(self.gate()['fully_discharged'])

    def test_retained_resource_cannot_disappear_in_next_revision(self):
        data = self.closure()
        data['resources'][0].update(state='retained', reason='Access still active', evidence_refs=[])
        self.save_closure(data)
        self.assertFalse(self.gate()['fully_discharged'])
        next_data = copy.deepcopy(data)
        next_data['resources'] = []
        with self.assertRaises(ValueError):
            self.save_closure(next_data, revision=2)
        next_data = copy.deepcopy(data)
        next_data['resources'][0].update(state='released', evidence_refs=[self.evidence])
        self.save_closure(next_data, revision=2)
        self.assertTrue(self.gate()['fully_discharged'])

    def test_rejected_conditional_and_unready_confirmation_cannot_prove_transfer(self):
        base = self.r.load_artifact(self.project, self.receipt)
        for index, (state, status) in enumerate((('rejected', 'ready'), ('conditional', 'ready'), ('accepted', 'draft'))):
            receipt = copy.deepcopy(base)
            receipt.update(artifact_id='BAD-RECEIPT-' + str(index), status=status)
            receipt['data'].update(state=state, open_items=[] if state == 'accepted' else ['Not received'])
            receipt_ref = self.r.register(self.project, receipt)
            for target in ('warranty', 'obligation'):
                data = self.closure()
                if target == 'warranty':
                    data['warranty'].update(applicable=True, owner='Support owner', start_date='2000-01-01',
                        end_date='2001-01-01', transfer_refs=[receipt_ref])
                else:
                    data['obligations'][0].update(state='transferred', recipient='Support owner', receipt_refs=[receipt_ref])
                with self.subTest(state=state, status=status, target=target), self.assertRaises(ValueError):
                    self.save_closure(data, inputs=[self.contract, self.decision, self.evidence, self.requirements, receipt_ref])

    def test_na_warranty_requires_contract_basis_and_cannot_hide_open_warranty_item(self):
        data = self.closure()
        data['warranty']['terms_refs'] = []
        with self.assertRaises(ValueError):
            self.save_closure(data)
        data = self.closure()
        data['warranty']['items'] = [dict(id='W1', title='Unresolved defect', owner='Support owner',
            state='open', evidence_refs=[])]
        self.save_closure(data)
        self.assertFalse(self.gate()['warranty_ended'])
        self.assertFalse(self.gate()['fully_discharged'])

    def test_unbound_wrong_kind_and_tampered_refs_do_not_become_evidence(self):
        for mutation in ('unbound', 'wrong_kind', 'hash'):
            data = self.closure()
            inputs = [self.contract, self.decision, self.evidence, self.requirements, self.receipt]
            if mutation == 'unbound':
                inputs.remove(self.decision)
            elif mutation == 'wrong_kind':
                data['administration']['decision_refs'] = [self.source]
                inputs.append(self.source)
            else:
                data['archive'][0]['artifact_ref'] = dict(self.requirements, sha256='0' * 64)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.save_closure(data, inputs=inputs)

    def test_source_revision_invalidates_closure_and_all_positive_gate_states(self):
        self.save_closure()
        (self.base / 'basis.txt').write_text('Revised synthetic contract basis')
        self.r.source(self.project, self.base / 'basis.txt', 'SRC')
        self.assertFalse(self.r.validate(self.project)['ok'])
        gate = self.gate()
        self.assertFalse(any(gate[key] for key in ('administrative_closed', 'warranty_transferred',
            'warranty_ended', 'fully_discharged', 'ready')))

    def test_closed_obligation_cannot_be_reopened_as_transferred_without_correction(self):
        data = self.closure()
        self.save_closure(data)
        reopened = copy.deepcopy(data)
        reopened['obligations'][0].update(state='transferred', recipient='Customer owner', receipt_refs=[self.receipt])
        with self.assertRaises(ValueError):
            self.save_closure(reopened, revision=2)
        reopened['obligations'][0]['correction_reason'] = 'Synthetic missed obligation discovered'
        self.save_closure(reopened, revision=2)
        self.assertFalse(self.gate()['fully_discharged'])


if __name__ == '__main__':
    unittest.main()
