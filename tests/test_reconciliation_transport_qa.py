"""Independent real-loopback adapter checks, not native Gateway execution."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
CASES=['terminal-without-proof', 'partial-native-tuple', 'invalid-generation', 'unknown', 'approval', 'retained-failed', 'queued-single-read', 'missing-run', 'denied-run', 'server-failure-no-retry', 'malformed-response', 'wrong-run-id', 'contradictory-http', 'resume-deadline-no-post', 'resume-abort-no-post', 'preaborted-resume', 'observer-cannot-resolve', 'valid-terminal', 'contradictory-classifier', 'blank-session-classifier', 'coerced-id-classifier', 'classifier-no-retry']

class TransportReconciliationQA(unittest.TestCase):
    pass

def make_case(name):
    def check(self):
        node=shutil.which('node')
        self.assertIsNotNone(node, 'Node is required; no skipped acceptance')
        completed=subprocess.run([node,str(ROOT/'scripts/qa/reconciliation_transport.mjs'),name],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
        receipt=json.loads(completed.stdout)
        self.assertEqual(receipt['scenario'],name)
        self.assertEqual(receipt['result'],'PASS')
    return check
for case in CASES:setattr(TransportReconciliationQA,'test_'+case.replace('-','_'),make_case(case))
if __name__=='__main__':unittest.main()
