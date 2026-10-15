"""Apply the real local recovery inspector to ten retained, already-closed native profiles.

No Gateway/model is started. This is read-only retrospective corroboration, not
new recovery executions. Private fixture credentials are read locally and never
included in stdout or the sanitized report.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def load(path: Path):
    if path.stat().st_size>8_388_608:raise ValueError('Oversized retained record')
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();workspace=a.source_workspace.resolve();runtime=workspace/'runtime';out=a.output.resolve()
    if not out.is_relative_to(runtime) or out==runtime or out.exists():raise ValueError('Fresh output under project runtime required')
    out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('qa_recovery_native_records',ROOT/'packages/claw-hermes/recovery_inspector.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    source=workspace/'vendor/hermes-agent';pin=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if pin!=module.PIN:raise ValueError('Unexpected source pin')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():raise ValueError('Vendor modified')
    programs={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['packages/claw-hermes/recovery_inspector.py','packages/upstream/hermes/hermes_state_keys.py','packages/upstream/hermes/terminal_status.py','scripts/qa/reconciliation_native_records.py']}
    cases=[];errors=[]
    for scenario in ('completed','before-model','after-tool','before-reserve','after-reserve'):
        for repetition in (1,2):
            name=f'accepted-{scenario}-{repetition}';case=runtime/'hyb004-208f'/name
            r=load(case/'recovery.json');private=load(case/'client-000-input.json')
            if r['result']!='PASS' or r['errors']:raise ValueError('Retained case was not accepted')
            for stage in ('first','second'):
                exit_record=load(case/stage/'exit-observation.json')
                if exit_record!=r[stage+'_exit'] or not exit_record['native_reaped'] or not exit_record['launcher_reaped']:raise ValueError('Retained native lifetime unconfirmed')
            ready=r['second_ready'];home=case/'profile'
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in home.glob('*.db*') if p.is_file()}
            observed=r['new_final']['value']['run'] if scenario=='before-reserve' else r['recovered_status']['value']
            context=module.LocalRecoveryContext(home,private['token'],ready['epoch'],ready['instance_id'])
            inspector=module.LocalRecoveryInspector(context)
            classification=inspector.inspect(body={'input':private['input']},idempotency_key=private['key'],observed=observed)
            expected='reservation_without_admission_observed' if scenario=='after-reserve' else 'execution_unknown' if scenario in ('before-model','after-tool') else 'canonical_terminal_verified'
            after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in home.glob('*.db*') if p.is_file()}
            ok=classification['classification']==expected and before==after and classification['retryAllowed'] is False and classification['repairAllowed'] is False and classification['writesPerformed'] is False
            if expected!='canonical_terminal_verified':ok=ok and classification['requiresOperator'] is True and classification.get('taskSucceeded',False) is False
            else:ok=ok and classification['canonicalVerified'] is True and classification['taskSucceeded'] is True
            cases.append({'case':name,'scenario':scenario,'expected':expected,'classification':classification,'native_profile_unchanged':before==after,'database_hashes':before,'retained_receipt_sha256':hashlib.sha256((case/'recovery.json').read_bytes()).hexdigest(),'result':'PASS' if ok else 'FAIL'})
            if not ok:errors.append(name)
    drift=[name for name,h in programs.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h]
    if drift:errors.append('program_drift')
    result={'scope':'independent readonly inspector applied to existing TEN closed native profiles; NOT ten new Gateway executions','source_commit':pin,'cases':cases,'passed':sum(c['result']=='PASS' for c in cases),'failed':sum(c['result']!='PASS' for c in cases),'errors':errors,'programs_sha256':programs,'drift':drift,'model_calls':0,'new_gateway_processes':0,'result':'FAIL' if errors else 'PASS','automatic_repair_accepted':False}
    (out/'native-record-recheck.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scope':result['scope'],'passed':result['passed'],'failed':result['failed'],'errors':errors,'classifications':[{'case':c['case'],'class':c['classification']['classification'],'reason':c['classification'].get('reason'),'unchanged':c['native_profile_unchanged']} for c in cases]},indent=2))
    return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())
