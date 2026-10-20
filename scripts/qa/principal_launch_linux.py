"""Unprivileged actual Linux admission/descriptor checks; NEVER execute UID drop."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import principal_launch as launch
SOURCES = ('packages/claw-hermes/principal_launch.py', 'scripts/run_principal_broker.py',
           'tests/test_principal_launch.py', 'scripts/qa/principal_launch_linux.py',
           'packages/claw-hermes/host_principal.py', 'packages/claw-hermes/linux_netns.py')


def hashes():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output_arg = parser.parse_args().output
    output = output_arg.resolve()
    if (sys.platform != 'linux' or os.getuid() == 0 or os.getgid() == 0
            or output_arg.is_symlink() or output.exists()
            or output.parent != (ROOT/'evidence/d3b-principal-launch-21oct').resolve()):
        raise SystemExit('unprivileged_fresh_evidence_required')
    before = hashes(); state = launch.observation(); checks = {}; errors = {}
    def check(name, fn):
        try: checks[name] = fn() is True
        except Exception as exc: checks[name] = False; errors[name] = type(exc).__name__
    def refused(fn, reason):
        try: fn()
        except launch.LaunchRejected as exc: return str(exc) == reason
        return False
    value = {'version': 1, 'enabled': True, 'role': 'broker',
        'principalContract': {'version': 1, 'enabled': True, 'gatewayUid': os.getuid(),
            'brokerUid': os.getuid()+10000, 'socketGroupGid': os.getgid(),
            'hostUserNamespace': state['userns']},
        'python': str(Path(sys.executable).resolve()), 'config': '/srv/alaz-no-fixture/config.json',
        'output': '/srv/alaz-no-fixture/sock', 'configSha256': 'a'*64, 'commandSha256': ''}
    value['commandSha256'] = launch.command_digest(launch.command(value))
    check('kernel_ids_match_current_process', lambda: state['uids'][:3] == os.getresuid()
          and state['gids'][:3] == os.getresgid() and state['pid'] == os.getpid())
    check('current_user_not_accepted_as_controller', lambda: refused(
        lambda: launch.launch(value), 'launch_authorized_host_root_required'))
    check('gateway_role_cannot_bypass_projection', lambda: refused(
        lambda: launch.launch(value | {'role': 'gateway'}),
        'launch_broker_only_gateway_projection_pending'))
    check('contract_not_read_without_host_root', lambda: refused(
        lambda: launch.load_contract('/not-opened-contract'), 'launch_authorized_host_root_required'))
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/', 'PYTHONNOUSERSITE': '1'}
    r = subprocess.run([sys.executable, '-I', '-B', str(ROOT/'scripts/run_principal_broker.py'),
                        '--contract', '/not-opened-contract'], capture_output=True, timeout=10,
                       env=env, cwd='/')
    try: cli = json.loads(r.stderr)
    except Exception: cli = {}
    check('real_cli_refuses_without_target_exec', lambda: r.returncode == 2
          and not r.stdout and cli.get('result') == 'REFUSED'
          and cli.get('fallback') is False and cli.get('targetExecutionVerified') is False)
    setup = 'import sys,os,socket,json;sys.path.insert(0,'+repr(str(ROOT/'packages/claw-hermes'))+');import principal_launch as p\n'
    child_close = setup + '''
fd=int(sys.argv[1])
p.close_ambient_fds()
try:os.fstat(fd)
except OSError:print(json.dumps({'closed':True}))
else:print(json.dumps({'closed':False}))
'''
    left, right = socket.socketpair()
    try:
        inherited = subprocess.run([sys.executable, '-I', '-B', '-c', child_close, str(left.fileno())],
            pass_fds=(left.fileno(),), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, cwd='/', timeout=10)
        check('real_inherited_socket_fd_closed_in_child', lambda: inherited.returncode == 0
              and json.loads(inherited.stdout).get('closed') is True)
        socket_stdin = setup + '''
try:p.close_ambient_fds()
except p.LaunchRejected as e:print(json.dumps({'refused':str(e)=='launch_stdio_must_be_pipe_or_devnull'}))
else:print(json.dumps({'refused':False}))
'''
        denied = subprocess.run([sys.executable, '-I', '-B', '-c', socket_stdin],
            stdin=left, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd='/', timeout=10)
        check('real_socket_stdio_refused', lambda: denied.returncode == 0
              and json.loads(denied.stdout).get('refused') is True)
        check('parent_owns_socket_after_child_cleanup', lambda: left.fileno() >= 0
              and right.fileno() >= 0 and os.fstat(left.fileno()).st_ino > 0)
    finally:
        left.close(); right.close()
    with tempfile.TemporaryDirectory(prefix='alaz-principal-launch-') as tmp:
        path = Path(tmp)/'owned.txt'; path.write_text('owned fixture only')
        prior = hashlib.sha256(path.read_bytes()).hexdigest()
        check('untrusted_directory_is_not_adopted', lambda: refused(
            lambda: launch.trusted_ancestors(path, {0}), 'launch_untrusted_parent'))
        check('fixture_bytes_unchanged', lambda: hashlib.sha256(path.read_bytes()).hexdigest() == prior)
    check('owned_temporary_directory_removed', lambda: not Path(tmp).exists())
    check('observer_identity_and_namespace_unchanged', lambda: launch.observation() == state)
    after = hashes()
    check('source_bytes_unchanged', lambda: before == after)
    report = {'result': 'PASS_SCOPED_UNPRIVILEGED' if all(checks.values()) else 'FAIL',
        'observedAt': datetime.datetime.now().astimezone().isoformat(),
        'checks': checks, 'checkCount': len(checks), 'errors': errors,
        'sourceSha256': before, 'sourceAfterSha256': after,
        'observedUid': os.getuid(), 'observedGid': os.getgid(),
        'privilegedSyscallsExecuted': False, 'positiveUidTransitionTested': False,
        'gatewayBrokerTwoUidTested': False, 'ipcV2MountTested': False,
        'fullD3BAccepted': False, 'realModelCalls': 0}
    with output.open('x', encoding='utf-8') as f: json.dump(report,f,indent=2); f.write('\n')
    print(json.dumps({'result': report['result'], 'checks': len(checks),
                      'failures': [k for k,v in checks.items() if not v], 'errors': errors}))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__': raise SystemExit(main())
