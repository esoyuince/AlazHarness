"""Trusted one-shot Gateway confinement primitive; not a production launcher.

Invoked only by an authorized fresh host-root supervisor in an immutable
installation. No elevation, fallback, provider call or user-namespace remap.
Writable directories become EMPTY PRIVATE TMPFS, not persisted host state.
Legacy ipc_view.prepare/project gates remain unchanged. Every failure is fatal
to the dedicated child: the caller MUST exit instead of running its workload.
"""
from __future__ import annotations
import ctypes
import os
from pathlib import Path, PurePosixPath
import socket
import stat
import struct

import credential_guard as fs_guard
import host_principal as hp
import ipc_view as ipc
import linux_netns as net
import principal_launch as launch

NEWNET = 0x40000000
NEWIPC = 0x08000000
PRIVATE_FLAGS = ipc.NEWNS | NEWNET | NEWIPC  # deliberately NO CLONE_NEWUSER


class ProjectionRejected(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise ProjectionRejected(reason)


def validate(value, filesystem):
    view, fs = ipc.validate(value, filesystem)
    require(view['version'] == 2, 'projection_principal_v2_required')
    require(fs.get('self_process_metadata') is True, 'projection_self_metadata_required')
    parent = PurePosixPath(view['brokerSocket']).parent
    for path in fs['readonly'] + fs['writable'] + fs['protected']:
        p = PurePosixPath(path)
        require(not p.is_relative_to(parent) and not parent.is_relative_to(p),
                'projection_broker_parent_export_overlap')
        require(path not in ('/opt', '/srv') and not p.is_relative_to('/proc')
                and not p.is_relative_to('/sys'), 'projection_reserved_export')
    require(any(p != '/dev/null' for p in fs['writable']), 'projection_private_workspace_required')
    # Return detached existing validators' results, not mutable caller authority.
    return view, fs


def metadata(path):
    s = Path(path).lstat()
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink)


def _path(path):
    p = Path(path)
    require(p.exists() and not p.is_symlink() and str(p.resolve()) == path,
            'projection_noncanonical_source')
    return p


def _root_controlled(p):
    s = p.lstat()
    require(s.st_uid == 0 and (stat.S_ISLNK(s.st_mode) or
            not stat.S_IMODE(s.st_mode) & 0o022), 'projection_untrusted_readonly')


def inspect(value, filesystem):
    """Read-only preparation; requires already-authorized host root."""
    view, fs = validate(value, filesystem)
    before = launch.controller({'principalContract': view['principalContract']})
    needed = (1 << 21) | (1 << 12)  # SYS_ADMIN, NET_ADMIN, beyond existing UID-drop caps
    require(before['caps']['CapEff'] & needed == needed, 'projection_controller_caps')
    root = _path(view['root'])
    root_info = root.lstat(); temporary = root.parent.lstat()
    require(stat.S_ISDIR(root_info.st_mode) and root_info.st_uid == root_info.st_gid == 0
            and stat.S_IMODE(root_info.st_mode) == 0o700 and not os.path.ismount(root)
            and not any(root.iterdir()), 'projection_root_not_owned_empty')
    require(root.parent == Path('/tmp') and temporary.st_uid == 0
            and stat.S_ISDIR(temporary.st_mode)
            and stat.S_IMODE(temporary.st_mode) == 0o1777, 'projection_anchor_parent')
    proof = ipc.inspect_principal_socket(view, fs)
    objects = {}; count = 0; p = view['principalContract']
    for category in ('readonly', 'writable', 'protected'):
        for path in fs[category]:
            item = _path(path); s = item.lstat()
            # No gateway-writable ancestors may select a different export.
            launch.trusted_ancestors(item, {0})
            if path in ('/dev/null', '/dev/urandom'):
                expected = os.makedev(1, 3 if path == '/dev/null' else 9)
                require(stat.S_ISCHR(s.st_mode) and s.st_uid == 0 and s.st_rdev == expected,
                        'projection_device_identity')
            elif category == 'writable':
                require(stat.S_ISDIR(s.st_mode) and not os.path.ismount(item)
                        and s.st_uid == p['gatewayUid'] and s.st_gid == p['socketGroupGid']
                        and stat.S_IMODE(s.st_mode) == 0o700 and not any(item.iterdir()),
                        'projection_ephemeral_workspace_must_be_empty')
            else:
                _root_controlled(item)
                require(stat.S_ISREG(s.st_mode) or category == 'readonly' and stat.S_ISDIR(s.st_mode),
                        'projection_regular_export')
                if category == 'protected':
                    require(s.st_nlink == 1, 'projection_protected_hardlink')
                if item.is_dir():
                    entries, hidden = ipc.inspect_tree(item)
                    require(not hidden, 'projection_nested_mount_refused')
                    count += entries
                    require(count <= ipc.MAX_ENTRIES, 'projection_tree_limit')
                    for current, dirs, names in os.walk(item, followlinks=False):
                        for name in dirs + names:
                            _root_controlled(Path(current) / name)
            objects[path] = metadata(item)
    return {'ipc': view, 'filesystem': fs, 'before': before, 'objects': objects,
            'anchor': metadata(root), 'socket': proof['socketPrincipal'], 'scanned': count}


class Mounts:
    """Small syscall adapter. Call only in a disposable, single-threaded child."""
    def __init__(self):
        self.lib = ctypes.CDLL(None, use_errno=True)
        self.lib.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                                   ctypes.c_ulong, ctypes.c_char_p]
        self.lib.mount.restype = ctypes.c_int
        self.lib.unshare.argtypes = [ctypes.c_int]; self.lib.unshare.restype = ctypes.c_int
        self.lib.umount2.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.umount2.restype = ctypes.c_int
        self.lib.syscall.restype = ctypes.c_long

    def check(self, result, label):
        if result < 0:
            raise ProjectionRejected(label + ':' + str(ctypes.get_errno()))

    def unshare(self):
        self.check(self.lib.unshare(PRIVATE_FLAGS), 'projection_unshare')

    def mount(self, source, target, kind=None, flags=0, data=None):
        self.check(self.lib.mount(os.fsencode(source) if source else None,
                   os.fsencode(target), kind.encode() if kind else None, flags,
                   data.encode() if data else None), 'projection_mount')

    def pivot(self, root):
        (root / '.old-root').mkdir()
        os.chdir(root)
        self.check(self.lib.syscall(ctypes.c_long(155), ctypes.c_char_p(b'.'),
                                   ctypes.c_char_p(b'.old-root')), 'projection_pivot')
        os.chdir('/')
        self.check(self.lib.umount2(b'/.old-root', ipc.DETACH), 'projection_old_root_detach')
        os.rmdir('/.old-root')


def _loopback_up():
    import fcntl
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        request = struct.pack('16sH', b'lo', 0)
        flags = struct.unpack('16sH', fcntl.ioctl(control.fileno(), 0x8913, request))[1]
        fcntl.ioctl(control.fileno(), 0x8914, struct.pack('16sH', b'lo', flags | 1))
    require(socket.if_nameindex() == [(1, 'lo')], 'projection_network_not_private')


def _project(plan, mounts):
    view, fs = plan['ipc'], plan['filesystem']; root = Path(view['root'])
    require(metadata(root) == plan['anchor'] and not any(root.iterdir()), 'projection_anchor_changed')
    hp.pinned_socket(view['principalContract'], view['brokerSocket'], plan['socket'])
    for name, expected in plan['objects'].items():
        require(metadata(_path(name)) == expected, 'projection_export_changed')
    mounts.mount(None, '/', flags=ipc.REC | ipc.PRIVATE)
    mounts.mount('tmpfs', root, 'tmpfs', ipc.NOSUID | ipc.NODEV, 'size=16m,mode=755')
    mounted = 0

    def destination(source, directory):
        target = root / source.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        if directory: target.mkdir(exist_ok=False)
        else: target.touch(exist_ok=False)
        return target

    def bind(source, device=False):
        nonlocal mounted
        expected = metadata(source)
        target = destination(source, Path(source).is_dir())
        # Nested mounts were refused; no recursive host mount cloning.
        mounts.mount(source, target, flags=ipc.BIND)
        flags = ipc.BIND | ipc.REMOUNT | ipc.NOSUID
        flags |= (0 if device else ipc.NODEV) | (0 if source == '/dev/null' else ipc.RDONLY)
        flags |= os.statvfs(source).f_flag & (ipc.RDONLY | ipc.NOSUID | ipc.NODEV | ipc.NOEXEC)
        mounts.mount(None, target, flags=flags)
        require(metadata(source) == expected == metadata(target), 'projection_bound_inode_changed')
        mounted += 1

    for name in fs['readonly']: bind(name, device=name == '/dev/urandom')
    for name in fs['writable']:
        if name == '/dev/null': bind(name, device=True)
        else:
            target = destination(name, True); p = view['principalContract']
            mounts.mount('tmpfs', target, 'tmpfs', ipc.NOSUID | ipc.NODEV | ipc.NOEXEC,
                         'size=16m,mode=700,uid=' + str(p['gatewayUid']) + ',gid=' + str(p['socketGroupGid']))
    for name in fs['protected']: bind(name)
    hp.pinned_socket(view['principalContract'], view['brokerSocket'], plan['socket'])
    bind(view['brokerSocket'])
    synthetic = root / str(PurePosixPath(view['brokerSocket']).parent).lstrip('/')
    p = view['principalContract']
    os.chown(synthetic, p['brokerUid'], p['socketGroupGid']); os.chmod(synthetic, hp.SOCKET_DIR_MODE)
    # Full subtree needed only for launch-time validation; Landlock subsequently
    # permits fixed self metadata files, never fd/mem/other-process read access.
    pid = os.getpid(); bind('/proc/' + str(pid)); bind('/proc/stat')
    (root / 'proc/self').symlink_to(str(pid))
    for alias, target in (('bin', 'usr/bin'), ('sbin', 'usr/sbin'), ('lib', 'usr/lib'), ('lib64', 'usr/lib64')):
        if (root / target).exists() and not (root / alias).exists():
            (root / alias).symlink_to(target)
    hp.pinned_socket(p, view['brokerSocket'], plan['socket'])
    mounts.pivot(root)
    mounts.mount(None, '/', flags=ipc.REMOUNT | ipc.RDONLY | ipc.NOSUID | ipc.NODEV | ipc.NOEXEC)
    observed = hp.socket_identity(p, view['brokerSocket'])
    require(observed['socket'] == plan['socket']['socket'], 'projection_socket_not_pinned')
    require(not any(Path(n).exists() for n in ('/.old-root', '/mnt/c', '/run/WSL', '/proc/1')),
            'projection_ambient_root_visible')
    return mounted


def _verify_gateway(principal, before, namespaces):
    hp.gateway_identity(principal)
    after = launch.observation()
    require(after['pid'] == before['pid'] and after['uids'] == (principal['gatewayUid'],) * 4
            and after['gids'] == (principal['socketGroupGid'],) * 4
            and after['groups'] == () and after['threads'] == 1 and after['nnp'] == 1
            and all(after['caps'][k] == 0 for k in launch.CAPS), 'projection_privileges_remain')
    require(after['userns'] == before['userns'] == principal['hostUserNamespace']
            and after['uidMap'] == before['uidMap'] and after['gidMap'] == before['gidMap'],
            'projection_host_identity_changed')
    for name, old in namespaces.items():
        require(os.readlink('/proc/self/ns/' + name) != old, 'projection_namespace_unchanged')
    return after


def enter(value, filesystem):
    """Confine this dedicated process; caller must exit on EVERY exception.

    Only an existing trusted host-root controller can enter. Return is NOT
    authorization to launch an arbitrary task, a persistence guarantee, or
    activation of the legacy combined guard/IPC v2 path.
    """
    plan = inspect(value, filesystem)
    p = plan['ipc']['principalContract']
    fs_guard.abi_version(fs_guard.kernel())  # fail before namespace side effects
    seccomp = net._load_seccomp()
    namespaces = {n: os.readlink('/proc/self/ns/' + n) for n in ('mnt', 'net', 'ipc')}
    launch.close_ambient_fds()
    mounts = Mounts(); mounts.unshare(); _loopback_up()
    bound = _project(plan, mounts)
    os.umask(0o077)
    # Reuse the exact UID/GID reduction mechanism, selecting Gateway explicitly;
    # this tiny internal argument is NOT a forged host-principal contract.
    launch.drop_identity({'brokerUid': p['gatewayUid'], 'socketGroupGid': p['socketGroupGid']})
    after = _verify_gateway(p, plan['before'], namespaces)
    net._filter(seccomp)
    require(net.status()['Seccomp'] == '2', 'projection_filter_missing')
    launch.close_ambient_fds()
    landlock = fs_guard.apply(plan['filesystem'])
    return {'version': 1, 'state': 'confined', 'pid': os.getpid(), 'gatewayUid': p['gatewayUid'],
            'hostUserNamespacePreserved': True, 'privateNetworkMountIpcNamespaces': True,
            'explicitHostSocketCount': 1, 'socketIdentity': plan['socket']['socket'],
            'syntheticSocketParent': True, 'oldRootDetached': True, 'boundRoots': bound,
            'privateEphemeralWritableDirectories': sum(n != '/dev/null' for n in plan['filesystem']['writable']),
            'hostWritableDirectoriesBound': 0, 'afterDrop': after, 'filesystem': landlock,
            'fullHermesGatewayTested': False, 'persistentGatewayState': False,
            'legacyIpcV2Activated': False, 'fullD3BAccepted': False}
