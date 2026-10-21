"""Supervisor sequencing tests. Privileged boundaries are explicit doubles."""
from contextlib import ExitStack
import errno
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import state_volume_supervisor as s


class Contracts(unittest.TestCase):
    def test_events_complete_empty(self):
        self.assertFalse(s.populated('populated 0\nfrozen 0\n'))
    def test_events_populated(self):
        self.assertTrue(s.populated('frozen 0\npopulated 1\n'))
    def test_events_unknown_key_does_not_hide_population(self):
        self.assertTrue(s.populated('newfield 9\npopulated 1\n'))
    def test_invalid_events_fail_closed(self):
        for value in ('','frozen 0\n','populated 2\n','populated 0\npopulated 1\n',
                      'populated -1\n','populated False\n','populated 0 junk\n','x'*8192,None):
            with self.subTest(value=value),self.assertRaises(s.SupervisorRejected):s.populated(value)
    def test_constructor_cannot_skip_begin(self):
        with self.assertRaises(s.SupervisorRejected):s.VolumeSupervisor()
    def test_nonlinux_refused_before_root_calls(self):
        with patch.object(s.sys,'platform','win32'),self.assertRaisesRegex(s.SupervisorRejected,'linux'):
            s.actor()
    def test_ioctl_layout_exact(self):
        self.assertEqual(s.INFO.size,232)
        self.assertEqual(8+s.INFO.size+64,304)
    def test_only_enxio_means_unattached(self):
        fake=SimpleNamespace(ioctl=Mock(side_effect=OSError(errno.ENXIO,'owned')))
        with patch.dict(sys.modules,{'fcntl':fake}):self.assertIsNone(s.loop_status(99))
        for code in (errno.EPERM,errno.EIO,errno.ENOENT,errno.EBUSY):
            fake.ioctl.side_effect=OSError(code,'owned')
            with patch.dict(sys.modules,{'fcntl':fake}),self.assertRaisesRegex(s.SupervisorRejected,'unknown'):
                s.loop_status(99)


class Teardown(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.scope=self.root/'scope';self.scope.mkdir()
        self.target=self.root/'target';self.target.mkdir()
        self.fence=self.root/'fence.json';self.fence.write_bytes(b'owned\n')
        self.events=[]
        self.v=object.__new__(s.VolumeSupervisor)
        self.v.stage='RUNNING';self.v.who=(os.getpid(),0);self.v.token='owned-test'
        self.v.lease=Mock();self.v.lease.close.side_effect=lambda:self.events.append('lease-close')
        self.v.pin=object();self.v.target=self.target;self.v.target_id=(1,2)
        self.v.scope=self.scope;self.v.scope_id=(1,3);self.v.fence=self.fence
        self.v.fence_id=(1,4);self.v.fence_bytes=b'owned\n';self.v.loop_fd=99
        self.v.spawn_uncertain=False
        self.worker=Mock();self.worker.poll.return_value=0;self.worker.returncode=0
        self.worker.stdin=self.worker.stdout=self.worker.stderr=None
        self.v.worker=self.worker
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.owned=self.stack.enter_context(patch.object(self.v,'_owned'))
        self.empty=self.stack.enter_context(patch.object(self.v,'_empty_scope',return_value=True))
        self.sync=self.stack.enter_context(patch.object(self.v,'_sync_parent',side_effect=lambda:self.events.append('fsync-parent')))
        self.attachments=self.stack.enter_context(patch.object(s,'attachments',return_value=[]))
        self.trusted=self.stack.enter_context(patch.object(s,'trusted',side_effect=lambda p,**kw:
            (1,2) if p==self.target else (1,4) if p==self.fence else (1,3)))
        self.closed=self.stack.enter_context(patch.object(s.os,'close',side_effect=lambda fd:self.events.append('loop-close')))
        self.stack.enter_context(patch.object(s.os.path,'ismount',return_value=False))
        s._RETAINED[self.v.token]=self.v
        self.addCleanup(lambda:s._RETAINED.pop(self.v.token,None))
    def assert_retained(self):
        self.assertTrue(self.fence.exists());self.v.lease.close.assert_not_called()
        self.assertIs(s._RETAINED[self.v.token],self.v)
    def test_normal_cleanup_then_unlock(self):
        result=self.v.finish()
        self.assertEqual(self.events,['loop-close','fsync-parent','lease-close'])
        self.assertFalse(self.scope.exists());self.assertFalse(self.fence.exists())
        self.assertEqual(self.v.stage,'CLOSED');self.assertTrue(result['leaseReleasedLast'])
        self.assertFalse(result['fullD3BAccepted']);self.worker.wait.assert_called_once_with(timeout=0)
    def test_live_worker_prevents_any_detach_or_unlock(self):
        self.worker.poll.return_value=None
        with self.assertRaisesRegex(s.SupervisorRejected,'worker_alive'):self.v.finish()
        self.closed.assert_not_called();self.assert_retained()
    def test_surviving_group_member_blocks_after_worker_exit(self):
        self.empty.return_value=False
        with self.assertRaisesRegex(s.SupervisorRejected,'users_still_active'):self.v.finish()
        self.closed.assert_not_called();self.assert_retained()
    def test_unknown_spawn_effect_cannot_be_released(self):
        self.v.spawn_uncertain=True
        with self.assertRaisesRegex(s.SupervisorRejected,'spawn_unknown'):self.v.finish()
        self.closed.assert_not_called();self.assert_retained()
    def test_incomplete_user_observation_retains_everything(self):
        self.empty.side_effect=PermissionError('owned fixture')
        with self.assertRaises(PermissionError):self.v.finish()
        self.closed.assert_not_called();self.assert_retained()
    def test_busy_loop_after_last_owned_close_retains_fence(self):
        self.attachments.return_value=[{'owned':True}]
        with self.assertRaisesRegex(s.SupervisorRejected,'attachment_remains'):self.v.finish()
        self.assertIsNone(self.v.loop_fd);self.assert_retained()
        self.assertTrue(self.scope.exists())
    def test_late_read_only_reconciliation_can_finish_without_reclose(self):
        self.attachments.return_value=[{}]
        with self.assertRaises(s.SupervisorRejected):self.v.finish()
        self.attachments.return_value=[];self.v.finish()
        self.assertEqual(self.events.count('loop-close'),1)
    def test_loop_inventory_error_is_not_empty(self):
        self.attachments.side_effect=s.SupervisorRejected('inventory_unknown')
        with self.assertRaisesRegex(s.SupervisorRejected,'unknown'):self.v.finish()
        self.assert_retained()
    def test_mount_reintroduced_in_parent_blocks(self):
        with patch.object(s.os.path,'ismount',return_value=True),self.assertRaisesRegex(
            s.SupervisorRejected,'host_mount_remains'):self.v.finish()
        self.closed.assert_not_called();self.assert_retained()
    def test_target_nonempty_refused(self):
        (self.target/'foreign').write_text('do not touch')
        with self.assertRaisesRegex(s.SupervisorRejected,'host_mount_remains'):self.v.finish()
        self.closed.assert_not_called();self.assert_retained()
    def test_repopulated_scope_refuses_fence_removal(self):
        self.empty.side_effect=[True,False]
        with self.assertRaisesRegex(s.SupervisorRejected,'repopulated'):self.v.finish()
        self.assert_retained();self.assertTrue(self.scope.exists())
    def test_cgroup_removal_failure_prevents_unlock(self):
        with (patch.object(Path,'rmdir',side_effect=OSError(errno.EBUSY,'owned')),
              self.assertRaises(OSError)):self.v.finish()
        self.assert_retained()
    def test_changed_fence_is_never_removed(self):
        self.fence.write_bytes(b'changed\n')
        with self.assertRaisesRegex(s.SupervisorRejected,'fence_changed'):self.v.finish()
        self.assert_retained();self.assertEqual(self.fence.read_bytes(),b'changed\n')
    def test_fsync_failure_does_not_release_lease(self):
        self.sync.side_effect=OSError(errno.EIO,'owned')
        with self.assertRaises(OSError):self.v.finish()
        self.v.lease.close.assert_not_called();self.assertIn(self.v.token,s._RETAINED)
    def test_attach_cannot_be_replayed(self):
        self.v.stage='ATTACHING'
        with self.assertRaisesRegex(s.SupervisorRejected,'attach_once'):self.v.attach()
        self.attachments.assert_not_called();self.assert_retained()
    def test_start_cannot_be_replayed(self):
        with patch.object(s.subprocess,'Popen') as spawn,self.assertRaisesRegex(s.SupervisorRejected,'start_once'):
            self.v.start()
        spawn.assert_not_called();self.assert_retained()
    def test_busy_stop_never_unlocks(self):
        self.worker.poll.return_value=None;self.worker.stdin=Mock()
        with (patch.object(s,'read_line',return_value={'pid':self.worker.pid,'token':self.v.token,'state':'BUSY'}),
              self.assertRaisesRegex(s.SupervisorRejected,'users_still_active')):self.v.stop()
        self.assertEqual(self.v.stage,'STOP_REFUSED');self.assert_retained()
    def test_unknown_stop_response_is_not_replayable(self):
        self.worker.poll.return_value=None;self.worker.stdin=Mock()
        with (patch.object(s,'read_line',side_effect=s.SupervisorRejected('timeout')),
              self.assertRaisesRegex(s.SupervisorRejected,'timeout')):self.v.stop()
        self.assertEqual(self.v.stage,'STOPPING');self.assert_retained()
        with self.assertRaisesRegex(s.SupervisorRejected,'stop_state'):self.v.stop()
    def test_stop_pipe_write_failure_sets_uncertain_before_effect(self):
        self.worker.poll.return_value=None;self.worker.stdin=Mock()
        self.worker.stdin.write.side_effect=BrokenPipeError('owned write fixture')
        with self.assertRaises(BrokenPipeError):self.v.stop()
        self.assertEqual(self.v.stage,'STOPPING');self.assert_retained()
        with self.assertRaisesRegex(s.SupervisorRejected,'stop_state'):self.v.stop()
        self.assertEqual(self.worker.stdin.write.call_count,1)
    def test_stop_pipe_flush_failure_sets_uncertain_before_effect(self):
        self.worker.poll.return_value=None;self.worker.stdin=Mock()
        self.worker.stdin.flush.side_effect=BrokenPipeError('owned flush fixture')
        with self.assertRaises(BrokenPipeError):self.v.stop()
        self.assertEqual(self.v.stage,'STOPPING');self.assert_retained()
        with self.assertRaisesRegex(s.SupervisorRejected,'stop_state'):self.v.stop()
        self.assertEqual(self.worker.stdin.write.call_count,1)
    def test_worker_control_never_accepts_foreign_token(self):
        self.worker.poll.return_value=None;self.worker.stdin=Mock()
        with (patch.object(s,'read_line',return_value={'pid':self.worker.pid,'token':'foreign','state':'UNMOUNTED'}),
              self.assertRaisesRegex(s.SupervisorRejected,'stop_reply')):self.v.stop()
        self.assert_retained()


if __name__=='__main__':unittest.main()
