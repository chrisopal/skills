"""Exercise actual isolated ZIPs; no adjacent suite checkout is available to the helper."""
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StandaloneWritingTests(unittest.TestCase):
    def test_isolated_packages_coordinate_and_merge_chapter_proposals(self):
        for number, skill in [(11, 'bid-technical-writing'), (17, 'bid-orchestrator')]:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with zipfile.ZipFile(ROOT / f'installable-zips/{number:02d}-{skill}.zip') as archive:
                    archive.extractall(root)
                package = root / skill
                project = root / 'project'
                shutil.copytree(ROOT / 'examples/smart-factory-demo', project)
                writing = json.loads((project / 'artifacts/11-technical-content.json').read_text())
                (project / 'work').mkdir(exist_ok=True)
                (project / 'work/project.json').write_text(json.dumps({'project_id': writing['project_id']}))
                script = '''import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'scripts'))
from writing_workspace import WritingWorkspace
from writing_batch import WritingBatch
p=Path(sys.argv[2])
w=WritingWorkspace(p,'artifacts/08-outline.json','artifacts/11-technical-content.json')
s=w.settings()
w.save_settings({'execution_mode':'parallel','max_parallel':2,
 'expected_revision':s['revision'],'expected_sha256':s['sha256']})
ids=[row['id'] for row in json.loads((p/'artifacts/08-outline.json').read_text())['data']['sections'][:2]]
b=WritingBatch(p,'standalone-fixture')
b.prepare(ids,effective_mode='parallel')
for section in ids:
 claim=b.claim(section)
 b.bind(section,'fixture-agent-'+section)
 context=json.loads((p/claim['context_path']).read_text())
 candidate={key:context[key] for key in ['batch_id','section_id','chapter_id','attempt','base_revision','base_sha256']}
 candidate.update(body_markdown='合成章节提案 '+section,requirement_ids=context['task']['requirement_ids'])
 proposal=p/claim['proposal_path']
 proposal.write_text(json.dumps(candidate,ensure_ascii=False))
 b.collect(section,claim['proposal_path'])
result=b.merge()
assert result['counts']['merged']==2 and result['merge']['downstream_refresh_required']
assert (Path(sys.argv[1])/'references/PARALLEL_WRITING.md').is_file()
print(json.dumps({'merged':2,'real_model':'NOT_RUN'}))
'''
                result = subprocess.run([shutil.which('python3.13') or 'python', '-c', script,
                                         str(package), str(project)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['merged'], 2)

    def test_each_editor_package_saves_with_the_writing_contract(self):
        for number, skill in [(11, 'bid-technical-writing'), (17, 'bid-orchestrator')]:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with zipfile.ZipFile(ROOT / f'installable-zips/{number:02d}-{skill}.zip') as archive:
                    archive.extractall(root)
                package = root / skill
                project = root / 'project'
                shutil.copytree(ROOT / 'examples/smart-factory-demo', project)
                writing = json.loads((project / 'artifacts/11-technical-content.json').read_text())
                (project / 'work').mkdir(exist_ok=True)
                (project / 'work/project.json').write_text(json.dumps({'project_id': writing['project_id']}))
                script = '''import sys,json
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])/'scripts'))
from writing_workspace import WritingWorkspace, WorkspaceError
w=WritingWorkspace(Path(sys.argv[2]), 'artifacts/08-outline.json', 'artifacts/11-technical-content.json')
s=w.state()
r=w.save({'chapter_id':s['chapter']['id'], 'expected_revision':s['writing']['revision'],
          'expected_sha256':s['writing']['sha256'], 'body_markdown':s['chapter']['body_markdown']+'\\n\\n合成编辑测试。'})
assert r['writing']['revision']==s['writing']['revision']+1
assert r['chapter']['state']=='proposed'
assert (Path(sys.argv[1])/'assets/ui/writing-editor.js').is_file()
settings=w.settings()
saved=w.save_settings({'visuals':{'enabled':True,'aspect_ratio':'4:3','max_images':3},
 'expected_revision':settings['revision'],'expected_sha256':settings['sha256']})
assert w.settings()['visuals']['aspect_ratio']=='4:3'
from render_writing_report import outline_html
assert '1.1' in outline_html([{'id':'a','number':'一','parent_id':None},
                            {'id':'b','number':'一.1','parent_id':'a'}])
assert (Path(sys.argv[1])/'assets/ui/writing-report.css').is_file()
print(json.dumps({'saved':True, 'revision':r['writing']['revision']}))
'''
                result = subprocess.run([shutil.which('python3.13') or 'python', '-c', script,
                                         str(package), str(project)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)['saved'])
