"""Pure host projection tests, not native process tests."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
CASES=('completed','missing-admission','bad-admission','missing-session','empty-session','missing-generation',
 'bool-generation','negative-generation','unsafe-generation','interrupted-unverified','cancelled-unverified','failed-unverified',
 'unknown','approval','in-progress','immutable','untrusted-flags-ignored','invalid')
class ProjectionTests(unittest.TestCase):
    def scenario(self,name):
        node=shutil.which('node')
        if not node:raise RuntimeError('Node required; no skips')
        p=subprocess.run([node,str(ROOT/'tests/node/recovery-projection.mjs'),name],capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),{'name':name,'result':'PASS'})
for name in CASES:
    def test(self,name=name):self.scenario(name)
    setattr(ProjectionTests,'test_'+name.replace('-','_'),test)
if __name__=='__main__':unittest.main()
