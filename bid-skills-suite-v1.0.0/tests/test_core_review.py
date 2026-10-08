import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests'))
import bidkit
import review_checks
from core_review_fixture import populate, review


class CoreReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.project=Path(self.tmp.name)/'project'
        bidkit.init_project(self.project,'TEST-CORE')
        matrix=populate(self.project)
        self.snapshot=self.project/'reviews/snapshot.json'
        snap=bidkit.snapshot(self.project,'reviews/snapshot.json')
        self.review=review(self.project,matrix,snap)

    def tearDown(self):self.tmp.cleanup()
    def check(self):return review_checks.check(self.project,self.review,self.snapshot)
    def mutate_upstream(self,name,operation):
        p=self.project/'artifacts'/name
        value=bidkit.read(p);operation(value);bidkit.atomic(p,value)
        snapshot=bidkit.snapshot(self.project,'reviews/snapshot.json')
        self.review['data']['reviewed_inputs_sha256']=snapshot['fingerprint']
        for ref in self.review['inputs']:
            ref['sha256']=bidkit.digest(self.project/ref['relative_path'])

    def test_complete_evidence_bound_review(self):
        result=self.check();self.assertEqual(result['errors'],[])
        self.assertEqual(result['release_blockers'],[])
        self.assertTrue(result['formal_release_ready'])
        self.assertNotEqual(result['semantic_acceptance'],'PASS')

    def test_prepare_never_marks_satisfied(self):
        p=review_checks.prepare(self.project)
        self.assertEqual(p['semantic_acceptance'],'NOT_RUN')
        self.assertTrue(all(r['conclusion']=='unknown' for rows in p['core_matrix'].values() for r in rows))

    def test_missing_scoring_leaf_is_not_pass(self):
        self.review['data']['core_matrix']['scoring']=[]
        self.assertTrue(any('漏审 S1' in e for e in self.check()['errors']))

    def test_missing_fatal_clause_is_not_pass(self):
        self.review['data']['core_matrix']['compliance']=[]
        self.assertTrue(any('漏审 C1' in e for e in self.check()['errors']))

    def test_missing_material_group_is_not_pass(self):
        self.review['data']['core_matrix']['materials'].pop(0)
        self.assertTrue(any('漏审 SEL1' in e for e in self.check()['errors']))

    def test_duplicate_review_is_not_pass(self):
        rows=self.review['data']['core_matrix']['scoring'];rows.append(copy.deepcopy(rows[0]))
        self.assertTrue(any('ID重复' in e for e in self.check()['errors']))

    def test_wrong_subject_expired_missing_pages_signature_inclusion(self):
        for field in ('subject','validity','scope','required_pages','signature','inclusion','authenticity'):
            with self.subTest(field=field):
                r=copy.deepcopy(self.review)
                row=r['data']['core_matrix']['materials'][0];row['dimensions'][field]='failed'
                result=review_checks.check(self.project,r,self.snapshot)
                self.assertTrue(result['errors']);self.assertTrue(result['release_blockers'])

    def test_all_material_dimensions_required(self):
        self.review['data']['core_matrix']['materials'][0]['dimensions'].pop('validity')
        self.assertTrue(any('逐维检查不完整' in e for e in self.check()['errors']))

    def test_deleting_actual_material_invalidates_review(self):
        source=bidkit.read(self.project/'inputs/source-registry.json')['sources'][1]
        (self.project/source['relative_path']).unlink()
        result=self.check();self.assertFalse(result['current']);self.assertTrue(result['errors'])

    def test_same_contract_cannot_be_counted_twice(self):
        self.mutate_upstream('09-evidence-selection.json',lambda x:
            x['data']['materials'][2].update(sources=x['data']['materials'][1]['sources']))
        material_row=self.review['data']['core_matrix']['materials'][1]
        material_row['sources']=[bidkit.read(self.project/'artifacts/09-evidence-selection.json')['data']['materials'][1]['sources'][0]]
        self.assertTrue(any('重复计数' in e for e in self.check()['warnings']))

    def test_score_only_gap_is_not_rejection(self):
        self.mutate_upstream('09-evidence-selection.json',lambda x:
            x['data']['selections'][1].update(independent_count=1))
        result=self.check()
        self.assertTrue(result['warnings']);self.assertFalse(result['release_blockers'])
        self.assertTrue(result['errors'])

    def test_candidate_qualification_is_blocking(self):
        self.mutate_upstream('09-evidence-selection.json',lambda x:
            x['data']['selections'][0].update(state='candidate'))
        self.assertTrue(self.check()['release_blockers'])

    def test_fake_body_location_and_whole_json_self_proof(self):
        for location in ['/data/chapters','/data/chapters/0/missing']:
            with self.subTest(location=location):
                r=copy.deepcopy(self.review)
                r['data']['core_matrix']['compliance'][0]['bid_refs'][0]['location']=location
                self.assertTrue(review_checks.check(self.project,r,self.snapshot)['errors'])

    def test_source_quote_wrong_position(self):
        self.review['data']['core_matrix']['compliance'][0]['sources'][0]['location']='L1'
        self.assertTrue(self.check()['errors'])

    def test_changed_bid_text_invalidates_snapshot_and_quote(self):
        p=self.project/'artifacts/11-technical-content.json'
        value=bidkit.read(p);value['data']['chapters'][0]['body']='遗漏正文';bidkit.atomic(p,value)
        self.assertFalse(self.check()['current']);self.assertTrue(self.check()['errors'])

    def test_unreviewed_fatal_not_applicable_is_blocking(self):
        row=self.review['data']['core_matrix']['compliance'][0]
        row.update(conclusion='not_applicable',rationale='未证明适用性',finding_ids=[])
        result=self.check();self.assertTrue(result['errors']);self.assertTrue(result['release_blockers'])

    def test_score_bounds_and_price_unknown_are_not_guessed(self):
        row=self.review['data']['core_matrix']['scoring'][0]
        row['score_estimate']=3
        self.assertTrue(any('得分超界' in e for e in self.check()['errors']))
        row['score_estimate']=None
        self.assertFalse(self.check()['errors'])

    def test_release_gate_cannot_skip_matrix(self):
        self.review['data']['core_matrix']['scoring']=[]
        p=self.project/'reviews/15-review.json';bidkit.atomic(p,self.review)
        with self.assertRaisesRegex(ValueError,'核心业务评审'):
            bidkit.release_gate(self.project,p,self.snapshot,self.project/'confirmations/missing.json')

    def test_upstream_not_in_review_inputs_is_rejected(self):
        self.review['inputs']=[x for x in self.review['inputs'] if '04-scoring' not in x['relative_path']]
        self.assertTrue(any('未绑定当前上游' in e for e in self.check()['errors']))

    def finding(self, row, state='resolved', path='confirmations/applicability.txt'):
        row['finding_ids']=['F-TEST']
        self.review['data']['findings']=[{
            'id':'F-TEST','severity':'warning','category':'evidence',
            'related_ids':[row['target_id']], 'description':'TEST ONLY applicability review',
            'evidence':row['sources'], 'remediation':'Read the actual condition',
            'state':state, 'confirmation_ref':path,
        }]

    def bind_applicability(self):
        path=self.project/'confirmations/applicability.txt'
        path.write_text('TEST ONLY 对照原文适用条件，记录无需此证明的具体理由。')
        self.review['inputs'].append({'artifact_id':'TEST-APPLICABILITY','revision':1,
                                     'relative_path':'confirmations/applicability.txt',
                                     'sha256':bidkit.digest(path)})
        return {'reason':'TEST ONLY 仅样例条件不适用',
                'relative_path':'confirmations/applicability.txt','sha256':bidkit.digest(path)}

    def test_na_accepted_warning_cannot_skip_scoring_review(self):
        row=self.review['data']['core_matrix']['scoring'][0]
        row['conclusion']='not_applicable'
        self.finding(row, 'accepted_warning')
        self.assertTrue(any('不适用须有已复核' in e for e in self.check()['errors']))
        path=self.project/'reviews/15-review.json';bidkit.atomic(path,self.review)
        with self.assertRaisesRegex(ValueError,'核心业务评审'):
            bidkit.release_gate(self.project,path,self.snapshot,self.project/'confirmations/missing.json')

    def test_na_nonexistent_and_unbound_confirmation_rejected(self):
        row=self.review['data']['core_matrix']['scoring'][0];row['conclusion']='not_applicable'
        self.finding(row)
        self.assertTrue(any('复核记录不存在' in e for e in self.check()['errors']))
        (self.project/'confirmations/applicability.txt').write_text('TEST ONLY')
        self.assertTrue(any('未绑定' in e for e in self.check()['errors']))
        self.bind_applicability()
        self.assertTrue(self.check()['formal_release_ready'])

    def test_rejection_cannot_downgrade_its_fatal_consequence(self):
        for fatal in (False,None):
            self.mutate_upstream('05-compliance.json',lambda x:
                x['data']['rules'][0].update(kind='rejection',fatal=fatal))
            self.assertTrue(any('否决类别与明确后果' in e for e in self.check()['errors']))

    def test_qualification_material_group_cannot_disappear_upstream(self):
        self.mutate_upstream('09-evidence-selection.json',lambda x:
            x['data']['selections'].pop(0))
        self.review['data']['core_matrix']['materials'].pop(0)
        self.assertTrue(any('C1: 上游漏建' in e for e in self.check()['release_blockers']))

    def test_verified_conditional_na_does_not_require_material(self):
        self.mutate_upstream('09-evidence-selection.json',lambda x:
            x['data']['selections'].pop(0))
        self.review['data']['core_matrix']['materials'].pop(0)
        row=self.review['data']['core_matrix']['compliance'][0];row['conclusion']='not_applicable'
        self.finding(row);self.bind_applicability()
        self.assertTrue(self.check()['formal_release_ready'])

    def test_blanket_material_na_requires_bound_dimension_reviews(self):
        row=self.review['data']['core_matrix']['materials'][0]
        row['dimensions']={d:'not_applicable' for d in review_checks.MATERIAL_DIMENSIONS}
        self.assertEqual(sum('不适用维度缺少' in e for e in self.check()['errors']),8)
        exemption=self.bind_applicability()
        row['dimension_exemptions']={d:copy.deepcopy(exemption) for d in review_checks.MATERIAL_DIMENSIONS}
        self.assertTrue(self.check()['formal_release_ready'])
        (self.project/exemption['relative_path']).write_text('changed applicability review')
        self.assertTrue(any('维度适用性复核缺失/过期' in e for e in self.check()['errors']))

    def test_changed_files_of_same_contract_are_not_independent(self):
        self.mutate_upstream('09-evidence-selection.json',lambda x:
            x['data']['materials'][2].update(independent_evidence_id='contract-a.txt'))
        result=self.check()
        self.assertTrue(any('身份重复计数' in e for e in result['warnings']))
        self.assertTrue(any('独立证明身份冲突' in e for e in result['errors']))

    def test_unknown_scoring_cannot_release_as_a_normal_warning(self):
        row=self.review['data']['core_matrix']['scoring'][0];row['conclusion']='unknown'
        self.finding(row,'accepted_warning');self.bind_applicability()
        self.assertTrue(any('尚未完成评分' in e for e in self.check()['release_blockers']))

    def test_known_scoring_loss_is_warning_without_rejection(self):
        row=self.review['data']['core_matrix']['scoring'][0];row['conclusion']='partial'
        self.finding(row,'accepted_warning');self.bind_applicability()
        result=self.check()
        self.assertTrue(result['warnings']);self.assertEqual(result['release_blockers'],[])
        self.assertEqual(result['errors'],[])

    def test_explicit_required_proof_in_requirements_must_have_group(self):
        path=self.project/'artifacts/03-requirements.json'
        bidkit.atomic(path,{'project_id':'TEST-CORE','data':{'requirements':[
            {'id':'R1','mandatory':'yes','material_required':True}]}})
        snapshot=bidkit.snapshot(self.project,'reviews/snapshot.json')
        self.review['data']['reviewed_inputs_sha256']=snapshot['fingerprint']
        self.review['inputs'].append({'artifact_id':'TEST-REQUIREMENTS','revision':1,
                                     'relative_path':'artifacts/03-requirements.json',
                                     'sha256':bidkit.digest(path)})
        self.assertTrue(any('R1: 上游漏建' in e for e in self.check()['release_blockers']))

    def test_standalone_installed_skill_uses_bundled_schema(self):
        installed=Path(self.tmp.name)/'installed-skill'
        shutil.copytree(ROOT/'skills/bid-review-remediation',installed)
        path=self.project/'reviews/15-review.json';bidkit.atomic(path,self.review)
        args=[sys.executable,str(installed/'scripts/review_checks.py'),'check',
              '--project',str(self.project),'--review',str(path),'--snapshot',str(self.snapshot)]
        result=subprocess.run(args,capture_output=True,text=True,cwd=self.tmp.name)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertTrue(json.loads(result.stdout)['formal_release_ready'])
        row=self.review['data']['core_matrix']['scoring'][0];row['conclusion']='unknown'
        self.finding(row,'accepted_warning');self.bind_applicability();bidkit.atomic(path,self.review)
        result=subprocess.run(args,capture_output=True,text=True,cwd=self.tmp.name)
        self.assertEqual(result.returncode,1,result.stderr+result.stdout)
        self.assertTrue(json.loads(result.stdout)['release_blockers'])

    def test_pdf_dependency_unavailable_is_explicit_unreviewed_error(self):
        path=self.project/'work/test-only.pdf';path.write_bytes(b'%PDF-1.4 TEST ONLY')
        registered=bidkit.register_source(self.project,path,'main')
        source={k:registered[k] for k in ('source_id','revision','sha256')}
        source.update(location='P1',quote='TEST ONLY',kind='synthetic')
        with patch.dict(sys.modules,{'fitz':None}):
            with self.assertRaisesRegex(ValueError,'PyMuPDF未配置'):
                review_checks.source_text(self.project,source,{})


if __name__=='__main__':unittest.main()
