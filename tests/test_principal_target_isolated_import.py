"""Fresh isolated interpreter regression; admission and loop execution MOCKED.

Real module imports and isolated sys.path, but no positive UID transition,
configuration read, event loop, socket, broker lifecycle execution or model.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
CHILD=r"""
from pathlib import Path
import asyncio
from contextlib import redirect_stderr
import io
import json
import runpy
import sys
from unittest.mock import patch
root=Path(sys.argv[1]).resolve();mode=sys.argv[2]
assert sys.flags.isolated==1 and sys.flags.ignore_environment==1
assert str(root/'scripts') not in sys.path
assert 'run_provider_broker' not in sys.modules
sys.path.insert(0,str(root/'packages/claw-hermes'))
import principal_target as target
configuration=object();events=[];observed={};diagnostic=io.StringIO()
policy={'version':1,'enabled':True,'gatewayUid':23001,'brokerUid':23002,
        'socketGroupGid':23003,'hostUserNamespace':'user:[4026531837]'}
def prepare(*args):
    events.append('admission')
    if mode=='deny':raise target.TargetRejected('owned_admission_refusal')
    return configuration
def no_execution(coroutine):
    events.append('coroutine_received_not_executed')
    try:
        observed['source']=str(Path(coroutine.cr_code.co_filename).resolve())
        observed['name']=coroutine.cr_code.co_name
        observed['configIdentity']=coroutine.cr_frame.f_locals['config'] is configuration
        observed['output']=str(coroutine.cr_frame.f_locals['output'])
    finally:coroutine.close()
def audit(event,args):
    if event=='socket.__new__':raise AssertionError('no_socket_allowed_in_import_probe')
sys.addaudithook(audit)
argv=[str(root/'scripts/run_principal_broker_target.py'),'--principal',json.dumps(policy),
      '--config','/srv/owned/private.json','--config-sha256','a'*64,'--output','/srv/owned/output']
with (patch.object(target,'prepare',side_effect=prepare),
      patch.object(asyncio,'run',side_effect=no_execution),patch.object(sys,'argv',argv),
      redirect_stderr(diagnostic)):
    try:runpy.run_path(str(root/'scripts/run_principal_broker_target.py'),run_name='__main__')
    except SystemExit as exc:code=exc.code
    else:raise AssertionError('entrypoint_did_not_exit')
module=sys.modules.get('run_provider_broker')
print(json.dumps({'exitCode':code,'events':events,'observed':observed,
                 'moduleFile':str(Path(module.__file__).resolve()) if module else None,
                 'diagnostic':json.loads(diagnostic.getvalue()) if diagnostic.getvalue() else None,
                 'isolated':sys.flags.isolated,'admissionMocked':True,'brokerExecuted':False}))
"""

class IsolatedBrokerTargetImports(unittest.TestCase):
    def probe(self,mode='allow',shadow=False):
        with tempfile.TemporaryDirectory(prefix='alaz-target-import-') as tmp:
            cwd=Path(tmp);decoys=[]
            if shadow:
                for name in ('run_provider_broker.py','principal_target.py'):
                    path=cwd/name;path.write_text("raise AssertionError('cwd_shadow_executed')\n",encoding='utf-8')
                    decoys.append((path,path.read_bytes()))
            result=subprocess.run([sys.executable,'-I','-B','-c',CHILD,str(ROOT),mode],
                cwd=cwd,env={**os.environ,'PYTHONPATH':str(cwd)},
                stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',timeout=25)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stderr,'')
            self.assertTrue(all(p.read_bytes()==raw for p,raw in decoys))
            self.assertFalse((cwd/'__pycache__').exists())
            return json.loads(result.stdout)

    def assert_admitted_import(self,record):
        self.assertEqual(record['exitCode'],0,record)
        self.assertIsNone(record['diagnostic'])
        self.assertEqual(record['events'],['admission','coroutine_received_not_executed'])
        expected=str((ROOT/'scripts/run_provider_broker.py').resolve())
        self.assertEqual(record['moduleFile'],expected)
        self.assertEqual(record['observed']['source'],expected)
        self.assertEqual(record['observed']['name'],'serve')
        self.assertIs(record['observed']['configIdentity'],True)
        self.assertEqual(record['observed']['output'],str(Path('/srv/owned/output')))
        self.assertEqual(record['isolated'],1)
        self.assertIs(record['admissionMocked'],True)
        self.assertIs(record['brokerExecuted'],False)

    def test_isolated_target_resolves_existing_lifecycle_after_mocked_admission(self):
        self.assert_admitted_import(self.probe())

    def test_cwd_and_pythonpath_cannot_shadow_lifecycle_or_admission(self):
        self.assert_admitted_import(self.probe(shadow=True))

    def test_refused_admission_does_not_import_lifecycle_or_create_loop(self):
        record=self.probe('deny',shadow=True)
        self.assertEqual(record['exitCode'],2)
        self.assertEqual(record['events'],['admission'])
        self.assertIsNone(record['moduleFile'])
        self.assertEqual(record['observed'],{})
        self.assertEqual(record['diagnostic'],{'result':'REFUSED','phase':'principal_broker_target',
                          'reasonType':'TargetRejected','fallback':False})
        self.assertIs(record['brokerExecuted'],False)

if __name__=='__main__':unittest.main()
