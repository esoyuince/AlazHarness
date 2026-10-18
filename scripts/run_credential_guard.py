"""Explicit child-only Landlock launcher. Exits on failure; never falls back."""
from pathlib import Path
import argparse
import json
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
from credential_guard import apply, unique_json, validate_policy, require, GuardRejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        require(bool(command) and Path(command[0]).is_absolute(), 'credential_guard_command_required')
        require(not args.policy.is_symlink() and args.policy.is_file(), 'credential_guard_policy_file')
        require(args.policy.stat().st_size <= 32768, 'credential_guard_policy_size')
        policy = validate_policy(unique_json(args.policy.read_text(encoding='utf-8')))
        receipt = args.receipt.absolute()
        require(not receipt.exists() and not receipt.is_symlink() and receipt.parent.is_dir()
                and receipt == receipt.resolve() and
                any(receipt.is_relative_to(Path(p)) for p in policy['writable']),
                'credential_guard_receipt_path')
        # Policy file must have been closed before FD preflight/enforcement.
        result = apply(policy)
        with receipt.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True)
            f.write('\n')
        os.execv(command[0], command)
    except Exception as exc:
        reason = str(exc) if isinstance(exc, GuardRejected) else type(exc).__name__
        print(json.dumps({"error":"credential_guard_launch_refused","reason":reason,"fallback":False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
