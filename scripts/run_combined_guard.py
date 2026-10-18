"""Opt-in same-process network + Landlock launcher; no single-layer fallback."""
from pathlib import Path
import argparse
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import combined_guard as combined
from credential_guard import unique_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a=p.parse_args()
    phase='preflight'
    try:
        cmd=a.command[1:] if a.command[:1]==['--'] else a.command
        combined.require(bool(cmd) and Path(cmd[0]).is_absolute() and Path(cmd[0]).is_file(),
                         'combined_absolute_existing_executable')
        combined.require(a.contract.is_file() and not a.contract.is_symlink()
                         and a.contract.stat().st_size <= 32768, 'combined_contract_file')
        value=combined.validate_contract(unique_json(a.contract.read_text(encoding='utf-8')))
        combined.require(combined.command_digest(cmd)==value['commandSha256'], 'combined_command_mismatch')
        receipt=a.receipt.absolute()
        combined.require(not receipt.exists() and not receipt.is_symlink()
            and receipt.parent.is_dir() and receipt==receipt.resolve()
            and any(receipt.is_relative_to(Path(x)) for x in value['filesystem']['writable']),
            'combined_receipt_path')
        phase='enforcement'
        record=combined.enforce(value,cmd)
        with receipt.open('x',encoding='utf-8') as f:
            json.dump(record,f,ensure_ascii=False,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
        phase='target_exec'
        os.execv(cmd[0],cmd)
    except Exception as exc:
        # Exception messages and argv can contain credentials; publish types only.
        print(json.dumps({'error':'combined_guard_launch_refused','phase':phase,
              'reasonType':type(exc).__name__,'fallback':False}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
