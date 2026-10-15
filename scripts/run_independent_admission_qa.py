"""Opt-in independent admission regression checks. No installs; fresh local SQLite only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from pi_probe_support import ROOT, check_source, digest, fresh_runtime_path, isolated_env


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',type=Path,required=True)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=args.prepared.resolve()/'source'
    pin=check_source(source)
    compat=json.loads((ROOT/'config/admission-compatibility.lock.json').read_text(encoding='utf-8'))
    if pin!=compat['source_commit'] or digest(source/compat['seam'])!=compat['seam_sha256']:
        raise ValueError('Unverified native admission seam')
    prepared=json.loads((args.prepared/'preparation.json').read_text(encoding='utf-8'))
    if (prepared.get('exit_code')!=0 or prepared.get('source_commit')!=pin or
        digest(source/'package-lock.json')!=prepared.get('package_lock_sha256')):
        raise ValueError('Unqualified prepared dependency environment')
    candidate=ROOT/'packages/admission/strict-admission.mjs'
    candidate_hash=digest(candidate)
    out=fresh_runtime_path(args.source_workspace,args.output);out.mkdir(parents=True)
    records=[]
    for name,worker,report in [('owner','admission-owner.mjs','qa-results.json'),('atomic','admission-atomic.mjs','atomic-results.json')]:
        work=out/name;work.mkdir()
        command=[shutil.which('node') or 'node','--import',(source/'packages/coding-agent/src/experimental/source-resolver.ts').as_uri(),str(ROOT/'scripts/qa'/worker),str(candidate),str(source),str(work)]
        with (work/'stdout.txt').open('w',encoding='utf-8') as stdout,(work/'stderr.txt').open('w',encoding='utf-8') as stderr:
            process=subprocess.run(command,cwd=work,env=isolated_env(work),stdout=stdout,stderr=stderr,timeout=45)
        value=json.loads((work/report).read_text(encoding='utf-8'))
        valid=process.returncode==0 and value.get('failed')==0 and value.get('passed')==6 and value.get('unchanged_during_run') is True and value.get('module_sha256')==candidate_hash
        records.append({'family':name,'exit_code':process.returncode,'result':'PASS' if valid else 'FAIL','details':value})
        print(name,records[-1]['result'],flush=True)
    summary={'scope':'independent real Pi SQLite passive admission; no model inference; graceful reopen and injected storage errors, not process-kill/powerloss qualification',
             'source_commit':pin,'candidate_sha256':candidate_hash,'candidate_unchanged':digest(candidate)==candidate_hash,
             'families':records,'result':'PASS' if all(x['result']=='PASS' for x in records) and digest(candidate)==candidate_hash else 'FAIL'}
    (out/'independent-qa.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='families'},indent=2))
    return 0 if summary['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
