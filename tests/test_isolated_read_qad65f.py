"""Independent D2 boundary checks using real ledger/bridge with synthetic ports.
No Docker, Gateway, actual native read, paid provider or personal profile is used.
Only this test's fresh SQLite stores are deliberately mutated for negative cases.
"""
from contextlib import closing
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import isolated_read as bridge
from execution_budget import ExecutionLedger,ExecutionPolicy,ExecutionDenied,seal
from recovery_inspector import LocalRecoveryContext,_json
from test_reconciliation_inspector_qa import StoreFixture,RID,TOKEN
from test_execution_budget import TestOwner


class IsolatedReadIndependentTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.home=self.root/'profile';self.home.mkdir()
        self.store=StoreFixture(self.home)
        self.store.sql("UPDATE session_admissions SET status='started',outcome=NULL,owner_epoch=2")
        self.context=LocalRecoveryContext(self.home,TOKEN,2,'owner-two')
        self.policy=ExecutionPolicy('chosen-model',2,5,100,20,240,1000,1000000,2000000)
        self.ledger=ExecutionLedger(TestOwner(self.home/'state.db'),self.context,self.policy);self.ledger.initialize()
        for name in ('capsules','receipts'):(self.root/name).mkdir()
        settings={'capsule_root':str(self.root/'capsules'),'receipt_root':str(self.root/'receipts'),
          'policy':asdict(bridge.ToolSandboxPolicy('sha256:'+'a'*64)),'use_sudo':False}
        self.iso=bridge.NativeReadIsolation(settings,lambda:self.ledger)
        self.iso.verify=lambda:None # Only the registry port is substituted, NOT native proof.
        self.file=self.root/'allowed.txt';self.file.write_text('satır α\nsecond\n',encoding='utf-8')
        self.args={'path':str(self.file),'offset':1,'limit':20}
        self.parent=SimpleNamespace(is_interrupted=False)
        self.kw={'task_id':RID,'session_id':RID,'user_task':'fixture','parent_agent':self.parent}
        fp=hashlib.sha256(_json({'name':'read_file','args':self.args,'session_id':RID}).encode()).hexdigest()
        self.ticket=self.ledger.claim('read_file',fp)
        self.runs=[];self.before_execute=None;self.backend_result=None;self.original_calls=0
        test=self
        class SyntheticRunner:
            def __init__(self,**kwargs):self.arguments=kwargs
            def run(self,*,cancel_event):
                test.runs.append(self.arguments)
                if cancel_event.is_set():raise RuntimeError('cancelled synthetic runner')
                return test.backend_result if test.backend_result is not None else test.good_result()
        for name,value in [('linux_available',lambda:True),('native_input_guard',lambda path:None),
                           ('native_redact_result',lambda text,path:text),('IsolatedToolRunner',SyntheticRunner)]:
            obj=patch.object(bridge,name,value);obj.start();self.addCleanup(obj.stop)
    def good_result(self):
        return {'result':'completed','errors':[],'capsuleUnchanged':True,'stdout':'native-fixture-payload','stderr':'',
          'outputTruncated':False,'exit':{'containerId':'c'*64,'exited':True,'removed':True,'neverStarted':False,'exitCode':0}}
    def original(self,args,**kwargs):
        self.original_calls+=1
        if self.before_execute:self.before_execute()
        result=bridge._Environment(self.iso).execute('printf native-fixture-payload',cwd='/workspace')
        return _json({'content':result['output']})
    def invoke(self,**changes):
        params=dict(original=self.original,args=self.args,canonical=str(self.file),kwargs=self.kw,ledger=self.ledger,ticket=self.ticket)
        return self.iso.invoke(**(params|changes))
    def expect_refusal_no_runner(self,**changes):
        with self.assertRaises(ExecutionDenied):self.invoke(**changes)
        self.assertEqual(self.runs,[],'authority rejection reached sandbox executor')
    def test_qualified_identity_executes_exactly_one_runner(self):
        self.assertEqual(json.loads(self.invoke()),{'content':'native-fixture-payload'})
        self.assertEqual(len(self.runs),1)
    def test_revoked_quarantine_blocks_previously_reserved_ticket(self):
        self.ledger.quarantine();self.expect_refusal_no_runner()
        self.assertTrue(self.ledger.snapshot()['quarantined']);self.assertEqual(self.ledger.snapshot()['toolCalls'],1)
    def test_quarantine_between_native_entry_and_execute_blocks(self):
        self.before_execute=self.ledger.quarantine;self.expect_refusal_no_runner()
    def test_generation_change_between_entry_and_execute_blocks(self):
        self.before_execute=lambda:self.store.sql('UPDATE session_admissions SET generation=generation+1')
        self.expect_refusal_no_runner()
    def test_admission_identity_change_between_entry_and_execute_blocks(self):
        self.before_execute=lambda:self.store.sql('UPDATE session_admissions SET admission_id=?',('d'*32,))
        self.expect_refusal_no_runner()
    def test_invalid_admission_id_is_not_authority(self):
        self.store.sql('UPDATE session_admissions SET admission_id=?',('not-an-admission',))
        self.expect_refusal_no_runner()
    def test_terminal_transition_before_execute_blocks(self):
        self.before_execute=lambda:self.store.sql("UPDATE session_admissions SET status='terminal',outcome='completed'")
        self.expect_refusal_no_runner()
    def test_unknown_transition_before_execute_blocks(self):
        self.before_execute=lambda:self.store.sql("UPDATE session_admissions SET status='unknown'")
        self.expect_refusal_no_runner()
    def test_active_epoch_change_blocks_before_runner(self):
        self.before_execute=lambda:self.store.sql('UPDATE runtime_epoch SET epoch=3')
        self.expect_refusal_no_runner()
    def test_read_only_policy_factory_revocation_blocks(self):
        def revoked():raise ExecutionDenied('execution_settings_changed')
        self.iso.ledger_factory=revoked;self.expect_refusal_no_runner()
    def test_changed_policy_instance_cannot_reuse_reserved_ticket(self):
        foreign=ExecutionLedger(self.ledger.db,self.context,replace(self.policy,max_tool_calls=4))
        self.iso.ledger_factory=lambda:foreign;self.expect_refusal_no_runner()
    def test_foreign_principal_never_reaches_executor(self):
        self.store.sql("UPDATE session_admissions SET principal_id='non-api'");self.expect_refusal_no_runner()
    def test_wrong_target_never_reaches_executor(self):
        self.store.sql("UPDATE session_admissions SET target_session_id='foreign'");self.expect_refusal_no_runner()
    def test_zero_generation_is_not_active_authority(self):
        self.store.sql('UPDATE session_admissions SET generation=0');self.expect_refusal_no_runner()
    def test_deleted_ticket_does_not_reset_budget(self):
        self.store.sql('DELETE FROM state_meta WHERE key=?',(self.ledger.prefix+self.ticket['ticket'],));self.expect_refusal_no_runner()
    def test_settled_ticket_never_reexecutes(self):
        self.ledger.settle(self.ticket['ticket'],None,'tool_return');self.expect_refusal_no_runner()
    def test_caller_ticket_mutation_refused(self):
        self.expect_refusal_no_runner(ticket=self.ticket|{'state':'settled'})
    def test_args_pagination_mutation_refused(self):
        self.expect_refusal_no_runner(args=self.args|{'offset':2})
    def test_canonical_path_mismatch_refused(self):
        other=self.root/'not-allowed.txt';other.write_text('private')
        self.expect_refusal_no_runner(canonical=str(other))
    def test_linux_unavailable_no_local_original_fallback(self):
        with patch.object(bridge,'linux_available',return_value=False):self.expect_refusal_no_runner()
        self.assertEqual(self.original_calls,0)
    def test_docker_construction_failure_keeps_reservation(self):
        before=self.ledger.snapshot()
        with patch.object(bridge,'IsolatedToolRunner',side_effect=OSError('missing docker')):self.expect_refusal_no_runner()
        self.assertEqual(self.ledger.snapshot(),before)
    def test_unknown_result_does_not_become_success(self):
        self.backend_result=self.good_result()|{'result':'unknown'}
        with self.assertRaises(ExecutionDenied):self.invoke()
        self.assertEqual(self.ledger.snapshot()['toolCalls'],1)
    def test_unremoved_result_does_not_become_success(self):
        self.backend_result=self.good_result();self.backend_result['exit']['removed']=False
        with self.assertRaises(ExecutionDenied):self.invoke()
    def test_never_started_result_does_not_become_success(self):
        self.backend_result=self.good_result();self.backend_result['exit']['neverStarted']=True
        with self.assertRaises(ExecutionDenied):self.invoke()
    def test_truncated_result_does_not_become_success(self):
        self.backend_result=self.good_result()|{'outputTruncated':True}
        with self.assertRaises(ExecutionDenied):self.invoke()
    def test_completed_nonzero_exit_contradiction_refused(self):
        self.backend_result=self.good_result();self.backend_result['exit']['exitCode']=1
        with self.assertRaises(ExecutionDenied):self.invoke()
    def test_failed_zero_exit_contradiction_refused(self):
        self.backend_result=self.good_result()|{'result':'tool_failed'}
        with self.assertRaises(ExecutionDenied):self.invoke()
    def test_context_reset_after_original_exception(self):
        def broken(*args,**kwargs):raise RuntimeError('synthetic original failure')
        with self.assertRaises(RuntimeError):self.invoke(original=broken)
        self.assertIsNone(bridge._ACTIVE.get());self.assertEqual(self.runs,[])
    def test_source_snapshot_bytes_are_exact(self):
        self.invoke();path=self.runs[0]['capsule']/('input-'+self.ticket['ticket']+'.txt')
        self.assertEqual(path.read_bytes(),self.file.read_bytes())
    def test_no_secret_or_state_store_in_capsule(self):
        self.invoke();capsule=self.runs[0]['capsule'];files=list(capsule.iterdir())
        self.assertEqual(len(files),3)
        for path in files:
            data=path.read_bytes();self.assertNotIn(TOKEN.encode(),data)
            self.assertNotIn(b'SQLite format 3',data)

if __name__=='__main__':unittest.main()
