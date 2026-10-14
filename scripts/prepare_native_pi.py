"""Prepare a separate pinned Pi source snapshot. Plan only unless --apply is passed."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
from pi_probe_support import check_source,digest,fresh_runtime_path,isolated_env,pi_record


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args();workspace=a.source_workspace.resolve()
    source=workspace/pi_record()['local_reference_path_from_default_workspace']
    pin=check_source(source);out=fresh_runtime_path(workspace,a.output)
    node=shutil.which('node')
    if node is None:raise ValueError('Node required')
    npm=Path(node).parent/'node_modules/npm/bin/npm-cli.js'
    if not npm.is_file():raise ValueError('Expected npm-cli.js alongside Node; no implicit install')
    cmd=[node,str(npm),'ci','--ignore-scripts','--no-audit','--no-fund']
    print(json.dumps({'mode':'apply' if a.apply else 'plan','source_commit':pin,'output':str(out),
                      'install_argv':cmd,'model_calls':0}))
    if not a.apply:return 0
    out.mkdir(parents=True);env=isolated_env(out);snapshot=out/'source'
    subprocess.run(['git','-c','core.hooksPath=NUL','clone','--local','--no-hardlinks','--no-checkout','--no-tags',str(source),str(snapshot)],check=True,capture_output=True,timeout=45)
    subprocess.run(['git','-C',str(snapshot),'-c','core.hooksPath=NUL','checkout','--detach',pin],check=True,capture_output=True,timeout=45)
    subprocess.run(['git','-C',str(snapshot),'config','remote.origin.pushurl','DISABLED'],check=True)
    original_lock=digest(snapshot/'package-lock.json');start=time.monotonic()
    with (out/'install.stdout.txt').open('w',encoding='utf-8') as stdout,(out/'install.stderr.txt').open('w',encoding='utf-8') as stderr:
        run=subprocess.run(cmd,cwd=snapshot,env=env,stdout=stdout,stderr=stderr,timeout=300)
    check_source(source);check_source(snapshot)
    if digest(snapshot/'package-lock.json')!=original_lock:raise ValueError('npm changed source lock')
    receipt={'scope':'dependency preparation only','source_commit':pin,'exit_code':run.returncode,
             'elapsed_seconds':round(time.monotonic()-start,3),'package_lock_sha256':original_lock,
             'source_unchanged':True,'lifecycle_scripts_enabled':False,'model_calls':0,
             'node':subprocess.check_output([node,'--version'],text=True).strip(),
             'npm':subprocess.check_output([node,str(npm),'--version'],text=True,env=env).strip()}
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    if run.returncode:print((out/'install.stderr.txt').read_text(encoding='utf-8')[-5000:])
    return run.returncode

if __name__=='__main__':raise SystemExit(main())
