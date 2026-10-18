"""Explicit operator launch in D3B1 network boundary. No ambient fallback."""
from pathlib import Path
import argparse,json,os,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from linux_netns import enter

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    if not cmd or not Path(cmd[0]).is_absolute() or not Path(cmd[0]).is_file():
        raise SystemExit('absolute_existing_executable_required')
    if a.receipt.exists() or a.receipt.is_symlink() or not a.receipt.parent.is_dir():
        raise SystemExit('new_receipt_path_required')
    try:
        record=enter()
        with a.receipt.open('x',encoding='utf-8') as f:
            json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
        os.execv(cmd[0],cmd)
    except Exception as exc:
        print('network_boundary_launch_failed:'+type(exc).__name__,file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
