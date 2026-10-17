"""Read R1 reports from recorded HYB005B native fixture profiles.

No new Gateway/tool/model runs; explicit single-fixture input is also supported. The past execution code may differ from
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


def _unlinked(path):
    return not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
                   for p in (path,*path.parents))


def validate_paths(workspace,out,fixture=None):
    """Operator-selected fixture only; never follow a path embedded in a receipt."""
    require(_unlinked(workspace) and _unlinked(out),'linked_verification_path')
    workspace=workspace.resolve();out=out.resolve()
    source=workspace/'runtime/hyb005b-close-3156'
    require(out.is_relative_to(workspace/'runtime') and out!=workspace/'runtime'
            and not out.is_relative_to(source) and not out.exists(),
            'fresh_distinct_runtime_output_required')
    if fixture is not None:
        require(fixture.is_absolute() and _unlinked(fixture),'linked_fixture_path')
        fixture=fixture.resolve()
        require(fixture.is_dir() and fixture.is_relative_to(workspace/'runtime')
                and fixture!=workspace/'runtime' and not out.is_relative_to(fixture)
                and not fixture.is_relative_to(out),'separate_runtime_fixture_required')
    return workspace,out,fixture


def validate_execution_receipt(record,scenario):
    """Qualification of a recorded fixture, NOT authentication of its producer."""
    require(scenario in CASES and type(record)is dict and
            record.get('source_commit')==PIN and record.get('scenario')==scenario,
            'wrong_retained_fixture')
    require(record.get('result')=='PASS' and all(record.get(k)==[] for k in
            ('errors','fixture_errors','code_drift')),'historical_run_not_qualified')
    require(all(type(record.get(k))is int and record[k]==0 for k in
            ('paid_calls','inference_calls','client_exit')),'unsupported_fixture_execution')
    exits=['exit','restart_exit'] if scenario=='normal' else ['exit']
    for name in exits:
        end=record.get(name)
        require(type(end)is dict and type(end.get('exit_code'))is int and
                end['exit_code']==0 and end.get('native_reaped')is True and
                end.get('launcher_reaped')is True and end.get('forced')is False and
                end.get('kill_requested')is False,'fixture_lifecycle_not_closed')
    if scenario=='normal':
        require(record.get('restart_no_refund')is True,'fixture_restart_not_qualified')
    require(type(record.get('client'))is dict,'fixture_client_missing')
    return record


def read_execution_receipt(path,scenario,expected_sha256=None):
    require(path.is_file() and _unlinked(path) and path.stat().st_size<=2097152,
            'invalid_evidence_file')
    if expected_sha256 is not None:
        require(type(expected_sha256)is str and len(expected_sha256)==64 and
                all(c in '0123456789abcdef' for c in expected_sha256),'invalid_receipt_digest')
    with path.open('rb') as stream:raw=stream.read(2097153)
    require(len(raw)<=2097152,'invalid_evidence_file')
    sha=hashlib.sha256(raw).hexdigest()
    require(expected_sha256 is None or sha==expected_sha256,'fixture_receipt_digest_mismatch')
    record=validate_execution_receipt(_load(raw.decode('utf-8')),scenario)
    return record,sha


def check_case(workspace,out,scenario,expect_expired=False,*,fixture=None,receipt_sha256=None):
    case=fixture if fixture is not None else workspace/'runtime/hyb005b-close-3156'/('final-'+scenario)
    home=case/'profile';receipt=case/'execution-result.json'
    record,read_sha=read_execution_receipt(receipt,scenario,receipt_sha256)
    paths=[home/'state.db',home/'runs_idempotency.db',home/'config.yaml',receipt]
    require(all(p.is_file() and _unlinked(p) for p in paths),'invalid_fixture_storage')
    before={p.name:digest(p) for p in paths}
    require(before[receipt.name]==read_sha,'fixture_receipt_changed')
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
    cli_text=subprocess.run(cmd+['--format','text'],capture_output=True,text=True,encoding='utf-8',timeout=15)
    require(cli_text.returncode==0 and not cli_text.stderr and cli_text.stdout==text,'text_cli_mismatch')
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
            'reportSha256':digest(own/'report.json'),'cliExit':cli.returncode,'textCliExit':cli_text.returncode,
            'newGatewayRuns':0,'newModelCalls':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expect-expired',action='store_true',help='Require retention refusal instead of a positive current snapshot; never changes clocks/stores')
    parser.add_argument('--fixture',type=Path,help='One explicit native execution fixture under source-workspace/runtime; no execution is started')
    parser.add_argument('--scenario',choices=CASES,help='Required with --fixture')
    parser.add_argument('--receipt-sha256',help='Required with --fixture; pins the existing execution-result.json bytes, not producer authenticity')
    args=parser.parse_args()
    require((args.fixture is not None)==(args.scenario is not None)==(args.receipt_sha256 is not None),
            'explicit_fixture_identity_required')
    workspace,out,fixture=validate_paths(args.source_workspace,args.output,args.fixture)
    out.mkdir(parents=True)
    programs=['packages/claw-hermes/evidence_view.py','packages/claw-hermes/host_report.py',
              'packages/claw-hermes/recovery_inspector.py','scripts/inspect_host_report.py',
              'scripts/verify_evidence_view_retained.py']
    before={n:digest(ROOT/n) for n in programs};rows=[];errors=[]
    cases=(args.scenario,) if fixture is not None else CASES
    for case in cases:
        try:rows.append(check_case(workspace,out,case,args.expect_expired,fixture=fixture,receipt_sha256=args.receipt_sha256))
        except Exception as exc:errors.append({'scenario':case,'errorType':type(exc).__name__})
    changed=[n for n,h in before.items() if digest(ROOT/n)!=h]
    result={'scope':'read-only R1 reports/CLI against recorded native fixtures; this verifier executes no Gateway or model',
            'expectedCases':len(cases),
            'expectation':'retention_refusal' if args.expect_expired else 'current_retained_evidence',
            'checks':rows,'errors':errors,'sourceSha256':before,'changed':changed,
            'newGatewayRuns':0,'newModelCalls':0,'paidCalls':0,
            'result':'PASS' if len(rows)==len(cases) and not errors and not changed else 'FAIL'}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
