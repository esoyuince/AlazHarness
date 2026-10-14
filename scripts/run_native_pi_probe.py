"""Opt-in pinned Pi native scenarios; no dependency install or real model access."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time

SCENARIOS = ('file-read','missing-file','cancelled-model','timeout-model','budget-stop',
             'retry-cap','truncated-stream','model-switch','event-barrier','permission-denied','concurrent-prompt')


def isolated_environment(work: Path) -> dict[str, str]:
    env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','PATH')}
    for name in ('home','temp','profile'): (work/name).mkdir(parents=True,exist_ok=True)
    env.update(HOME=str(work/'home'),USERPROFILE=str(work/'home'),APPDATA=str(work/'home'),
               LOCALAPPDATA=str(work/'home'),TEMP=str(work/'temp'),TMP=str(work/'temp'),
               XDG_CONFIG_HOME=str(work/'home'),XDG_CACHE_HOME=str(work/'temp'),
               PI_CODING_AGENT_DIR=str(work/'profile'))
    return env


def safe_source_path(root: Path, name: str) -> Path:
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '\\' in name or ':' in name or '..' in p.parts or '.git' in p.parts:
        raise ValueError('Unsafe source manifest path')
    candidate=root/name
    if not candidate.resolve().is_relative_to(root.resolve()):raise ValueError('Escaping source path')
    return candidate


def source_manifest_sha256(manifest: dict) -> str:
    canonical=json.dumps(manifest,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def validate_prepared(prepared: Path, project: Path) -> dict:
    receipt=json.loads((prepared/'install-receipt.json').read_text(encoding='utf-8'))
    lock=json.loads((project/'config/research-sources.lock.json').read_text(encoding='utf-8'))
    pin=next(x['commit'] for x in lock['sources'] if x['name']=='pi')
    if receipt.get('source_commit')!=pin or receipt.get('exit_code')!=0 or receipt.get('scripts_disabled') is not True:
        raise ValueError('Unverified Pi preparation')
    native_lock=json.loads((project/'config/pi-native-probe.lock.json').read_text(encoding='utf-8'))
    raw_manifest=(prepared/'source-files.json').read_bytes()
    if native_lock['source_commit']!=pin or source_manifest_sha256(json.loads(raw_manifest))!=native_lock['source_manifest_sha256']:
        raise ValueError('Untrusted source manifest')
    if receipt.get('files')!=native_lock['source_files'] or receipt.get('lock_sha256')!=native_lock['package_lock_sha256']:
        raise ValueError('Untrusted preparation counts or lock')
    manifest=json.loads(raw_manifest)
    if not manifest or len(manifest)!=receipt.get('files'):raise ValueError('Incomplete source manifest')
    for name,digest in manifest.items():
        path=safe_source_path(prepared/'source',name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Prepared source changed: '+name)
    if manifest.get('package-lock.json')!=receipt.get('lock_sha256'):raise ValueError('Lock mismatch')
    dependency_paths=('source/node_modules/openai/package.json','source/packages/ai/node_modules/openai/package.json')
    dependencies=[json.loads((prepared/name).read_text(encoding='utf-8')) for name in dependency_paths if (prepared/name).is_file()]
    if not dependencies or any(d.get('version')!=native_lock['provider_dependency']['version'] for d in dependencies):
        raise ValueError('Missing or mismatched provider dependency')
    return {'source_commit':pin,'source_files_verified':len(manifest),'lock_sha256':receipt['lock_sha256']}


def validate_result(value: dict, scenario: str, exit_code: int) -> None:
    if exit_code!=0 or value.get('result')!='PASS' or value.get('scenario')!=scenario:
        raise ValueError('Native scenario failed')
    if not value.get('serverClosed') or value.get('openServerSockets')!=0 or not value.get('settled'):
        raise ValueError('Incomplete cleanup or settlement')
    if value.get('modelInferenceCalls')!=0 or value.get('paidCalls')!=0:raise ValueError('Unexpected model execution')


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared-root',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--scenario',choices=('all',*SCENARIOS),default='all')
    args=p.parse_args();project=Path(__file__).resolve().parents[1];prepared=args.prepared_root.resolve()
    validation=validate_prepared(prepared,project)
    output=args.output.absolute()
    if output.exists():raise FileExistsError('Use a fresh output directory')
    if output.resolve().is_relative_to((prepared/'source').resolve()):raise ValueError('Do not write to source tree')
    node=shutil.which('node')
    if not node:raise RuntimeError('Node is required')
    version=subprocess.check_output([node,'--version'],text=True,timeout=10).strip()
    if int(version.lstrip('v').split('.')[0])<24:raise RuntimeError('Native probe requires Node24+')
    output.mkdir(parents=True)
    cases=SCENARIOS if args.scenario=='all' else (args.scenario,)
    rows=[]
    for scenario in cases:
        work=output/scenario;work.mkdir();env=isolated_environment(work)
        command=[node,'--import',(prepared/'source/packages/coding-agent/src/experimental/source-resolver.ts').as_uri(),
                 str(project/'scripts/probes/native-pi-worker.mjs'),scenario,str(work)]
        start=time.monotonic();timed_out=False
        with (work/'stdout.txt').open('w',encoding='utf-8') as stdout,(work/'stderr.txt').open('w',encoding='utf-8') as stderr:
            try:
                proc=subprocess.run(command,cwd=work,env=env,stdout=stdout,stderr=stderr,timeout=30)
                code=proc.returncode
            except subprocess.TimeoutExpired:
                timed_out=True;code=-1
        path=work/'receipt.json'
        value=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        try:validate_result(value,scenario,code);status='PASS'
        except ValueError:status='FAIL'
        row={'scenario':scenario,'result':status,'exit_code':code,'timed_out':timed_out,
             'elapsed_seconds':round(time.monotonic()-start,3),'receipt':value}
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='receipt'}),flush=True)
        if status=='FAIL':print((work/'stderr.txt').read_text(encoding='utf-8')[-2500:])
    validate_prepared(prepared,project)
    summary={'scope':'Pi Agent core + native read + native HTTP provider, scripted model; not full SDK/Durable/M1',
             'result':'PASS' if rows and all(x['result']=='PASS' for x in rows) else 'FAIL',
             'validation':validation,'node':version,'cases':rows,'native_cases':len(rows),
             'worker_sha256':hashlib.sha256((project/'scripts/probes/native-pi-worker.mjs').read_bytes()).hexdigest(),
             'gate_sha256':hashlib.sha256((project/'packages/hybrid-runtime/provider-request-gate.mjs').read_bytes()).hexdigest()}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print('NATIVE_SUMMARY',summary['result'],len(rows))
    return 0 if summary['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
