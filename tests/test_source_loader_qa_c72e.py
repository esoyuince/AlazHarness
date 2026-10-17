"""Regression: native plugin shim removes PRODUCT from sys.path after registration.
Fresh interpreter executes actual isolate/capture path; OS/native ports are synthetic.
"""
from pathlib import Path
import json
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
PROGRAM=r"""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import json,sys
root=Path(sys.argv[1]); product=root/'packages/claw-hermes'
sys.path[:0]=[str(product),str(root/'tests')]
import test_isolated_read as fx
case=fx.IsolatedReadContracts()
case.setUp()
try:
 case.iso.record_source = sys.argv[2]=='enabled'
 fake=ModuleType('tools');fake.approval_context=SimpleNamespace(
  _approval_session_id=SimpleNamespace(get=lambda:fx.RID),
  _approval_tool_call_id=SimpleNamespace(get=lambda:'native-call-path-qa'))
 sys.modules['tools']=fake
 # Native install_probe_plugin does this after calling actual_register(ctx).
 # Fixture/context creation above is deliberately already complete.
 sys.path=[p for p in sys.path if Path(p).resolve()!=product.resolve()]
 assert str(product) not in sys.path
 result=case.invoke()
 assert json.loads(result)=={'content':'native-payload'}
 assert len(case.runs)==1
 print('EXECUTED_WITHOUT_REGISTRATION_SEARCH_PATH')
finally:
 case.doCleanups()
"""


class SourceLoaderIndependentQA(unittest.TestCase):
    def run_case(self, enabled):
        return subprocess.run([sys.executable,'-I','-B','-c',PROGRAM,str(ROOT),
                               'enabled' if enabled else 'disabled'],
                              capture_output=True,text=True,encoding='utf-8',timeout=20)

    def test_capture_after_plugin_registration_path_is_removed(self):
        result=self.run_case(True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'EXECUTED_WITHOUT_REGISTRATION_SEARCH_PATH')

    def test_legacy_optout_after_registration_path_is_removed(self):
        result=self.run_case(False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'EXECUTED_WITHOUT_REGISTRATION_SEARCH_PATH')
