"""Single-profile lifecycle using the PINNED Hermes ownership implementation.

Run after the last exec/FD cleanup, under the final ordinary Gateway UID.
No new locking algorithm, database engine, mount or privilege transition.
The installation/import path must already be trusted. The caller must drain
ALL tasks/writers before finish; native registered writers are an extra guard,
not an inventory of unregistered code. Cooperative locking is NOT isolation
against malicious same-UID/same-process code or a persistent-volume solution.
"""
from __future__ import annotations
import os
from pathlib import Path
import stat
import sys
import threading
import gateway_storage_mounts as mounts


class ProfileLeaseRejected(RuntimeError):
    """Bounded reason; no profile pathname or native lock-record disclosure."""


def require(condition, reason):
    if not condition:
        raise ProfileLeaseRejected(reason)


def _actor():
    require(sys.platform == 'linux', 'profile_linux_required')
    require(threading.current_thread() is threading.main_thread(), 'profile_main_thread_required')
    uid, gid = os.getuid(), os.getgid()
    require(uid > 0 and gid > 0 and os.getresuid() == (uid,) * 3
            and os.getresgid() == (gid,) * 3, 'profile_final_identity_required')
    return os.getpid(), uid, gid, threading.get_ident()


def _native():
    # Normal import from the already pinned trusted runtime; no alternate loader.
    from gateway import runtime_ownership as native
    require(type(native.process_ownership) is native.ProfileOwnership,
            'profile_native_owner_required')
    return native


def _private(info, uid, gid, directory=False):
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    require(kind(info.st_mode) and info.st_uid == uid and info.st_gid == gid
            and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
            and (directory or info.st_nlink == 1), 'profile_private_object_required')
    stable = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)
    # Creating legitimate child directories changes parent nlink. File locks
    # must stay single-linked; the writable profile directory need not freeze.
    return stable if directory else (*stable, info.st_nlink)


def _prepared(home, actor):
    require(isinstance(home, (str, Path)), 'profile_path_required')
    home = Path(home)
    require(home.is_absolute() and home == home.resolve(strict=True)
            and not any(p.is_symlink() for p in (home, *home.parents)), 'profile_path_not_canonical')
    require(os.environ.get('HERMES_HOME') == str(home), 'profile_explicit_home_required')
    _, uid, gid, _ = actor
    parent = _private(home.lstat(), uid, gid, True)
    lock = _private((home / 'gateway.lock').lstat(), uid, gid)
    require(parent[0] == lock[0], 'profile_lock_other_device')
    return home, parent, lock


def _held(owner, home, actor, parent, lock):
    require(owner.homes == (home,), 'profile_reservation_set_changed')
    require(owner.owns(home) is True, 'profile_native_reservation_lost')
    _, current_parent, current_lock = _prepared(home, actor)
    require(current_parent == parent and current_lock == lock, 'profile_reserved_path_changed')
    handle = owner._handles.get(home)  # tied to the pinned native API, not JSON authority
    require(handle is not None and not handle.closed, 'profile_native_handle_missing')
    fd = handle.fileno()
    require(_private(os.fstat(fd), actor[1], actor[2]) == lock,
            'profile_open_lock_mismatch')
    require(not os.get_inheritable(fd), 'profile_lock_inheritable')
    return handle


class ProfileLease:
    """Process/thread-bound reservation; explicitly finish only after writers drain.

    Never use across fork/exec; a forked child's finish must not unlock its
    parent's open-file-description lock. No destructor or force-release path.
    """
    def __init__(self, owner, home, actor, parent, lock, handle, observation):
        self._owner, self._home, self._actor = owner, home, actor
        self._parent, self._lock, self._handle = parent, lock, handle
        self._observation = dict(observation)
        self._finished = False

    def check(self):
        try:
            require(not self._finished, 'profile_lease_finished')
            require(_actor() == self._actor, 'profile_lease_other_process_or_thread')
            with self._owner._mutex:
                require(_held(self._owner, self._home, self._actor, self._parent, self._lock)
                        is self._handle, 'profile_native_handle_changed')
            return {'state': 'NATIVE_PROFILE_RESERVED', 'profileCount': 1,
                    'nativeOwner': 'gateway.runtime_ownership.process_ownership',
                    'lockPathStillNamesHeldHandle': True, 'snapshotOnly': True,
                    'databaseOpened': False, 'allWritersInventoried': False,
                    'persistentVolumeIntegrated': False, 'launchAuthorized': False}
        except ProfileLeaseRejected:
            raise
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            raise ProfileLeaseRejected('profile_lease_unavailable') from None

    def finish(self):
        # The caller's current process identity is checked even after finish.
        require(_actor() == self._actor, 'profile_lease_other_process_or_thread')
        if self._finished:
            return
        with self._owner._mutex:
            self.check()
            # Reuse native close: it RETAINS all handles while registered writer
            # threads are alive. Never call release(home) to defeat that guard.
            self._owner.close()
            require(not self._owner.owns(self._home), 'profile_writers_still_active')
            require(self._handle.closed, 'profile_native_handle_not_closed')
            self._finished = True


def reserve_profile(profile_home, expected_mount):
    """Reserve a prepared profile before admission, reusing native ownership.

    Both databases MUST already exist on the expected local filesystem. The
    empty/private gateway.lock MUST be provisioned separately. Never adopt,
    repair or remove a foreign lock. No listener, database, provider or task is
    started here. Future fixed entrypoint must perform the remaining database,
    recovery and persistent-domain qualification before exposing admission.
    """
    owner = None
    acquired = False
    try:
        actor = _actor()
        home, parent, lock = _prepared(profile_home, actor)
        native = _native(); owner = native.process_ownership
        with owner._mutex:
            require(not owner.homes and not owner._writers, 'profile_native_owner_already_used')
            mounts.observe_profile_mounts(home, expected_mount)
            try:
                owner.reserve([home])
            except native.OwnershipConflict:
                raise ProfileLeaseRejected('profile_already_owned') from None
            acquired = True
            handle = _held(owner, home, actor, parent, lock)
            observation = mounts.observe_profile_mounts(home, expected_mount)
            require(_actor() == actor, 'profile_actor_changed')
            _held(owner, home, actor, parent, lock)
            return ProfileLease(owner, home, actor, parent, lock, handle, observation)
    except BaseException as exc:
        # A failed pre-admission reservation has not handed authority to any
        # workload. Clean up ONLY our newly acquired native reservation. Never
        # close a reservation that existed before this call or one now shared.
        if acquired and _actor() == actor:
            with owner._mutex:
                if owner.homes == (home,):
                    owner.close()  # native live-writer retention still applies
        if isinstance(exc, ProfileLeaseRejected):
            raise
        if isinstance(exc, (OSError, ValueError, AttributeError, KeyError, TypeError)):
            raise ProfileLeaseRejected('profile_reservation_unavailable') from None
        raise
