"""Read R1 reports from five retained HYB005B native fixture profiles.

NOT five new Gateway/tool/model runs. The past execution code may differ from
current report code: it is retained state, never attributed to current execution.
Writes only new reports/private CLI input under an explicitly fresh runtime dir.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,PIN,_load,_json,RESULT
from execution_budget import ExecutionPolicy
from host_report import HostReportInspector
from evidence_view import EvidenceViewInspector,EvidenceSelection,render_evidence_text
CASES=('normal','provider-limit','tool-limit','denied-write','summary')


def require(value,reason):
    if not value:raise ValueError(reason)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def object_file(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=2097152,'invalid_evidence_file')
    obj=_load(path.read_text(encoding='utf-8'));require(type(obj)is dict,'invalid_evidence_shape');return obj


def check_case(workspace,out,scenario,expect_expired=False):
    case=workspace/'runtime/hyb005b-close-3156'/('final-'+scenario)
    home=case/'profile';receipt=case/'execution-result.json'
    record=object_file(receipt)
    require(record['source_commit']==PIN and record['scenario']==scenario,'wrong_retained_fixture')
    require(record['errors']==[] and record['fixture_errors']==[] and record['code_drift']==[],'historical_run_not_qualified')
    paths=[home/'state.db',home/'runs_idempotency.db',home/'config.yaml',receipt]
    before={p.name:digest(p) for p in paths}
    cfg=object_file(home/'config.yaml')
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        epoch,instance=db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
    token=cfg['platforms']['api_server']['key'];context=LocalRecoveryContext(home,token,epoch,instance)
    ep=cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']
    policy=ExecutionPolicy(**ep['policy']);client=record['client'];run=client['runId']
    with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        keys=db.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',
                        (context.scope,run)).fetchall()
    require(len(keys)==1,'ambiguous_retained_request')
    request={'body':{'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'},
             'idempotency_key':keys[0][0],'observed':client['final']['run']}
    legacy=HostReportInspector(context,policy).inspect(**request)
    inspector=EvidenceViewInspector(context,policy);report=inspector.inspect(**request)
    if expect_expired:
        # An explicit negative qualification. Never revive expired originals,
        # rewrite timestamps, replace the current clock, or call this a fresh run.
        require(report['reportStatus']=='unverified' and report.get('reason')=='retention_expired',
                'expected_expiration_not_observed')
        require(report['evidenceView']['available'] is False and report['evidenceView']['references']==[],
                'expired_content_was_exposed')
        require(all(report[k] is False for k in ('writesPerformed','executionAllowed','retryAllowed','repairAllowed')),
                'expired_report_granted_authority')
        own=out/scenario;own.mkdir();private=own/'private';private.mkdir()
        c=asdict(context);c['profile_home']=str(c['profile_home']);c.pop('profile_name')
        for name,obj in [('context',c),('policy',asdict(policy)),('request',request)]:
            (private/(name+'.json')).write_text(json.dumps(obj),encoding='utf-8')
        cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(private/'context.json'),
             '--policy',str(private/'policy.json'),'--request',str(private/'request.json'),'--include-evidence']
        cli=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=15)
        require(cli.returncode==2 and not cli.stderr and json.loads(cli.stdout)==report,'expired_cli_mismatch')
        require(before=={p.name:digest(p) for p in paths},'expired_store_changed')
        (own/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        return {'scenario':scenario,'result':'PASS_EXPECTED_RETENTION_REFUSAL','cliExit':cli.returncode,
                'evidenceReferences':0,'modelVisibility':'unknown','sourceDatabaseAndReceiptUnchanged':True,
                'historicalReceiptSha256':before[receipt.name],'newGatewayRuns':0,'newModelCalls':0}

    require(report['reportStatus']=='verified_snapshot','report_snapshot_not_verified')
    section=report['evidenceView'];without=dict(report);without.pop('evidenceView')
    require(without==legacy,'legacy_report_changed')
    require(section['available'] and section['modelVisibility']=='unknown','unproven_visibility')
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        saved=_load(db.execute('SELECT value FROM state_meta WHERE key=?',
                                           (RESULT+request['observed']['admission_id'],)).fetchone()[0])
    require(section['recordDigest']==hashlib.sha256(_json(saved).encode()).hexdigest(),'record_digest_mismatch')
    tools=[m for m in saved['result']['messages'] if m['role']=='tool']
    refs=[r for r in section['references'] if r['kind']=='retained_tool_result']
    require(len(tools)==len(refs),'tool_record_count_mismatch')
    for message,ref in zip(tools,refs):
        raw=message['content'].encode('utf-8')
        require(ref['content']['sha256']==hashlib.sha256(raw).hexdigest() and ref['content']['utf8Bytes']==len(raw),'stored_content_mismatch')
        require(ref['originalSource']['sha256'] is None and ref['originalSource']['coverage']=='unknown','invented_source_file_proof')
        require(ref['executionAttribution']=='not_proven' and ref['modelView']['ranges'] is None,'invented_execution_or_wire_proof')
    require(refs and refs[0]['content']['utf8Bytes']>1,'expected_tool_fixture_absent')
    ref=refs[0];selection=EvidenceSelection(ref['evidenceId'],ref['content']['sha256'],0,1)
    projected=inspector.inspect(**request,selection=selection)
    require(projected['evidenceView']['localView']['coverageOfStoredContent']=='partial','partial_view_relabelled')
    own=out/scenario;own.mkdir();private=own/'private';private.mkdir()
    c=asdict(context);c['profile_home']=str(c['profile_home']);c.pop('profile_name')
    for name,obj in [('context',c),('policy',asdict(policy)),('request',request),('selection',asdict(selection))]:
        (private/(name+'.json')).write_text(json.dumps(obj),encoding='utf-8')
    cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(private/'context.json'),
         '--policy',str(private/'policy.json'),'--request',str(private/'request.json'),'--include-evidence',
         '--evidence-selection',str(private/'selection.json')]
    cli=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=15)
    require(cli.returncode==0 and not cli.stderr and json.loads(cli.stdout)==projected,'cli_mismatch')
    text=render_evidence_text(projected)
    secrets=[token,str(home),request['idempotency_key'],request['body']['input'],ep['provider_bearer'],request['observed'].get('output','')]
    require(not any(s and s in cli.stdout+text for s in secrets),'private_value_in_report')
    require(all(projected[k] is False for k in ('writesPerformed','executionAllowed','retryAllowed','repairAllowed')),'report_granted_authority')
    require(before=={p.name:digest(p) for p in paths},'retained_evidence_changed')
    (own/'report.json').write_text(json.dumps(projected,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (own/'report.txt').write_text(text,encoding='utf-8')
    return {'scenario':scenario,'result':'PASS','nativeStatus':report['task']['nativeStatus'],
            'recordedToolTexts':len(refs),'toolTextBytes':[ref['content']['utf8Bytes'] for ref in refs],
            'localViewBytes':1,'localViewCoverage':'partial','modelVisibility':'unknown',
            'sourceDatabaseAndReceiptUnchanged':True,'historicalReceiptSha256':before[receipt.name],
            'reportSha256':digest(own/'report.json'),'cliExit':cli.returncode,
            'newGatewayRuns':0,'newModelCalls':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expect-expired',action='store_true',help='Require retention refusal instead of a positive current snapshot; never changes clocks/stores')
    args=parser.parse_args();workspace=args.source_workspace.resolve();out=args.output.resolve()
    source=workspace/'runtime/hyb005b-close-3156'
    require(out.is_relative_to(workspace/'runtime') and not out.is_relative_to(source)
            and not out.exists(),'fresh_distinct_runtime_output_required')
    out.mkdir(parents=True)
    programs=['packages/claw-hermes/evidence_view.py','packages/claw-hermes/host_report.py',
              'packages/claw-hermes/recovery_inspector.py','scripts/inspect_host_report.py',
              'scripts/verify_evidence_view_retained.py']
    before={n:digest(ROOT/n) for n in programs};rows=[];errors=[]
    for case in CASES:
        try:rows.append(check_case(workspace,out,case,args.expect_expired))
        except Exception as exc:errors.append({'scenario':case,'errorType':type(exc).__name__})
    changed=[n for n,h in before.items() if digest(ROOT/n)!=h]
    result={'scope':'new read-only R1 reports/CLI against five past native fixture stores; NO new native execution',
            'expectation':'retention_refusal' if args.expect_expired else 'current_retained_evidence',
            'checks':rows,'errors':errors,'sourceSha256':before,'changed':changed,
            'newGatewayRuns':0,'newModelCalls':0,'paidCalls':0,
            'result':'PASS' if len(rows)==5 and not errors and not changed else 'FAIL'}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
