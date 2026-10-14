"""Prepare a fresh pinned Hermes environment through its PM API. Dry-run by default."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from run_native_hermes_probe import isolated_environment, pinned_source


def build_code(source: Path, output: Path) -> str:
    # Only generated literals enter the child; no shell interpolation or user code.
    return (
        'import sys,json;from pathlib import Path;'
        f'sys.path.insert(0,{str(source)!r});import pm;'
        f'p=pm.build_environment(source=Path({str(source)!r}),'
        f'out=Path({str(output / "env")!r}),python=Path(sys.executable),'
        f'cache=Path({str(output / "cache")!r}),extras=(),groups=(),'
        'no_install_project=True,frozen=True,explicit=True,timeout=420);'
        'print(json.dumps({"python":str(p)}))'
    )


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    source=pinned_source(Path(__file__).resolve().parents[1],args.source_workspace)
    out=args.output.absolute()
    if out.exists():raise FileExistsError('Use a new environment output directory')
    if sys.version_info[:2]!=(3,14):raise RuntimeError('Pinned Hermes native execution requires Python 3.14')
    print(json.dumps({'mode':'apply' if args.apply else 'plan','source':str(source),
                      'output':str(out),'frozen':True,'extras':[],
                      'builder':'pm.build_environment','agent_started':False}))
    if not args.apply:return 0
    out.mkdir(parents=True)
    env=isolated_environment(out)
    # Dependency installation is explicitly authorized only in this preparation child.
    env.pop('HERMES_DISABLE_LAZY_INSTALLS',None)
    env.update(UV_CACHE_DIR=str(out/'cache'),UV_PYTHON_INSTALL_DIR=str(out/'tools/bootstrap-python'))
    code=build_code(source,out)
    started=time.monotonic()
    with (out/'build.stdout.txt').open('w',encoding='utf-8') as stdout,(out/'build.stderr.txt').open('w',encoding='utf-8') as stderr:
        result=subprocess.run([sys.executable,'-I','-B','-c',code],cwd=out,env=env,stdout=stdout,stderr=stderr,timeout=540)
    receipt={'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-started,2),
             'builder':'pm.build_environment','frozen':True,'extras':[],
             'scope':'dependency preparation only; not native-agent acceptance'}
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
