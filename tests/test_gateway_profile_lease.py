"""Lifecycle sequencing with an explicit native-owner double, not OS lock proof."""
from contextlib import ExitStack
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
import gateway_profile_lease as lease


class NativeConflict(RuntimeError):
    pass


class OwnerDouble:
    def __init__(self):
        self._mutex = threading.RLock(); self._handles = {}; self._writers = []
        self.events = []; self.conflict = False
    @property
    def homes(self): return tuple(self._handles)
    def owns(self, home): return home in self._handles
    def reserve(self, homes):
        self.events.append('reserve')
        if self.conflict: raise NativeConflict('fixture')
        for home in homes:
            self._handles[home] = (home/'gateway.lock').open('r+',encoding='utf-8')
    def close(self):
        self.events.append('close')
        if any(writer.is_alive() for writer in self._writers): return
        self._writers.clear()
        for handle in self._handles.values(): handle.close()
        self._handles.clear()


class ProfileLeaseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='alaz-lease-unit-')
        self.addCleanup(tmp.cleanup); self.home = Path(tmp.name).resolve()
        self.home.chmod(0o700)
        for name in ('gateway.lock','state.db','runs_idempotency.db'):
            (self.home/name).write_bytes(b'owned fixture'); (self.home/name).chmod(0o600)
        self.owner = OwnerDouble(); self.addCleanup(self.owner.close)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.actor = (os.getpid(), self.home.stat().st_uid, self.home.stat().st_gid, threading.get_ident())
        self.actor_call = self.stack.enter_context(patch.object(lease,'_actor',return_value=self.actor))
        self.stack.enter_context(patch.dict(os.environ,{'HERMES_HOME':str(self.home)}))
        self.stack.enter_context(patch.object(lease,'_native',return_value=SimpleNamespace(
            process_ownership=self.owner, OwnershipConflict=NativeConflict)))
        self.observation = self.stack.enter_context(patch.object(lease.mounts,'observe_profile_mounts',
            return_value={'state':'CONFIGURED_MOUNT_OBSERVED'}))
        # Windows cannot express POSIX modes. Isolate only those metadata fields;
        # parser tests below exercise exact owner/mode/link validation separately.
        original=lease._private
        def private(info,uid,gid,directory=False):
            if os.name=='nt':
                info=SimpleNamespace(**{name:getattr(info,name) for name in
                    ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink')})
                info.st_mode=stat.S_IFMT(info.st_mode)|(0o700 if directory else 0o600)
            return original(info,uid,gid,directory)
        self.stack.enter_context(patch.object(lease,'_private',side_effect=private))

    def begin(self): return lease.reserve_profile(self.home,object())
    def test_reservation_wraps_mount_validation_and_releases_native_handle(self):
        current=self.begin();self.assertEqual(self.owner.events,['reserve'])
        self.assertEqual(self.observation.call_count,2)
        result=current.check();self.assertEqual(result['state'],'NATIVE_PROFILE_RESERVED')
        self.assertFalse(result['launchAuthorized']);self.assertFalse(result['persistentVolumeIntegrated'])
        self.assertFalse(result['allWritersInventoried'])
        current.finish();self.assertEqual(self.owner.events,['reserve','close'])
        self.assertFalse(self.owner.homes)
    def test_conflict_never_closes_other_owner(self):
        self.owner.conflict=True
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'already_owned'):self.begin()
        self.assertEqual(self.owner.events,['reserve'])
    def test_preexisting_same_process_reservation_never_adopted(self):
        self.owner.reserve([self.home]);events=list(self.owner.events)
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'already_used'):self.begin()
        self.assertEqual(self.owner.events,events);self.assertTrue(self.owner.owns(self.home))
    def test_wrong_environment_has_no_native_side_effect(self):
        with patch.dict(os.environ,{'HERMES_HOME':str(self.home/'other')}),self.assertRaisesRegex(
            lease.ProfileLeaseRejected,'explicit_home'):self.begin()
        self.assertEqual(self.owner.events,[])
    def test_missing_lock_never_created(self):
        (self.home/'gateway.lock').unlink()
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'unavailable'):self.begin()
        self.assertFalse((self.home/'gateway.lock').exists());self.assertEqual(self.owner.events,[])
    def test_mount_failure_before_reservation_does_not_open_lock(self):
        self.observation.side_effect=lease.mounts.StorageMountRejected('fixture')
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'unavailable'):self.begin()
        self.assertEqual(self.owner.events,[])
    def test_post_acquire_mount_failure_closes_only_new_reservation(self):
        self.observation.side_effect=[{},lease.mounts.StorageMountRejected('fixture')]
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'unavailable'):self.begin()
        self.assertEqual(self.owner.events,['reserve','close']);self.assertFalse(self.owner.homes)
    def test_live_registered_writer_prevents_early_release(self):
        current=self.begin();writer=SimpleNamespace(is_alive=lambda:True);self.owner._writers.append(writer)
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'writers_still_active'):current.finish()
        self.assertTrue(self.owner.owns(self.home));self.assertFalse(current._handle.closed)
        self.owner._writers.clear();current.finish()
        self.assertFalse(self.owner.homes)
    def test_finish_is_idempotent_and_check_after_finish_refused(self):
        current=self.begin();current.finish();current.finish()
        self.assertEqual(self.owner.events.count('close'),1)
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'finished'):current.check()
    def test_changed_process_cannot_release_parent_reservation(self):
        current=self.begin();self.actor_call.return_value=(self.actor[0]+1,*self.actor[1:])
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'other_process'):current.finish()
        self.assertEqual(self.owner.events,['reserve']);self.assertTrue(self.owner.owns(self.home))
    def test_other_thread_cannot_release_reservation(self):
        current=self.begin();self.actor_call.return_value=(*self.actor[:3],self.actor[3]+1)
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'other_process'):current.finish()
        self.assertEqual(self.owner.events,['reserve'])
    def test_additional_reserved_home_blocks_bulk_cleanup(self):
        current=self.begin();self.owner._handles[self.home/'other']=self.owner._handles[self.home]
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'reservation_set'):current.finish()
        self.assertTrue(self.owner.owns(self.home));self.assertEqual(self.owner.events,['reserve'])
        del self.owner._handles[self.home/'other']
    def test_native_fd_closed_by_other_code_refused(self):
        current=self.begin();current._handle.close()
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'handle_missing'):current.check()
    def test_fd_inheritance_refused_and_acquired_handle_closed(self):
        with patch.object(lease.os,'get_inheritable',return_value=True),self.assertRaisesRegex(
            lease.ProfileLeaseRejected,'inheritable'):self.begin()
        self.assertFalse(self.owner.homes)
    def test_lock_file_bytes_not_touched_by_adapter(self):
        before={p.name:p.read_bytes() for p in self.home.iterdir()}
        current=self.begin();current.check();current.finish()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.home.iterdir()})
    def test_new_profile_subdirectory_does_not_invalidate_reservation(self):
        current=self.begin();(self.home/'owned-new-subdirectory').mkdir()
        self.assertEqual(current.check()['state'],'NATIVE_PROFILE_RESERVED')
        current.finish();self.assertFalse(self.owner.homes)

    def test_finished_writer_is_cleared_by_native_close(self):
        current=self.begin();self.owner._writers.append(SimpleNamespace(is_alive=lambda:False))
        current.finish();self.assertFalse(self.owner._writers)
    def test_relative_profile_refused(self):
        with self.assertRaisesRegex(lease.ProfileLeaseRejected,'canonical'):
            lease.reserve_profile(Path('.'),object())
        self.assertEqual(self.owner.events,[])
    def test_permission_error_is_bounded(self):
        with patch.object(Path,'lstat',side_effect=PermissionError(str(self.home))),self.assertRaisesRegex(
            lease.ProfileLeaseRejected,'^profile_reservation_unavailable$'):self.begin()
        self.assertEqual(self.owner.events,[])


class ObjectChecks(unittest.TestCase):
    def test_private_regular_and_directory_shapes(self):
        for directory,kind,mode in ((False,stat.S_IFREG,0o600),(True,stat.S_IFDIR,0o700)):
            info=SimpleNamespace(st_dev=1,st_ino=2,st_mode=kind|mode,st_uid=123,st_gid=456,st_nlink=1)
            self.assertEqual(lease._private(info,123,456,directory)[:2],(1,2))
    def test_wrong_owner_group_mode_type_and_link_count_rejected(self):
        fields=dict(st_dev=1,st_ino=2,st_mode=stat.S_IFREG|0o600,st_uid=123,st_gid=456,st_nlink=1)
        for diff in ({'st_uid':2},{'st_gid':2},{'st_mode':stat.S_IFREG|0o644},
                     {'st_mode':stat.S_IFLNK|0o600},{'st_nlink':2}):
            with self.subTest(diff=diff),self.assertRaises(lease.ProfileLeaseRejected):
                lease._private(SimpleNamespace(**(fields|diff)),123,456)
    def test_directory_link_count_is_not_a_frozen_runtime_field(self):
        fields=dict(st_dev=1,st_ino=2,st_mode=stat.S_IFDIR|0o700,st_uid=123,st_gid=456)
        self.assertEqual(lease._private(SimpleNamespace(**fields,st_nlink=2),123,456,True),
                         lease._private(SimpleNamespace(**fields,st_nlink=7),123,456,True))

    def test_non_linux_refused_without_user_calls(self):
        with patch.object(lease.sys,'platform','win32'),self.assertRaisesRegex(
            lease.ProfileLeaseRejected,'linux_required'):lease._actor()

if __name__=='__main__':unittest.main()
