"""Read-only operator corroboration of a CLOSED opt-in scripted broker experiment.

Origin-side request bytes are measured independently by the fixture. This script
never starts/replays a Gateway/model/tool and never writes the source databases.
"""
from contextlib import closing
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext, PIN, _json, _load
from execution_budget import ExecutionPolicy
from evidence_view import EvidenceViewInspector, render_evidence_text
from request_view import PREFIX


def require(ok,reason):
    if not ok:raise ValueError(reason)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=2_097_152,'invalid_fixture_file')
    return _load(path.read_text(encoding='utf-8'))


def verify(fixture,out,receipt_sha):
    require(fixture.is_absolute() and out.is_absolute() and not out.exists()
            and not out.is_relative_to(fixture) and not fixture.is_relative_to(out),'fresh_separate_output_required')
    require(not any(p.is_symlink() for p in (fixture,*fixture.parents,out,*out.parents)),'linked_fixture_path')
    rp=fixture/'broker-native-result.json';require(digest(rp)==receipt_sha,'native_receipt_changed')
    rec=read(rp)
    require(rec['result']=='PASS' and rec['source_commit']==PIN and not rec['errors'] and not rec['source_drift']
            and rec['gateway_exit']==rec['broker_exit']==0 and rec['inference_calls']==rec['paid_calls']==0,
            'native_experiment_not_qualified')
    home=fixture/'profile';paths=[home/'state.db',home/'runs_idempotency.db',home/'config.yaml',rp,fixture/'input.txt']
    before={str(p):digest(p) for p in paths};aux_before={p.name:digest(p) for p in home.glob('*') if p.is_file()}
    cfg=read(home/'config.yaml');settings=cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        epoch,instance=db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        rows=[_load(v) for (v,) in db.execute('SELECT value FROM state_meta WHERE key GLOB ?',(PREFIX+'*',))]
    context=LocalRecoveryContext(home,cfg['platforms']['api_server']['key'],epoch,instance)
    policy=ExecutionPolicy(**settings['policy']);observed=rec['client']['final']['run'];rid=observed['run_id']
    with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON');keys=db.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',
                                                       (context.scope,rid)).fetchall()
    require(len(keys)==1,'fixture_key_ambiguous')
    request={'body':{'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'},
             'idempotency_key':keys[0][0],'observed':observed}
    report=EvidenceViewInspector(context,policy).inspect(**request)
    require(report['reportStatus']=='verified_snapshot','request_report_unverified')
    section=report['evidenceView'];require(section['modelVisibility']=='unknown','model_processing_invented')
    enabled=settings.get('record_request_view',False)
    require(type(enabled) is bool and enabled==rec['record_request_view'],'request_setting_mismatch')
    origin=rec['origin_request_views'];require(len(origin)==rec['origin_accepted'],'origin_request_count_mismatch')
    require(len({x['requestSha256'] for x in origin})==len(origin),'fixture_duplicate_payload_not_qualified')
    origin_by={x['requestSha256']:x for x in origin}
    counts=[]
    if enabled:
        views=section['providerRequestViews'];require(views['inventoryScope']=='profile_provider_requests','request_scope_mislabelled')
        require(len(rows)==len(views['requests'])==len(origin),'request_manifest_count_mismatch')
        by={x['requestDigest']:x for x in rows}
        require(set(by)==set(origin_by),'request_digest_not_actual_wire_bytes')
        for view in views['requests']:
            row=by[view['requestDigest']];actual=origin_by[view['requestDigest']]
            require(row['requestBytes']==view['requestBytes']==actual['requestBytes'],'actual_request_size_mismatch')
            require(row['messageCount']==view['messageCount']==actual['messageCount'],'actual_message_count_mismatch')
            require([{k:v for k,v in x.items() if k!='sourceCaptureDigest'} for x in row['toolMessages']]==actual['toolMessages'],
                    'actual_tool_text_not_request_metadata')
            require(view['initiatingRunId'] is None and not view['initiatingRunVerified'] and not view['modelProcessingVerified'],
                    'inferred_run_or_model_processing')
            is_lost=(rec['scenario']=='upstream-disconnect' or
                     (rec['scenario']=='after-tool-disconnect' and bool(actual['toolMessages'])))
            require(view['state']==('handoff_armed' if is_lost else 'broker_response_observed'),'request_phase_mismatch')
            require(view['brokerHttpResponseObserved'] is (not is_lost),'response_observation_invented')
            require(view['providerResponseValidated'] is (not is_lost),'response_validation_invented')
            for inc in view['selectedEvidenceInclusions']:
                require(inc['coverageOfReturnedText']=='complete' and inc['sourceFileCoverage']=='not_inferred',
                        'source_coverage_conflated')
                require(inc['preparationRecorded'] and inc['handoffIntentRecorded'],'preparation_or_handoff_missing')
                require(inc['brokerHttpResponseObserved'] is (not is_lost) and not inc['understandingVerified']
                        and not inc['modelProcessingVerified'] and not inc['grantsExecutionPermission'],'inclusion_claim_overreach')
                ref=next(r for r in section['references'] if r['evidenceId']==inc['evidenceId'])
                require(inc['contentSha256']==ref['content']['sha256'] and inc['range']['end']==ref['content']['utf8Bytes'],
                        'returned_text_mismatch')
            counts.append({'requestDigest':view['requestDigest'],'requestBytes':view['requestBytes'],
                           'state':view['state'],'toolMessages':view['toolMessageCount'],
                           'selectedInclusions':len(view['selectedEvidenceInclusions'])})
        expected_inclusions=1 if rec['scenario'] in ('normal','after-tool-disconnect') and rec['record_source'] else 0
        require(sum(x['selectedInclusions'] for x in counts)==expected_inclusions,'source_inclusion_count_mismatch')
        if rec['scenario']=='provider-limit':
            require(len(section.get('sourceCaptures',[]))==1 and not any(x['selectedInclusions'] for x in counts),
                    'blocked_second_request_fabricated')
    else:
        require(not rows and 'providerRequestViews' not in section,'disabled_view_fabricated')
    partial=rec.get('read_limit') is not None and rec['fixture_lines']>rec['read_limit']
    if partial:
        with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
            db.execute('PRAGMA query_only=ON');outputs=[_load(v) for (v,) in db.execute("SELECT content FROM messages WHERE role='tool'")]
        require(len(outputs)==1 and outputs[0]['total_lines']==rec['fixture_lines'],'partial_fixture_missing')
        text=outputs[0]['content'];limit=rec['read_limit']
        require('line '+str(limit)+' ışık' in text and 'line '+str(limit+1)+' ışık' not in text
                and 'line '+str(rec['fixture_lines'])+' ışık' not in text,'actual_partial_source_not_preserved')
    out.mkdir(parents=True,mode=0o700);private=out/'private';private.mkdir(mode=0o700)
    conf=asdict(context);conf['profile_home']=str(home);conf.pop('profile_name')
    for name,value in [('context',conf),('policy',asdict(policy)),('request',request)]:
        (private/(name+'.json')).write_text(_json(value),encoding='utf-8')
    cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(private/'context.json'),
         '--policy',str(private/'policy.json'),'--request',str(private/'request.json'),'--include-evidence']
    for fmt in ('json','text'):
        result=subprocess.run(cmd+['--format',fmt],capture_output=True,text=True,encoding='utf-8',timeout=20)
        require(result.returncode==0 and not result.stderr,'request_cli_failed')
        require(json.loads(result.stdout)==report if fmt=='json' else result.stdout==render_evidence_text(report),'request_cli_mismatch')
        require(not any(s and s in result.stdout for s in (context.api_token,settings['provider_bearer'],
                settings['provider_broker']['signing_key'],str(home),str(fixture/'input.txt'),request['idempotency_key'])),
                'private_data_in_request_report')
        (out/('report.json' if fmt=='json' else 'report.txt')).write_text(result.stdout,encoding='utf-8')
    require(before=={str(p):digest(p) for p in paths},'main_state_changed_during_read')
    aux_after={p.name:digest(p) for p in home.glob('*') if p.is_file()}
    summary={'result':'PASS','scenario':rec['scenario'],'requestViewEnabled':enabled,'nativeReceiptSha256':receipt_sha,
             'originRequests':len(origin),'manifestRows':len(rows),'requests':counts,'actualPartialRead':partial,
             'sourceBytes':(fixture/'input.txt').stat().st_size,
             'toolOutputBytes':[r['content']['utf8Bytes'] for r in section['references'] if r['kind']=='retained_tool_result'],
             'nativeStatus':observed['status'],'modelVisibility':'unknown','initiatingRunVerified':False,
             'mainStoresUnchanged':True,'auxiliaryFilesChanged':[k for k in set(aux_before)|set(aux_after) if aux_before.get(k)!=aux_after.get(k)],
             'newNativeRuns':0,'inferenceCalls':0,'paidCalls':0,'cliFormats':['json','text']}
    (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--receipt-sha256',required=True);args=parser.parse_args()
    print(json.dumps(verify(args.fixture.resolve(),args.output.resolve(),args.receipt_sha256),indent=2))

if __name__=='__main__':main()
