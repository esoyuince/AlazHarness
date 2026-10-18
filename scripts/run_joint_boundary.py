"""Opt-in composition of the existing network and credential launchers.

Order is fixed: network namespace/seccomp -> Landlock -> explicit target.
Neither component is weakened. No service, scheduler or unconfined fallback.
This is not a complete host IPC/UID sandbox or independent budget authority.
"""
from pathlib import Path
import argparse
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
from credential_guard import GuardRejected, require, unique_json, validate_policy


def _absolute_file(value, reason):
    path = Path(value).absolute()
    require(Path(value).is_absolute() and path == path.resolve()
            and path.is_file() and not path.is_symlink(), reason)
    return path


def compose(policy_file, network_receipt, credential_receipt, command,
            *, python=None, root=ROOT):
    require(isinstance(command, (tuple, list)) and 1 <= len(command) <= 128,
            'joint_command_count')
    require(all(type(x) is str and '\x00' not in x and len(x.encode()) <= 8192
                for x in command), 'joint_command_argument')
    require(sum(len(x.encode()) for x in command) <= 131072, 'joint_command_size')
    executable = _absolute_file(command[0], 'joint_target_file')
    interpreter = _absolute_file(python or sys.executable, 'joint_python_file')
    cfg = _absolute_file(policy_file, 'joint_policy_file')
    require(cfg.stat().st_size <= 32768, 'joint_policy_size')
    policy = validate_policy(unique_json(cfg.read_text(encoding='utf-8')))
    net = Path(network_receipt).absolute()
    cred = Path(credential_receipt).absolute()
    require(net != cred and net != cfg and cred != cfg, 'joint_receipt_collision')
    for path in (net, cred):
        require(path == path.resolve() and path.parent.is_dir()
                and not path.exists() and not path.is_symlink()
                and any(path.is_relative_to(Path(p)) for p in policy['writable']),
                'joint_fresh_granted_receipt_required')
    scripts = Path(root).resolve()/'scripts'
    network = _absolute_file(scripts/'run_in_network_namespace.py', 'joint_network_launcher')
    credential = _absolute_file(scripts/'run_credential_guard.py', 'joint_credential_launcher')
    require(any(executable.is_relative_to(Path(p)) for p in policy['readonly']),
            'joint_target_not_readonly')
    return (str(interpreter), '-I', '-B', str(network), '--receipt', str(net), '--',
            str(interpreter), '-I', '-B', str(credential), '--policy', str(cfg),
            '--receipt', str(cred), '--', *command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--network-receipt', type=Path, required=True)
    parser.add_argument('--credential-receipt', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        require(sys.platform == 'linux', 'joint_linux_required')
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        argv = compose(args.policy, args.network_receipt, args.credential_receipt, command)
        os.execv(argv[0], argv)
    except Exception as error:
        reason = str(error) if isinstance(error, GuardRejected) else type(error).__name__
        import json
        print(json.dumps({'error':'joint_launch_refused','reason':reason,'fallback':False}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
