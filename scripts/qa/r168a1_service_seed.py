"""Task-free real service-profile producer for the unchanged R167 installation.

This separate QA file never starts a listener or task. Unknown native effects
retain the original process, loop and references; no automatic cleanup/retry.
The audit/profile tripwires are cooperative observations, not a sandbox.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import socket
import sqlite3
import stat
import sys
import sysconfig
import threading
import time
import types

LAB = 'AlazHarness-D3B-P71C'
INSTALLATION = Path('/opt/alaz-r167a1')
INPUT = Path('/opt/alaz-r167a1-input')
DEPENDENCIES = Path('/opt/alaz-f126c1a6/dependencies')
PYTHON = '/usr/bin/python3.12'
GATEWAY_UID, SOCKET_GID = 23001, 23003
SUPPORT = INPUT / 'qa/r167a1_import_probe.py'
SUPPORT_SHA = '9261a63ab741cefe0df32296cdced122e29e420278075bb8a5f295de2b826bab'
INSTALLER = INPUT / 'scripts/install_service_candidate.py'
INSTALLER_SHA = 'bc014b7e4f9ac2a0c6d170e80501eee5e458d526a2b21c4f076bfa4f590de30a'
RECEIPT_SHA = '0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f'
HARNESS = '1600eba430562795b9114209d1168bfa0d6ea5fd'
NATIVE = '5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d'
MANIFEST = 'a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8'
ARCHIVE = '43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a'
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
NODE_SHA = 'e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb'
IPV6_NAME = 'urllib3/util/connection.py'
IPV6_PATH = str(INSTALLATION / 'dependencies' / IPV6_NAME)
IPV6_SHA = '2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74'
MAX_SOURCE = 4 * 1024 * 1024
MAX_CONFIG, MAX_RESULT, MAX_DISCOVERY = 65536, 65536, 262144
MAX_CANDIDATES = 1024
MAX_ELAPSED_MILLIS = 60000
HELPERS = ('run_store_preopen.py', 'run_response_preopen.py')
FORBIDDEN_NATIVE_CALLS = frozenset((
    'run_api_turn', 'execute_finite_admission', 'run_conversation',
    '_build_fresh_agent', 'commit_and_publish', 'settle_session_input',
))
_attempt = None


class SeedRejected(ValueError):
    pass


def require(value, reason):
    if not value:
        raise SeedRejected(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def decimal(value):
    require(type(value) is str and re.fullmatch('[1-9][0-9]{0,19}', value) is not None,
            'seed_decimal')
    number = int(value)
    require(number < 2**64, 'seed_decimal')
    return number


def digest(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None,
            'seed_digest')
    return value


def canonical_path(value):
    require(type(value) is str and 1 < len(value) <= 4096 and '\x00' not in value
            and '\\' not in value and not value.startswith('//'), 'seed_path')
    path = PurePosixPath(value)
    require(path.is_absolute() and str(path) == value and '..' not in path.parts
            and '.' not in value.split('/'), 'seed_path')
    return Path(value)


def validate_arguments(args):
    home, config = canonical_path(args.home), canonical_path(args.config_file)
    require(type(args.instance_id) is str
            and re.fullmatch('[A-Za-z0-9._-]{1,128}', args.instance_id), 'seed_instance')
    for name in ('parent_pid', 'parent_start_ticks', 'expected_profile_device',
                 'expected_profile_inode', 'expected_mount_namespace_inode'):
        value = getattr(args, name)
        require(type(value) is int and 0 < value < 2**64, 'seed_identity_argument')
    require(args.parent_pid < 2**31, 'seed_parent_argument')
    require(type(args.expected_user_namespace) is str
            and re.fullmatch(r'user:\[[1-9][0-9]{0,19}\]', args.expected_user_namespace),
            'seed_namespace_argument')
    digest(args.expected_config_sha256)
    digest(args.expected_seed_sha256)
    require(not any(home == p or p in home.parents or home in p.parents
                    for p in (INSTALLATION, INPUT, DEPENDENCIES)), 'seed_home_overlap')
    require(config != home and home not in config.parents, 'seed_input_inside_profile')
    return home, config


def process_start(pid):
    raw = Path('/proc/' + str(pid) + '/stat').read_text(encoding='ascii')
    require(len(raw) <= 8192 and raw.startswith(str(pid) + ' ('), 'seed_process_stat')
    return int(raw.rsplit(')', 1)[1].split()[19])


def validate_parent(args):
    require(os.getppid() == args.parent_pid and os.getpid() != args.parent_pid
            and process_start(args.parent_pid) == args.parent_start_ticks,
            'seed_parent_changed')
    rows = Path('/proc/' + str(args.parent_pid) + '/status').read_text().splitlines()
    uids = [row.split()[1:] for row in rows if row.startswith('Uid:')]
    require(uids == [['0', '0', '0', '0']], 'seed_root_parent_required')


def validate_actor(args):
    require(sys.platform == 'linux' and platform.machine() == 'x86_64'
            and platform.python_implementation() == 'CPython'
            and sys.version_info[:3] == (3, 12, 3) and sys.executable == PYTHON,
            'seed_fixed_interpreter')
    require(sys.flags.isolated == 1 and sys.flags.no_site == 1
            and sys.dont_write_bytecode and not sys.flags.optimize,
            'seed_interpreter_flags')
    require(Path('/etc/alaz-p71c-lab-id').read_text().strip() == LAB
            and os.environ.get('WSL_DISTRO_NAME', LAB) == LAB
            and not Path('/mnt/c/Windows').exists(), 'seed_wrong_lab')
    require(os.getresuid() == (GATEWAY_UID,) * 3 and os.getresgid() == (SOCKET_GID,) * 3
            and set(os.getgroups()) <= {SOCKET_GID}, 'seed_ordinary_actor')
    require(os.readlink('/proc/self/ns/user') == args.expected_user_namespace
            and Path('/proc/self/ns/mnt').stat().st_ino == args.expected_mount_namespace_inode,
            'seed_namespace_changed')
    validate_parent(args)
    require(threading.current_thread() is threading.main_thread()
            and threading.active_count() == 1 and sys.getprofile() is None,
            'seed_fresh_process')
    forbidden = ('gateway', 'gateway_', 'hermes_', 'hermes_cli', 'tools', 'agent',
                 'run_agent', 'model_tools')
    require(not any(name == prefix or name.startswith(prefix + '.')
                    or prefix.endswith('_') and name.startswith(prefix)
                    for name in sys.modules for prefix in forbidden),
            'seed_native_already_imported')


def home_identity(home, args, *, fresh):
    require(home.resolve(strict=True) == home
            and not any(p.is_symlink() for p in (home, *home.parents)), 'seed_home_alias')
    fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
                and (info.st_uid, info.st_gid) == (GATEWAY_UID, SOCKET_GID)
                and (info.st_dev, info.st_ino) ==
                (args.expected_profile_device, args.expected_profile_inode), 'seed_home_identity')
        if fresh:
            require(not os.listdir(fd), 'seed_home_not_empty')
        require(stamp(home.lstat())[:5] == stamp(info)[:5], 'seed_home_changed')
        return info.st_dev, info.st_ino
    finally:
        os.close(fd)


def trusted_source(path, expected, *, limit=MAX_SOURCE):
    digest(expected)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'seed_source_alias')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'seed_source_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022
                and 0 < info.st_size <= limit, 'seed_source_metadata')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        require(len(raw) == info.st_size and sha(raw) == expected
                and stamp(info) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                'seed_source_changed')
        return raw
    finally:
        os.close(fd)


def source_identity(expected):
    path = Path(__file__)
    require(path.is_absolute() and path.name == 'r168a1_service_seed.py'
            and main.__code__.co_filename == str(path), 'seed_file_backed_source')
    raw = trusted_source(path, expected)
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw),
            'mode': 'root_controlled_file', 'fileBackedIdentityClaimed': True}


def config_document(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_CONFIG, 'seed_config_size')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'seed_config_duplicate')
            value[key] = item
        return value
    def integer(value):
        require(len(value.lstrip('-')) <= 20, 'seed_config_number')
        return int(value)
    def constant(value):
        raise SeedRejected('seed_config_number')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_int=integer, parse_constant=constant)
        require(type(value) is dict, 'seed_config_object')
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            require(depth <= 16 and count + len(pending) <= 4096, 'seed_config_complexity')
            if type(item) is dict:
                pending.extend((part, depth + 1) for pair in item.items() for part in pair)
            elif type(item) is list:
                pending.extend((part, depth + 1) for part in item)
            elif type(item) is str:
                require(len(item) <= 4096 and '\x00' not in item and ('$' + '{') not in item,
                        'seed_config_string')
            else:
                require(item is None or type(item) in (bool, int)
                        or type(item) is float and math.isfinite(item), 'seed_config_value')
        require(raw == json.dumps(value, sort_keys=True, separators=(',', ':'),
                    ensure_ascii=False, allow_nan=False).encode('utf-8'), 'seed_config_noncanonical')
        return value
    except SeedRejected:
        raise
    except (ValueError, UnicodeError, TypeError, RecursionError, OverflowError):
        raise SeedRejected('seed_config_invalid') from None


def read_private_config(path, expected):
    digest(expected)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'seed_config_alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and (info.st_uid, info.st_gid) == (GATEWAY_UID, SOCKET_GID)
                and stat.S_IMODE(info.st_mode) == 0o600
                and 0 < info.st_size <= MAX_CONFIG, 'seed_config_input_metadata')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_CONFIG + 1)
        require(len(raw) == info.st_size and sha(raw) == expected
                and stamp(info) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                'seed_config_input_changed')
    finally:
        os.close(fd)
    return raw, config_document(raw)


def zero_capacity(settings, expected_user_namespace):
    policy = settings.execution['policy']
    for name in ('max_provider_calls', 'max_tool_calls', 'total_token_limit', 'total_cost_microusd'):
        require(type(policy.get(name)) is int and policy[name] == 0, 'seed_nonzero_execution_capacity')
    principal = settings.execution['provider_broker']['principal_contract']
    expected = {'version': 1, 'enabled': True, 'gatewayUid': GATEWAY_UID,
                'brokerUid': 23002, 'socketGroupGid': SOCKET_GID,
                'hostUserNamespace': expected_user_namespace}
    require(canonical(principal) == canonical(expected), 'seed_principal_binding')


def verify_installation():
    """Byte-only public helper; no native import, runtime execution or writes."""
    name = '_r168_frozen_r167_import_support'
    raw = trusted_source(SUPPORT, SUPPORT_SHA, limit=65536)
    require(name not in sys.modules, 'seed_verifier_already_loaded')
    helper = types.ModuleType(name)
    helper.__file__ = str(SUPPORT)
    sys.modules[name] = helper
    exec(compile(raw, str(SUPPORT), 'exec'), helper.__dict__)
    installer = helper.load_installer(str(INSTALLER), INSTALLER_SHA)
    prepared = installer._verifier().verify_files(INPUT / 'candidate/manifest.json',
        INPUT / 'candidate/service-source.tar', expected_manifest_sha256=MANIFEST,
        expected_archive_sha256=ARCHIVE, expected_harness_commit=HARNESS,
        expected_native_feature=NATIVE)
    require(len(prepared.source) == 878 and len(prepared.dependencies) == 1162
            and prepared.dependencies.get(IPV6_NAME) == IPV6_SHA, 'seed_inventory')
    receipt, binaries = helper.installed_bytes(installer, prepared, RECEIPT_SHA)
    require(binaries['python']['sha256'] == PYTHON_SHA
            and binaries['node']['sha256'] == NODE_SHA, 'seed_runtime_pin')
    tools = {str(SUPPORT): SUPPORT_SHA}
    p = installer._legacy()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).resolve().parent == INSTALLER.parent:
            target = Path(filename).resolve()
            data, _ = p._read_path(str(target), MAX_SOURCE, trusted=True)
            tools[str(target)] = sha(data)
    roots = tuple(sorted({Path(value).resolve() for value in (
        sysconfig.get_path('stdlib'), sysconfig.get_path('platstdlib'),
        sysconfig.get_config_var('DESTSHARED')) if value}))
    return types.SimpleNamespace(helper=helper, installer=installer, prepared=prepared,
        receipt=receipt, binaries=binaries, tools=tools, stdlib_roots=roots)


def configure_environment(home):
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8',
                      TZ='UTC', HERMES_HOME=str(home), TMPDIR=str(home))
    os.chdir(home)


class OfflineBoundary:
    """Fixed trusted-program tripwire; never claims hostile-code confinement."""
    def __init__(self, home, progress):
        self.home, self.progress = home, progress
        self.native_prefix = str(INSTALLATION / 'native') + '/'
        self.reference_schema_opens = 0
        self.reference_handle_pending = False
        self.reference_connections, self.sqlite_opens, self.helpers = [], [], []
        self.denied, self.native_work_attempts, self.ipv6 = [], [], []
        progress['boundaryRejections'] = self.denied
        progress['nativeWorkAttempts'] = self.native_work_attempts
        progress['blockedCapabilityProbes'] = []

    def reject(self, reason, event):
        if len(self.denied) < 16:
            self.denied.append({'phase': self.progress['phase'], 'reason': reason, 'event': event})
        raise SeedRejected(reason)

    def owned(self, value, dir_fd=None):
        try:
            if type(value) is int:
                if value < 0:
                    return False
                path = Path(os.readlink('/proc/self/fd/' + str(value)))
            else:
                path = Path(os.fsdecode(value))
                if not path.is_absolute():
                    parent = Path.cwd() if dir_fd in (None, -1) else Path(
                        os.readlink('/proc/self/fd/' + str(dir_fd)))
                    path = parent / path
            return path.is_absolute() and path.resolve(strict=False).is_relative_to(self.home)
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def reference_schema_open(self, path, caller):
        module = sys.modules.get('hermes_state_schema')
        filename = str(INSTALLATION / 'native/hermes_state_schema.py')
        if (path != ':memory:' or self.progress['phase'] != 'CREATE_COLD_STORES'
                or self.reference_schema_opens != 0 or module is None
                or getattr(module, '__file__', None) != filename):
            return False
        original = module.SessionSchemaMixin._parse_schema_columns
        return (caller.f_code is original.__code__ and caller.f_code.co_filename == filename
                and caller.f_globals is vars(module)
                and caller.f_locals.get('schema_sql') is module.SCHEMA_SQL)

    def ipv6_probe(self, args, caller):
        module = sys.modules.get('urllib3.util.connection')
        original = getattr(module, '_has_ipv6', None) if module is not None else None
        if type(args) is not tuple or len(args) != 2:
            return False
        sock, address = args
        parent = caller.f_back
        return (not self.ipv6 and self.progress['phase'] in
                ('SOURCE_QUALIFICATION', 'IMPORT_NATIVE_TYPES', 'PREPARE_CONSUMER')
                and module is not None and getattr(module, '__file__', None) == IPV6_PATH
                and type(original) is types.FunctionType
                and original.__name__ == '_has_ipv6'
                and original.__module__ == 'urllib3.util.connection'
                and caller.f_code is original.__code__
                and caller.f_code.co_filename == IPV6_PATH
                and caller.f_code.co_firstlineno == 114 and caller.f_lineno == 127
                and caller.f_globals is vars(module)
                and caller.f_locals.get('host') == '::1'
                and caller.f_locals.get('has_ipv6') is False
                and caller.f_locals.get('sock') is sock
                and parent is not None and parent.f_globals is vars(module)
                and parent.f_code.co_filename == IPV6_PATH
                and parent.f_code.co_name == '<module>' and parent.f_lineno == 137
                and type(address) is tuple and len(address) == 2
                and type(address[0]) is str and address[0] == '::1'
                and type(address[1]) is int and address[1] == 0
                and type(sock) is socket.socket and sock.family == socket.AF_INET6
                and sock.type == socket.SOCK_STREAM and sock.proto == 0 and sock.fileno() >= 0)

    def ipv6_closed(self):
        module = sys.modules.get('urllib3.util.connection')
        require(len(self.ipv6) == 1 and self.ipv6[0][0].fileno() == -1
                and module is self.ipv6[0][1]
                and getattr(module, '_has_ipv6', None) is self.ipv6[0][2]
                and getattr(module, '__file__', None) == IPV6_PATH
                and module.HAS_IPV6 is False, 'seed_ipv6_probe_not_closed')
        row = self.progress['blockedCapabilityProbes'][0]
        row['socketClosed'], row['hasIPv6AfterImports'] = True, False
        return dict(row)

    def __call__(self, event, args):
        if event == 'socket.bind' and self.ipv6_probe(args, sys._getframe(1)):
            module = sys.modules['urllib3.util.connection']
            self.ipv6.append((args[0], module, module._has_ipv6))
            self.progress['blockedCapabilityProbes'].append({
                'event': event, 'phase': self.progress['phase'], 'sourceSha256': IPV6_SHA,
                'function': '_has_ipv6', 'firstLine': 114, 'bindLine': 127,
                'importCallLine': 137, 'address': ['::1', 0],
                'guardDenied': True, 'bindPerformed': False,
                'socketClosed': False, 'hasIPv6AfterImports': None})
            raise PermissionError('seed_ipv6_capability_probe_denied')
        if event == 'subprocess.Popen':
            executable, argv, cwd, env = args
            index = len(self.helpers)
            expected = ([PYTHON, '-I', '-B', str(INSTALLATION / 'scripts' / HELPERS[index])]
                        if index < len(HELPERS) else None)
            if not (self.progress['phase'] == 'START_OWNER'
                    and isinstance(argv, (list, tuple)) and list(argv) == expected
                    and executable == PYTHON and str(cwd) == str(INSTALLATION)
                    and env == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}):
                self.reject('seed_process_forbidden', event)
            self.helpers.append({'phase': self.progress['phase'], 'script': HELPERS[index],
                                 'siteStartupDisabled': False})
        elif event in {'socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo',
                'socket.gethostbyname', 'socket.gethostbyaddr', 'socket.getnameinfo',
                'socket.sendto', 'socket.sendmsg', 'os.system', 'os.posix_spawn',
                'os.exec', 'os.fork', 'os.forkpty'}:
            self.reject('seed_network_or_process_forbidden', event)
        elif event == 'sqlite3.connect':
            path = str(args[0])
            allowed = {str(self.home / name) for name in
                       ('state.db', 'runs_idempotency.db', 'response_store.db')}
            if not (path in allowed and self.progress['phase'] in ('CREATE_COLD_STORES', 'START_OWNER')):
                if not self.reference_schema_open(path, sys._getframe(1)):
                    self.reject('seed_database_path_or_phase_forbidden', event)
                self.reference_schema_opens += 1
                self.reference_handle_pending = True
            if len(self.sqlite_opens) >= 32:
                self.reject('seed_database_open_bound', event)
            self.sqlite_opens.append({'phase': self.progress['phase'], 'path': path})
        elif event == 'sqlite3.connect/handle' and self.reference_handle_pending:
            self.reference_connections.append(args[0])
            self.reference_handle_pending = False
        elif event == 'open':
            path, mode, flags = args
            write = (type(mode) is str and any(c in mode for c in 'wax+')) or (
                type(flags) is int and bool(flags & (
                    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
            # Popen wraps its newly created pipe FDs during the fixed cold helpers.
            pipe = (type(path) is int and path >= 0 and self.progress['phase'] == 'START_OWNER'
                    and stat.S_ISFIFO(os.fstat(path).st_mode))
            if write and not (pipe or self.owned(path)):
                self.reject('seed_write_outside_profile', event)
        elif event in {'os.mkdir', 'os.chmod'}:
            if not self.owned(args[0], args[2]):
                self.reject('seed_mutation_outside_profile', event)
        elif event in {'os.remove', 'os.rmdir'}:
            if not self.owned(args[0], args[1]):
                self.reject('seed_mutation_outside_profile', event)
        elif event in {'os.utime', 'os.chown'}:
            if not self.owned(args[0], args[3]):
                self.reject('seed_mutation_outside_profile', event)
        elif event in {'os.setxattr', 'os.removexattr', 'os.truncate'}:
            if not self.owned(args[0]):
                self.reject('seed_mutation_outside_profile', event)
        elif event in {'os.rename', 'os.link'}:
            if not self.owned(args[0], args[2]) or not self.owned(args[1], args[3]):
                self.reject('seed_mutation_outside_profile', event)
        elif event == 'os.symlink':
            self.reject('seed_symlink_forbidden', event)
        elif event == 'os.chdir' and not self.owned(args[0]):
            self.reject('seed_chdir_outside_profile', event)

    def profile(self, frame, event, arg):
        if event != 'call' or not frame.f_code.co_filename.startswith(self.native_prefix):
            return
        name = frame.f_code.co_name
        if name in FORBIDDEN_NATIVE_CALLS or frame.f_code.co_qualname == 'AIAgent.__init__':
            if len(self.native_work_attempts) < 16:
                self.native_work_attempts.append(name)
            self.reject('seed_native_work_forbidden', 'python.call')


def source_discovery_rows(proof, registry):
    native, hashes = proof
    require(type(hashes) is dict and native.resolve(strict=True) == native, 'seed_source_proof')
    selected = {}
    for name, digest in hashes.items():
        path = PurePosixPath(name)
        parts = path.parts
        candidate = len(parts) == 2 and parts[0] == 'tools' and path.suffix == '.py'
        candidate = candidate or (len(parts) == 3 and parts[0] == 'tools' and parts[2] == 'tool.py'
                                  and str(PurePosixPath(*parts[:2]) / '__init__.py') in hashes)
        if candidate and path.name not in ('__init__.py', 'registry.py', 'mcp_tool.py'):
            selected[native / path] = digest
    require(0 < len(selected) <= MAX_CANDIDATES, 'seed_discovery_count')
    candidates = registry._tool_module_candidates(native / 'tools')
    actual = [p for p in candidates if p.name not in ('__init__.py', 'registry.py', 'mcp_tool.py')
              and (p.parent == native / 'tools' or (p.parent / '__init__.py').is_file())]
    require(len(actual) == len(set(actual)) and set(actual) == set(selected),
            'seed_discovery_candidates_changed')
    result = {}
    for path, digest in sorted(selected.items()):
        info = path.lstat()
        require(path.resolve(strict=True) == path and stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1 and 0 <= info.st_size <= MAX_SOURCE
                and 0 <= info.st_mtime_ns < 2**63, 'seed_tool_source_file')
        raw = path.read_bytes()
        require(len(raw) == info.st_size and hashlib.sha256(raw).hexdigest() == digest,
                'seed_tool_source_changed')
        registers = registry._module_registers_tools(path)
        after = path.stat()
        require(type(registers) is bool and (after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns) == (info.st_dev, info.st_ino, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns), 'seed_tool_source_changed')
        result[str(path)] = [info.st_mtime_ns, info.st_size, registers]
    require(len(canonical(result)) <= MAX_DISCOVERY, 'seed_discovery_size')
    return result


def initialize_auxiliaries(home, consumer, instance_id):
    import hermes_constants
    import hermes_cli.auth as auth
    import hermes_cli.active_sessions as active
    import gateway.platforms.base as base
    import tools.registry as registry
    from agent.safe_worker_policy import safe_worker_enabled
    from gateway_prepared_consumer import verify_imports
    require(not safe_worker_enabled(), 'seed_safe_worker_incompatible')
    require(Path(hermes_constants.get_hermes_home()) == home
            and hermes_constants.get_hermes_home_override() is None,
            'seed_native_home_changed')
    require(base.DOCUMENT_CACHE_DIR == base._CACHE_DIR_IMPORT_DEFAULTS['DOCUMENT_CACHE_DIR']
            and Path(base.DOCUMENT_CACHE_DIR) == home / 'cache/documents'
            and not (home / 'document_cache').exists(), 'seed_document_cache_redirected')
    with auth._auth_store_lock(timeout_seconds=2.0, target_path=home / 'auth.json'):
        require(not (home / 'auth.json').exists(), 'seed_unexpected_auth_store')
    require(base.get_document_cache_dir() == home / 'cache/documents',
            'seed_document_cache_redirected')
    with active.active_session_liveness_guard(instance_id, registry_home=home,
                                               own_live_lease_ids=None) as is_active:
        require(is_active is False, 'seed_active_session_present')
    require(active.active_session_registry_snapshot(registry_home=home, strict=True) == [],
            'seed_active_sessions_present')
    require(registry._discovery_cache_path() == home / 'cache/tool_discovery_cache.json',
            'seed_discovery_redirected')
    rows = source_discovery_rows(consumer._source_proof, registry)
    registry._save_discovery_cache(rows)
    cache = home / 'cache/tool_discovery_cache.json'
    require(cache.is_file() and not cache.is_symlink() and cache.stat().st_size <= MAX_DISCOVERY,
            'seed_discovery_write_missing')
    raw = cache.read_bytes()
    from gateway_retained_profile import _json
    require(_json(raw) == rows, 'seed_discovery_write_changed')
    verify_imports(consumer._source_proof)
    return {'sourceDerivedCacheEntries': len(rows),
            'sourceDerivedCacheSha256': hashlib.sha256(raw).hexdigest(),
            'completeToolRegistrationPerformed': False, 'activeSessionEntries': 0}


def physically_closed(connections):
    require(len(connections) == 3 and len({id(c) for c in connections}) == 3,
            'seed_three_original_connections')
    for connection in connections:
        try:
            connection.execute('SELECT 1')
        except sqlite3.ProgrammingError:
            continue
        raise SeedRejected('seed_connection_not_physically_closed')


def write_config_once(home, raw, args):
    home_identity(home, args, fresh=False)
    target = home / 'config.yaml'
    fd = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(fd, 'w+b', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
            info = os.fstat(fd)
            stream.seek(0)
            observed = stream.read(MAX_CONFIG + 1)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600
                and (info.st_uid, info.st_gid) == (GATEWAY_UID, SOCKET_GID)
                and info.st_dev == args.expected_profile_device
                and observed == raw and sha(observed) == args.expected_config_sha256
                and stamp(info) == stamp(os.fstat(fd)) == stamp(target.lstat()),
                'seed_config_write_unconfirmed')
        config_info = info
    finally:
        os.close(fd)
    directory = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(directory)
        require((info.st_dev, info.st_ino) ==
                (args.expected_profile_device, args.expected_profile_inode), 'seed_home_changed')
        os.fsync(directory)
    finally:
        os.close(directory)
    require(stamp(target.lstat()) == stamp(config_info), 'seed_config_write_unconfirmed')
    return config_info


def capture_service(attempt, args, auxiliary):
    import gateway_service_profile as profile
    import gateway_service_handoff as handoff
    import gateway_store_startup as startup
    import gateway_prepared_consumer as prepared
    owner, consumer, held = attempt.owner, attempt.consumer, attempt.held
    require(type(owner) is startup.NativeStoreStartup and owner._stage == 'CLOSED'
            and owner._held is held and held._finished is False, 'seed_closed_owner_required')
    owner._owned()
    require(type(consumer) is prepared.PreparedRuntimeConsumer and owner._prepared_consumer is consumer
            and consumer._owner is owner and consumer._held is held
            and consumer._stage == 'DETACHED' and consumer._borrowed_service is True
            and consumer._selected_feature == NATIVE and consumer._service_source == attempt.selection
            and consumer._binding._stage == 'DETACHED' and consumer._bundle._stage == 'DETACHED',
            'seed_detached_service_consumer_required')
    physically_closed(attempt.connections)
    prepared.verify_imports(consumer._source_proof)
    config_info = write_config_once(attempt.home, attempt.config_raw, args)
    databases = []
    for name in ('state.db', 'runs_idempotency.db', 'response_store.db'):
        info = (attempt.home / name).stat()
        databases.append((info.st_dev, info.st_ino))
    databases = tuple(databases)
    require(databases == (owner._expected.state_identity, owner._expected.replay_identity,
                          owner._response_expected.response_identity), 'seed_closed_database_changed')
    receipt = profile.ServiceProfileExpectation(1, attempt.selection, str(attempt.home),
        home_identity(attempt.home, args, fresh=False), databases,
        owner._expected.epoch, owner._expected.instance_id, auxiliary['sourceDerivedCacheSha256'],
        (config_info.st_dev, config_info.st_ino), config_info.st_size, sha(attempt.config_raw))
    profile.inspect_profile(attempt.home, uid=GATEWAY_UID, gid=SOCKET_GID,
                            device=args.expected_profile_device, expectation=receipt)
    record = handoff.ServiceStartup(owner._expected, owner._response_expected, receipt)
    wire = handoff.encode(record, expected_home=str(attempt.home))
    require(handoff.decode(wire, expected_home=str(attempt.home)) == record, 'seed_handoff_roundtrip')
    owner._owned()
    prepared.verify_imports(consumer._source_proof)
    attempt.record, attempt.wire = record, wire
    return {'handoff': wire.decode('ascii'), 'handoffSha256': sha(wire),
        'previousEpoch': receipt.epoch, 'instanceId': receipt.instance_id,
        'profileIdentity': list(receipt.home_identity),
        'databaseIdentities': [list(pair) for pair in receipt.database_identities],
        'configIdentity': list(receipt.config_identity), 'configSize': receipt.config_size,
        'configSha256': receipt.config_sha256, 'serviceCapturedWhileLeaseHeld': True}


class Attempt:
    def __init__(self):
        self.progress = {'phase': 'ARGUMENTS', 'nativeEffectsAttempted': False}
        self.loop = self.task = self.owner = self.consumer = self.held = None
        self.parked = self.boundary = self.record = self.wire = None
        self.connections = ()
        self.cold_stores = {}
        self.normal_loop_shutdown = self.profile_released = False


async def native_lifecycle(attempt, args):
    home, progress, boundary = attempt.home, attempt.progress, attempt.boundary
    progress['phase'] = 'SOURCE_QUALIFICATION'
    import gateway_service_sources as sources
    import gateway_prepared_consumer as prepared
    attempt.selection = sources.load_selection()
    attempt.proof = prepared.qualify_sources(local_admission=True, canonical_api=True,
        finite_turn=True, service_selection=attempt.selection)
    require(attempt.selection.native_feature == NATIVE and len(attempt.proof[1]) == 760,
            'seed_service_source_selection')
    progress['phase'] = 'IMPORT_NATIVE_TYPES'
    from gateway.runtime_ownership import process_ownership
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.config import GatewayConfig, PlatformConfig
    import gateway_store_startup as startup
    import gateway_profile_lease as lease
    import gateway_storage_mounts as mounts
    import gateway_native_layout as layout
    import gateway_service_profile as profile
    import gateway_service_factory as factory
    import hermes_state_registry as registry
    from agent.safe_worker_policy import safe_worker_enabled
    profile._config_document(attempt.config_raw)
    attempt.settings = factory.validate_settings(attempt.config_document)
    zero_capacity(attempt.settings, args.expected_user_namespace)
    prepared.verify_imports(attempt.proof)
    require(not safe_worker_enabled() and not process_ownership.homes
            and registry.stats()['total_refcounts'] == 0, 'seed_existing_native_owner')
    selected = mounts.select_mount(mounts.parse_mountinfo(mounts._read_mountinfo()), str(home))
    attempt.mount = mounts.ExpectedMount(selected.mount_id, selected.device, selected.root,
                                         selected.mount_point, selected.filesystem)
    require(attempt.mount.filesystem == 'ext4'
            and os.makedev(*attempt.mount.device) == args.expected_profile_device, 'seed_ext4_binding')
    home_identity(home, args, fresh=False)
    require(not boundary.sqlite_opens and not boundary.helpers, 'seed_import_opened_store_or_helper')
    def identity(name):
        info = (home / name).stat()
        return info.st_dev, info.st_ino
    progress['phase'] = 'CREATE_COLD_STORES'
    lock = os.open(home / 'gateway.lock',
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    os.close(lock)
    process_ownership.reserve([home])
    attempt.cold_stores['state'] = state = SessionDB(home / 'state.db')
    require(boundary.reference_schema_opens == 1 and not boundary.reference_handle_pending
            and len(boundary.reference_connections) == 1, 'seed_reference_schema_connection')
    try:
        boundary.reference_connections[0].execute('SELECT 1')
    except sqlite3.ProgrammingError:
        pass
    else:
        raise SeedRejected('seed_reference_connection_not_closed')
    attempt.cold_stores['replay'] = replay = RunIdempotencyStore(str(home / 'runs_idempotency.db'))
    attempt.cold_stores['response'] = response = ResponseStore(
        db_path=str(home / 'response_store.db'), canonical_state=state, max_size=100, max_identities=1000)
    cold_connections = (state._conn, replay._conn, response._conn)
    expected = startup.live.PreparedStoreExpectation(
        startup.live.NATIVE_PIN, startup.live.schema_digest(state._conn),
        startup.live.schema_digest(replay._conn),
        state._conn.execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0],
        state._conn.execute('PRAGMA application_id').fetchone()[0],
        identity('state.db'), identity('runs_idempotency.db'), 0, None)
    response_expected = startup.response_preopen.PreparedResponseExpectation(
        startup.response_preopen.NATIVE_FEATURE, startup.response_preopen.SCHEMA_SHA256,
        identity('response_store.db'))
    require(startup.live.schema_digest(response._conn) == response_expected.schema_sha256,
            'seed_response_schema')
    for store in (response, replay, state):
        store.close()
    physically_closed(cold_connections)
    process_ownership.close()
    require(not process_ownership.homes and registry.stats()['total_refcounts'] == 0,
            'seed_cold_owner_not_released')
    progress['phase'] = 'RESERVE_PROFILE'
    attempt.held = held = lease.reserve_profile(home, attempt.mount)
    require(held.check()['state'] == 'NATIVE_PROFILE_RESERVED', 'seed_profile_lease')
    layout.inspect_profile(home, uid=GATEWAY_UID, gid=SOCKET_GID,
                           device=args.expected_profile_device, include_response=True)
    attempt.owner = owner = startup.NativeStoreStartup(held, attempt.mount, expected,
        instance_id=args.instance_id, response_expected=response_expected, prepared_layout=True)
    progress['phase'] = 'START_OWNER'
    started = owner.start()
    require(owner.expectation.epoch == 1 and len(started['completedChecks']) == 6,
            'seed_cold_start')
    require([item['script'] for item in boundary.helpers] == list(HELPERS), 'seed_cold_helper_count')
    attempt.connections = (owner.state_store._conn, owner.replay_store._conn, owner.response_store._conn)
    progress['phase'] = 'PREPARE_CONSUMER'
    attempt.consumer = consumer = await owner.prepare_runtime(
        GatewayConfig(multiplex_profiles=False, write_sessions_json=False, loop_watchdog=False,
                      systemd_watchdog_seconds=0, sessions_dir=home / 'sessions'),
        PlatformConfig(enabled=True, extra=attempt.settings.api),
        local_admission=True, canonical_api=True, finite_turn=True, borrowed_service=True)
    observed = consumer.check()
    require(observed['nativeAdmissionState'] == 'PREPARED'
            and observed['canonicalApiPublicationState'] == 'NEW'
            and observed['borrowedServiceSelected'] is True and observed['nativeFeature'] == NATIVE
            and all(a is b for a, b in zip(consumer._connections, attempt.connections)),
            'seed_consumer_not_idle')
    require(attempt.connections[0].execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0] == 0,
            'seed_admission_rows_present')
    blocked = boundary.ipv6_closed()
    progress['phase'] = 'INITIALIZE_AUXILIARIES'
    auxiliary = initialize_auxiliaries(home, consumer, args.instance_id)
    auxiliary['blockedIpv6CapabilityProbe'] = blocked
    progress['phase'] = 'DETACH_CONSUMER'
    await consumer.detach()
    consumer.assert_store_closeable(owner)
    require(not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()
                 and not task.done()], 'seed_pending_async_work')
    progress['phase'] = 'CLOSE_OWNER'
    owner.close()
    physically_closed(attempt.connections)
    require(owner._stage == 'CLOSED' and consumer._stage == 'DETACHED'
            and held.check()['state'] == 'NATIVE_PROFILE_RESERVED', 'seed_close_or_lease')
    progress['phase'] = 'CAPTURE_SERVICE'
    result = capture_service(attempt, args, auxiliary)
    require(not boundary.native_work_attempts and not boundary.denied, 'seed_forbidden_effect')
    prepared.verify_imports(consumer._source_proof)
    result.update(completedChecks=started['completedChecks'], allThreeConnectionsPhysicallyClosed=True,
        ownerState=owner._stage, consumerState=consumer._stage,
        mount={'mount_id': attempt.mount.mount_id, 'device': list(attempt.mount.device),
               'root': attempt.mount.root, 'mount_point': attempt.mount.mount_point,
               'filesystem': attempt.mount.filesystem},
        auxiliaryInitialization=auxiliary, coldHelperCalls=boundary.helpers,
        sqliteOpenCount=len(boundary.sqlite_opens), qualifiedNativeSourceCount=len(consumer._source_proof[1]))
    return result


def retain_unknown(attempt):
    """Keep the original loop and all references; no replacement or cleanup."""
    while True:
        if attempt.loop is None or attempt.loop.is_closed():
            if attempt.parked is None:
                attempt.parked = threading.Event()
            try:
                attempt.parked.wait()
            except BaseException:
                continue
        else:
            try:
                attempt.loop.run_forever()
            except BaseException:
                continue


def failure_report(attempt, exc, started):
    progress = attempt.progress
    reason = str(exc) if type(exc) is SeedRejected else 'seed_operation_failed'
    if not re.fullmatch('[a-z_]{1,100}', reason):
        reason = 'seed_operation_failed'
    return {'kind': 'R168A1_TASK_FREE_SERVICE_SEED', 'result': 'NOT_ACCEPTED',
        'state': 'SEED_OUTCOME_UNKNOWN' if progress['nativeEffectsAttempted'] else 'REFUSED',
        **progress, 'reason': reason, 'reasonType': type(exc).__name__[:96],
        'totalMillis': int((time.monotonic() - started) * 1000),
        'partialStatePreserved': True, 'processRetained': progress['nativeEffectsAttempted'],
        'normalLoopShutdown': attempt.normal_loop_shutdown,
        'profileLeaseReleasedNormally': attempt.profile_released,
        'automaticCleanup': False, 'automaticRetry': False,
        'serviceAccepted': False, 'kernelAccepted': False, 'fullD3BAccepted': False}


def bootstrap(args, attempt):
    started = time.monotonic()
    attempt.home, config = validate_arguments(args)
    validate_actor(args)
    source = source_identity(args.expected_seed_sha256)
    os.umask(0o077)
    home_identity(attempt.home, args, fresh=True)
    attempt.progress['phase'] = 'VERIFY_INSTALLATION'
    verified = verify_installation()
    verified.tools[source['path']] = source['sha256']
    attempt.config_raw, attempt.config_document = read_private_config(config, args.expected_config_sha256)
    verified_at = time.monotonic()
    home_identity(attempt.home, args, fresh=True)
    configure_environment(attempt.home)
    sys.path[:] = [str(INSTALLATION / 'packages/claw-hermes'), str(INSTALLATION / 'native'),
                  str(INSTALLATION / 'dependencies'), *map(str, verified.stdlib_roots)]
    attempt.boundary = OfflineBoundary(attempt.home, attempt.progress)
    sys.addaudithook(attempt.boundary)
    sys.setprofile(attempt.boundary.profile)
    threading.setprofile(attempt.boundary.profile)
    # Both irreversible audit guard and native-work observer remain through exit.
    attempt.progress.update(phase='NATIVE_IMPORTS', nativeEffectsAttempted=True)
    with contextlib.redirect_stdout(sys.stderr):
        attempt.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(attempt.loop)
        attempt.task = attempt.loop.create_task(native_lifecycle(attempt, args))
        result = attempt.loop.run_until_complete(attempt.task)
        require(not asyncio.all_tasks(attempt.loop), 'seed_loop_not_terminal')
        attempt.progress['phase'] = 'NORMAL_LOOP_SHUTDOWN'
        attempt.loop.run_until_complete(attempt.loop.shutdown_asyncgens())
        attempt.loop.run_until_complete(attempt.loop.shutdown_default_executor(timeout=5.0))
        require(threading.active_count() == 1 and not asyncio.all_tasks(attempt.loop),
                'seed_thread_or_task_retained')
        attempt.loop.close()
        asyncio.set_event_loop(None)
        attempt.normal_loop_shutdown = True
    attempt.progress['phase'] = 'POST_READBACK'
    origins = verified.helper.imported_origins(
        verified.installer, verified.prepared, verified.tools, verified.stdlib_roots)
    receipt, binaries = verified.helper.installed_bytes(
        verified.installer, verified.prepared, RECEIPT_SHA)
    require(verified.installer.canonical(receipt) == verified.installer.canonical(verified.receipt)
            and binaries == verified.binaries, 'seed_installed_inputs_changed')
    require(source_identity(args.expected_seed_sha256) == source, 'seed_source_changed')
    validate_parent(args)
    home_identity(attempt.home, args, fresh=False)
    require(os.readlink('/proc/self/ns/user') == args.expected_user_namespace
            and Path('/proc/self/ns/mnt').stat().st_ino == args.expected_mount_namespace_inode,
            'seed_namespace_changed')
    attempt.boundary.ipv6_closed()
    require(not attempt.boundary.denied and not attempt.boundary.native_work_attempts,
            'seed_forbidden_effect')
    require((time.monotonic() - started) * 1000 < MAX_ELAPSED_MILLIS, 'seed_elapsed_budget')
    attempt.progress['phase'] = 'RELEASE_PROFILE'
    import gateway_service_profile as profile
    import hermes_state_registry as registry
    profile.inspect_profile(attempt.home, uid=GATEWAY_UID, gid=SOCKET_GID,
                            device=args.expected_profile_device, expectation=attempt.record.service)
    attempt.held.check()
    attempt.held.finish()
    require(attempt.held._finished and not attempt.held._owner.homes
            and registry.stats()['total_refcounts'] == 0, 'seed_lease_or_registry_retained')
    attempt.profile_released = True
    finished = time.monotonic()
    attempt.progress['phase'] = 'COMPLETE'
    result.update(kind='R168A1_TASK_FREE_SERVICE_SEED', result='PASS', state='SERVICE_SEED_CREATED',
        phase='COMPLETE', installationReceiptSha256=RECEIPT_SHA,
        harnessCommit=HARNESS, nativeFeature=NATIVE, sourceFileCount=878, dependencyFileCount=1162,
        sourceIdentity=source, sourceAndDependencyBytesReadBackBeforeAndAfter=True,
        runtimeBinaryBytesReadBackBeforeAndAfter=True, runtimeBinaries=binaries,
        importedOriginCounts={name: len(rows) for name, rows in origins.items()},
        importedOriginsSha256=sha(canonical(origins)), fullSharedLibraryClosureAccepted=False,
        home=str(attempt.home), pid=os.getpid(), parentPid=os.getppid(), startTicks=process_start(os.getpid()),
        parentStartTicks=args.parent_start_ticks, gatewayUid=GATEWAY_UID, socketGroupGid=SOCKET_GID,
        supplementaryGroups=os.getgroups(), resUid=list(os.getresuid()), resGid=list(os.getresgid()),
        userNamespace=os.readlink('/proc/self/ns/user'), mountNamespace=os.readlink('/proc/self/ns/mnt'),
        mountNamespaceInode=Path('/proc/self/ns/mnt').stat().st_ino,
        isolated=sys.flags.isolated == 1, noSite=sys.flags.no_site == 1,
        verificationMillis=int((verified_at - started) * 1000),
        nativeAndReadbackMillis=int((finished - verified_at) * 1000),
        totalMillis=int((finished - started) * 1000),
        normalLoopShutdown=True, profileLeaseReleasedNormally=True,
        outstandingAsyncTasks=0, outstandingThreads=0, executedTasks=0, realModelCalls=0,
        listenersCreated=0, apiAdmissionPublished=False, providerExchangePerformed=False,
        zeroExecutionCapacity=True, auditGuardIsOSConfinement=False,
        serviceAccepted=False, kernelAccepted=False, fullD3BAccepted=False,
        automaticCleanup=False, automaticRetry=False)
    require(len(canonical(result)) <= MAX_RESULT, 'seed_result_size')
    return result


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'instance-id', 'config-file', 'expected-user-namespace'):
        parser.add_argument('--' + name, required=True)
    for name in ('expected-config-sha256', 'expected-seed-sha256'):
        parser.add_argument('--' + name, required=True, type=digest)
    for name in ('expected-profile-device', 'expected-profile-inode', 'parent-pid',
                 'parent-start-ticks', 'expected-mount-namespace-inode'):
        parser.add_argument('--' + name, type=decimal, required=True)
    return parser.parse_args(argv)


def main(argv=None):
    global _attempt
    started = time.monotonic()
    require(_attempt is None, 'seed_process_already_owned')
    _attempt = attempt = Attempt()
    try:
        result = bootstrap(arguments(argv), attempt)
        sys.stdout.buffer.write(canonical(result))
        sys.stdout.buffer.flush()
        return 0
    except BaseException as exc:
        if isinstance(exc, SystemExit) and not attempt.progress['nativeEffectsAttempted']:
            raise
        report = failure_report(attempt, exc, started)
        try:
            sys.stderr.buffer.write(canonical(report))
            sys.stderr.buffer.flush()
        except BaseException:
            pass
        if attempt.progress['nativeEffectsAttempted']:
            return retain_unknown(attempt)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
