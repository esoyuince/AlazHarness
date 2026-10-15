"""Run selected OpenCode source components with fixture services. No model/API/server."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import secrets
import shutil
import subprocess
import time
from pi_probe_support import isolated_env, fresh_runtime_path
from opencode_probe_support import ROOT, verify_prepared, digest
from prepare_opencode_components import source_for

EXPECTED_CASES = ('rules-default-ask', 'rules-last-match', 'rules-action-and-resource', 'wildcard-platform-path', 'wildcard-not-path-sandbox', 'permission-allow-deny-no-pending', 'permission-session-rule-precedence', 'permission-deny-before-saved-and-hook', 'permission-any-resource-denied', 'permission-partial-resources-ask', 'permission-empty-resource-characterization', 'permission-missing-agent-denies', 'permission-missing-session', 'permission-explicit-agent', 'permission-hook-can-resolve-ask', 'permission-once-consumed', 'permission-reject-session-batch', 'permission-feedback-typed', 'permission-always-project-wide', 'permission-always-preserves-new-deny', 'permission-foreign-session-guard', 'permission-aborted-wait-cleans-pending', 'permission-close-fails-closed', 'permission-publish-failure-cleans-pending', 'permission-duplicate-pending-id', 'event-frame-json', 'event-encode-once-many-subscribers', 'event-internal-filter-before-capacity', 'event-fifo', 'event-only-lagging-subscriber-fails', 'event-encoding-error-and-new-subscriber', 'event-no-replay-after-reconnect', 'event-no-encode-without-subscribers', 'event-rpc-public-type', 'event-owner-scope-unsubscribes')


def validate_receipt(value: dict, nonce: str, pid: int, exit_code: int) -> list[str]:
    if not isinstance(value,dict):return ['missing receipt']
    errors=[]
    if exit_code!=0:errors.append('nonzero exit')
    if type(pid) is not int or pid<=0 or type(value.get('pid')) is not int or value.get('pid')!=pid or value.get('nonce')!=nonce:errors.append('wrong child identity')
    rows=value.get('cases')
    if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):return errors+['invalid case list']
    if tuple(r.get('name') for r in rows)!=EXPECTED_CASES:errors.append('missing duplicate reordered or unknown case')
    if any(r.get('result')!='PASS' for r in rows):errors.append('failed component case')
    if any(type(r.get('elapsed_ms')) is not int or r['elapsed_ms']<0 for r in rows):errors.append('invalid case duration')
    for key,wanted in [('total',len(EXPECTED_CASES)),('passed',len(EXPECTED_CASES)),('failed',0),('model_inference_calls',0),('paid_calls',0)]:
        if type(value.get(key)) is not int or value[key]!=wanted:errors.append('invalid '+key)
    for key in ('full_server_tested','http_routing_tested','persistent_database_tested','os_sandbox_claimed'):
        if value.get(key) is not False:errors.append('unsupported claim '+key)
    if value.get('platform') not in ('win32','linux','darwin'):errors.append('unknown platform')
    return errors


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--prepared',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--repeats',type=int,choices=(1,2),default=2)
    a=p.parse_args();source=source_for(a.source_workspace);prepared=a.prepared.resolve()
    if not prepared.is_relative_to((a.source_workspace.resolve()/'runtime').resolve()):raise ValueError('Prepared environment must be local runtime')
    projection=verify_prepared(source,prepared)
    out=fresh_runtime_path(a.source_workspace,a.output);out.mkdir(parents=True)
    runs=[];node=shutil.which('node')
    if not node:raise ValueError('Node must already exist')
    for repeat in range(1,a.repeats+1):
        work=out/str(repeat);work.mkdir();nonce=secrets.token_hex(16);timed_out=False;started=time.monotonic()
        command=[node,'--experimental-transform-types',str(prepared/'projected/worker.mjs'),str(work),nonce]
        with (work/'stdout.txt').open('w',encoding='utf-8') as stdout,(work/'stderr.txt').open('w',encoding='utf-8') as stderr:
            child=subprocess.Popen(command,cwd=work,env=isolated_env(work),stdout=stdout,stderr=stderr)
            try:child.wait(timeout=70)
            except subprocess.TimeoutExpired:timed_out=True
            finally:
                if child.poll() is None:child.kill()
                child.wait(timeout=5)
        receipt=work/'receipt.json';value=None
        if receipt.is_file() and receipt.stat().st_size<=131072:
            try:value=json.loads(receipt.read_text(encoding='utf-8'))
            except ValueError:pass
        errors=validate_receipt(value,nonce,child.pid,child.returncode)
        if timed_out:errors.append('timed out')
        runs.append({'repeat':repeat,'pid':child.pid,'exit_code':child.returncode,'timed_out':timed_out,'reaped':child.poll() is not None,'elapsed_seconds':round(time.monotonic()-started,3),'result':'FAIL' if errors else 'PASS','errors':errors,'receipt':value})
        print('REPEAT',repeat,runs[-1]['result'],errors,flush=True)
    drift=False
    try:verify_prepared(source,prepared)
    except Exception:drift=True
    summary={'scope':'selected OpenCode source-owned Permission/EventFeed components with explicit external dependency fixtures',
             'source_commit':projection['source_commit'],'scenario_count':len(EXPECTED_CASES),'repeats':a.repeats,
             'passed':sum(len(EXPECTED_CASES) for r in runs if r['result']=='PASS'),
             'all_repeats_passed':all(r['result']=='PASS' for r in runs) and not drift,'source_drift':drift,
             'model_inference_calls':0,'paid_calls':0,'full_opencode_acceptance':False,'product_adoption':False,
             'files_sha256':{name:digest(ROOT/'scripts'/name) for name in ['opencode_component_worker.mjs','opencode_services.mjs','opencode_probe_support.py','run_opencode_components.py']},
             'projection_sha256':digest(prepared/'projection.json'),'runs':runs}
    (out/'suite.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='runs'},indent=2))
    return 0 if summary['all_repeats_passed'] else 1

if __name__=='__main__':raise SystemExit(main())
