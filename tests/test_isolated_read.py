"""Read-bridge contracts: real ledger/guards, fabricated SQLite/native/Docker ports.
Not native Gateway, native provider registry or actual Docker execution evidence.
"""
from contextlib import closing
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import isolated_read as m
from execution_budget import ExecutionLedger,ExecutionPolicy
from recovery_inspector import LocalRecoveryContext,_json
from test_reconciliation_inspector_qa import StoreFixture,RID,TOKEN
from test_execution_budget import TestOwner


class IsolatedReadContracts(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve();self.home=self.root/'profile';self.home.mkdir()
        self.f=StoreFixture(self.home);self.f.sql("UPDATE session_admissions SET status='started',outcome=NULL,owner_epoch=2")
        self.context=LocalRecoveryContext(self.home,TOKEN,2,'owner-two')
        self.policy=ExecutionPolicy('chosen-model',2,5,100,20,240,1000,1000000,2000000)
        self.ledger=ExecutionLedger(TestOwner(self.home/'state.db'),self.context,self.policy);self.ledger.initialize()
        for n in ('capsules','receipts'):(self.root/n).mkdir()
        self.settings={'capsule_root':str(self.root/'capsules'),'receipt_root':str(self.root/'receipts'),
            'policy':asdict(m.ToolSandboxPolicy('sha256:'+'a'*64)),'use_sudo':False}
        self.iso=m.NativeReadIsolation(self.settings,lambda:self.ledger)
        self.iso.verify=lambda:None # Native plugin registry is tested separately.
        self.file=self.root/'input.txt';self.file.write_text('hello input\n',encoding='utf-8')
        self.args={'path':str(self.file),'offset':1,'limit':20};self.parent=SimpleNamespace(is_interrupted=False)
        self.kw={'session_id':RID,'task_id':RID,'parent_agent':self.parent}
        self.fp=hashlib.sha256(_json({'name':'read_file','args':self.args,'session_id':RID}).encode()).hexdigest()
        self.ticket=self.ledger.claim('read_file',self.fp)
        self.runs=[];self.backend_result=None
        outer=self
        class Runner:
            def __init__(self,**kwargs):self.args=kwargs
            def run(self,*,cancel_event):
                outer.runs.append(self.args)
                if outer.backend_result is not None:return outer.backend_result
                if cancel_event.is_set():raise RuntimeError('authority lost')
                return {'result':'completed','errors':[],'capsuleUnchanged':True,'stdout':'native-payload',
                    'stderr':'','outputTruncated':False,'exit':{'containerId':'a'*64,'exited':True,'removed':True,
                    'neverStarted':False,'exitCode':0}}
        for target,value in [('linux_available',lambda:True),('native_input_guard',lambda path:None),
                            ('native_redact_result',lambda text,path:text),('IsolatedToolRunner',Runner)]:
            mock=patch.object(m,target,value);mock.start();self.addCleanup(mock.stop)
    def original(self,args,**kw):
        self.assertEqual(kw['session_id'],RID);self.assertEqual(kw['task_id'],RID)
        result=m._Environment(self.iso).execute('printf native-payload',cwd='/workspace')
        return _json({'content':result['output']})
    def invoke(self,original=None,**changes):
        values=dict(original=original or self.original,args=self.args,canonical=str(self.file),kwargs=self.kw,
                    ledger=self.ledger,ticket=self.ticket);values.update(changes)
        return self.iso.invoke(**values)
    def refused_before_runner(self,fn):
        before=self.ledger.snapshot()
        with self.assertRaises(Exception):fn()
        self.assertEqual(self.runs,[]);self.assertEqual(self.ledger.snapshot(),before)
    def test_qualified_read_calls_one_runner(self):
        self.assertEqual(json.loads(self.invoke()),{'content':'native-payload'});self.assertEqual(len(self.runs),1)
    def test_only_snapshot_input_and_fixed_program_are_staged(self):
        self.invoke();p=self.runs[0]['capsule']
        self.assertEqual(sorted(x.name for x in p.iterdir()),['command.txt','input-'+self.ticket['ticket']+'.txt','program.py'])
        self.assertNotIn(TOKEN,''.join(x.read_text() for x in p.iterdir()))
    def test_canonical_ids_not_rewritten(self):self.invoke()
    def test_ticket_cannot_be_used_twice(self):
        self.invoke()
        with self.assertRaisesRegex(m.ExecutionDenied,'already_attempted'):self.invoke()
        self.assertEqual(len(self.runs),1)
    def test_outside_context_never_runs(self):
        self.refused_before_runner(lambda:m._Environment(self.iso).execute('echo x'))
    def test_second_shell_probe_refused(self):
        def original(args,**kw):
            env=m._Environment(self.iso);env.execute('printf first');return env.execute('printf second')
        with self.assertRaisesRegex(m.ExecutionDenied,'already_attempted'):self.invoke(original)
        self.assertEqual(len(self.runs),1)
    def test_another_bridge_cannot_take_context(self):
        other=m.NativeReadIsolation(self.settings,lambda:self.ledger)
        self.refused_before_runner(lambda:self.invoke(lambda a,**k:m._Environment(other).execute('x')))
    def test_cancel_before_execution(self):
        self.parent.is_interrupted=True;self.refused_before_runner(self.invoke)
    def test_missing_cancel_source(self):self.refused_before_runner(lambda:self.invoke(kwargs={'session_id':RID}))
    def test_nonbool_cancel_source(self):
        self.parent.is_interrupted=1;self.refused_before_runner(self.invoke)
    def test_native_error_does_not_become_host_fallback(self):
        with patch.object(m,'IsolatedToolRunner',side_effect=OSError('no docker')):
            self.refused_before_runner(self.invoke)
    def test_nonlinux_refuses(self):
        with patch.object(m,'linux_available',return_value=False):self.refused_before_runner(self.invoke)
    def test_read_outside_registered_native_provider_refused(self):
        def missing():raise m.ExecutionDenied('isolation_provider_missing')
        self.iso.verify=missing;self.refused_before_runner(self.invoke)
    def test_no_admission_refused(self):
        self.f.sql('DELETE FROM session_admissions');self.refused_before_runner(self.invoke)
    def test_terminal_admission_refused(self):
        self.f.sql("UPDATE session_admissions SET status='terminal'");self.refused_before_runner(self.invoke)
    def test_unknown_admission_refused(self):
        self.f.sql("UPDATE session_admissions SET status='unknown'");self.refused_before_runner(self.invoke)
    def test_queued_admission_refused(self):
        self.f.sql("UPDATE session_admissions SET status='queued'");self.refused_before_runner(self.invoke)
    def test_wrong_principal_refused(self):
        self.f.sql("UPDATE session_admissions SET principal_id='other'");self.refused_before_runner(self.invoke)
    def test_wrong_target_refused(self):
        self.f.sql("UPDATE session_admissions SET target_session_id='other'");self.refused_before_runner(self.invoke)
    def test_foreign_scope_refused(self):
        self.f.payload['api_turn_v1']['run_owner_scope']='e'*64;self.f.change_payload(self.f.payload)
        self.refused_before_runner(self.invoke)
    def test_tampered_payload_refused(self):
        self.f.sql("UPDATE session_admissions SET payload_digest=?",('e'*64,));self.refused_before_runner(self.invoke)
    def test_old_claimed_owner_refused(self):
        self.f.sql('UPDATE session_admissions SET owner_epoch=1');self.refused_before_runner(self.invoke)
    def test_current_epoch_change_refused(self):
        self.f.sql('UPDATE runtime_epoch SET epoch=3')
        with self.assertRaises(Exception):self.invoke()
        self.assertFalse(self.runs)
    def test_changed_fingerprint_refused(self):
        self.refused_before_runner(lambda:self.invoke(args=self.args|{'limit':19}))
    def test_alternate_canonical_file_refused(self):
        second=self.root/'other.txt';second.write_text('not allowed')
        self.refused_before_runner(lambda:self.invoke(canonical=str(second)))
    def test_missing_ticket_refused(self):
        self.refused_before_runner(lambda:self.invoke(ticket=self.ticket|{'ticket':'f'*32}))
    def test_settled_ticket_cannot_execute(self):
        self.ledger.settle(self.ticket['ticket'],None,'tool_return');self.refused_before_runner(self.invoke)
    def test_native_guard_blocks_original_host_path(self):
        with patch.object(m,'native_input_guard',side_effect=m.ExecutionDenied('native_input_refused')):
            self.refused_before_runner(self.invoke)
    def test_original_never_executes_is_not_success(self):
        with self.assertRaisesRegex(m.ExecutionDenied,'without_isolated_execution'):self.invoke(lambda a,**k:'{}')
    def test_no_stdin_or_extra_command_parameters(self):
        self.refused_before_runner(lambda:self.invoke(lambda a,**k:m._Environment(self.iso).execute('x',stdin_data='x')))
    def test_wrong_cwd_is_not_host_cwd(self):
        self.refused_before_runner(lambda:self.invoke(lambda a,**k:m._Environment(self.iso).execute('x',cwd='/')))
    def test_returned_failure_keeps_budget(self):
        self.backend_result={'result':'refused','errors':['docker_missing'],'capsuleUnchanged':True}
        before=self.ledger.snapshot()
        with self.assertRaises(Exception):self.invoke()
        self.assertEqual(self.ledger.snapshot(),before)
    def test_unremoved_container_never_success(self):
        self.backend_result={'result':'completed','errors':[],'capsuleUnchanged':True,
            'exit':{'exited':True,'removed':False,'neverStarted':False,'exitCode':0},'stdout':'x'}
        with self.assertRaisesRegex(m.ExecutionDenied,'exit_unverified'):self.invoke()
    def test_context_removed_after_exception(self):
        with self.assertRaises(Exception):self.invoke(lambda a,**k:(_ for _ in ()).throw(RuntimeError('x')))
        self.assertIsNone(m._ACTIVE.get())
    def test_operator_roots_cannot_overlap(self):
        with self.assertRaises(m.ExecutionDenied):m.NativeReadIsolation(self.settings|{'receipt_root':str(self.root/'capsules')},lambda:self.ledger)
    def test_unknown_settings_refused(self):
        with self.assertRaises(m.ExecutionDenied):m.NativeReadIsolation(self.settings|{'network':'host'},lambda:self.ledger)
    def test_large_input_refused(self):
        self.file.write_bytes(b'a'*65537);self.refused_before_runner(self.invoke)

if __name__=='__main__':unittest.main()
