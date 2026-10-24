"""Pure prepared-work contracts using explicit native-object doubles.
Actual asyncio/native/SQL acceptance is separate; no kernel/model execution here.
"""
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_prepared_consumer as c
RUNNER={'adapters':dict,'_profile_adapters':dict,'_background_tasks':set,'_sessions':dict,
        '_fatal_handler_tasks':set,'_completion_notification_batch_tasks':dict,
        '_completion_notification_batches':dict,'_completion_deliveries_inflight':set,
        '_completion_notification_batch_flush_tasks':set,'_session_db_handles':dict,
        '_startup_restore_tasks':list,'_startup_restore_queue':list,'_agent_cache':OrderedDict}
AUTH={'sessions':dict,'waiters':dict,'events':dict,'native_waiters':set,'pending_results':dict,
      'pending_deliveries':dict,'adopted':dict,'executing':dict,'pending_stops':dict,
      'pending_steers':dict,'cancel_obligations':set}
OPTIONAL={'_turn_workers':dict,'_managed_workers':dict,'_mutation_tasks':set,
          '_bot_mailbox_operations':set,'_bot_receipt_tasks':set,'_cron_cancellations':dict}
class PreparedWorkContracts(unittest.TestCase):
    def setUp(self):
        self.state=object();self.r=SimpleNamespace(**{n:t() for n,t in RUNNER.items()})
        self.a=SimpleNamespace(**{n:t() for n,t in AUTH.items()})
        self.r._running=False
        for n in ('_executor','_housekeeping_executor','_loop_heartbeat_task','_stop_task'):setattr(self.r,n,None)
        self.a.runner=self.r;self.a.db=self.state;self.r.session_authority=self.a
        self.b=SimpleNamespace(_authority=self.a);self.r._caller_owned_state=self.b
        self.v=c.PreparedRuntimeConsumer.__new__(c.PreparedRuntimeConsumer)
        self.v._local_admission=False  # Explicit default normally set by the real constructor.
        self.v._runner=self.r;self.v._binding=self.b;self.v._stores=(self.state,)
    def refuse(self):
        with self.assertRaises(c.PreparedConsumerRejected):self.v._work_absent()
    def payload(self,kind):
        if kind in (dict,OrderedDict):return kind([('owned',object())])
        return kind([object()])
    def test_idle_fixed_containers_pass_without_replacement(self):
        before={n:id(getattr(self.r,n)) for n in RUNNER};self.v._work_absent()
        self.assertEqual(before,{n:id(getattr(self.r,n)) for n in RUNNER})
    def test_every_runner_work_field_refuses_nonempty(self):
        for n,t in RUNNER.items():
            old=getattr(self.r,n);value=self.payload(t);setattr(self.r,n,value)
            try:
                with self.subTest(field=n):self.refuse();self.assertIs(getattr(self.r,n),value)
            finally:setattr(self.r,n,old)
    def test_every_authority_work_field_refuses_nonempty(self):
        for n,t in AUTH.items():
            old=getattr(self.a,n);setattr(self.a,n,self.payload(t))
            try:
                with self.subTest(field=n):self.refuse()
            finally:setattr(self.a,n,old)
    def test_lazy_registries_absent_none_and_correct_empty_allowed(self):
        for n,t in OPTIONAL.items():
            for v in (None,t()):setattr(self.a,n,v);self.v._work_absent()
            delattr(self.a,n)
    def test_every_lazy_registry_refuses_any_retained_work(self):
        for n,t in OPTIONAL.items():
            value=self.payload(t);setattr(self.a,n,value)
            try:
                with self.subTest(field=n):self.refuse();self.assertIs(getattr(self.a,n),value)
            finally:delattr(self.a,n)
    def test_falsy_invalid_containers_fail_closed(self):
        for owner,fields in ((self.r,RUNNER),(self.a,AUTH),(self.a,OPTIONAL)):
            for n,t in fields.items():
                had=hasattr(owner,n);old=getattr(owner,n,None)
                for bad in (False,0,'',()):
                    setattr(owner,n,bad)
                    with self.subTest(field=n,bad=repr(bad)):self.refuse()
                if had:setattr(owner,n,old)
                else:delattr(owner,n)
    def test_missing_mandatory_fields_not_assumed_idle(self):
        for owner,fields in ((self.r,RUNNER),(self.a,AUTH)):
            for n in fields:
                old=getattr(owner,n);delattr(owner,n)
                try:
                    with self.subTest(field=n):self.refuse()
                finally:setattr(owner,n,old)
    def test_lifecycle_handles_and_integer_false_are_refused(self):
        for n in ('_executor','_housekeeping_executor','_loop_heartbeat_task','_stop_task'):
            setattr(self.r,n,object())
            try:self.refuse()
            finally:setattr(self.r,n,None)
        self.r._running=0;self.refuse()
    def test_foreign_authority_or_state_refused(self):
        self.r.session_authority=object();self.refuse();self.r.session_authority=self.a
        self.a.db=object();self.refuse();self.a.db=self.state
        self.a.runner=object();self.refuse()
    def test_done_or_cancelled_task_methods_never_called(self):
        task=SimpleNamespace(done=Mock(side_effect=AssertionError('must not prune')),cancel=Mock(side_effect=AssertionError('must not cancel')))
        self.r._background_tasks={id(task)};self.refuse()
        self.a._turn_workers={1:(task,[])};self.r._background_tasks.clear();self.refuse()
        task.done.assert_not_called();task.cancel.assert_not_called();self.assertIn(1,self.a._turn_workers)
    def test_check_refuses_work_before_sql_or_native_selection(self):
        self.v._stage='ATTACHED';self.v._identity=Mock();self.v._storage=Mock()
        self.v._bundle=SimpleNamespace(select=Mock());self.r._background_tasks.add(object())
        with self.assertRaises(c.PreparedConsumerRejected):self.v.check()
        self.v._storage.assert_not_called();self.v._bundle.select.assert_not_called()
    def test_history_only_stops_are_not_reclassified_as_live_work(self):
        self.a.delivered_stops={'past-fixture':1};self.v._work_absent()
        self.assertEqual(self.a.delivered_stops,{'past-fixture':1})
    def test_callback_side_effects_are_not_used_to_measure_empty(self):
        class FalseCollection:
            def __bool__(self):raise AssertionError('unknown object executed')
        self.r._background_tasks=FalseCollection();self.refuse()
if __name__=='__main__':unittest.main()
