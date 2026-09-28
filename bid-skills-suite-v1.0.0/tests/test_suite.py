"""Offline engineering checks; synthetic confirmation fixtures are never real approval."""
import copy, hashlib, json, sys, tempfile, unittest, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import bidkit, check_suite, extract_sources
from validate_output import validate
from bundle_delivery import bundle
REG=bidkit.read(ROOT/'registry.json');DEMO=ROOT/'examples/smart-factory-demo'
def sample(n):return bidkit.read(ROOT/'skills'/REG['skills'][n-1]['id']/'assets/example.output.json')
def schema(n):return bidkit.read(ROOT/'skills'/REG['skills'][n-1]['id']/'assets/output.schema.json')

class StructureTests(unittest.TestCase):
    def test_package_structure(self):self.assertEqual(check_suite.check()['errors'],[])
    def test_changed_installable_zip_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);skill=root/'skills/bid-test';skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('current',encoding='utf-8')
            packages=root/'installable-zips';packages.mkdir()
            with zipfile.ZipFile(packages/'01-bid-test.zip','w') as out:out.writestr('bid-test/SKILL.md','stale')
            errors=check_suite.check_installable_zips(root,{'skills':[{'sequence':1,'id':'bid-test'}]})
            self.assertTrue(any('内容与技能目录不一致' in error for error in errors))
    def test_examples_validate(self):
        for n in range(1,18):
            with self.subTest(skill=n):self.assertEqual(validate(sample(n),schema(n)),[])
    def test_source_quotes_hashes_and_lines(self):
        sources={'SRC-001':(DEMO/'inputs/synthetic-tender.md').read_bytes(),'SRC-002':(DEMO/'inputs/synthetic-supplier.md').read_bytes()}
        def walk(x):
            if isinstance(x,dict):
                if all(k in x for k in ('source_id','sha256','quote','location')):
                    raw=sources[x['source_id']];self.assertEqual(x['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(raw.decode().splitlines()[int(x['location'][1:])-1],x['quote'])
                for v in x.values():walk(v)
            elif isinstance(x,list):
                for v in x:walk(v)
        for n in range(1,18):walk(sample(n))
    def test_upstream_hashes(self):
        for n in range(1,18):
            for x in sample(n)['inputs']:self.assertEqual(bidkit.digest(DEMO/x['relative_path']),x['sha256'])
    def test_profiles_validate(self):
        from jsonschema import Draft202012Validator
        v=Draft202012Validator(bidkit.read(ROOT/'profiles/profile.schema.json'))
        for p in (ROOT/'profiles').glob('*/*.json'):self.assertEqual(list(v.iter_errors(bidkit.read(p))),[])
    def test_duplicate_ids_rejected(self):
        x=sample(3);x['data']['requirements'].append(copy.deepcopy(x['data']['requirements'][0]));self.assertTrue(validate(x,schema(3)))
    def test_explicit_without_source_rejected(self):
        x=sample(3);x['data']['requirements'][0]['sources']=[];self.assertTrue(validate(x,schema(3)))
    def test_ready_with_blockers_rejected(self):
        x=sample(3);x.update(status='ready',blockers=['not resolved']);self.assertTrue(validate(x,schema(3)))
    def test_acceptance_without_confirmation_rejected(self):
        x=sample(11);x['data']['chapters'][0]['state']='accepted';self.assertTrue(validate(x,schema(11)))
    def test_evidence_count_rejected(self):
        x=sample(9);x['data']['selections'][0].update(state='accepted',confirmation_ref='TEST-ONLY',required_count=2);self.assertTrue(validate(x,schema(9)))
    def test_extra_field_rejected(self):
        x=sample(3);x['data']['auto_approve']=True;self.assertTrue(validate(x,schema(3)))
    def test_invalid_release_recommendation_rejected(self):
        x=sample(15);x['data']['release_recommendation']='eligible_for_user_release';self.assertTrue(validate(x,schema(15)))

class FileTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=self.root/'project';bidkit.init_project(self.p,'TEST-ONLY')
    def tearDown(self):self.tmp.cleanup()
    def test_init_refuses_overwrite(self):
        with self.assertRaises(ValueError):bidkit.init_project(self.p,'OTHER')
    def test_register_preserves_bytes(self):
        source=self.root/'a.md';source.write_text('原文\n',encoding='utf-8');x=bidkit.register_source(self.p,source,'main');self.assertEqual(x['sha256'],bidkit.digest(source));self.assertEqual((self.p/x['relative_path']).read_bytes(),source.read_bytes())
    def test_register_collision_does_not_delete_file(self):
        source=self.root/'a.md';source.write_text('new');target=self.p/'inputs/SRC-001-a.md';target.write_text('KEEP')
        with self.assertRaises(ValueError):bidkit.register_source(self.p,source,'main')
        self.assertEqual(target.read_text(),'KEEP')
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):bidkit.safe(self.p,'../out')
    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError):bidkit.safe(self.p,str(self.root/'out'))
    def test_snapshot_current(self):
        bidkit.snapshot(self.p,'reviews/snap.json');self.assertTrue(bidkit.verify_snapshot(self.p,self.p/'reviews/snap.json')['current'])
    def test_snapshot_changed(self):
        target=self.p/'artifacts/a.md';target.write_text('old');bidkit.snapshot(self.p,'reviews/snap.json');target.write_text('new');self.assertFalse(bidkit.verify_snapshot(self.p,self.p/'reviews/snap.json')['current'])
    def test_snapshot_added(self):
        bidkit.snapshot(self.p,'reviews/snap.json');(self.p/'inputs/addendum.md').write_text('new');self.assertFalse(bidkit.verify_snapshot(self.p,self.p/'reviews/snap.json')['current'])
    def test_snapshot_deleted(self):
        target=self.p/'artifacts/a.md';target.write_text('old');bidkit.snapshot(self.p,'reviews/snap.json');target.unlink();self.assertFalse(bidkit.verify_snapshot(self.p,self.p/'reviews/snap.json')['current'])
    def test_snapshot_cannot_be_self_referential(self):
        with self.assertRaises(ValueError):bidkit.snapshot(self.p,'artifacts/snap.json')
    def test_snapshot_tampering(self):
        bidkit.snapshot(self.p,'reviews/snap.json');target=self.p/'reviews/snap.json';x=bidkit.read(target);x['fingerprint']='0'*64;bidkit.atomic(target,x)
        with self.assertRaises(ValueError):bidkit.verify_snapshot(self.p,target)
    def test_native_text_line(self):
        source=self.root/'a.md';source.write_text('# 标题\n采购2台设备\n',encoding='utf-8');bidkit.register_source(self.p,source,'main');x=extract_sources.extract(self.p,'TEST-ONLY');self.assertEqual(validate(x,schema(1)),[]);self.assertEqual(x['data']['blocks'][1]['location'],'L2');self.assertEqual(x['status'],'needs_review')
    def test_extraction_rejects_other_project_id(self):
        with self.assertRaises(ValueError):extract_sources.extract(self.p,'OTHER-PROJECT')
    def test_changed_original_rejected(self):
        source=self.root/'a.md';source.write_text('old');x=bidkit.register_source(self.p,source,'main');(self.p/x['relative_path']).write_text('new')
        with self.assertRaises(ValueError):extract_sources.extract(self.p,'TEST-ONLY')
    def test_unsupported_format_is_blocked(self):
        source=self.root/'a.doc';source.write_bytes(b'unsupported');bidkit.register_source(self.p,source,'main');x=extract_sources.extract(self.p,'TEST-ONLY');self.assertEqual(x['status'],'blocked');self.assertTrue(x['blockers'])
    def test_profiles_keep_namespaces(self):
        x=bidkit.compose_profiles([ROOT/'profiles/procurement/enterprise-procurement.json',ROOT/'profiles/domain/equipment-supply.json'],self.root/'profiles.json');self.assertEqual(len(x['profiles']),2);self.assertEqual(x['status'],'needs_review')
    def test_duplicate_profiles_rejected(self):
        p=ROOT/'profiles/domain/smart-factory.json'
        with self.assertRaises(ValueError):bidkit.compose_profiles([p,p],self.root/'profiles.json')

class MatrixTests(unittest.TestCase):
    def test_simple_total(self):self.assertTrue(bidkit.scoring_check(sample(4))['arithmetic_valid'])
    def test_wrong_total(self):
        x=sample(4);x['data']['declared_total']=99;self.assertFalse(bidkit.scoring_check(x)['arithmetic_valid'])
    def test_orphan_score(self):
        x=sample(4);x['data']['items'][0]['parent_id']='missing';self.assertFalse(bidkit.scoring_check(x)['arithmetic_valid'])
    def test_cycle_score(self):
        x=sample(4);x['data']['items'][0]['parent_id']='S-002';x['data']['items'][1]['parent_id']='S-001';self.assertFalse(bidkit.scoring_check(x)['arithmetic_valid'])
    def test_capped_score_requires_manual(self):
        x=sample(4);x['data']['items'][0]['aggregation']='capped';x['data']['declared_total']=80;r=bidkit.scoring_check(x);self.assertTrue(r['arithmetic_valid']);self.assertTrue(r['manual_checks'])
    def test_complete_mapping(self):
        x=bidkit.coverage_check(*[DEMO/'artifacts'/n for n in ('03-requirements.json','04-scoring.json','05-compliance.json','08-outline.json')]);self.assertTrue(x['mapping_valid'])
    def test_mapping_missing_and_cycle(self):
        with tempfile.TemporaryDirectory() as work:
            x=sample(8);x['data']['sections'][0]['parent_id']='SEC-02';x['data']['sections'][1]['parent_id']='SEC-01';x['data']['sections'][-1]['compliance_ids']=[];p=Path(work)/'out.json';bidkit.atomic(p,x)
            result=bidkit.coverage_check(DEMO/'artifacts/03-requirements.json',DEMO/'artifacts/04-scoring.json',DEMO/'artifacts/05-compliance.json',p);self.assertFalse(result['mapping_valid']);self.assertIn('C-001',result['missing'])

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=self.root/'project';bidkit.init_project(self.p,'TEST-ONLY');(self.p/'artifacts/a.md').write_text('synthetic')
        self.snap=self.p/'reviews/snapshot.json';snap=bidkit.snapshot(self.p,'reviews/snapshot.json');self.review=self.p/'reviews/review.json';x=sample(15);x.update(project_id='TEST-ONLY',status='ready',blockers=[]);x['data'].update(review_scope='full',reviewed_inputs_sha256=snap['fingerprint'],findings=[],checks=[{'area':'TEST-ONLY','state':'passed','note':'Synthetic test fixture.'}],human_approval_ref='TEST-ONLY',release_recommendation='eligible_for_user_release');bidkit.atomic(self.review,x)
        self.approval=self.p/'confirmations/release.json';bidkit.atomic(self.approval,{'project_id':'TEST-ONLY','decision':'approved','actor':'TEST-ONLY','decided_at':'2026-09-27T00:00:00Z','authorization_ref':'TEST-ONLY','review_sha256':bidkit.digest(self.review),'snapshot_fingerprint':snap['fingerprint']})
    def tearDown(self):self.tmp.cleanup()
    def test_mechanical_gate(self):self.assertEqual(bidkit.release_gate(self.p,self.review,self.snap,self.approval)['mechanical_gate'],'passed')
    def test_review_from_other_project_blocks(self):
        x=bidkit.read(self.review);x['project_id']='OTHER-PROJECT';bidkit.atomic(self.review,x)
        approval=bidkit.read(self.approval);approval['review_sha256']=bidkit.digest(self.review);bidkit.atomic(self.approval,approval)
        with self.assertRaises(ValueError):bidkit.release_gate(self.p,self.review,self.snap,self.approval)
    def test_approval_from_other_project_blocks(self):
        x=bidkit.read(self.approval);x['project_id']='OTHER-PROJECT';bidkit.atomic(self.approval,x)
        with self.assertRaises(ValueError):bidkit.release_gate(self.p,self.review,self.snap,self.approval)
    def test_snapshot_from_other_project_blocks(self):
        x=bidkit.read(self.snap);x['project_id']='OTHER-PROJECT';bidkit.atomic(self.snap,x)
        with self.assertRaises(ValueError):bidkit.release_gate(self.p,self.review,self.snap,self.approval)
    def test_pending_approval_blocks(self):
        x=bidkit.read(self.approval);x['decision']='pending';bidkit.atomic(self.approval,x)
        with self.assertRaises(ValueError):bidkit.release_gate(self.p,self.review,self.snap,self.approval)
    def test_changed_content_blocks(self):
        (self.p/'artifacts/a.md').write_text('modified')
        with self.assertRaises(ValueError):bidkit.release_gate(self.p,self.review,self.snap,self.approval)
    def test_changed_review_blocks(self):
        x=bidkit.read(self.review);x['summary']='modified review';bidkit.atomic(self.review,x)
        with self.assertRaises(ValueError):bidkit.release_gate(self.p,self.review,self.snap,self.approval)
    def test_internal_file_cannot_be_bundled(self):
        x=sample(16);x.update(status='ready',blockers=[]);target=self.p/'artifacts/a.md';x['data'].update(reviewed_inputs_sha256=bidkit.read(self.snap)['fingerprint'],delivery_status='ready',signature_state='not_applicable',user_release_authorization_ref='TEST-ONLY',remaining_actions=[],artifacts=[{'id':'EXP-TEST','relative_path':'artifacts/a.md','format':'docx','sha256':bidkit.digest(target),'bytes':target.stat().st_size,'text_qa':'passed','visual_qa':'passed'}]);manifest=self.p/'deliverables/manifest.json';bidkit.atomic(manifest,x)
        with self.assertRaises(ValueError):bundle(self.p,self.review,self.snap,self.approval,manifest,self.root/'out.zip')
    def test_manifest_from_other_project_blocks(self):
        x=sample(16);x.update(project_id='OTHER-PROJECT',status='ready',blockers=[])
        target=self.p/'artifacts/a.md'
        x['data'].update(reviewed_inputs_sha256=bidkit.read(self.snap)['fingerprint'],delivery_status='ready',signature_state='not_applicable',user_release_authorization_ref='TEST-ONLY',remaining_actions=[],artifacts=[{'id':'EXP-TEST','relative_path':'artifacts/a.md','format':'docx','sha256':bidkit.digest(target),'bytes':target.stat().st_size,'text_qa':'passed','visual_qa':'passed'}])
        manifest=self.p/'deliverables/manifest.json';bidkit.atomic(manifest,x)
        with self.assertRaisesRegex(ValueError,'交付清单项目与工作目录不一致'):
            bundle(self.p,self.review,self.snap,self.approval,manifest,self.root/'out.zip')

if __name__=='__main__':unittest.main()
