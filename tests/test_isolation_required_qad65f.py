"""Independent isolated-required client contracts, loopback fixtures not Gateway."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]

class IsolatedRequiredIndependentTests(unittest.TestCase):
    def run_case(self,name):
        p=subprocess.run(['node',str(ROOT/'tests/node/isolation-required-qad65f.mjs'),name],cwd=ROOT,
          capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(p.stdout);self.assertEqual(data['scenario'],name);self.assertEqual(data['result'],'PASS')
        self.assertIs(data['raw_start_fallback'],False)
    def test_untyped_requirement_refused(self):self.run_case('invalid-option')
    def test_disabling_execution_conflicts_with_isolation(self):self.run_case('conflicting-execution')
    def test_missing_isolation_has_no_intent_or_dispatch(self):self.run_case('missing-isolation')
    def test_wrong_backend_has_no_intent(self):self.run_case('wrong-backend')
    def test_boolean_is_not_version(self):self.run_case('boolean-version')
    def test_isolation_also_requires_execution_gate(self):self.run_case('missing-execution')
    def test_downgrade_between_prepare_dispatch_refused(self):self.run_case('downgrade')
    def test_required_headers_one_dispatch_and_no_raw_fallback(self):self.run_case('guarded')

if __name__=='__main__':unittest.main()
