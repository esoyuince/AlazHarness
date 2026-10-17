"""Independent metadata corroboration of closed scripted native R1B2 profiles.
No product proof helper is imported, no native/model job is launched. Only exact
recorded Docker IDs are read via inspect. Never reads broker-private/config keys.
"""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import datetime


def check(ok,message):
    if not ok:raise ValueError(message)

def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(path):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size<=2_097_152,'invalid_metadata_file')
    return json.loads(path.read_text(encoding='utf-8'))
def sealed(value):
    check(isinstance(value,dict) and value.get('digest')==sha(encoded({k:v for k,v in value.items() if k!='digest'})),'corrupt_record_digest')
    return value

def check_case(root,code,case_name,view_name):
    check(re.fullmatch('[a-z0-9-]{1,80}',case_name) and re.fullmatch('[a-z0-9-]{1,80}',view_name),'invalid_case')
    case=root/case_name;view=root/view_name
    rec=read(case/'broker-native-result.json');report=read(view/'report.json')
    check(rec['result']=='PASS' and rec['errors']==[] and rec['source_drift']==[],'native_not_qualified')
    check(rec['gateway_exit']==rec['broker_exit']==0 and rec['inference_calls']==rec['paid_calls']==0,'native_close_or_scope_invalid')
    check(report['reportStatus']=='verified_snapshot','report_unverified')
    for rel,expected in rec['programs'].items():
        p=code/rel;check(p.resolve().is_relative_to(code.resolve()) and sha(p.read_bytes())==expected,'source_revision_mismatch')
    selected_files=[case/'profile/state.db',case/'profile/runs_idempotency.db',case/'broker-native-result.json',case/'input.txt',view/'report.json']
    selected_files += [p for p in (case/'capsules').rglob('*') if p.is_file()]
    before={str(p):sha(p.read_bytes()) for p in selected_files}
    with closing(sqlite3.connect((case/'profile/state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
        entries=dict(db.execute("SELECT key,value FROM state_meta WHERE key GLOB 'alaz.evidence.*' OR key GLOB 'alaz.execution.claim.*' OR key GLOB 'alaz.execution.egress.*' OR key GLOB 'gateway.admission.result.*'"))
    docs={k:sealed(json.loads(v)) for k,v in entries.items() if not k.startswith('gateway.')}
    requests={d['requestDigest']:d for k,d in docs.items() if k.startswith('alaz.evidence.request.v1.')}
    check(len(requests)==sum(k.startswith('alaz.evidence.request.v1.') for k in docs),'duplicate_fixture_request')
    sources={d['digest']:d for k,d in docs.items() if k.startswith('alaz.evidence.source.v1.')}
    section=report['evidenceView'];check(section['modelVisibility']=='unknown','model_visibility_overclaim')
    native_result=json.loads(entries['gateway.admission.result.v1.'+rec['client']['final']['run']['admission_id']])
    messages=native_result['result'].get('messages',[])
    tool_results=[m for m in messages if m.get('role')=='tool']
    origin={o['requestSha256']:o for o in rec['origin_request_views']}
    check(len(origin)==rec['origin_accepted'],'origin_count_or_identity')
    details=[];inclusion_count=0
    if rec['record_request_view']:
        check(set(requests)==set(origin),'actual_wire_manifest_digests')
        views={v['requestDigest']:v for v in section['providerRequestViews']['requests']}
        check(set(views)==set(requests),'report_manifest_set')
        for digest,row in requests.items():
            actual=origin[digest];display=views[digest]
            check(row['requestBytes']==actual['requestBytes']==display['requestBytes'],'actual_request_bytes')
            check(row['messageCount']==actual['messageCount']==display['messageCount'],'actual_message_count')
            check([{k:v for k,v in t.items() if k!='sourceCaptureDigest'} for t in row['toolMessages']]==actual['toolMessages'],'actual_tool_metadata')
            claim=docs['alaz.execution.claim.v1.'+row['scope']+'.'+row['ticket']]
            grant=docs['alaz.execution.egress.v1.'+row['scope']+'.'+row['ticket']]
            check(claim['kind']=='provider' and claim['fingerprint']==digest==grant['fingerprint'],'claim_fingerprint')
            check(grant['digest']==row['egressDigest'],'grant_digest')
            for key in ['scope','binding','policy','ticket','epoch','instance']:
                check(row[key]==claim[key]==grant[key],'identity_'+key)
            check(row['brokerId']==grant['brokerId'] and row['routeFingerprint']==grant['routeFingerprint'],'broker_identity')
            lost=rec['scenario']=='upstream-disconnect' or (rec['scenario']=='after-tool-disconnect' and bool(actual['toolMessages']))
            check(row['state']==('handoff_armed' if lost else 'broker_response_observed'),'request_state')
            check(display['brokerHttpResponseObserved'] is (not lost) and display['providerResponseValidated'] is (not lost),'phase_overclaim')
            check(display['initiatingRunId'] is None and display['initiatingRunVerified'] is False and display['modelProcessingVerified'] is False,'initiator_or_model_overclaim')
            check(claim['state']==('reserved' if lost else 'settled'),'physical_claim_state')
            if lost:check(claim['usage'] is None and row['responseSha256'] is None,'lost_response_fabricated')
            bound=[]
            for item in row['toolMessages']:
                d=item['sourceCaptureDigest']
                if d is None:continue
                cap=sources[d]
                check(cap['state']=='returned' and cap['toolCallHash']==item['toolCallHash'] and cap['outputSha256']==item['contentSha256'] and cap['outputBytes']==item['contentBytes'],'source_return_pair')
                tc=docs['alaz.execution.claim.v1.'+cap['scope']+'.'+cap['ticket']]
                check(tc['kind']=='read_file' and tc['state']=='settled' and tc['outcome']=='tool_return','native_tool_claim')
                native=[m for m in tool_results if sha(m.get('tool_call_id','').encode())==cap['toolCallHash'] and sha(m.get('content','').encode())==cap['outputSha256']]
                check(len(native)==1 and len(native[0]['content'].encode())==cap['outputBytes'],'actual_native_tool_return')
                captured=case/'input.txt';check(sha(captured.read_bytes())==cap['sourceSha256'] and captured.stat().st_size==cap['sourceBytes'],'actual_input_snapshot')
                staged=list((case/'capsules').glob('*/input-'+cap['ticket']+'.txt'))
                check(len(staged)==1 and staged[0].read_bytes()==captured.read_bytes(),'actual_staged_snapshot')
                bindings=[b for b in rec['bindings'] if b['ticket']==cap['ticket']]
                check(len(bindings)==1 and bindings[0]['inputDigest']==cap['sourceSha256'] and bindings[0]['admissionId']==cap['admissionId'] and bindings[0]['executionGeneration']==cap['generation'],'native_process_binding')
                bound.append({'inputBytes':cap['sourceBytes'],'toolBytes':cap['outputBytes'],'sourceDigest':cap['sourceSha256'],'sourceToActualRequestBound':True})
            incs=display['selectedEvidenceInclusions'];check(len(incs)==len(bound),'selected_inclusion_count')
            for inc in incs:
                check(inc['preparationRecorded'] and inc['handoffIntentRecorded'],'missing_phase')
                check(inc['brokerHttpResponseObserved'] is (not lost) and inc['providerResponseValidated'] is (not lost),'inclusion_phase')
                check(not any(inc[k] for k in ['initiatingRunVerified','modelProcessingVerified','understandingVerified','grantsExecutionPermission']),'inclusion_overclaim')
                check(inc['coverageOfReturnedText']=='complete' and inc['sourceFileCoverage']=='not_inferred','coverage_overclaim')
            inclusion_count+=len(incs)
            details.append({'requestBytes':row['requestBytes'],'state':row['state'],'toolMessages':len(row['toolMessages']),'inclusions':len(incs),'boundSources':bound,'brokerResponseObserved':display['brokerHttpResponseObserved']})
        expected=1 if rec['record_source'] and rec['scenario'] in ['normal','after-tool-disconnect'] else 0
        check(inclusion_count==expected,'native_scenario_inclusions')
    else:
        check(not requests and 'providerRequestViews' not in section,'optout_false_evidence')
    partial=False
    if rec.get('read_limit') is not None and rec['fixture_lines']>rec['read_limit']:
        check(len(tool_results)==1,'partial_result_missing');value=json.loads(tool_results[0]['content']);limit=rec['read_limit']
        check(value['total_lines']==rec['fixture_lines'] and value['truncated'] is True,'partial_scope')
        content=value['content'];check('line '+str(limit)+' ışık' in content and 'line '+str(limit+1)+' ışık' not in content and 'line '+str(rec['fixture_lines'])+' ışık' not in content,'partial_return_boundary');partial=True
    containers=[]
    for b in rec['bindings']:
        cid=b['containerId'];check(re.fullmatch('[a-f0-9]{64}',cid) and b['exited'] and b['removed'],'invalid_container_receipt')
        r=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/docker','inspect',cid],capture_output=True,text=True,timeout=10)
        check(r.returncode==1 and json.loads(r.stdout)==[] and ('no such object: '+cid) in r.stderr.lower(),'container_absence_unconfirmed');containers.append(cid)
    check(not(case/'broker/egress.sock').exists(),'broker_socket_remaining')
    check(before=={str(p):sha(p.read_bytes()) for p in selected_files},'source_or_main_store_mutated')
    return {'case':case_name,'scenario':rec['scenario'],'result':'CORROBORATED','nativeReceiptSha256':before[str(case/'broker-native-result.json')],
        'sourceRevisionFilesChecked':len(rec['programs']),'providerRequests':rec['origin_accepted'],'isolatedReads':rec['tool_reservations'],
        'manifestRows':len(requests),'sourceCaptures':len(sources),'sourceToRequestInclusions':inclusion_count,'details':details,
        'actualPartialReadConfirmed':partial,'ownedContainersAbsent':len(containers),'brokerSocketAbsent':True,
        'mainStoresAndInputUnchanged':True,'newNativeRuns':0,'paidCalls':0,'filesystemSilenceClaim':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-root',type=Path,required=True);parser.add_argument('--code',type=Path,required=True)
    parser.add_argument('--case',action='append',required=True,help='closed-fixture-name:view-directory-name')
    parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    root=a.experiment_root.resolve();code=a.code.resolve();out=a.output.resolve()
    check(root==Path('/tmp/alaz-r1b2-af13') and code.is_relative_to(root),'explicit_experiment_required')
    check(out.is_relative_to(Path('/tmp/alaz-r1b2-qa-9b08')) and not out.exists(),'fresh_own_output_required')
    rows=[]
    for arg in a.case:
        parts=arg.split(':');check(len(parts)==2,'invalid_case_pair');rows.append(check_case(root,code,*parts))
    result={'scope':'independent closed-native metadata/source/wire corroboration; no new native/model runs','observedAt':datetime.datetime.now().astimezone().isoformat(),'result':'PASS','cases':rows,'newNativeRuns':0,'paidCalls':0}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
