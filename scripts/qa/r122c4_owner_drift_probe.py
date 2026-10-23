"""Focused ownership mutation checks on prepared-but-not-running native runner."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import r122c4_native_runner as q
class PreparedDriftChecks(unittest.TestCase):
    setUp=q.NativeRunnerChecks.setUp
    tearDown=q.NativeRunnerChecks.tearDown
    make=q.NativeRunnerChecks.make
    watched=q.NativeRunnerChecks.watched
    def test_authority_epoch_drift_refuses_selection(self):
        self.make();a=self.authority;old=a.epoch;a.epoch+=1
        try:
            with self.watched(),self.assertRaises(q.Rejected):self.runner._session_db
        finally:a.epoch=old
    def test_descriptor_replacement_refuses_before_detach(self):
        self.make();r=self.runner;old=r.session_runtime_descriptor;r.session_runtime_descriptor=dict(old)
        try:
            with self.watched(),self.assertRaises(q.Rejected):r.close_all_session_db_handles()
            self.assertEqual(self.binding.status()['state'],'PREPARED')
        finally:r.session_runtime_descriptor=old
    def test_foreign_authority_registry_entry_refuses_detach(self):
        self.make();registry=self.runner.session_authorities;home=self.home/'other'
        registry.add(home,object())
        try:
            with self.watched(),self.assertRaises(q.Rejected):self.runner.close_all_session_db_handles()
        finally:registry.remove(home)
    def test_native_admission_gate_is_closed(self):
        self.make()
        with self.watched(),self.assertRaises(q.Runtime.RuntimeStoreError) as caught:self.authority._require_admission_open()
        self.assertEqual(caught.exception.reason,'runtime_draining')
if __name__=='__main__':
    q.NativeRunnerChecks=PreparedDriftChecks
    raise SystemExit(q.main())
