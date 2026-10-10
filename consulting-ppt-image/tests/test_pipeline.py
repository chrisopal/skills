"""Regression tests use only synthetic raster fixtures, not real client approvals."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ppt_pipeline as p

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.pack = p.load_json(ROOT / "examples/minimal/slide-content-pack.json")
        self.pack["approval_ref"] = "SYNTHETIC TEST FIXTURE ONLY — not a real approval"
        self.pack["version"] = "1.0.0-test"
        for slide in self.pack["slides"]:
            slide["review_status"] = "approved"
        self.pack_path = self.base / "pack.json"
        p.save_json(self.pack_path, self.pack)
        self.project = self.base / "project"
        p.init_project(self.pack_path, self.project, ROOT / "assets/white-inkgreen.json")

    def tearDown(self):
        self.tmp.cleanup()

    def image(self, label, size=(1600, 900)):
        path = self.base / f"{label}.png"
        seed = sum(ord(c) for c in label)
        Image.new("RGB", size, (seed % 200, (seed * 7) % 200, (seed * 13) % 200)).save(path)
        return path

    def ready(self, sid, version=1, label=None):
        v = p.register_image(self.project, sid, self.image(label or sid), version, "synthetic-test-only")
        r = {"slide_id": sid, "version": version, "artifact_sha256": v["sha256"],
             "reviewer": "UNIT TEST FIXTURE, NOT A REAL VISUAL REVIEW",
             "checks": {k: True for k in p.CHECKS}, "notes": "Synthetic fixture assertion only"}
        rp = self.base / f"{sid}-{version}-review.json"
        p.save_json(rp, r)
        p.record_review(self.project, rp)
        p.select_image(self.project, sid, version, "SYNTHETIC TEST SELECTION")
        return v

    def errors(self, pack):
        return "\n".join(p.check_pack(pack)["errors"])

    def test_01_structure_valid(self):
        self.assertFalse(p.check_pack(self.pack)["errors"])

    def test_02_page_count_35_but_30_blocks(self):
        q = copy.deepcopy(self.pack); q["page_budget"] = 35
        self.assertIn("page_budget=35", self.errors(q))

    def test_03_missing_or_duplicate_order_blocks(self):
        q = copy.deepcopy(self.pack); q["slides"][2]["order"] = 2
        self.assertIn("orders", self.errors(q))

    def test_04_section_interruption_blocks(self):
        q = copy.deepcopy(self.pack); q["slides"][2]["section"] = "context"
        self.assertIn("interrupted", self.errors(q))

    def test_05_exact_duplicate_purpose_blocks(self):
        q = copy.deepcopy(self.pack); q["slides"][1]["purpose_id"] = q["slides"][0]["purpose_id"]
        self.assertIn("Duplicate purpose_id", self.errors(q))

    def test_06_early_closing_blocks(self):
        q = copy.deepcopy(self.pack); q["slides"][0]["story_role"] = "closing"
        self.assertIn("before the deck ends", self.errors(q))

    def test_07_unknown_evidence_blocks(self):
        q = copy.deepcopy(self.pack); q["slides"][0]["evidence_ids"] = ["made-up-evidence"]
        self.assertIn("unknown evidence", self.errors(q))

    def test_08_benchmark_entity_mismatch_blocks(self):
        q = copy.deepcopy(self.pack)
        q["slides"][0]["benchmark"] = {"entity_id": "example-company-a"}
        q["slides"][0]["evidence_ids"] = ["e1"]
        q["citation_index"] = [{"id":"e1","title":"test","type":"official_screenshot",
                                 "locator":"test only","verification_status":"verified","entity_id":"example-company-b"}]
        self.assertIn("benchmark entity", self.errors(q))

    def test_09_milestone_and_fs_dependency_blocks(self):
        q = copy.deepcopy(self.pack)
        q["schedule"] = {"milestones":[{"id":"go-live","date":"2027-07-01"}],
         "tasks":[{"id":"test","start":"2027-06-01","end":"2027-08-01","must_finish_before":["go-live"]},
                  {"id":"start","start":"2027-07-01","end":"2027-07-02","depends_on":["test"]}]}
        e = self.errors(q)
        self.assertIn("required milestone", e); self.assertIn("FS dependency", e)

    def test_10_schedule_cycle_blocks(self):
        q = copy.deepcopy(self.pack)
        q["schedule"] = {"tasks":[{"id":"a","start":"2027-01-01","end":"2027-01-02","depends_on":["b"]},
                                  {"id":"b","start":"2027-01-01","end":"2027-01-02","depends_on":["a"]}]}
        self.assertIn("cycle", self.errors(q))

    def test_11_bad_aspect_ratio_blocks(self):
        with self.assertRaises(p.PipelineError):
            p.register_image(self.project, "S001", self.image("bad", (1600,1600)), 1, "test")

    def test_12_missing_review_prevents_selection(self):
        p.register_image(self.project, "S001", self.image("a"), 1, "test")
        with self.assertRaises(p.PipelineError):
            p.select_image(self.project,"S001",1,"test")

    def test_13_wrong_review_hash_blocks(self):
        p.register_image(self.project,"S001",self.image("a"),1,"test")
        review={"slide_id":"S001","version":1,"artifact_sha256":"0"*64,"reviewer":"test",
                "checks":{k:True for k in p.CHECKS},"notes":"test"}
        path=self.base/'review.json'; p.save_json(path,review)
        with self.assertRaises(p.PipelineError): p.record_review(self.project,path)

    def test_14_image_bytes_changed_blocks_audit(self):
        v=self.ready("S001")
        (self.project/v["path"]).write_bytes(b"modified")
        self.assertTrue(p.audit(self.project,"final","1")["errors"])

    def test_15_mutation_of_pack_or_style_detected(self):
        sp=self.project/'style-profile.json'; style=p.load_json(sp);style['palette']['title']='#0000FF';p.save_json(sp,style)
        with self.assertRaises(p.PipelineError): p.get_project(self.project)

    def test_16_immutable_versions(self):
        self.ready("S001")
        with self.assertRaises(p.PipelineError):
            p.register_image(self.project,"S001",self.image("b"),1,"test")

    def test_17_explicit_version_wins_over_newer_file(self):
        v=self.ready("S001",1,"a")
        p.register_image(self.project,"S001",self.image("newer"),2,"test")
        output=self.base/'partial.pptx'
        r=p.assemble(self.project,output,"1")
        self.assertEqual(r['embedded_image_sha256'],[v['sha256']])
        self.assertEqual(r['scope'],'explicit_partial:1')

    def test_18_complete_pptx_one_picture_and_hashes(self):
        expected=[self.ready(f'S{i:03d}')["sha256"] for i in range(1,4)]
        receipt=p.assemble(self.project,self.base/'complete.pptx')
        self.assertEqual(receipt['slide_count'],3)
        self.assertEqual(receipt['embedded_image_sha256'],expected)
        self.assertTrue(receipt['original_image_bytes_preserved'])

    def test_19_full_export_missing_page_blocks(self):
        self.ready("S001")
        with self.assertRaises(p.PipelineError):
            p.assemble(self.project,self.base/'incomplete.pptx')

    def test_20_sync_invalidates_changed_image_keeps_history(self):
        self.ready("S001"); self.ready("S002")
        q=copy.deepcopy(self.pack);q['version']='1.0.1-test';q['slides'][0]['title']='改变后的测试标题'
        path=self.base/'new.json';p.save_json(path,q)
        r=p.sync_pack(self.project,path,'TEST change reference')
        m,_,_=p.get_project(self.project)
        self.assertIn('S001',r['invalidated_or_new'])
        self.assertIsNone(m['pages']['S001']['selected_version'])
        self.assertEqual(m['pages']['S002']['selected_version'],1)
        self.assertEqual(len(m['pages']['S001']['versions']),1)

    def test_21_duplicate_raster_blocks_final(self):
        self.ready("S001",1,"same");self.ready("S002",1,"same")
        self.assertIn('Identical raster', '\n'.join(p.audit(self.project,'final','1-2')['errors']))

    def test_22_three_page_draft_not_production_ready(self):
        q=p.load_json(ROOT/'examples/minimal/slide-content-pack.json')
        self.assertTrue(p.check_pack(q,'render')['errors'])

    def test_23_generic_outline_not_claimed_complete(self):
        q=p.load_json(ROOT/'examples/generic-35/slide-content-pack.outline.json')
        self.assertEqual(q['page_budget'],35)
        self.assertFalse(p.check_pack(q)['errors'])
        self.assertTrue(p.check_pack(q,'render')['errors'])

    def test_24_separate_prompts_for_each_slide(self):
        result=p.make_plan(self.project,'1-3')
        self.assertEqual(result['count'],3)
        paths=[x['prompt'] for x in result['queue']]
        self.assertEqual(len(set(paths)),3)
        for path in paths:
            self.assertTrue(Path(path).is_file())

    def test_25_diagram_dangling_edge_blocks(self):
        q=copy.deepcopy(self.pack);q['slides'][1]['diagram_spec']['edges'][0]['to']='missing'
        self.assertIn('undeclared node',self.errors(q))

    def test_26_invalid_json_reports_error(self):
        path=self.base/'bad.json';path.write_text('{',encoding='utf-8')
        with self.assertRaises(p.PipelineError):p.load_json(path)

    def test_27_reexport_does_not_overwrite(self):
        self.ready('S001');out=self.base/'partial.pptx';p.assemble(self.project,out,'1')
        with self.assertRaises(p.PipelineError):p.assemble(self.project,out,'1')

    def test_28_manifest_path_cannot_escape_project(self):
        with self.assertRaises(p.PipelineError):p.safe_path(self.project,'../outside.png')

    def test_29_failed_rereview_removes_selection(self):
        v=self.ready('S001')
        review={"slide_id":"S001","version":1,"artifact_sha256":v["sha256"],"reviewer":"test",
                "checks":{k:True for k in p.CHECKS},"notes":"Synthetic failed review"}
        review['checks']['text_fidelity']=False
        path=self.base/'failed-review.json';p.save_json(path,review)
        result=p.record_review(self.project,path)
        self.assertEqual(result['status'],'qa_failed')
        m,_,_=p.get_project(self.project)
        self.assertIsNone(m['pages']['S001']['selected_version'])
        with self.assertRaises(p.PipelineError):p.select_image(self.project,'S001',1,'test')

    def test_30_theme_mismatch_is_rejected(self):
        q=copy.deepcopy(self.pack);q['theme_profile']='different-theme'
        path=self.base/'theme-mismatch.json';p.save_json(path,q)
        with self.assertRaises(p.PipelineError):
            p.init_project(path,self.base/'different',ROOT/'assets/white-inkgreen.json')

    def test_31_evidence_revision_invalidates_page(self):
        style=p.load_json(ROOT/'assets/white-inkgreen.json')
        q=copy.deepcopy(self.pack)
        q['citation_index']=[{'id':'ev','title':'first','type':'attachment','locator':'test','verification_status':'provided'}]
        q['slides'][0]['evidence_ids']=['ev']
        a=p.signature(q,style,q['slides'][0])
        q['citation_index'][0]['title']='second'
        b=p.signature(q,style,q['slides'][0])
        self.assertNotEqual(a,b)

    def test_32_content_change_outside_sync_detected(self):
        path=self.project/'slide-content-pack.json';q=p.load_json(path)
        q['slides'][0]['title']='Unapproved mutation';p.save_json(path,q)
        with self.assertRaises(p.PipelineError):p.get_project(self.project)

if __name__=='__main__':
    unittest.main(verbosity=2)
