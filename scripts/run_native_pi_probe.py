"""Opt-in native Pi probe; uses a prepared source snapshot, not an installed personal agent."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from pi_probe_support import ROOT,check_source,digest,fresh_runtime_path,isolated_env

SCENARIOS=('file-read','missing-file','cancel-model','one-round','request-cap','truncated-tool')

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scenario',choices=SCENARIOS,default='file-read')
    a=p.parse_args();prepared=a.prepared.resolve();source=prepared/'source'
    pin=check_source(source)
    receipt=json.loads((prepared/'preparation.json').read_text(encoding='utf-8'))
    if receipt.get('exit_code')!=0 or receipt.get('source_commit')!=pin:raise ValueError('Preparation did not succeed')
    if digest(source/'package-lock.json')!=receipt['package_lock_sha256']:raise ValueError('Preparation lock mismatch')
    if not (source/'node_modules/openai/package.json').is_file():raise ValueError('Native dependencies missing; never auto-installed')
    node=shutil.which('node')
    if not node:raise ValueError('Node required')
    output=fresh_runtime_path(a.source_workspace,a.output);output.mkdir(parents=True)
    env=isolated_env(output);env['PI_PROBE_OUTPUT']=str(output)
    resolver=source/'packages/coding-agent/src/experimental/source-resolver.ts'
    worker=ROOT/'scripts/native_pi_probe_worker.mjs'
    cmd=[node,'--import',resolver.as_uri(),str(worker),a.scenario]
    with (output/'stdout.txt').open('w',encoding='utf-8') as stdout,(output/'stderr.txt').open('w',encoding='utf-8') as stderr:
        try:
            r=subprocess.run(cmd,cwd=output,env=env,stdout=stdout,stderr=stderr,timeout=35)
        except subprocess.TimeoutExpired:
            (output/'execution.json').write_text(json.dumps({'exit_code':None,'timed_out':True,'direct_child_reaped':True,'native_accepted':False})+'\n',encoding='utf-8')
            print('Native probe timed out; not accepted');return 124
    check_source(source)
    (output/'execution.json').write_text(json.dumps({'exit_code':r.returncode,'timed_out':False,'direct_child_reaped':True,'source_commit':pin,'worker_sha256':digest(worker),'contract_sha256':digest(ROOT/'scripts/pi_probe_contract.mjs')},indent=2)+'\n',encoding='utf-8')
    proof=output/'receipt.json';print('NATIVE_EXIT',r.returncode)
    if proof.exists():print(proof.read_text(encoding='utf-8'))
    else:print('Native acceptance receipt absent')
    if r.returncode:print((output/'stderr.txt').read_text(encoding='utf-8')[-4500:])
    return r.returncode

if __name__=='__main__':raise SystemExit(main())
