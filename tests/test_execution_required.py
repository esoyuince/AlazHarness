"""Execution-required client tests against a loopback contract fixture, not Gateway."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ExecutionRequiredTests(unittest.TestCase):
    def run_case(self,name):
        process=subprocess.run(['node',str(ROOT/'tests/node/execution-required.mjs'),name],capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(process.returncode,0,process.stderr)
        data=json.loads(process.stdout);self.assertEqual(data['checks'],'PASS');self.assertEqual(data['scenario'],name)
    def test_rejects_untyped_option(self):self.run_case('invalid-option')
    def test_refuses_missing_execution_before_intent(self):self.run_case('missing')
    def test_boolean_is_not_version_one(self):self.run_case('boolean-version')
    def test_rechecks_execution_before_dispatch(self):self.run_case('downgrade')
    def test_no_http_for_preaborted_request(self):self.run_case('aborted')
    def test_required_header_and_verified_dispatch(self):self.run_case('guarded')
if __name__=='__main__':unittest.main()
