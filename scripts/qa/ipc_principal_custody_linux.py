"""Owned Linux pathname-socket metadata/race probes; never two-UID acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import ipc_view as ipc

SOURCES = ('packages/claw-hermes/ipc_view.py',
           'packages/claw-hermes/host_principal.py',
           'scripts/qa/ipc_principal_custody_linux.py',
           'tests/test_ipc_principal_custody.py')

def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCES}

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    dest = args.output.resolve()
    expected = (ROOT / 'evidence/d3b-ipc-custody-cf57').resolve()
    if (sys.platform != 'linux' or os.getuid() == 0 or os.getgid() == 0
            or not expected.is_dir() or dest.parent != expected
            or dest.exists() or args.output.is_symlink()):
        raise SystemExit('unprivileged_new_owned_evidence_required')
    before = hashes()
    checks = {}
    errors = {}
    temp_paths = []
    def check(name, action):
        try:
            checks[name] = action() is True
        except Exception as exc:
            checks[name] = False
            errors[name] = type(exc).__name__
    def fixture_case(kind):
        with tempfile.TemporaryDirectory(prefix='alaz-ipc-cf57-') as tmp:
            root = Path(tmp)
            temp_paths.append(root)
            directory = root / 'broker'
            directory.mkdir(mode=0o710)
            directory.chmod(0o710)
            path = directory / 'egress.sock'
            sockets = []
            def bind():
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sockets.append(sock)
                sock.bind(str(path))
                path.chmod(0o660)
            bind()
            principal = {'version': 1, 'enabled': True,
                         'gatewayUid': os.getuid() + 1,
                         'brokerUid': os.getuid(),
                         'socketGroupGid': os.getgid(),
                         'hostUserNamespace': os.readlink('/proc/self/ns/user')}
            value = {'version': 2, 'mode': 'projected_root_principal',
                     'root': '/tmp/alaz-ipc-cf57-unused',
                     'brokerSocket': str(path), 'principalContract': principal}
            fs = {'version': 1, 'enabled': True, 'readonly': ['/usr'],
                  'writable': ['/dev/null'], 'protected': [str(root / 'canary')]}
            original = ipc.identity
            fired = []
            def mutate(selected):
                if not fired and str(selected) == str(path):
                    fired.append(kind)
                    if kind == 'inode':
                        path.unlink()
                        bind()  # Keep original socket open: inode reuse is excluded.
                    elif kind == 'mode':
                        path.chmod(0o666)
                    elif kind == 'parent_mode':
                        directory.chmod(0o711)
                return original(selected)
            try:
                if kind == 'stable':
                    value_before = json.dumps(value, sort_keys=True)
                    record = ipc.inspect_principal_socket(value, fs)
                    return (record['mountAuthorized'] is False
                            and record['socketIdentity'][:2] == record['socketPrincipal']['socket'][:2]
                            and json.dumps(value, sort_keys=True) == value_before)
                if kind == 'gate':
                    ipc.inspect_principal_socket(value, fs)
                    try:
                        ipc.prepare(value, fs)
                    except ipc.IPCViewRejected as exc:
                        return str(exc) == 'ipc_principal_runtime_not_integrated'
                    return False
                with patch.object(ipc, 'identity', side_effect=mutate):
                    try:
                        ipc.inspect_principal_socket(value, fs)
                    except ipc.IPCViewRejected as exc:
                        return (bool(fired) and str(exc) in
                                ('ipc_principal_socket_changed', 'ipc_principal_socket_invalid'))
                    return False
            finally:
                for sock in sockets:
                    sock.close()
    for name, kind in [('stable_owned_metadata_only', 'stable'),
                       ('actual_socket_inode_rebind_refused', 'inode'),
                       ('actual_socket_mode_drift_refused', 'mode'),
                       ('actual_parent_mode_drift_refused', 'parent_mode'),
                       ('successful_metadata_cannot_open_mount_gate', 'gate')]:
        check(name, lambda kind=kind: fixture_case(kind))
    check('owned_temporary_paths_removed', lambda: all(not p.exists() for p in temp_paths))
    after = hashes()
    check('source_bytes_unchanged_during_run', lambda: before == after)
    value = {'result': 'PASS_SCOPED_METADATA' if all(checks.values()) else 'FAIL',
             'scope': 'unprivileged Linux owned pathname-socket metadata and injected timing only',
             'checks': checks, 'errors': errors, 'checkCount': len(checks),
             'sourceSha256': before, 'sourceSha256After': after,
             'observerUid': os.getuid(), 'observerGid': os.getgid(),
             'declaredGatewayFixtureUid': os.getuid() + 1,
             'declaredGatewayIsNotAnObservedProcess': True,
             'separateHostUidVerified': False, 'gatewayBrokerTransportTested': False,
             'mountPerformed': False, 'fullD3BAccepted': False, 'realModelCalls': 0}
    with dest.open('x', encoding='utf-8') as out:
        json.dump(value, out, indent=2)
        out.write(chr(10))
    print(json.dumps(value, sort_keys=True), flush=True)
    return 0 if all(checks.values()) else 1

if __name__ == '__main__':
    raise SystemExit(main())
