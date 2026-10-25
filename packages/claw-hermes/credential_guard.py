"""Opt-in Linux Landlock ABI3 filesystem restriction for a fresh child process.

Not a network sandbox, separate UID, or protection from the trusted host.
Apply before untrusted imports/threads; unknown policy/kernel fails closed.
Public API ABI: Linux 6.6 include/uapi/linux/landlock.h and userspace docs.
"""
from __future__ import annotations
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat

HANDLED = (1 << 15) - 1
READ = (1 << 0) | (1 << 2) | (1 << 3)
FILE_READ = (1 << 0) | (1 << 2)
# Writable state cannot create devices or gain native executable permission.
WRITE = HANDLED & ~((1 << 0) | (1 << 6) | (1 << 11))
FILE_WRITE = (1 << 1) | (1 << 2) | (1 << 14)
FIELDS = {'version', 'enabled', 'readonly', 'writable', 'protected'}
BROAD = {'/', '/home', '/mnt', '/tmp', '/var', '/run', '/root', '/etc', '/dev'}

class GuardRejected(ValueError):
    """Bounded diagnostic only; never include credential content."""


def require(ok, reason):
    if not ok:
        raise GuardRejected(reason)


def unique_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'credential_guard_duplicate_key')
            out[key] = value
        return out
    require(type(text) is str and len(text.encode('utf-8')) <= 32768,
            'credential_guard_policy_size')
    try:
        return json.loads(text, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except GuardRejected:
        raise
    except Exception:
        raise GuardRejected('credential_guard_invalid_json') from None


def beneath(child, parent):
    return PurePosixPath(child).is_relative_to(PurePosixPath(parent))


def validate_policy(value):
    require(type(value) is dict and set(value) in (FIELDS, FIELDS | {'self_process_metadata'}),
            'credential_guard_policy_fields')
    require(type(value['version']) is int and value['version'] == 1,
            'credential_guard_version')
    require(value['enabled'] is True, 'credential_guard_optin_required')
    out = {'version': 1, 'enabled': True}
    if 'self_process_metadata' in value:
        require(type(value['self_process_metadata']) is bool, 'credential_guard_metadata_boolean')
        out['self_process_metadata'] = value['self_process_metadata']
    for name, limit in (('readonly', 64), ('writable', 16), ('protected', 16)):
        paths = value[name]
        require(type(paths) is list and 1 <= len(paths) <= limit,
                'credential_guard_path_count')
        for path in paths:
            require(type(path) is str and 0 < len(path.encode('utf-8')) <= 4096,
                    'credential_guard_path_type')
            p = PurePosixPath(path)
            require(p.is_absolute() and str(p) == path and '..' not in p.parts
                    and not path.startswith('//') and '\x00' not in path,
                    'credential_guard_path_not_canonical')
            if name != 'protected':
                require(path not in BROAD and not beneath(path, '/proc')
                        and not beneath(path, '/sys'), 'credential_guard_broad_grant')
                require(not beneath(path, '/dev') or path == '/dev/null'
                        or name == 'readonly' and path == '/dev/urandom',
                        'credential_guard_device_grant')
                if name == 'writable':
                    require(path != '/usr' and not beneath(path, '/usr')
                            and not beneath(path, '/etc') and len(p.parts) >= 3,
                            'credential_guard_system_write')
        require(len(paths) == len(set(paths)), 'credential_guard_duplicate_path')
        out[name] = sorted(paths)
    for protected in out['protected']:
        require(not any(beneath(protected, p) for p in out['readonly'] + out['writable']),
                'credential_guard_secret_in_granted_tree')
    for ro in out['readonly']:
        require(not any(beneath(ro, rw) or beneath(rw, ro) for rw in out['writable']),
                'credential_guard_overlapping_access')
    return out


def policy_digest(policy):
    return hashlib.sha256(json.dumps(policy, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()


class Ruleset(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


class PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def kernel():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64',
            'credential_guard_unsupported_platform')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc


def abi_version(libc):
    abi = libc.syscall(ctypes.c_long(444), ctypes.c_void_p(), ctypes.c_size_t(0),
                       ctypes.c_uint32(1))
    require(abi >= 3, 'credential_guard_landlock_abi3_required')
    return abi


def _preflight(policy):
    require(len(os.listdir('/proc/self/task')) == 1,
            'credential_guard_existing_threads')
    protected_inodes = set()
    for name in ('readonly', 'writable', 'protected'):
        for value in policy[name]:
            p = Path(value)
            require(p.exists() and not p.is_symlink() and str(p.resolve()) == value,
                    'credential_guard_path_changed')
            s = p.stat()
            ordinary = stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)
            require(ordinary or value in ('/dev/null', '/dev/urandom') and stat.S_ISCHR(s.st_mode),
                    'credential_guard_special_file')
            if name == 'protected':
                require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1,
                        'credential_guard_protected_alias')
                protected_inodes.add((s.st_dev, s.st_ino))
    # Some relocatable Python builds retain a read-only FD to their own ELF.
    # Close only that verified executable FD, never permit other ambient FDs.
    import fcntl
    executable = Path('/proc/self/exe').stat()
    closed_executable_fds = 0
    # /proc listing opens a temporary FD which is closed before fstat below.
    for raw in os.listdir('/proc/self/fd'):
        fd = int(raw)
        try:
            info = os.fstat(fd)
        except OSError as ex:
            if ex.errno == errno.EBADF:
                continue
            raise
        if fd > 2:
            target = os.readlink('/proc/self/fd/' + raw)
            exact_executable = (info.st_dev, info.st_ino) == (executable.st_dev, executable.st_ino)
            readonly = (fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE) == os.O_RDONLY
            require(exact_executable and readonly and any(beneath(target, p) for p in policy['readonly']),
                    'credential_guard_inherited_fd')
            os.close(fd)
            closed_executable_fds += 1
            continue
        require(not stat.S_ISSOCK(info.st_mode), 'credential_guard_socket_stdio')
        require((info.st_dev, info.st_ino) not in protected_inodes,
                'credential_guard_secret_stdio')
        if stat.S_ISREG(info.st_mode):
            target = os.readlink('/proc/self/fd/' + raw)
            allowed = policy['readonly'] + policy['writable'] if fd == 0 else policy['writable']
            require(any(beneath(target, p) for p in allowed),
                    'credential_guard_ungranted_stdio')
    return closed_executable_fds


def self_metadata_paths(pid, *, mountinfo=False, identity_maps=False):
    """Fixed self-only process identity files plus system boot-time statistics.

    Never expose /proc directories, arbitrary PIDs, environ, mem, fd or exe.
    Evaluated at launch; exec keeps the PID. A descendant gets no new grant.
    """
    require(type(pid) is int and pid > 0, 'credential_guard_metadata_pid')
    require(type(mountinfo) is bool, 'credential_guard_mount_metadata_boolean')
    require(type(identity_maps) is bool, 'credential_guard_identity_metadata_boolean')
    return tuple('/proc/' + str(pid) + '/' + name
                 for name in ('stat', 'status', 'statm', 'cmdline')) + ('/proc/stat',) + (
                     ('/proc/' + str(pid) + '/mountinfo',) if mountinfo else ()) + (
                     tuple('/proc/' + str(pid) + '/' + name for name in ('uid_map', 'gid_map'))
                     if identity_maps else ())


def apply(policy, *, self_mount_metadata=False, self_identity_metadata=False):
    """Irreversibly restrict only this fresh process and future descendants.

    Any failure is fatal to the caller: do not continue the intended workload.
    Does not try to revoke already-open descriptors in sibling processes.
    """
    require(type(self_mount_metadata) is bool, 'credential_guard_mount_metadata_boolean')
    require(type(self_identity_metadata) is bool, 'credential_guard_identity_metadata_boolean')
    policy = validate_policy(policy)
    require(not self_mount_metadata or policy.get('self_process_metadata') is True,
            'credential_guard_mount_metadata_requires_self')
    require(not self_identity_metadata or policy.get('self_process_metadata') is True,
            'credential_guard_identity_metadata_requires_self')
    libc = kernel()
    abi = abi_version(libc)
    closed_executable_fds = _preflight(policy)
    ruleset = Ruleset(HANDLED)
    handle = libc.syscall(ctypes.c_long(444), ctypes.byref(ruleset),
                           ctypes.c_size_t(ctypes.sizeof(ruleset)), ctypes.c_uint32(0))
    require(handle >= 0, 'credential_guard_ruleset_failed')
    try:
        for name in ('readonly', 'writable'):
            for value in policy[name]:
                fd = os.open(value, os.O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
                try:
                    info = os.fstat(fd)
                    require((info.st_dev, info.st_ino) ==
                            (Path(value).stat().st_dev, Path(value).stat().st_ino),
                            'credential_guard_path_changed')
                    access = (READ if stat.S_ISDIR(info.st_mode) else FILE_READ) if name == 'readonly' else (
                              WRITE if stat.S_ISDIR(info.st_mode) else FILE_WRITE)
                    rule = PathRule(access, fd)
                    rc = libc.syscall(ctypes.c_long(445), ctypes.c_int(handle),
                                      ctypes.c_int(1), ctypes.byref(rule), ctypes.c_uint32(0))
                    require(rc == 0, 'credential_guard_add_rule_failed')
                finally:
                    os.close(fd)
        # Caller selects only the fixed self-map pair; never accept a PID/path from policy JSON.
        identity_options = {'identity_maps': True} if self_identity_metadata else {}
        metadata = self_metadata_paths(os.getpid(), mountinfo=self_mount_metadata,
            **identity_options) if policy.get('self_process_metadata', False) else ()
        for value in metadata:
            require(value not in policy['protected'], 'credential_guard_protected_metadata')
            fd = os.open(value, os.O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                require(stat.S_ISREG(os.fstat(fd).st_mode), 'credential_guard_metadata_file')
                # READ_FILE only: no executable, writable, directory or process-memory grant.
                rule = PathRule(1 << 2, fd)
                rc = libc.syscall(ctypes.c_long(445), ctypes.c_int(handle),
                                  ctypes.c_int(1), ctypes.byref(rule), ctypes.c_uint32(0))
                require(rc == 0, 'credential_guard_metadata_rule_failed')
            finally:
                os.close(fd)
        require(libc.prctl(38, 1, 0, 0, 0) == 0, 'credential_guard_no_new_privs_failed')
        require(libc.syscall(ctypes.c_long(446), ctypes.c_int(handle), ctypes.c_uint32(0)) == 0,
                'credential_guard_enforcement_failed')
    finally:
        os.close(handle)
    require(libc.prctl(39, 0, 0, 0, 0) == 1, 'credential_guard_no_new_privs_missing')
    # Verify deny on the protected files without returning or reading content.
    denied = 0
    for value in policy['protected']:
        try:
            fd = os.open(value, os.O_RDONLY | os.O_CLOEXEC)
        except OSError as ex:
            require(ex.errno in (errno.EACCES, errno.EPERM),
                    'credential_guard_protected_check_unknown')
            denied += 1
        else:
            os.close(fd)
            raise GuardRejected('credential_guard_protected_read_permitted')
    effective_policy = policy
    if self_mount_metadata:
        effective_policy = effective_policy | {'self_mount_metadata': True}
    if self_identity_metadata:
        effective_policy = effective_policy | {'self_identity_metadata': True}
    result = {'version': 1, 'state': 'enforced', 'landlockAbi': abi,
            'handledFilesystemRights': HANDLED, 'noNewPrivs': True,
            'closedSelfExecutableFds': closed_executable_fds,
            'protectedReadDenials': denied,
            'policySha256': policy_digest(effective_policy),
            'scope': 'Landlock ABI3 filesystem opens; not network/UID/metadata isolation',
            'selfProcessMetadata': bool(policy.get('self_process_metadata', False)),
            'metadataReadFileCount': len(metadata), 'selfMountMetadata': self_mount_metadata,
            'networkConfinementVerified': False, 'separateHostUid': False}
    if self_identity_metadata:
        result['selfIdentityMetadata'] = True
    return result
