"""PLAT-002D-RECOVERY POSIX temp-fixture file descriptor safety tests.

Linux CI uses exclusively tempfile.TemporaryDirectory() fixture paths.
No WSL/guest, user home, production state, daemon, model or host services
are created or modified. Windows test discovery skips these POSIX cases.
"""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

MODULE=Path(__file__).resolve().parents[1]/'scripts/qa/wsl2_persistent_lease.py'
sp=importlib.util.spec_from_file_location('plat002d_persistent_io',MODULE)
L=importlib.util.module_from_spec(sp)
sp.loader.exec_module(L)
SUPPORTED=(os.name=='posix' and hasattr(os,'O_NOFOLLOW')
    and hasattr(os,'O_DIRECTORY') and hasattr(os,'O_CLOEXEC')
    and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd
    and hasattr(os,'getuid'))

RUN='e'*24
BOOT='01234567-89ab-cdef-0123-456789abcdef'
PREPARED={
    'version':1,'kind':L.KIND,'phase':'PREPARED','runId':RUN,
    'nonceSha256':'b'*64,'sourceSha256':'c'*64,'bootId':BOOT,
    'guestUid':1000,'issuedBoottimeNs':10_000_000_000,
    'expiresBoottimeNs':17_000_000_000,
    'issuerPid':881,'issuerStartTick':901,
    'externalEffectOutcome':'UNKNOWN_DO_NOT_REPLAY',
    'agentToolStarted':False,'realModelCalls':0,'fullD3BAccepted':False,
}

@unittest.skipUnless(SUPPORTED,'Linux/POSIX fd-only disposable fixture')
class NativePosixFixtureSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='plat002d-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.uid=os.getuid()
        self.parent=os.open(str(self.base),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self.addCleanup(os.close,self.parent)

    def root(self):
        return L._open_owned_directory(self.parent,L.DIR_NAME,self.uid,create=True)

    def run_dir(self,rootfd):
        return L._open_owned_directory(rootfd,'run-'+RUN,self.uid,create=True)

    def test_private_root_and_run_modes_are_exact_0700(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                for handle in (rootfd,fd):
                    info=os.fstat(handle)
                    self.assertEqual(stat.S_IMODE(info.st_mode),0o700)
                    self.assertEqual(info.st_uid,self.uid)
                    self.assertTrue(stat.S_ISDIR(info.st_mode))
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_fsync_dir_and_exact_0600_record(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                data=L.encode_frame(PREPARED)
                L._durable_file(fd,'prepare.json',data)
                from_disk=L._read_record(fd,'prepare.json','PREPARED')
                self.assertEqual(from_disk,PREPARED)
                st=(self.base/L.DIR_NAME/('run-'+RUN)/'prepare.json').stat()
                self.assertEqual(stat.S_IMODE(st.st_mode),0o600)
                self.assertEqual(st.st_uid,self.uid)
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_replay_duplicate_run_directory_refused(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            os.close(fd)
            with self.assertRaises(FileExistsError):
                self.run_dir(rootfd)
        finally:os.close(rootfd)

    def test_root_symlink_open_rejected(self):
        self.assertTrue(self.base.is_dir())
        fake=self.base/L.DIR_NAME
        fake.symlink_to(self.base,target_is_directory=True)
        with self.assertRaises((OSError,L.LedgerRejected)):
            L._open_owned_directory(self.parent,L.DIR_NAME,self.uid,create=False)

    def test_run_symlink_open_rejected(self):
        rootfd=self.root()
        try:
            link=self.base/L.DIR_NAME/('run-'+RUN)
            link.symlink_to(self.base,target_is_directory=True)
            with self.assertRaises((OSError,L.LedgerRejected)):
                L._open_owned_directory(rootfd,'run-'+RUN,self.uid,create=False)
        finally:os.close(rootfd)

    def test_0600_read_symlink_is_rejected_by_nofollow(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                directory=self.base/L.DIR_NAME/('run-'+RUN)
                victim=directory/'other.txt'
                victim.write_bytes(L.encode_frame(PREPARED))
                victim.chmod(0o600)
                (directory/'prepare.json').symlink_to(victim)
                with self.assertRaises(OSError):
                    L._read_record(fd,'prepare.json','PREPARED')
                self.assertTrue(victim.exists())
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_hardlinked_record_file_refused(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                L._durable_file(fd,'prepare.json',L.encode_frame(PREPARED))
                directory=self.base/L.DIR_NAME/('run-'+RUN)
                os.link(directory/'prepare.json',directory/'alias')
                with self.assertRaises(L.LedgerRejected):
                    L._read_record(fd,'prepare.json','PREPARED')
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_record_duplicate_file_write_rejected_with_no_overwrite(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                data=L.encode_frame(PREPARED)
                L._durable_file(fd,'prepare.json',data)
                with self.assertRaises(FileExistsError):
                    L._durable_file(fd,'prepare.json',data)
                self.assertEqual(L._read_record(fd,'prepare.json','PREPARED'),
                                 PREPARED)
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_reject_unlisted_file_names_before_writing(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                with self.assertRaises(L.LedgerRejected):
                    L._durable_file(fd,'../../../secrets',b'x')
                with self.assertRaises(L.LedgerRejected):
                    L._read_record(fd,'../../escape','PREPARED')
                self.assertEqual(list(
                    (self.base/L.DIR_NAME/('run-'+RUN)).iterdir()),[])
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_existing_root_bad_mode_rejected(self):
        self.base.joinpath(L.DIR_NAME).mkdir(mode=0o700)
        path=self.base/L.DIR_NAME
        path.chmod(0o755)
        with self.assertRaises(L.LedgerRejected):
            L._open_owned_directory(self.parent,L.DIR_NAME,self.uid,create=False)

    def test_partial_os_write_is_completed_before_sync(self):
        rootfd=self.root()
        try:
            fd=self.run_dir(rootfd)
            try:
                raw=L.encode_frame(PREPARED)
                actual=os.write
                write_count=[0]
                def short_write(fd_value,data):
                    write_count[0]+=1
                    return actual(fd_value,data[:max(1,len(data)//3)])
                with patch.object(L.os,'write',side_effect=short_write):
                    L._durable_file(fd,'prepare.json',raw)
                self.assertGreater(write_count[0],1)
                self.assertEqual(L._read_record(fd,'prepare.json','PREPARED'),
                                 PREPARED)
            finally:os.close(fd)
        finally:os.close(rootfd)

    def test_all_fixture_files_stay_inside_private_temp(self):
        rootfd=self.root()
        os.close(rootfd)
        self.assertEqual(sorted(
            child.name for child in self.base.iterdir()),[L.DIR_NAME])

if __name__=='__main__':
    unittest.main()
