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
print(json.dumps({'saved':True, 'revision':r['writing']['revision']}))
'''
                result = subprocess.run([shutil.which('python3.13') or 'python', '-c', script,
                                         str(package), str(project)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)['saved'])
