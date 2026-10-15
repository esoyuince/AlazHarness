"""Offline HostGateClient loopback tests. Does not load Hermes or aiohttp."""
from pathlib import Path
import os
import shutil
import subprocess
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('accessor','symbol','normal','bad-input','preaborted','missing','redirect','oversized','wrong-id','consumed','foreign','copied','lost-ack','server-refusal','bad-admission','concurrent','readonly')
class HostClientTests(unittest.TestCase):
    def scenario(self,name):
        node=shutil.which('node')
        if not node:raise RuntimeError('Node24 required')
        env={k:v for k,v in os.environ.items() if k.upper() in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP')}
        p=subprocess.run([node,str(ROOT/'tests/node/host-client-cases.mjs'),name],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[-4000:]);r=json.loads(p.stdout.strip().splitlines()[-1]);self.assertEqual(r['result'],'PASS');self.assertEqual(r['rawStartCalls'],0)
for name in SCENARIOS:
    def run(self,case=name):self.scenario(case)
    setattr(HostClientTests,'test_'+name.replace('-','_'),run)
if __name__=='__main__':unittest.main()
