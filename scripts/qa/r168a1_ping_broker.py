"""Bounded installed broker for one R168 readiness ping; no provider task or upstream.

The root controller owns launch, raw stdout/stderr, control pipe, and reaping.
This child never provisions identities, adopts a socket, restarts, or kills a PID.
An unconfirmed terminal outcome retains the controller's attempt ownership.
"""
from __future__ import annotations
import argparse
import asyncio
try:
    import fcntl
except ImportError:
    fcntl = None
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import uuid

INSTALLATION = Path('/opt/alaz-r167a1')
MODULE_DIRECTORY = INSTALLATION / 'packages/claw-hermes'
RECEIPT_SHA = '0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f'
PYTHON = Path('/usr/bin/python3.12')
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
MODULE_SHA = {
    'provider_broker': 'e2e4c304bf861ff818ae869f1088102aaca3cf38ccf602ee9e3be5c980cfe13b',
    'provider_egress': 'e32cba404b93c9b1b54ad9631b8a16eaf6bf6bbdf96c01d6d0f2329dcfa49e3d',
    'host_principal': '3b07c3a5ad0d5af4b5f2d89728fbf5700d72c32c85e9eaf948cfc4104d16f5e0',
    'execution_budget': '43de8231185d6dbaace9696c494fe7c2c154c8dfb6d3830905ae0f5bdfd87f78',
    'recovery_inspector': '1c242f76ee71e08969f7f48fb3865a88ccda20b7af47cfa3977711608ec69b50',
    'request_view': '29cc8a80fe84a8a31fc51c9cbe011b215dbcd20f65d73b14b26fb2d059765d9e',
    'source_capture': '5adccf7349ec104e0a7d5345c5c5cf1f01f738aa43b7b11861274aaa72293211',
}
UPSTREAM = 'http://127.0.0.1:1/v1'
MODEL = 'r168a1-ping-only'
DUMMY_BEARER = 'R168A1-NO-UPSTREAM-CREDENTIAL-' + '0' * 32
SPEC_FIELDS = {'schema', 'kind', 'attemptId', 'brokerDirectory', 'principalContract',
    'signingKey', 'scope', 'binding', 'policyFingerprint', 'owner', 'control',
    'maxLifetimeSeconds', 'expectedPings'}


class Refused(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Refused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def decode(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def constant(_):
        raise Refused('nonfinite_json_value')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def hexed(value, size=64):
    return type(value) is str and re.fullmatch('[a-f0-9]{' + str(size) + '}', value) is not None


def integer(value, minimum=0, maximum=2**63 - 1):
    return type(value) is int and minimum <= value <= maximum


def validate_spec(value):
    require(type(value) is dict and set(value) == SPEC_FIELDS
        and type(value['schema']) is int and value['schema'] == 1
        and value['kind'] == 'R168A1_PING_BROKER', 'ping_broker_spec_fields')
    require(type(value['attemptId']) is str and re.fullmatch('[a-z0-9-]{3,48}', value['attemptId'])
        and type(value['brokerDirectory']) is str
        and re.fullmatch('/run/alaz-r168a1-[a-z0-9-]{1,48}/broker', value['brokerDirectory'])
        and len((value['brokerDirectory'] + '/egress.sock').encode()) <= 100, 'ping_broker_attempt_path')
    require(all(hexed(value[k]) for k in ('signingKey', 'scope', 'binding', 'policyFingerprint'))
        and integer(value['expectedPings'], 1, 8)
        and integer(value['maxLifetimeSeconds'], 10, 300), 'ping_broker_bounds')
    owner, control, principal = value['owner'], value['control'], value['principalContract']
    require(type(owner) is dict and set(owner) == {'pid', 'startTicks', 'uid'}
        and integer(owner['pid'], 2, 2**31 - 1) and integer(owner['startTicks'], 1)
        and type(owner['uid']) is int and owner['uid'] == 0, 'ping_broker_owner')
    require(type(control) is dict and set(control) == {'dev', 'ino', 'nonce'}
        and integer(control['dev']) and integer(control['ino'], 1) and hexed(control['nonce'], 32),
        'ping_broker_control')
    require(type(principal) is dict and set(principal) == {'version', 'enabled', 'gatewayUid',
        'brokerUid', 'socketGroupGid', 'hostUserNamespace'}
        and type(principal['version']) is int and principal['version'] == 1 and principal['enabled'] is True
        and all(integer(principal[k], 1, 2**31 - 2) for k in ('gatewayUid', 'brokerUid', 'socketGroupGid'))
        and principal['gatewayUid'] != principal['brokerUid']
        and type(principal['hostUserNamespace']) is str
        and re.fullmatch(r'user:\[[0-9]{1,20}\]', principal['hostUserNamespace']), 'ping_broker_principal')
    return value


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_spec(fd, expected):
    require(sys.platform == 'linux' and integer(fd, 3) and hexed(expected), 'ping_broker_spec_descriptor')
    before = os.fstat(fd)
    require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 0
        and stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
        and 0 < before.st_size <= 16384 and fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY,
        'ping_broker_private_spec_fd')
    raw = os.pread(fd, 16385, 0)
    require(stamp(before) == stamp(os.fstat(fd)) and len(raw) == before.st_size and sha(raw) == expected,
        'ping_broker_spec_bytes')
    return validate_spec(decode(raw))


def trusted_bytes(path, expected, limit=2 * 1024 * 1024):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'ping_broker_canonical_source')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
            'ping_broker_source_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 0
            and before.st_nlink == 1 and not before.st_mode & 0o022 and 0 < before.st_size <= limit,
            'ping_broker_source_metadata')
        raw = os.pread(fd, limit + 1, 0)
        require(stamp(before) == stamp(os.fstat(fd)) == stamp(path.lstat())
            and len(raw) == before.st_size and sha(raw) == expected, 'ping_broker_source_bytes')
        return raw
    finally:
        os.close(fd)


def installed_readback():
    trusted_bytes(INSTALLATION / '.alaz-service-installation.json', RECEIPT_SHA)
    trusted_bytes(PYTHON, PYTHON_SHA, 16 * 1024 * 1024)
    for name, expected in MODULE_SHA.items():
        trusted_bytes(MODULE_DIRECTORY / (name + '.py'), expected)
        if name in sys.modules:
            require(Path(sys.modules[name].__file__) == MODULE_DIRECTORY / (name + '.py'),
                'ping_broker_module_origin')
    return {'installationReceiptSha256': RECEIPT_SHA, 'pythonSha256': PYTHON_SHA, 'moduleSha256': dict(MODULE_SHA)}


def load_installed():
    require(sys.platform == 'linux' and Path(sys.executable).resolve() == PYTHON
        and sys.version_info[:3] == (3, 12, 3) and sys.flags.isolated == sys.flags.no_site == 1
        and sys.dont_write_bytecode and sys.flags.optimize == 0, 'ping_broker_isolated_python')
    require(not any(name in sys.modules for name in MODULE_SHA)
        and not (MODULE_DIRECTORY / '__pycache__').exists(), 'ping_broker_fresh_imports')
    installed_readback()
    sys.path.insert(0, str(MODULE_DIRECTORY))
    principal = importlib.import_module('host_principal')
    broker = importlib.import_module('provider_broker')
    egress = importlib.import_module('provider_egress')
    require(all(name in sys.modules for name in MODULE_SHA), 'ping_broker_import_closure')
    installed_readback()
    return broker, egress, principal


def proc_start_ticks(raw):
    end = raw.rfind(')')
    require(end > 0 and raw[:raw.find('(')].strip().isdigit(), 'ping_broker_proc_stat')
    parts = raw[end + 1:].split()
    require(len(parts) >= 20 and parts[19].isdigit(), 'ping_broker_proc_stat')
    return int(parts[19])


def check_parent(owner):
    require(os.getppid() == owner['pid'], 'ping_broker_parent_changed')
    root = Path('/proc') / str(owner['pid'])
    require(proc_start_ticks((root / 'stat').read_text()) == owner['startTicks'], 'ping_broker_parent_reused')
    rows = [line.split()[1:] for line in (root / 'status').read_text().splitlines() if line.startswith('Uid:')]
    require(rows == [[str(owner['uid'])] * 4], 'ping_broker_parent_identity')


def descriptor_preflight(spec, spec_fd, control_fd):
    require(integer(control_fd, 3) and control_fd != spec_fd, 'ping_broker_control_descriptor')
    info = os.fstat(control_fd)
    require(stat.S_ISFIFO(info.st_mode) and info.st_uid == info.st_gid == 0
        and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
        and (info.st_dev, info.st_ino) == (spec['control']['dev'], spec['control']['ino'])
        and fcntl.fcntl(control_fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
        and os.readlink('/proc/self/fd/' + str(control_fd)) == f'pipe:[{info.st_ino}]',
        'ping_broker_owned_control_pipe')
    streams = [os.fstat(fd) for fd in (1, 2)]
    require(all(stat.S_ISREG(s.st_mode) and s.st_uid == s.st_gid == 0 and s.st_nlink == 1
        and stat.S_IMODE(s.st_mode) == 0o600 and s.st_size == 0 for s in streams)
        and (streams[0].st_dev, streams[0].st_ino) != (streams[1].st_dev, streams[1].st_ino),
        'ping_broker_owned_raw_streams')


def directory_preflight(spec, principal):
    directory = Path(spec['brokerDirectory']); contract = spec['principalContract']
    principal.broker_identity(contract)
    require(os.getresuid() == (contract['brokerUid'],) * 3
        and os.getresgid() == (contract['socketGroupGid'],) * 3, 'ping_broker_saved_identity')
    require(directory.resolve(strict=True) == directory, 'ping_broker_canonical_directory')
    for parent in directory.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
            'ping_broker_host_owned_parent')
    principal.regular(str(directory), 'dir', contract['brokerUid'], contract['socketGroupGid'], 0o710)
    require(not any(directory.iterdir()), 'ping_broker_directory_not_fresh')
    require(not os.path.lexists(directory.parent / 'broker-no-authority'), 'ping_broker_authority_must_be_absent')
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require(stamp(os.fstat(fd)) == stamp(directory.lstat()), 'ping_broker_directory_replaced')
        return fd
    except BaseException:
        os.close(fd)
        raise


def publish_receipt(directory_fd, name, value):
    require(name in ('ready.json', 'shutdown.json', 'unknown.json'), 'ping_broker_receipt_name')
    raw = encode(value); require(len(raw) <= 32768, 'ping_broker_receipt_bound')
    temporary = '.' + name + '-' + uuid.uuid4().hex
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
        os.fsync(directory_fd)
    finally:
        os.unlink(temporary, dir_fd=directory_fd)
    return {'file': name, 'sha256': sha(raw), 'bytes': len(raw)}


class NoUpstream:
    """QA observation only, not a claim of hostile-code or kernel isolation."""
    def __init__(self, socket_path):
        self.socket_path = socket_path; self.denied = []; self.denied_count = 0

    def __call__(self, event, args):
        refused = event in {'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname',
            'socket.gethostbyaddr', 'socket.getnameinfo', 'subprocess.Popen', 'os.system',
            'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec'}
        refused |= event == 'socket.__new__' and args[1] != socket.AF_UNIX
        refused |= event == 'socket.bind' and args[1] != self.socket_path
        if refused:
            self.denied_count += 1
            if len(self.denied) < 16:
                self.denied.append(event)
            raise Refused('ping_broker_forbidden_effect')


def validate_shutdown(raw, spec, broker_id):
    require(type(raw) is bytes and 0 < len(raw) <= 1024 and raw.endswith(b'\n')
        and raw.count(b'\n') == 1, 'ping_broker_shutdown_frame')
    value = decode(raw)
    require(type(value) is dict and set(value) == {'schema', 'operation', 'attemptId', 'brokerId', 'nonce'}
        and type(value['schema']) is int and value['schema'] == 1 and value['operation'] == 'shutdown'
        and value['attemptId'] == spec['attemptId'] and value['brokerId'] == broker_id
        and value['nonce'] == spec['control']['nonce'], 'ping_broker_shutdown_identity')


async def wait_shutdown(fd, spec, broker_id, *, owner_check=check_parent):
    loop = asyncio.get_running_loop(); future = loop.create_future(); data = bytearray()
    blocking = os.get_blocking(fd); os.set_blocking(fd, False)
    def readable():
        if future.done():
            return
        try:
            part = os.read(fd, 1025 - len(data))
            require(part, 'ping_broker_control_eof')
            data.extend(part)
            require(len(data) <= 1024, 'ping_broker_shutdown_frame')
            if b'\n' in data:
                validate_shutdown(bytes(data), spec, broker_id); future.set_result(True)
        except BlockingIOError:
            pass
        except Exception as exc:
            future.set_exception(exc)
    registered = False; deadline = loop.time() + spec['maxLifetimeSeconds']
    try:
        loop.add_reader(fd, readable); registered = True
        while not future.done():
            owner_check(spec['owner'])
            left = deadline - loop.time(); require(left > 0, 'ping_broker_lifetime_expired')
            try:
                await asyncio.wait_for(asyncio.shield(future), min(left, 0.25))
            except asyncio.TimeoutError:
                continue
        result = future.result(); owner_check(spec['owner']); return result
    finally:
        if registered:
            loop.remove_reader(fd)
        os.set_blocking(fd, blocking)
        if not future.done():
            future.cancel()


def validate_closed(value, broker_id, expected_pings):
    require(type(value) is dict and value.get('brokerId') == broker_id and value.get('pid') == os.getpid()
        and value.get('socketRemoved') is True and type(value.get('activeRequests')) is int
        and value['activeRequests'] == 0, 'ping_broker_close_unconfirmed')
    require(encode(value.get('counters')) == encode({'physicalAttempts': 0, 'responses': 0,
        'refused': 0, 'pings': expected_pings}), 'ping_broker_counters_not_ping_only')


START_OBSERVATION_SECONDS = 10
CLOSE_OBSERVATION_SECONDS = 8


async def hold_custody(record):
    """No automatic exit, task cancellation, socket cleanup, or control replay."""
    await asyncio.Future()


async def serve(api, spec, control_fd, directory_fd, guard, *, owner_check=check_parent,
                readback=installed_readback, publish=publish_receipt, wait_control=wait_shutdown,
                retain=hold_custody):
    broker, egress, principal = api; directory = Path(spec['brokerDirectory'])
    owner_check(spec['owner']); before = readback()
    config = egress.BrokerConfig(UPSTREAM, MODEL, DUMMY_BEARER, spec['signingKey'],
        str(directory.parent / 'broker-no-authority/state.db'), spec['scope'], spec['binding'],
        spec['policyFingerprint'], budget_authority=None, principal_contract=spec['principalContract'])
    server = broker.ProviderBrokerServer(config, directory)
    ready = None; closed = None; accepted_stop = False; start_task = None; close_task = None

    async def unknown(phase, exc):
        # This suspended frame keeps the original server and owned tasks alive.
        # A deadline is an observation failure, never shutdown authorization.
        record = {'schema': 1, 'kind': 'R168A1_PING_BROKER_UNKNOWN', 'result': 'UNKNOWN',
            'attemptId': spec['attemptId'], 'pid': os.getpid(), 'owner': spec['owner'],
            'phase': phase, 'broker': ready, 'shutdownCommandAccepted': accepted_stop,
            'reason': str(exc) if isinstance(exc, Refused) else type(exc).__name__,
            'startTaskDone': start_task.done() if start_task is not None else False,
            'closeTaskDone': close_task.done() if close_task is not None else False,
            'serverAcquired': server.server is not None,
            'countersObserved': dict(server.counts), 'closedObservation': closed,
            'readbackBefore': before, 'observationOnly': True, 'processRetained': True,
            'controllerMustRetainOwnership': True, 'automaticRetry': False, 'automaticCleanup': False,
            'upstreamStarted': False, 'providerSendInvokedByLauncher': False,
            'realModelCalls': 0, 'productionAcceptance': False}
        try:
            receipt = publish(directory_fd, 'unknown.json', record)
            record = dict(record, receipt=receipt)
        except BaseException:
            record = dict(record, custodyReceiptPublished=False)
        try:
            print(encode(record).decode(), end='', flush=True)
        except BaseException:
            pass
        await retain(record)
        raise Refused('ping_broker_custody_must_not_return')

    try:
        start_task = asyncio.create_task(server.start())
        ready = await asyncio.wait_for(asyncio.shield(start_task), START_OBSERVATION_SECONDS)
        require(type(ready) is dict and set(ready) == {'brokerId', 'socketPath', 'routeFingerprint', 'pid', 'backend'}
            and hexed(ready['brokerId'], 32) and ready['pid'] == os.getpid()
            and ready['socketPath'] == str(directory / 'egress.sock') and ready['routeFingerprint'] == config.route
            and ready['backend'] == 'linux_unix_credential_broker', 'ping_broker_ready_identity')
        identity = principal.socket_identity(spec['principalContract'], ready['socketPath'])
        require(encode(server.counts) == encode({'physicalAttempts': 0, 'responses': 0, 'refused': 0, 'pings': 0}),
            'ping_broker_start_counters')
        owner_check(spec['owner'])
        record = dict(before, schema=1, kind='R168A1_PING_BROKER_READY', attemptId=spec['attemptId'],
            pid=os.getpid(), owner=spec['owner'], broker=ready, principalContract=spec['principalContract'],
            socketIdentity=identity, expectedPings=spec['expectedPings'], maxLifetimeSeconds=spec['maxLifetimeSeconds'])
        receipt = publish(directory_fd, 'ready.json', record)
        print(encode(dict(record, receipt=receipt)).decode(), end='', flush=True)
    except BaseException as exc:
        return await unknown('START_OR_READY', exc)
    try:
        require(await wait_control(control_fd, spec, ready['brokerId'], owner_check=owner_check) is True,
                'ping_broker_shutdown_not_acknowledged')
        accepted_stop = True
    except BaseException as exc:
        return await unknown('WAIT_CONTROL', exc)
    try:
        # Only the exact accepted owner command may initiate this one close.
        close_task = asyncio.create_task(server.close())
        closed = await asyncio.wait_for(asyncio.shield(close_task), CLOSE_OBSERVATION_SECONDS)
        require(type(closed) is dict and closed.get('brokerId') == ready['brokerId']
            and closed.get('pid') == os.getpid() and closed.get('socketRemoved') is True
            and type(closed.get('activeRequests')) is int and closed['activeRequests'] == 0
            and not os.path.lexists(directory / 'egress.sock'), 'ping_broker_socket_close_unconfirmed')
    except BaseException as exc:
        return await unknown('CLOSE_OBSERVATION', exc)
    reason = None; after = None
    try:
        after = readback(); require(encode(before) == encode(after), 'ping_broker_source_changed')
        validate_closed(closed, ready['brokerId'], spec['expectedPings'])
        require(guard.denied_count == 0, 'ping_broker_forbidden_effect_observed')
    except BaseException as exc:
        reason = str(exc) if isinstance(exc, Refused) else type(exc).__name__
    result = 'PASS' if reason is None else 'FAIL'
    record = {'schema': 1, 'kind': 'R168A1_PING_BROKER_TERMINAL', 'result': result,
        'attemptId': spec['attemptId'], 'pid': os.getpid(), 'owner': spec['owner'], 'broker': ready,
        'shutdownCommandAccepted': True, 'closeConfirmed': True,
        'closed': closed, 'reason': reason, 'readbackBefore': before, 'readbackAfter': after,
        'forbiddenEffects': {'count': guard.denied_count, 'events': list(guard.denied)},
        'controllerMustRetainOwnership': result != 'PASS', 'automaticRetry': False,
        'upstreamStarted': False, 'providerSendInvokedByLauncher': False, 'realModelCalls': 0,
        'productionAcceptance': False, 'processExitMustBeObservedByController': True}
    try:
        receipt = publish(directory_fd, 'shutdown.json', record)
        print(encode(dict(record, receipt=receipt)).decode(), end='', flush=True)
    except BaseException as exc:
        return await unknown('TERMINAL_PUBLICATION', exc)
    return dict(record, receipt=receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec-fd', type=int, required=True)
    parser.add_argument('--control-fd', type=int, required=True)
    parser.add_argument('--expected-spec-sha256', required=True)
    args = parser.parse_args(); directory_fd = None
    try:
        spec = read_spec(args.spec_fd, args.expected_spec_sha256)
        check_parent(spec['owner']); descriptor_preflight(spec, args.spec_fd, args.control_fd)
        guard = NoUpstream(spec['brokerDirectory'] + '/egress.sock'); sys.addaudithook(guard)
        api = load_installed(); directory_fd = directory_preflight(spec, api[2])
        result = asyncio.run(serve(api, spec, args.control_fd, directory_fd, guard))
        return 0 if result['result'] == 'PASS' else 2
    except BaseException as exc:
        print(json.dumps({'kind': 'R168A1_PING_BROKER_REFUSED', 'result': 'FAIL',
            'reason': str(exc) if isinstance(exc, Refused) else type(exc).__name__,
            'controllerMustRetainOwnership': True, 'automaticRetry': False}, sort_keys=True), flush=True)
        return 2
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


if __name__ == '__main__':
    raise SystemExit(main())
