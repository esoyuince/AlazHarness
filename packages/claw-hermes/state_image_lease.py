"""Controller-side advisory lease for an EXISTING dedicated state image.

This is not Hermes's gateway.lock and does not replace ProfileOwnership.
No creation, truncation, content read/write, formatting, mount or launch occurs.
Only cooperating controllers are excluded. A trusted supervisor must separately
prove no other loop attachment/mount/writer and retain this lease until every
volume user is reaped and the volume detached. This primitive does not do that.
"""
from __future__ import annotations
from dataclasses import dataclass
import errno
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import weakref


class VolumeLeaseRejected(RuntimeError):
    """Bounded reason without private paths or image contents."""


def require(ok, reason):
    if not ok:
        raise VolumeLeaseRejected(reason)


@dataclass(frozen=True)
class ImagePin:
    """Explicit local supervisor observation, never untrusted caller authority."""
    path: str
    device: int
    inode: int
    size: int
    uid: int
    gid: int
    parent_device: int
    parent_inode: int

    def __post_init__(self):
        require(type(self.path) is str and 0 < len(self.path) <= 4096
                and self.path.startswith('/') and not self.path.startswith('//')
                and '\0' not in self.path and '\\' not in self.path,
                'volume_path_invalid')
        p = PurePosixPath(self.path)
        require(str(p) == self.path and p.name not in ('', '.', '..')
                and '..' not in p.parts and '.' not in self.path.split('/'),
                'volume_path_invalid')
        for name in ('device', 'inode', 'size', 'uid', 'gid', 'parent_device', 'parent_inode'):
            value = getattr(self, name)
            require(type(value) is int and 0 <= value < 2**63, 'volume_pin_invalid')
        require(self.inode > 0 and self.parent_inode > 0 and 4096 <= self.size <= 2**50
                and self.size % 4096 == 0, 'volume_pin_invalid')


def _parent(info, pin):
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
            and (info.st_dev, info.st_ino, info.st_uid, info.st_gid)
                == (pin.parent_device, pin.parent_inode, pin.uid, pin.gid),
            'volume_parent_identity')


def _image(info, pin):
    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_nlink == 1
            and (info.st_dev, info.st_ino, info.st_size, info.st_uid, info.st_gid)
                == (pin.device, pin.inode, pin.size, pin.uid, pin.gid),
            'volume_image_identity')


_ACTIVE = weakref.WeakSet()


class ImageLease:
    """Owns descriptors, not a serialized permission or file-descriptor API.

    Do not manually close/duplicate the private descriptors or release them
    while an image user lives. Methods are for one trusted controller thread.
    On fork, the child's copies close WITHOUT LOCK_UN, preserving the parent's
    flock. On exec, CLOEXEC prevents propagation. Parent teardown closes once.
    """
    def __init__(self, pin, parent_fd, image_fd):
        self._pin = pin
        self._parent_fd = parent_fd
        self._image_fd = image_fd
        self._pid = os.getpid()
        _ACTIVE.add(self)

    def confirm(self):
        require(self._pid == os.getpid() and self._image_fd is not None,
                'volume_lease_not_owned')
        pin = self._pin
        try:
            require(os.getuid() == os.geteuid() == pin.uid
                    and os.getgid() == os.getegid() == pin.gid, 'volume_controller_changed')
            parent = Path(pin.path).parent
            require(parent == parent.resolve(strict=True), 'volume_parent_changed')
            _parent(os.fstat(self._parent_fd), pin)
            _parent(parent.lstat(), pin)
            _image(os.fstat(self._image_fd), pin)
            _image(os.stat(Path(pin.path).name, dir_fd=self._parent_fd,
                           follow_symlinks=False), pin)
            require(not os.get_inheritable(self._image_fd)
                    and not os.get_inheritable(self._parent_fd), 'volume_descriptor_inheritable')
        except (OSError, ValueError, TypeError):
            raise VolumeLeaseRejected('volume_identity_unavailable') from None
        return {'version': 1, 'state': 'EXCLUSIVE_IMAGE_LEASE_HELD',
                'cooperatingControllersExcluded': True, 'advisoryLock': True,
                'contentOpenedForReading': False, 'writesPerformed': False,
                'existingMountsOrLoopsExcluded': False, 'profileWriterOwnership': False,
                'physicalDurabilityVerified': False, 'mountAuthorized': False,
                'fullGatewayPersistenceAccepted': False}

    def close(self):
        # Close only: LOCK_UN on a fork-shared open description could unlock
        # the parent's live lease. Never unlink/recreate the lock-bearing image.
        descriptors = (self._image_fd, self._parent_fd)
        self._image_fd = self._parent_fd = None
        _ACTIVE.discard(self)
        failed = False
        for descriptor in descriptors:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    failed = True
        require(not failed, 'volume_descriptor_close_failed')

    def __enter__(self):
        self.confirm()
        return self

    def __exit__(self, *unused):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def _after_fork_child():
    for lease in tuple(_ACTIVE):
        try:
            lease.close()
        except Exception:
            pass  # close errors never authorize child use; confirm rejects PID.


if sys.platform == 'linux':
    os.register_at_fork(after_in_child=_after_fork_child)


def acquire_image_lease(pin):
    """Acquire once/nonblocking on exact existing inode; no fallback or repair.

    The private parent and expected identities come from a trusted supervisor.
    Directory-FD-relative lookup pins the final parent. Ancestors must be under
    supervisor control; this is not protection against malicious host root or
    a compromised same-UID controller. Image content is intentionally not hashed
    here because a mounted filesystem legitimately mutates it.
    """
    require(sys.platform == 'linux', 'volume_linux_required')
    require(type(pin) is ImagePin, 'volume_trusted_pin_required')
    import fcntl
    parent_fd = image_fd = None
    lease = None
    try:
        require(os.getuid() == os.geteuid() == pin.uid
                and os.getgid() == os.getegid() == pin.gid, 'volume_controller_identity')
        path = Path(pin.path)
        require(path == path.resolve(strict=True), 'volume_noncanonical_path')
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        _parent(os.fstat(parent_fd), pin)
        image_fd = os.open(path.name, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                           dir_fd=parent_fd)
        _image(os.fstat(image_fd), pin)
        try:
            fcntl.flock(image_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
                raise VolumeLeaseRejected('volume_busy') from None
            raise
        lease = ImageLease(pin, parent_fd, image_fd)
        parent_fd = image_fd = None
        lease.confirm()
        return lease
    except VolumeLeaseRejected:
        if lease is not None:
            lease.close()
        raise
    except (OSError, ValueError, TypeError):
        if lease is not None:
            lease.close()
        raise VolumeLeaseRejected('volume_unavailable') from None
    finally:
        for descriptor in (image_fd, parent_fd):
            if descriptor is not None:
                os.close(descriptor)
