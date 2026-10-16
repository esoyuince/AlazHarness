"""Actual D2 cancellation bridge with synthetic native context ports, offline only.
The real native thread module is separately characterized by the opt-in observer.
"""
from contextvars import ContextVar
from pathlib import Path
import sys
import threading
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import isolated_read as bridge
import test_isolated_read_qad65f as read_fixture

RID='run_'+'a'*32


class NativeCancellationBridgeTests(unittest.TestCase):
    def setUp(self):
        self.marked=set();self.actor=ContextVar('qa_actor',default=None)
        self.sid=ContextVar('qa_sid',default='');self.callid=ContextVar('qa_call',default='')
        self.sid.set(RID);self.callid.set('call_fixture')
        tools=ModuleType('tools');tools.__path__=[]
        interrupt=ModuleType('tools.interrupt');interrupt.acting_for_tid=self.actor
        interrupt.is_thread_interrupted=lambda tid:tid is not None and tid in self.marked
        approval=ModuleType('tools.approval_context');approval._approval_session_id=self.sid;approval._approval_tool_call_id=self.callid
        tools.interrupt=interrupt;tools.approval_context=approval
        patcher=patch.dict(sys.modules,{'tools':tools,'tools.interrupt':interrupt,'tools.approval_context':approval})
        patcher.start();self.addCleanup(patcher.stop)
    def source(self):return bridge._NativeInterruptSource(RID)
    def test_native_context_without_parent_agent_is_supported(self):
        source=self.source();self.assertIs(source.is_interrupted,False)
    def test_wrong_session_context_is_refused(self):
        self.sid.set('run_'+'b'*32)
        with self.assertRaises(bridge.ExecutionDenied):self.source()
    def test_missing_call_context_is_refused(self):
        self.callid.set('')
        with self.assertRaises(bridge.ExecutionDenied):self.source()
    def test_boolean_acting_thread_is_not_identity(self):
        self.actor.set(True)
        with self.assertRaises(bridge.ExecutionDenied):self.source()
    def test_current_thread_stop_is_seen(self):
        source=self.source();self.marked.add(threading.get_ident());self.assertIs(source.is_interrupted,True)
    def test_acting_thread_stop_is_seen(self):
        self.actor.set(876543);source=self.source();self.marked.add(876543);self.assertIs(source.is_interrupted,True)
    def test_unrelated_thread_stop_does_not_cancel(self):
        source=self.source();self.marked.add(876544);self.assertIs(source.is_interrupted,False)
    def test_context_change_does_not_replace_captured_actor(self):
        self.actor.set(876543);source=self.source();self.actor.set(876544)
        self.marked.add(876543);self.assertIs(source.is_interrupted,True)
    def test_other_polling_thread_still_sees_owner_stop(self):
        source=self.source();self.marked.add(threading.get_ident());result=[]
        thread=threading.Thread(target=lambda:result.append(source.is_interrupted));thread.start();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertEqual(result,[True])
    def test_cancellation_is_sticky_after_native_flag_clears(self):
        source=self.source();self.marked.add(threading.get_ident())
        checks=[];call=SimpleNamespace(parent_agent=source,owner=SimpleNamespace(check_call=lambda c:checks.append(c)))
        stop=bridge._Cancellation(call);self.assertTrue(stop.is_set());self.marked.clear()
        self.assertTrue(stop.is_set());self.assertEqual(stop.reason,'native_read_cancelled');self.assertEqual(checks,[])
    def test_authority_failure_latches_cancel(self):
        def denied(call):raise bridge.ExecutionDenied('execution_budget_quarantined')
        stop=bridge._Cancellation(SimpleNamespace(parent_agent=self.source(),owner=SimpleNamespace(check_call=denied)))
        self.assertTrue(stop.is_set());self.assertEqual(stop.reason,'isolated_read_authority_lost')
    def make_read(self):
        # Reuse the SAME test-only DB/Docker/native-handler fixtures, not production state.
        fixture=read_fixture.IsolatedReadIndependentTests(methodName='test_qualified_identity_executes_exactly_one_runner')
        fixture.setUp();self.addCleanup(fixture.doCleanups);self.sid.set(fixture.kw['session_id'])
        return fixture
    def test_real_dispatch_kwargs_shape_reaches_bridge_without_fabricated_parent(self):
        fixture=self.make_read();kwargs={k:fixture.kw[k] for k in ('task_id','session_id','user_task')}
        result=fixture.invoke(kwargs=kwargs);self.assertIn('native-fixture-payload',result);self.assertEqual(len(fixture.runs),1)
    def test_real_dispatch_kwargs_acting_stop_blocks_runner(self):
        fixture=self.make_read();self.actor.set(876543);self.marked.add(876543)
        kwargs={k:fixture.kw[k] for k in ('task_id','session_id','user_task')}
        with self.assertRaises(bridge.ExecutionDenied):fixture.invoke(kwargs=kwargs)
        self.assertEqual(fixture.runs,[])
    def test_real_dispatch_kwargs_wrong_native_scope_blocks_runner(self):
        fixture=self.make_read();self.sid.set('run_'+'f'*32)
        kwargs={k:fixture.kw[k] for k in ('task_id','session_id','user_task')}
        with self.assertRaises(bridge.ExecutionDenied):fixture.invoke(kwargs=kwargs)
        self.assertEqual(fixture.runs,[])

if __name__=='__main__':unittest.main()
