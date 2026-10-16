"""Opt-in pinned Hermes Linux environment preparation, not agent acceptance.
Fresh operator-owned destination only. No system package install or user profile.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args();source=a.source.resolve();out=a.output.absolute()
    if os.name!='posix' or not a.source.is_absolute() or not a.output.is_absolute():
        raise ValueError('Explicit Linux paths required')
    if out.exists() or out==source or out.is_relative_to(source):raise ValueError('Fresh separate destination required')
    manifest=json.loads((source/'alaz-source-manifest.json').read_text())
    if manifest['sourceCommit']!=PIN:raise ValueError('Unexpected source pin')
    for n,digest in manifest['files'].items():
        candidate=source/n
        if not candidate.resolve().is_relative_to(source) or candidate.is_symlink() or hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:
            raise ValueError('Source bytes changed')
    import tomllib
    project=tomllib.loads((source/'pyproject.toml').read_text())
    if project['project']['optional-dependencies']['sms']!=['aiohttp==3.14.3']:raise ValueError('HTTP dependency changed')
    print(json.dumps({'mode':'apply' if a.apply else 'plan','source_commit':PIN,'source_files':len(manifest['files']),
        'frozen':True,'extras':['sms'],'agent_started':False,'system_packages_modified':False}),flush=True)
    if not a.apply:return 0
    out.mkdir(parents=True,mode=0o700)
    for n in ('home','profile','tools','cache','tmp','xdg-data','xdg-config','xdg-cache'):(out/n).mkdir()
    env={'PATH':'/usr/bin:/bin','HOME':str(out/'home'),'HERMES_HOME':str(out/'profile'),
         'HERMES_RUNTIME_DIR':str(out/'tools'),'TMPDIR':str(out/'tmp'),'UV_CACHE_DIR':str(out/'cache'),
         'UV_PYTHON_INSTALL_DIR':str(out/'tools/bootstrap-python'),'PYTHONDONTWRITEBYTECODE':'1',
         'PYTHONUNBUFFERED':'1','LANG':'C.UTF-8','XDG_DATA_HOME':str(out/'xdg-data'),
         'XDG_CONFIG_HOME':str(out/'xdg-config'),'XDG_CACHE_HOME':str(out/'xdg-cache')}
    code=('import sys,json;from pathlib import Path;sys.path.insert(0,'+repr(str(source))+');import pm;'
          'p=pm.build_environment(source=Path('+repr(str(source))+'),out=Path('+repr(str(out/'env'))+'),'
          'cache=Path('+repr(str(out/'cache'))+'),extras=("sms",),groups=(),no_install_project=True,'
          'frozen=True,explicit=True,timeout=480);print(json.dumps({"python":str(p)}))')
    started=time.monotonic();timeout=False
    with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
        child=subprocess.Popen(['/usr/bin/python3','-I','-B','-c',code],cwd=out,env=env,
            stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
        (out/'process.json').write_text(json.dumps({'pid':child.pid,'start_ticks':Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]}))
        try:child.wait(timeout=600)
        except subprocess.TimeoutExpired:
            timeout=True
            if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
            child.wait(timeout=10)
    receipt={'source_commit':PIN,'scope':'frozen dependency preparation only, not native Gateway or isolation acceptance',
        'exit_code':child.returncode,'timed_out':timeout,'parent_reaped':child.poll() is not None,
        'elapsed_seconds':round(time.monotonic()-started,3),'environment_names':sorted(env),
        'expected_python':str(out/'env/bin/python'),'model_calls':0,'system_packages_modified':False}
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
    if child.returncode:print((out/'stderr.txt').read_text(errors='replace')[-6000:],file=sys.stderr)
    return 0 if child.returncode==0 else 1

if __name__=='__main__':raise SystemExit(main())
