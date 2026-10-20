"""One-shot, opt-in broker UID launcher for a TRUSTED immutable Linux install.

Not a setuid helper, provisioner, daemon or Gateway sandbox. The supervisor must
already be authorized as host root, supply a root-owned contract and provision
the broker's private config, budget and empty socket directory. Never elevate
or retry under a different identity. On failure the dedicated process must exit.
The interpreter/dependencies and this code are part of the trusted installation.
"""
from __future__ import annotations
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import platform
import stat
import sys
import threading

import host_principal as hp
from combined_guard import command_digest
from credential_guard import unique_json
import linux_netns as net

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {'version', 'enabled', 'role', 'principalContract', 'python', 'config',
          'configSha256', 'output', 'commandSha256'}
CAPS = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')


class LaunchRejected(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise LaunchRejected(reason)


def command(value):
    return [value['python'], '-I', '-B', str(ROOT / 'scripts/run_provider_broker.py'),
            '--config', value['config'], '--output', value['output']]


def validate(value):
    require(type(value) is dict and set(value) == FIELDS, 'launch_contract_fields')
    require(type(value['version']) is int and value['version'] == 1
            and value['enabled'] is True, 'launch_opt_in_required')
    # No general executable/role passthrough and no unconfined Gateway fallback.
    require(value['role'] == 'broker', 'launch_broker_only_gateway_projection_pending')
    out = dict(value)
    out['principalContract'] = hp.policy(value['principalContract'])
    for key in ('python', 'config', 'output'):
        hp.canonical(value[key])
    require(len((value['output'] + '/egress.sock').encode()) <= 100,
            'launch_socket_path_too_long')
    require(not Path(value['config']).is_relative_to(Path(value['output']))
            and not Path(value['output']).is_relative_to(Path(value['config'])),
            'launch_config_output_overlap')
    for key in ('configSha256', 'commandSha256'):
        require(type(value[key]) is str and len(value[key]) == 64
                and all(c in '0123456789abcdef' for c in value[key]), 'launch_digest')
    require(command_digest(command(out)) == out['commandSha256'], 'launch_command_mismatch')
    return out


def observation():
    """Read kernel state, including real/effective/saved/filesystem IDs."""
    require(sys.platform == 'linux' and platform.machine() == 'x86_64',
            'launch_linux_x86_64_required')
    rows = {}
    for line in Path('/proc/self/status').read_text(encoding='ascii').splitlines():
        key, _, text = line.partition(':')
        if key in ('Uid', 'Gid', 'Groups', 'NoNewPrivs', 'Threads', *CAPS):
            require(key not in rows, 'launch_duplicate_kernel_field')
            rows[key] = text.split()
    require(set(rows) == {'Uid', 'Gid', 'Groups', 'NoNewPrivs', 'Threads', *CAPS},
            'launch_kernel_fields')
    require(len(rows['Uid']) == len(rows['Gid']) == 4
            and all(len(rows[k]) == 1 for k in ('NoNewPrivs', 'Threads', *CAPS)),
            'launch_kernel_field_shape')
    return {'pid': os.getpid(), 'uids': tuple(map(int, rows['Uid'])),
            'gids': tuple(map(int, rows['Gid'])), 'groups': tuple(map(int, rows['Groups'])),
            'threads': int(rows['Threads'][0]), 'nnp': int(rows['NoNewPrivs'][0]),
            'caps': {k: int(rows[k][0], 16) for k in CAPS},
            'userns': os.readlink('/proc/self/ns/user'),
            'uidMap': Path('/proc/self/uid_map').read_text().split(),
            'gidMap': Path('/proc/self/gid_map').read_text().split()}


def controller(value):
    state = observation()
    require(state['uids'] == (0, 0, 0, 0) and state['gids'] == (0, 0, 0, 0),
            'launch_authorized_host_root_required')
    require(state['userns'] == value['principalContract']['hostUserNamespace']
            and state['uidMap'] == ['0', '0', '4294967295']
            and state['gidMap'] == ['0', '0', '4294967295'],
            'launch_initial_user_namespace_required')
    require(state['threads'] == 1 and threading.active_count() == 1,
            'launch_single_thread_required')
    needed = (1 << 6) | (1 << 7) | (1 << 8)  # SETGID, SETUID, SETPCAP
    require(state['caps']['CapEff'] & needed == needed,
            'launch_controller_capabilities_required')
    return state


def trusted_ancestors(path, owners):
    """Reject replacement by Gateway-writable ancestors; no symlink traversal."""
    p = Path(hp.canonical(str(path)))
    for parent in (p.parent, *p.parent.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in owners
                and not stat.S_IMODE(info.st_mode) & 0o022,
                'launch_untrusted_parent')
    return p


def file_bytes(path, owner, mode, limit):
    p = trusted_ancestors(path, {0, owner})
    # NONBLOCK also prevents a malicious FIFO from hanging open before fstat.
    fd = os.open(p, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == owner
                and stat.S_IMODE(before.st_mode) == mode and before.st_nlink == 1
                and 0 < before.st_size <= limit, 'launch_private_file_metadata')
        data = bytearray()
        while len(data) <= limit:
            part = os.read(fd, min(8192, limit + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        after = os.fstat(fd)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_gid, s.st_mode,
                            s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(fields(before) == fields(after) == fields(p.lstat())
                and len(data) == before.st_size, 'launch_private_file_changed')
        return bytes(data)
    finally:
        os.close(fd)


def load_contract(path):
    require(sys.platform == 'linux' and os.getuid() == os.geteuid() == 0,
            'launch_authorized_host_root_required')
    return validate(unique_json(file_bytes(path, 0, 0o600, 32768).decode('utf-8')))


def trusted_install(value):
    """The invoking Python runtime/dependencies remain a supervisor trust input."""
    files = [Path(value['python']), ROOT / 'scripts/run_principal_broker.py',
             ROOT / 'scripts/run_provider_broker.py']
    package = ROOT / 'packages/claw-hermes'
    files.extend(package.glob('*.py'))
    require(package.is_dir() and len(files) > 3, 'launch_install_missing')
    for p in files:
        trusted_ancestors(p, {0})
        s = p.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1
                and not stat.S_IMODE(s.st_mode) & 0o6022,
                'launch_untrusted_install')
    require(os.access(value['python'], os.X_OK), 'launch_python_not_executable')


def deployment(value):
    principal = value['principalContract']
    uid, gid = principal['brokerUid'], principal['socketGroupGid']
    raw = file_bytes(value['config'], uid, 0o600, 32768)
    require(hashlib.sha256(raw).hexdigest() == value['configSha256'],
            'launch_config_changed')
    cfg = unique_json(raw.decode('utf-8'))
    require(type(cfg) is dict and cfg.get('principal_contract') == principal,
            'launch_config_principal_mismatch')
    # Invoke existing config validation too, with no network or provisioning.
    from provider_egress import BrokerConfig
    config = BrokerConfig(**cfg)
    authority = config.budget_authority
    require(type(authority) is dict and authority.get('enabled') is True,
            'launch_private_budget_required')
    trusted_ancestors(Path(authority['directory']) / 'budget.sqlite3', {0, uid})
    budget = hp.budget_identity(principal, authority['directory'])
    out = trusted_ancestors(value['output'], {0, uid})
    directory = hp.regular(str(out), 'dir', uid, gid, hp.SOCKET_DIR_MODE)
    require(not any(out.iterdir()), 'launch_socket_directory_not_empty')
    require(not Path(authority['directory']).is_relative_to(out)
            and not out.is_relative_to(Path(authority['directory'])),
            'launch_budget_socket_overlap')
    return {'directory': directory, 'budget': budget,
            'configSha256': hashlib.sha256(raw).hexdigest()}


def close_ambient_fds():
    for fd in (0, 1, 2):
        info = os.fstat(fd)
        require(stat.S_ISFIFO(info.st_mode) or
                (stat.S_ISCHR(info.st_mode) and info.st_rdev == os.makedev(1, 3)),
                'launch_stdio_must_be_pipe_or_devnull')
    for name in os.listdir('/proc/self/fd'):
        fd = int(name)
        if fd > 2:
            try:
                os.close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise


def drop_identity(principal):
    """Irreversible in this dedicated process; never continue after an error."""
    lib = ctypes.CDLL(None, use_errno=True)
    lib.prctl.restype = ctypes.c_int
    lib.capset.argtypes = [ctypes.POINTER(net.CapHeader), ctypes.POINTER(net.CapData)]
    lib.capset.restype = ctypes.c_int
    def prctl(*args):
        require(lib.prctl(*args) == 0, 'launch_privilege_syscall_failed')
    prctl(38, 1, 0, 0, 0)             # NO_NEW_PRIVS; does not prevent UID reduction
    prctl(8, 0, 0, 0, 0)              # no KEEP_CAPS
    prctl(47, 4, 0, 0, 0)             # clear ambient capabilities
    os.setgroups([])
    terminated = False
    for cap in range(64):
        result = lib.prctl(23, cap, 0, 0, 0)
        if result < 0:
            require(cap > 0 and ctypes.get_errno() == errno.EINVAL,
                    'launch_capability_read_failed')
            terminated = True
            break
        require(result in (0, 1), 'launch_capability_read_failed')
        prctl(24, cap, 0, 0, 0)       # drop bounding set while SETPCAP still effective
    require(terminated, 'launch_unknown_capability_range')
    gid, uid = principal['socketGroupGid'], principal['brokerUid']
    os.setresgid(gid, gid, gid)
    os.setresuid(uid, uid, uid)
    header = net.CapHeader(0x20080522, 0)
    empty = (net.CapData * 2)()
    require(lib.capset(ctypes.byref(header), empty) == 0, 'launch_capset_failed')
    prctl(4, 0, 0, 0, 0)              # dumpability; exec may reset, not a sandbox claim


def verify_target(value, before):
    hp.broker_identity(value['principalContract'])
    after = observation()
    p = value['principalContract']
    require(after['pid'] == before['pid']
            and after['userns'] == before['userns'] == p['hostUserNamespace']
            and after['uidMap'] == before['uidMap'] and after['gidMap'] == before['gidMap'],
            'launch_identity_namespace_changed')
    require(after['uids'] == (p['brokerUid'],) * 4
            and after['gids'] == (p['socketGroupGid'],) * 4
            and after['groups'] == () and after['threads'] == 1
            and after['nnp'] == 1 and all(after['caps'][k] == 0 for k in CAPS),
            'launch_privileges_remain')


def launch(value):
    """Replace this process by the existing broker only after verified reduction."""
    value = validate(value)          # detached copy; caller cannot change role/UID mid-launch
    before = controller(value)      # reject unprivileged/userns roots before touching files
    trusted_install(value)
    pinned = deployment(value)
    seccomp = net._load_seccomp()    # load from trusted runtime BEFORE UID change
    close_ambient_fds()
    os.chdir('/')
    os.umask(0o077)
    drop_identity(value['principalContract'])
    verify_target(value, before)
    require(deployment(value) == pinned, 'launch_deployment_changed')
    net._filter(seccomp)            # inherited denial of setns/mount/ptrace/FD receiving
    # No PATH search, shell, inherited environment, retries, daemonization or logs with secrets.
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/',
           'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    argv = command(value)
    os.execve(argv[0], argv, env)
    raise LaunchRejected('launch_exec_returned')
