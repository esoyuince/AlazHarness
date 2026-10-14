"""Run one bounded scripted component demo; no model keys, agents or network calls."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=('tool-round','echo'), default='tool-round')
    parser.add_argument('--text', default='Demonstrate the scripted 2 + 3 tool round')
    parser.add_argument('--iterations', type=int, default=2, choices=range(1,17))
    args=parser.parse_args()
    node=shutil.which('node')
    if not node:parser.error('Node 24+ is required')
    root=Path(__file__).resolve().parents[1]
    return subprocess.run([node,str(root/'packages/hybrid-runtime/demo.mjs'),sys.executable,
                           str(root/'runtime/component-demo'),args.scenario,args.text,str(args.iterations)],
                          cwd=root,timeout=20).returncode
if __name__=='__main__':raise SystemExit(main())
