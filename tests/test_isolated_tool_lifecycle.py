"""Faulted Docker transport tests; no Docker process is run by this module."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import isolated_tool as m
from test_isolated_tool import inspection,P,CID

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve();self.cap=self.root/'capsule';self.cap.mkdir()
        (self.cap/'program.py').write_text('print(42)\n')
        self.runner=m.IsolatedToolRunner(root=self.root,capsule=self.cap,receipt_dir=self.root/'receipt',policy=P)
    def raw(self):
        raw=inspection();raw['Name']='/alaz-isolated-'+self.runner.owner
        raw['Config']['Labels'][m.OWNER_LABEL]=self.runner.owner
        return raw
    def simulated_start(self, *, cli_exit=125, never_started=True):
        raw=self.raw()
        if not never_started:raw['State']['Status']='exited'
        calls=[]
        def docker(args,**kwargs):
            calls.append(args)
            if args[:2]==['image','inspect']:value=[{'Id':P.image,'Os':'linux','Config':{}}]
            elif args[0]=='create':return SimpleNamespace(stdout=(CID+'\n').encode())
            elif args[0]=='inspect':value=[raw]
            else:return SimpleNamespace(stdout=b'',stderr=b'',returncode=0)
            return SimpleNamespace(stdout=json.dumps(value).encode(),stderr=b'',returncode=0)
        # The transport fixture returns created at preflight; then desired final state.
        before=copy.deepcopy(raw);before['State']['Status']='created'
        phases=iter([before,raw,raw])
        def inspect(_):return copy.deepcopy(next(phases))
        proc=SimpleNamespace(stdout=io.BytesIO(b''),stderr=io.BytesIO(b'controlled client failure'),returncode=cli_exit,
            poll=lambda:cli_exit,wait=lambda **kw:cli_exit,kill=lambda:None)
        original=Path
        def paths(*a,**kw):
            if a==('/proc/self/ns/net',):return SimpleNamespace(exists=lambda:True)
            return original(*a,**kw)
        with patch.object(m,'os',SimpleNamespace(name='posix')),patch.object(m,'Path',paths),\
             patch.object(m,'create_arguments',return_value=['create']),\
             patch.object(m,'validate_container',return_value={}),\
             patch.object(self.runner,'_docker',docker),patch.object(self.runner,'_inspect',inspect),\
             patch.object(m.subprocess,'Popen',return_value=proc):
            result=self.runner.run()
        return result,calls
    def test_failed_docker_start_never_means_completed_tool(self):
        result,calls=self.simulated_start()
        self.assertNotEqual(result['result'],'completed')
        self.assertTrue(result['exit']['neverStarted']);self.assertTrue(result['exit']['removed'])
        self.assertFalse(result['automaticRetry'])
    def test_lost_attach_status_not_proof_of_success(self):
        result,_=self.simulated_start(cli_exit=125,never_started=False)
        self.assertNotEqual(result['result'],'completed')
        self.assertFalse(result['automaticRetry'])
    def test_foreign_container_is_never_killed_or_removed(self):
        raw=self.raw();raw['Config']['Labels'][m.OWNER_LABEL]='f'*32
        with patch.object(self.runner,'_inspect',return_value=raw),patch.object(self.runner,'_docker') as act:
            with self.assertRaisesRegex(m.IsolationError,'container_ownership_mismatch'):self.runner._close()
            act.assert_not_called()
    def test_wrong_id_never_killed_or_removed(self):
        self.runner.cid=CID;raw=self.raw();raw['Id']='d'*64
        with patch.object(self.runner,'_inspect',return_value=raw),patch.object(self.runner,'_docker') as act:
            with self.assertRaisesRegex(m.IsolationError,'container_identity_mismatch'):self.runner._close()
            act.assert_not_called()
    def test_unevidenced_exit_never_removed(self):
        raw=self.raw();raw['State'].update(Status='running',Running=True,Pid=100)
        self.runner.receipt_dir.mkdir()
        with patch.object(self.runner,'_inspect',return_value=raw),patch.object(self.runner,'_docker',return_value=SimpleNamespace(stdout=b'')) as act:
            with self.assertRaisesRegex(m.IsolationError,'container_exit_unconfirmed'):self.runner._close()
            self.assertNotIn('rm',[c.args[0][0] for c in act.call_args_list])
    def test_created_container_does_not_wait_for_execution(self):
        raw=self.raw();self.runner.receipt_dir.mkdir()
        with patch.object(self.runner,'_inspect',return_value=raw),patch.object(self.runner,'_docker',return_value=SimpleNamespace(stdout=b'')) as act:
            result=self.runner._close()
            self.assertTrue(result['neverStarted']);self.assertTrue(result['removed'])
            self.assertNotIn('wait',[c.args[0][0] for c in act.call_args_list])
    def test_removal_must_be_confirmed(self):
        raw=self.raw();self.runner.receipt_dir.mkdir()
        def act(args,**kw):return SimpleNamespace(stdout=CID.encode() if args[0]=='ps' else b'')
        with patch.object(self.runner,'_inspect',return_value=raw),patch.object(self.runner,'_docker',act):
            with self.assertRaisesRegex(m.IsolationError,'container_removal_unconfirmed'):self.runner._close()
    def test_changed_capsule_refused_before_daemon(self):
        (self.cap/'program.py').write_text('print(43)')
        original=Path
        def paths(*a,**kw):
            return SimpleNamespace(exists=lambda:True) if a==('/proc/self/ns/net',) else original(*a,**kw)
        with patch.object(m,'os',SimpleNamespace(name='posix')),patch.object(m,'Path',paths),patch.object(self.runner,'_docker') as act:
            with self.assertRaisesRegex(m.IsolationError,'capsule_changed'):self.runner.run()
            act.assert_not_called()
    def test_engine_timeout_is_unknown_not_replayed(self):
        self.runner._base=['docker'];self.runner._env={}
        with patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixture',10)) as act:
            with self.assertRaisesRegex(m.IsolationError,'docker_operation_outcome_unknown'):self.runner._docker(['create'])
            self.assertEqual(act.call_count,1)
    def test_missing_engine_never_falls_back_to_host(self):
        self.runner._base=['docker'];self.runner._env={}
        with patch.object(m.subprocess,'run',side_effect=FileNotFoundError) as act:
            with self.assertRaisesRegex(m.IsolationError,'docker_unavailable'):self.runner._docker(['create'])
            self.assertEqual(act.call_count,1)
    def test_daemon_diagnostics_not_exposed(self):
        self.runner._base=['docker'];self.runner._env={}
        fake=SimpleNamespace(returncode=125,stdout=b'',stderr=b'PRIVATE_FIXTURE_DIAGNOSTIC')
        with patch.object(m.subprocess,'run',return_value=fake):
            with self.assertRaisesRegex(m.IsolationError,'^docker_operation_failed$'):self.runner._docker(['create'])
    def test_path_symlink_refused(self):
        # Hardlinks work without Windows symlink privileges; no OS permission change.
        import os
        os.link(self.cap/'program.py',self.cap/'alias.py')
        with self.assertRaisesRegex(m.IsolationError,'hardlinked_capsule_entry'):m.checked_capsule(self.root,self.cap)

if __name__=='__main__':unittest.main()
