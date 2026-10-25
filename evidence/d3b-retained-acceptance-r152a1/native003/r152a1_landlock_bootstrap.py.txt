"""Fresh fixed QA interpreter: original guard before native imports, then QA exec.

This exists because a completed native owner can leave unrelated non-inheritable
interpreter descriptors. Ordinary exec supplies a fresh interpreter; this helper
never closes arbitrary descriptors or weakens the original guard's FD check.
It is not the product projected launcher or a namespace/privilege transition.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/usr/bin/python3.12'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--compute-failure', action='store_true')
    args = parser.parse_args()
    assert sys.platform == 'linux' and sys.executable == PYTHON
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert os.getresuid() == (23001,) * 3 and os.getresgid() == (23003,) * 3
    assert args.native == ROOT.parent / 'native' and args.output == ROOT.parent / 'result'
    assert args.home.parent == ROOT.parent / 'tmp' and args.home.name.startswith('alaz-r152a1-home-')
    assert args.home.resolve(strict=True) == args.home
    assert os.environ['HOME'] == os.environ['HERMES_HOME'] == str(args.home)
    assert os.environ['TMPDIR'] == str(args.home.parent)
    assert set(os.environ) == {'PATH', 'LANG', 'HOME', 'HERMES_HOME', 'TMPDIR', 'TMP', 'TEMP',
                               'WSL_DISTRO_NAME', 'PYTHONUTF8', 'TZ', 'R152_HANDOFF', 'R152_PRIOR_SHA256'}
    raw = (args.output / 'pre-exec.json').read_bytes()
    prior_sha = hashlib.sha256(raw).hexdigest()
    assert prior_sha == os.environ['R152_PRIOR_SHA256']
    prior = json.loads(raw)
    start = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
    assert prior['pid'] == os.getpid() and prior['startTicks'] == start
    assert prior['home'] == str(args.home) and prior['computeFailure'] is args.compute_failure
    assert prior['allOwnersClosedBeforeExec'] and prior['checks'] and all(prior['checks'].values())
    sys.path[:0] = [str(ROOT / 'scripts/qa'), str(ROOT / 'packages/claw-hermes')]
    import r152a1_landlock_native as qa
    assert Path(qa.__file__).resolve() == ROOT / 'scripts/qa/r152a1_landlock_native.py'
    assert not any(name == 'gateway' or name.startswith('gateway.') or name.startswith('hermes_state')
                   or name == 'run_agent' for name in sys.modules)
    proof = qa.apply_current_landlock(args.native, args.output, args.home)
    proof.update(pid=os.getpid(), startTicks=start, preExecSha256=prior_sha,
                 freshInterpreterBeforeGuard=True, noNativeModulesBeforeGuard=True,
                 bootstrapSourceSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 driverSourceSha256=hashlib.sha256(Path(qa.__file__).read_bytes()).hexdigest())
    proof_bytes = (json.dumps(proof, indent=2, sort_keys=True) + '\n').encode('utf-8')
    with (args.output / 'kernel-proof.json').open('xb') as stream:
        stream.write(proof_bytes)
    environment = dict(os.environ)
    environment['R152_KERNEL_SHA256'] = hashlib.sha256(proof_bytes).hexdigest()
    entry = "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
    command = [PYTHON, '-I', '-B', '-c', entry, '/opt/alaz-f126c1a6/dependencies',
               str(ROOT / 'scripts/qa/r152a1_landlock_native.py'), '--native', str(args.native),
               '--output', str(args.output), '--resume', '--home', str(args.home)]
    if args.compute_failure:
        command.append('--compute-failure')
    print('R152_CONFINED_EXECVE_REQUEST ' + json.dumps({'pid': os.getpid(), 'samePid': True,
          'fixedQaTarget': True, 'productProjectedTarget': False}), flush=True)
    os.execve(PYTHON, command, environment)
    raise RuntimeError('fixed_exec_returned')


if __name__ == '__main__':
    raise SystemExit(main())
