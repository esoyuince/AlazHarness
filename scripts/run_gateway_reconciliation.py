"""New native kill/reopen scenario, followed by read-only host reconciliation.

Reuses HYB-004's owned-process machinery, not another Gateway implementation.
"""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
from run_native_hermes_probe import pinned_source
from run_gateway_recovery import run as run_native_recovery
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,LocalRecoveryInspector

EXPECTED={'completed':'canonical_terminal_verified','before-model':'execution_unknown',
          'after-tool':'execution_unknown','after-reserve':'reservation_without_admission_observed'}


def inspect_native_output(out: Path, record: dict) -> dict:
    private=json.loads((out/'client-000-input.json').read_text(encoding='utf-8'))
    ready=record['second_ready'];body={'input':private['input']}
    context=LocalRecoveryContext(out/'profile',private['token'],ready['epoch'],ready['instance_id'])
    observed=record['recovered_status']['value']
    args={'body':body,'idempotency_key':private['key'],'observed':observed}
    files=sorted((out/'profile').glob('*.db'));before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    result=LocalRecoveryInspector(context).inspect(**args)
    wrong_token=LocalRecoveryInspector(dataclasses.replace(context,api_token='invalid-test-credential')).inspect(**args)
    stale=LocalRecoveryInspector(dataclasses.replace(context,epoch=context.epoch-1)).inspect(**args)
    conflict=LocalRecoveryInspector(context).inspect(**(args|{'body':{'input':body['input']+' different'}}))
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert before==after,'Inspector changed retained native stores'
    assert result['classification']==EXPECTED[record['scenario']],result
    assert result['retryAllowed'] is False and result['repairAllowed'] is False
    assert wrong_token['classification']=='unverified' and wrong_token['reason']=='lookup_unavailable'
    assert stale['reason']=='stale_epoch' and conflict['reason']=='request_payload_conflict'
    projected=record['resumed']['value']
    assert projected['recoveryContractVersion']==1 and projected['canonicalVerified'] is False
    if record['scenario']=='after-reserve':
        assert projected['classification']=='terminal_unverified' and projected['requiresOperator'] is True
        assert projected['backendConfirmed'] is False and projected['transportConfirmed'] is True
    return {'classification':result,'http_projection':{k:projected[k] for k in ('recoveryContractVersion','classification','requiresOperator','backendConfirmed','transportConfirmed','canonicalVerified','retryAllowed')},
      'negative_reasons':[wrong_token['reason'],stale['reason'],conflict['reason']],
      'database_bytes_unchanged':True,'additional_model_requests':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',required=True,type=Path);parser.add_argument('--python',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--scenario',required=True,choices=tuple(EXPECTED))
    a=parser.parse_args();source=pinned_source(ROOT,a.source_workspace);out=a.output.resolve()
    runtime=(a.source_workspace.resolve()/'runtime').resolve()
    if out.exists() or out==runtime or not out.is_relative_to(runtime):raise ValueError('Fresh project runtime required')
    if not a.python.is_file() or not a.python.resolve().is_relative_to(runtime):raise ValueError('Existing project interpreter required')
    files=[ROOT/'packages/claw-hermes'/p for p in ('hermes-runs.mjs','run-recovery.mjs','recovery_inspector.py')]
    files.extend([Path(__file__),ROOT/'scripts/inspect_gateway_recovery.py'])
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    native=run_native_recovery(source,a.python,out,a.scenario)
    report={'scope':'native recovery plus new host projection and readonly inspector; no repair or M1 acceptance',
            'scenario':a.scenario,'errors':[],'native_result':native['result'],
            'new_native_incarnations':2,'new_owned_kills':1,'model_inference_calls':0,'paid_calls':0,'files_sha256':hashes}
    try:
        assert native['result']=='PASS' and native['errors']==[],native['errors']
        report['inspection']=inspect_native_output(out,native)
        report['model_http_calls']=len(native['model_calls'])
        report['first_exit']=native['first_exit'];report['second_exit']=native['second_exit']
        report['native_receipt_sha256']=hashlib.sha256((out/'recovery.json').read_bytes()).hexdigest()
        assert all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[p.relative_to(ROOT).as_posix()] for p in files),'Program changed during execution'
        pinned_source(ROOT,a.source_workspace)
    except Exception as exc:report['errors'].append(type(exc).__name__+': '+str(exc))
    report['result']='FAIL' if report['errors'] else 'PASS'
    (out/'reconciliation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return int(bool(report['errors']))

if __name__=='__main__':raise SystemExit(main())
