"""Opt-in S101 profile projection through the qualified G84E confinement.

Only trusted host-root startup in an existing supervised volume namespace.
No mounting an arbitrary host tree, provision, namespace join, workload dispatch
or legacy IPC gate activation. The caller MUST exit on any failure. This does
not perform native Hermes admission/recovery or claim durable media semantics.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

import gateway_projection as gp
import gateway_storage_mounts as storage
import state_volume_supervisor as supervisor
from state_image_lease import ImagePin

TARGET = '/run/alaz-state/profile'
REQUIRED = frozenset(('state.db', 'runs_idempotency.db', 'gateway.lock'))
ALLOWED = REQUIRED | frozenset(storage.SIDECAR_NAMES)
SAFE_FLAGS = gp.ipc.NOSUID | gp.ipc.NODEV | gp.ipc.NOEXEC
MINIMAL_LAYOUT = 'minimal-v1'
NATIVE_STORE_LAYOUT = 'hermes-native-stores-cold-v1'

def validate_layout(value):
    require(type(value) is str and value in (MINIMAL_LAYOUT,NATIVE_STORE_LAYOUT),
            'state_projection_layout_invalid')
    return value


class StateProjectionRejected(RuntimeError):
    """Bounded diagnostics; never database contents or credentials."""


def require(ok, reason):
    if not ok:
        raise StateProjectionRejected(reason)


def canonical(value):
    require(type(value) is str and 0 < len(value) <= 4096 and value.startswith('/')
            and not value.startswith('//') and '\x00' not in value and '\\' not in value,
            'state_projection_path')
    p = PurePosixPath(value)
    require(str(p) == value and '..' not in p.parts and '.' not in value.split('/'),
            'state_projection_path')
    return p


@dataclass(frozen=True)
class VolumeBinding:
    """Trusted per-run observations; a serialized copy is NOT launch authority."""
    image: ImagePin
    scope: str
    scope_identity: tuple[int, int]
    token: str
    controller_pid: int
    controller_start: int
    worker_pid: int
    worker_start: int
    namespace_inode: int
    mountpoint: str
    profile_inode: int
    loop_number: int
    fence_sha256: str

    def __post_init__(self):
        require(type(self.image) is ImagePin and self.image.uid == self.image.gid == 0,
                'state_projection_root_image')
        scope = canonical(self.scope); point = canonical(self.mountpoint)
        require(type(self.token) is str and re.fullmatch(r'[0-9a-f]{32}', self.token) is not None,
                'state_projection_token')
        require(scope.is_relative_to('/sys/fs/cgroup') and scope.name == 'volume-' + self.token
                and len(scope.parts) >= 6, 'state_projection_scope')
        require(point.is_relative_to('/srv') and len(point.parts) >= 4,
                'state_projection_mountpoint')
        require(type(self.scope_identity) is tuple and len(self.scope_identity) == 2
                and all(type(n) is int and 0 < n < 2**63 for n in self.scope_identity),
                'state_projection_scope_identity')
        for name in ('controller_pid','controller_start','worker_pid','worker_start',
                     'namespace_inode','profile_inode'):
            n = getattr(self, name)
            require(type(n) is int and 0 < n < 2**63, 'state_projection_identity')
        require(self.controller_pid != self.worker_pid, 'state_projection_same_pid')
        require(type(self.loop_number) is int and 0 <= self.loop_number < 65536,
                'state_projection_loop_number')
        require(type(self.fence_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', self.fence_sha256) is not None,
                'state_projection_fence_digest')


def process_start(pid):
    # Field 22 is the start time; comm may itself contain spaces/parentheses.
    text = (Path('/proc') / str(pid) / 'stat').read_text()
    fields = text.rsplit(')', 1)[1].split()
    require(len(fields) >= 20 and fields[0] not in ('Z', 'X'), 'state_projection_dead_process')
    return int(fields[19])


def _live_root(pid, start):
    require(pid != os.getpid() and process_start(pid) == start, 'state_projection_process_changed')
    status = {}
    for row in (Path('/proc') / str(pid) / 'status').read_text().splitlines():
        key, _, value = row.partition(':'); status[key] = value.split()
    require(status.get('Uid') == ['0'] * 4, 'state_projection_controller_not_root')


def validate_exports(binding, view, filesystem):
    require(type(binding) is VolumeBinding, 'state_projection_trusted_binding_required')
    source = PurePosixPath(binding.mountpoint) / 'profile'
    protected = [PurePosixPath(TARGET), source, PurePosixPath(binding.mountpoint)]
    exported = filesystem['readonly'] + filesystem['writable'] + filesystem['protected']
    exported += [view['root'], str(PurePosixPath(view['brokerSocket']).parent)]
    for name in exported:
        item = PurePosixPath(name)
        require(not any(item.is_relative_to(p) or p.is_relative_to(item) for p in protected),
                'state_projection_export_overlap')
    full = dict(filesystem)
    full['writable'] = list(filesystem['writable']) + [TARGET]
    return gp.fs_guard.validate_policy(full)


def _metadata(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def inspect_volume(binding, principal, *, joined_namespace=True, profile_layout=MINIMAL_LAYOUT):
    """Prove existing S101 authority and sole-user admission; never repair it."""
    require(type(binding) is VolumeBinding, 'state_projection_trusted_binding_required')
    validate_layout(profile_layout)
    supervisor.actor()
    try:
        _live_root(binding.controller_pid, binding.controller_start)
        _live_root(binding.worker_pid, binding.worker_start)
        require(os.readlink('/proc/' + str(binding.worker_pid) + '/ns/mnt') ==
                'mnt:[' + str(binding.namespace_inode) + ']', 'state_projection_worker_namespace')
        if joined_namespace:
            require(os.stat('/proc/self/ns/mnt').st_ino == binding.namespace_inode,
                    'state_projection_namespace_not_joined')
        scope = Path(binding.scope)
        require(supervisor.trusted(scope, directory=True) == binding.scope_identity
                and supervisor.fs_type(scope) == supervisor.CGROUP2_MAGIC,
                'state_projection_scope_changed')
        members = (scope / 'cgroup.procs').read_text().split()
        require(len(members) == 2 and set(members) == {str(binding.worker_pid), str(os.getpid())}
                and not any(p.is_dir() for p in scope.iterdir()), 'state_projection_other_volume_users')
        relative = scope.relative_to('/sys/fs/cgroup').as_posix()
        require('0::/' + relative in Path('/proc/self/cgroup').read_text().splitlines(),
                'state_projection_unregistered_user')
        fence = Path(binding.image.path + '.volume-owner.json')
        supervisor.trusted(fence)
        s = fence.stat()
        require(s.st_nlink == 1 and stat.S_IMODE(s.st_mode) == 0o600 and 0 < s.st_size < 16384,
                'state_projection_fence_metadata')
        raw = fence.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == binding.fence_sha256, 'state_projection_fence_changed')
        value = json.loads(raw)
        require(value == {'version':1,'token':binding.token,'controllerPid':binding.controller_pid,
                          'image':asdict(binding.image),'scope':binding.scope,'mountpoint':binding.mountpoint},
                'state_projection_fence_binding')
        rows = supervisor.attachments(binding.image)
        expected = {'device':binding.image.device,'inode':binding.image.inode,'offset':0,
                    'sizeLimit':0,'number':binding.loop_number,'flags':supervisor.AUTOCLEAR,'encryption':0}
        require(rows == [expected], 'state_projection_attachment_mismatch')
        mountpoint = Path(binding.mountpoint)
        supervisor.trusted(mountpoint, directory=True)
        require(os.path.ismount(mountpoint) and supervisor.fs_type(mountpoint) == 0xEF53,
                'state_projection_not_ext4_mount')
        records = storage.parse_mountinfo(storage._read_mountinfo())
        mounted = storage.select_mount(records, binding.mountpoint)
        require(mounted.mount_point == binding.mountpoint and mounted.root == '/'
                and mounted.filesystem == 'ext4' and mounted.device == (7, binding.loop_number)
                and {'rw','nosuid','nodev','noexec'} <= mounted.mount_options
                and 'rw' in mounted.super_options, 'state_projection_mount_flags')
        profile = mountpoint / 'profile'; s = profile.lstat()
        require(str(profile.resolve(strict=True)) == str(profile)
                and stat.S_ISDIR(s.st_mode) and stat.S_IMODE(s.st_mode) == 0o700
                and (s.st_dev,s.st_ino,s.st_uid,s.st_gid) == (os.makedev(7,binding.loop_number),
                    binding.profile_inode,principal['gatewayUid'],principal['socketGroupGid']),
                'state_projection_profile_identity')
        require(not any(PurePosixPath(r.mount_point).is_relative_to(profile) for r in records),
                'state_projection_nested_mount')
        if profile_layout == NATIVE_STORE_LAYOUT:
            import gateway_native_layout as native_layout
            try:
                objects = native_layout.inspect_profile(profile,uid=s.st_uid,gid=s.st_gid,device=s.st_dev)
            except native_layout.NativeLayoutRejected as exc:
                raise StateProjectionRejected(str(exc)) from None
        else:
            names = {p.name for p in profile.iterdir()}
            require(REQUIRED <= names <= ALLOWED, 'state_projection_profile_inventory')
            objects = {'profile':_metadata(s)}
            for name in sorted(names):
                item = (profile / name).lstat()
                require(stat.S_ISREG(item.st_mode) and item.st_nlink == 1
                        and stat.S_IMODE(item.st_mode) == 0o600 and item.st_dev == s.st_dev
                        and (item.st_uid,item.st_gid) == (s.st_uid,s.st_gid),
                        'state_projection_private_regular_file')
                objects[name] = _metadata(item)
        require(set(members) == set((scope/'cgroup.procs').read_text().split())
                and process_start(binding.worker_pid) == binding.worker_start
                and process_start(binding.controller_pid) == binding.controller_start,
                'state_projection_authority_changed')
        return objects
    except StateProjectionRejected:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, supervisor.SupervisorRejected):
        raise StateProjectionRejected('state_projection_observation_unavailable') from None


class _ProfileMounts(gp.Mounts):
    """One fixed pre-pivot extension; no override of the baseline UID/filter path."""
    def __init__(self, binding, principal, observed, profile_layout=MINIMAL_LAYOUT):
        super().__init__()
        self.binding, self.principal, self.observed = binding, principal, observed
        self.profile_layout = validate_layout(profile_layout)
        self.projected = False

    def pivot(self, root):
        require(not self.projected, 'state_projection_once')
        current = (inspect_volume(self.binding,self.principal,joined_namespace=False)
                   if self.profile_layout == MINIMAL_LAYOUT else
                   inspect_volume(self.binding,self.principal,joined_namespace=False,profile_layout=self.profile_layout))
        require(current == self.observed, 'state_projection_profile_changed')
        source = Path(self.binding.mountpoint)/'profile'
        target = root / TARGET.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir(exist_ok=False)
        self.mount(str(source), target, flags=gp.ipc.BIND)
        self.mount(None, target, flags=gp.ipc.BIND | gp.ipc.REMOUNT | SAFE_FLAGS)
        require(_metadata(target.lstat()) == self.observed['profile']
                and _metadata(source.lstat()) == self.observed['profile'], 'state_projection_bound_identity')
        flags = os.statvfs(target).f_flag
        require(flags & SAFE_FLAGS == SAFE_FLAGS and not flags & gp.ipc.RDONLY,
                'state_projection_bound_flags')
        self.projected = True
        super().pivot(root)


def enter(value, filesystem, binding, *, observe_self_mount=False, profile_layout=MINIMAL_LAYOUT):
    """Confine one joined root child; only its checked image profile persists.

    Caller joins the root-controlled S101 cgroup BEFORE the volume namespace.
    A complete production child launcher/admission pipeline is still required.
    Do not run a workload after any exception or return to the host caller.
    """
    validate_layout(profile_layout)
    require(type(observe_self_mount) is bool, 'state_projection_mount_observation_boolean')
    plan = gp.inspect(value, filesystem)
    full_policy = validate_exports(binding, plan['ipc'], plan['filesystem'])
    p = plan['ipc']['principalContract']
    observed = (inspect_volume(binding,p) if profile_layout == MINIMAL_LAYOUT else
                inspect_volume(binding,p,profile_layout=profile_layout))
    gp.fs_guard.abi_version(gp.fs_guard.kernel())
    seccomp = gp.net._load_seccomp()
    namespaces = {n:os.readlink('/proc/self/ns/'+n) for n in ('mnt','net','ipc')}
    gp.launch.close_ambient_fds()
    mounts = (_ProfileMounts(binding,p,observed) if profile_layout == MINIMAL_LAYOUT else
              _ProfileMounts(binding,p,observed,profile_layout))
    mounts.unshare(); gp._loopback_up()
    bound = gp._project(plan,mounts)
    require(mounts.projected, 'state_projection_not_projected')
    require(_metadata(Path(TARGET).lstat()) == observed['profile'], 'state_projection_final_identity')
    os.umask(0o077)
    gp.launch.drop_identity({'brokerUid':p['gatewayUid'],'socketGroupGid':p['socketGroupGid']})
    after = gp._verify_gateway(p,plan['before'],namespaces)
    gp.net._filter(seccomp)
    require(gp.net.status()['Seccomp'] == '2', 'state_projection_filter_missing')
    gp.launch.close_ambient_fds()
    landlock = (gp.fs_guard.apply(full_policy, self_mount_metadata=True) if observe_self_mount
                else gp.fs_guard.apply(full_policy))
    return {'version':1,'state':'confined_state_profile','pid':os.getpid(),
            'profile':TARGET,'profileDevice':observed['profile'][0],'profileInode':binding.profile_inode,
            'profileLayout':profile_layout,
            'persistentProfileProjected':True,'stateDirectoryCount':1,'ambientHostDirectoriesBound':0,
            'privateEphemeralDirectories':sum(n!='/dev/null' for n in plan['filesystem']['writable']),
            'hostUserNamespacePreserved':True,'rootPrivilegesDropped':True,'afterDrop':after,
            'boundRuntimeRoots':bound,'filesystem':landlock,'profileOwnershipAcquired':False,
            'nativeHermesStoresOpened':False,'realHermesGatewayTested':False,
            'legacyIpcV2Activated':False,'fullD3BAccepted':False}
