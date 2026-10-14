"""Run the real Hermes probe in a fresh, credential-free profile. No installs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def isolated_environment(work: Path) -> dict[str,str]:
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','PATH','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'}}
    for name in ('home','home/local','home/roaming','temp','profile','tools'):
        (work/name).mkdir(parents=True,exist_ok=True)
    env.update(HOME=str(work/'home'),USERPROFILE=str(work/'home'),LOCALAPPDATA=str(work/'home/local'),
               APPDATA=str(work/'home/roaming'),TEMP=str(work/'temp'),TMP=str(work/'temp'),
               HERMES_HOME=str(work/'profile'),HERMES_RUNTIME_DIR=str(work/'tools'),
               HERMES_DISABLE_LAZY_INSTALLS='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    return env


def pinned_source(root: Path, source_workspace: Path) -> Path:
    source=source_workspace.resolve()/'vendor/hermes-agent'
    lock=json.loads((root/'sources.lock.json').read_text(encoding='utf-8'))
    pin=next(r['commit'] for r in lock['repositories'] if r['name']=='hermes-agent')
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,timeout=15).strip()
    if head!=pin:raise RuntimeError('Refusing unpinned source')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True,timeout=15).strip():
        raise RuntimeError('Refusing modified vendor source')
    if (source/'.env').exists():raise RuntimeError('Refusing source with dotenv')
    return source


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path)
    p.add_argument('--python',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--scenario',choices=('file-read','budget-summary'),default='file-read')
    args=p.parse_args();root=Path(__file__).resolve().parents[1]
    source=pinned_source(root,args.source_workspace);work=args.output.absolute()
    if not args.python.is_file():raise RuntimeError('Prepared interpreter is missing; no automatic install')
    if work.exists():raise FileExistsError('Use a fresh output directory')
    work.mkdir(parents=True)
    env=isolated_environment(work)
    command=[str(args.python.absolute()),'-I','-B',str(root/'scripts/native_hermes_probe_worker.py'),str(source),str(work),args.scenario]
    with (work/'stdout.txt').open('w',encoding='utf-8') as out,(work/'stderr.txt').open('w',encoding='utf-8') as err:
        run=subprocess.run(command,cwd=work,env=env,stdout=out,stderr=err,timeout=100)
    receipt=work/'receipt.json'
    print('EXIT',run.returncode)
    print(receipt.read_text(encoding='utf-8') if receipt.exists() else 'No native acceptance receipt')
    if run.returncode:
        print((work/'stderr.txt').read_text(encoding='utf-8')[-6500:])
        print((work/'stdout.txt').read_text(encoding='utf-8')[-3000:])
    return run.returncode

if __name__=='__main__':raise SystemExit(main())
