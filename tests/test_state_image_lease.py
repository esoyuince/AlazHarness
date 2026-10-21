"""Real cooperative image leases on Linux, contract-only tests on Windows.

All images are inert bytes in private TemporaryDirectory fixtures. No mount,
format, actual persistent Gateway, vendor module, network or UID change.
"""
from dataclasses import asdict, replace, FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import state_image_lease as images


def sample():
    return images.ImagePin('/private/state.img',1,2,65536,1000,1000,1,3)


def pin(path):
    s=path.lstat();p=path.parent.lstat()
    return images.ImagePin(str(path),s.st_dev,s.st_ino,s.st_size,
                           s.st_uid,s.st_gid,p.st_dev,p.st_ino)


class ImagePinContracts(unittest.TestCase):
    def test_valid_pin_is_immutable(self):
        p=sample()
        with self.assertRaises(FrozenInstanceError):p.inode=4
    def test_noncanonical_paths(self):
        for path in ('relative','//x/y','/a/../b','/a/./b','/a//b','/a/b/','/',
                     '/a'+chr(92)+'b','/a'+chr(0)+'b'):
            with self.subTest(path=repr(path)),self.assertRaises(images.VolumeLeaseRejected):
                replace(sample(),path=path)
    def test_identifiers_reject_bool_float_negative_or_unbounded(self):
        for key in ('device','inode','size','uid','gid','parent_device','parent_inode'):
            for value in (True,1.0,-1,2**63):
                with self.subTest(key=key,value=value),self.assertRaises(images.VolumeLeaseRejected):
                    replace(sample(),**{key:value})
    def test_empty_inode_and_unaligned_sizes(self):
        for changes in ({'inode':0},{'parent_inode':0},{'size':0},{'size':4097},{'size':2**50+4096}):
            with self.subTest(changes=changes),self.assertRaises(images.VolumeLeaseRejected):
                replace(sample(),**changes)
    def test_pin_construction_does_no_io(self):
        with patch.object(os,'open',side_effect=AssertionError('no open')):
            self.assertEqual(sample().size,65536)
    def test_nonlinux_rejected_before_io(self):
        with patch.object(images.sys,'platform','win32'),patch.object(os,'open') as opened:
            with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_linux_required'):
                images.acquire_image_lease(sample())
        opened.assert_not_called()
    def test_untrusted_dictionary_rejected_before_io(self):
        with patch.object(images.sys,'platform','linux'),patch.object(os,'open') as opened:
            with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_trusted_pin_required'):
                images.acquire_image_lease(asdict(sample()))
        opened.assert_not_called()
    def test_rejection_has_no_path_contents(self):
        with self.assertRaises(images.VolumeLeaseRejected) as caught:
            replace(sample(),path='private-sensitive-path')
        self.assertEqual(str(caught.exception),'volume_path_invalid')


@unittest.skipUnless(sys.platform=='linux','real Linux flock/dirfd/fork required')
class NativeImageLeaseTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='alaz-v98r-')
        self.addCleanup(tmp.cleanup);self.home=Path(tmp.name).resolve();self.home.chmod(0o700)
        self.image=self.home/'state.img';self.image.write_bytes(b'A'*65536);self.image.chmod(0o600)
        self.pin=pin(self.image)
    def acquire(self):
        lease=images.acquire_image_lease(self.pin);self.addCleanup(lease.close);return lease
    def contender(self):
        return subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),
            '--lease-child','try',json.dumps(asdict(self.pin))],capture_output=True,text=True,timeout=10)
    def test_real_acquisition_preserves_bytes_and_metadata(self):
        before=self.image.stat();digest=hashlib.sha256(self.image.read_bytes()).hexdigest()
        with images.acquire_image_lease(self.pin) as lease:
            result=lease.confirm();self.assertEqual(result['state'],'EXCLUSIVE_IMAGE_LEASE_HELD')
            self.assertIs(result['advisoryLock'],True)
            for field in ('writesPerformed','existingMountsOrLoopsExcluded','profileWriterOwnership',
                          'physicalDurabilityVerified','mountAuthorized','fullGatewayPersistenceAccepted'):
                self.assertIs(result[field],False)
        after=self.image.stat()
        self.assertEqual((before.st_ino,before.st_size,before.st_mode,before.st_mtime_ns),
                         (after.st_ino,after.st_size,after.st_mode,after.st_mtime_ns))
        self.assertEqual(digest,hashlib.sha256(self.image.read_bytes()).hexdigest())
    def test_no_content_read_write_or_unlink(self):
        with (patch.object(os,'read',side_effect=AssertionError('read')),
              patch.object(os,'write',side_effect=AssertionError('write')),
              patch.object(os,'unlink',side_effect=AssertionError('unlink')),
              patch.object(os,'ftruncate',side_effect=AssertionError('truncate'))):
            with images.acquire_image_lease(self.pin) as lease:lease.confirm()
    def test_same_process_second_owner_refused(self):
        first=self.acquire()
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_busy'):
            images.acquire_image_lease(self.pin)
        first.confirm()
    def test_actual_child_contends_then_acquires_after_close(self):
        first=self.acquire();r=self.contender()
        self.assertEqual(r.returncode,2,r.stderr);self.assertEqual(r.stdout.strip(),'volume_busy')
        first.close();r=self.contender()
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'acquired')
    def test_exception_releases_owned_lease_without_unlink(self):
        inode=self.image.stat().st_ino
        with self.assertRaisesRegex(RuntimeError,'owned failure'):
            with images.acquire_image_lease(self.pin):raise RuntimeError('owned failure')
        self.assertEqual(self.image.stat().st_ino,inode);self.acquire().confirm()
    def test_missing_file_not_created(self):
        self.image.unlink()
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_unavailable'):
            images.acquire_image_lease(self.pin)
        self.assertFalse(self.image.exists())
    def test_wrong_identity_rejected(self):
        for change in ({'inode':self.pin.inode+1},{'size':self.pin.size+4096},
                       {'parent_inode':self.pin.parent_inode+1},{'device':self.pin.device+1}):
            with self.subTest(change=change),self.assertRaises(images.VolumeLeaseRejected):
                images.acquire_image_lease(replace(self.pin,**change))
        self.acquire().confirm()
    def test_parent_mode_must_be_private(self):
        self.home.chmod(0o755)
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_parent_identity'):
            images.acquire_image_lease(self.pin)
        self.home.chmod(0o700);self.acquire().confirm()
    def test_image_mode_must_be_private(self):
        self.image.chmod(0o644)
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_image_identity'):
            images.acquire_image_lease(self.pin)
        self.image.chmod(0o600);self.acquire().confirm()
    def test_symlink_is_never_followed(self):
        alias=self.home/'alias.img';alias.symlink_to(self.image)
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_noncanonical_path'):
            images.acquire_image_lease(replace(self.pin,path=str(alias)))
        self.assertTrue(alias.is_symlink());self.acquire().confirm()
    def test_hardlink_refused_without_repair(self):
        alias=self.home/'alias.img';os.link(self.image,alias)
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_image_identity'):
            images.acquire_image_lease(self.pin)
        self.assertEqual(self.image.stat().st_nlink,2)
    def test_resize_during_lease_refuses_confirmation(self):
        lease=self.acquire()
        with self.image.open('r+b') as stream:stream.truncate(65536+4096)
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_image_identity'):
            lease.confirm()
    def test_replaced_image_not_adopted(self):
        lease=self.acquire();old=self.home/'old.img';self.image.rename(old)
        self.image.write_bytes(b'B'*65536);self.image.chmod(0o600)
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_image_identity'):
            lease.confirm()
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_image_identity'):
            images.acquire_image_lease(self.pin)
        self.assertEqual(old.stat().st_ino,self.pin.inode)
    def test_parent_path_replacement_rejected(self):
        lease=self.acquire();moved=self.home.with_name(self.home.name+'-moved')
        self.home.rename(moved);self.home.mkdir(mode=0o700)
        try:
            with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_parent_identity'):
                lease.confirm()
        finally:
            self.home.rmdir();moved.rename(self.home)
    def test_exec_does_not_inherit_image_or_parent_descriptors(self):
        lease=self.acquire()
        pairs=[(fd,os.fstat(fd).st_dev,os.fstat(fd).st_ino)
               for fd in (lease._image_fd,lease._parent_fd)]
        r=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),
                          '--lease-child','fds',json.dumps(pairs)],
                         close_fds=False,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),[False,False])
        lease.confirm()
    def test_fork_child_cannot_release_parent_lock(self):
        lease=self.acquire();pid=os.fork()
        if pid==0:
            try:
                try:lease.confirm()
                except images.VolumeLeaseRejected:pass
                else:os._exit(2)
                lease.close();os._exit(0)
            except BaseException:os._exit(3)
        got,status=os.waitpid(pid,0);self.assertEqual(os.waitstatus_to_exitcode(status),0)
        lease.confirm()
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_busy'):
            images.acquire_image_lease(self.pin)
    def test_abrupt_owner_exit_releases_kernel_lock(self):
        process=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),
            '--lease-child','abrupt',json.dumps(asdict(self.pin))],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            ready,_,_=select.select([process.stdout],[],[],10)
            self.assertTrue(ready,'owned child did not report readiness')
            self.assertEqual(process.stdout.readline().strip(),b'held')
            with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_busy'):
                images.acquire_image_lease(self.pin)
            output,error=process.communicate(b'x',timeout=10)
            self.assertEqual(process.returncode,73,error)
            self.acquire().confirm()
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
            for stream in (process.stdin,process.stdout,process.stderr):stream.close()
    def test_closed_lease_cannot_be_reused(self):
        lease=self.acquire();lease.close();lease.close()
        with self.assertRaisesRegex(images.VolumeLeaseRejected,'volume_lease_not_owned'):lease.confirm()
        self.acquire().confirm()


def child(mode,value):
    if mode=='fds':
        result=[]
        for fd,device,inode in value:
            try:info=os.fstat(fd);result.append((info.st_dev,info.st_ino)==(device,inode))
            except OSError:result.append(False)
        print(json.dumps(result));return int(any(result))
    try:
        lease=images.acquire_image_lease(images.ImagePin(**value))
    except images.VolumeLeaseRejected as exc:print(str(exc));return 2
    with lease:
        if mode=='try':print('acquired');return 0
        if mode=='abrupt':
            print('held',flush=True);sys.stdin.buffer.read(1);os._exit(73)
    return 3


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--lease-child':
        raise SystemExit(child(sys.argv[2],json.loads(sys.argv[3])))
    unittest.main()
