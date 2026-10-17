"""Read-only independent corroboration of selected closed Dream test profiles.
Stdlib only; never imports the product verifier, starts a model, or replays work.
Input restricted to the existing /tmp/alaz-dream-e458 native test workspace.
"""
import argparse
import ast
from contextlib import closing
import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess

BASE=Path('/tmp/alaz-dream-e458')
def require(ok,reason):
    if not ok:raise ValueError(reason)
def encoded(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(x):return sha(encoded(x))
def filehash(p):return sha(p.read_bytes())
def read(p):
    require(p.is_file() and not any(x.is_symlink() for x in [p,*p.parents]) and p.stat().st_size<=2097152,'invalid_input_file')
    return json.loads(p.read_text(encoding='utf-8'))
def const(code,name):
    for n in ast.parse(code.read_text(encoding='utf-8')).body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets):
            v=ast.literal_eval(n.value);require(type(v) is str,'nonliteral_contract');return v
    raise ValueError('constant_not_found')
def sealed(row):require(row.get('digest')==digest({k:v for k,v in row.items() if k!='digest'}),'row_digest_mismatch')
def scope_path(name):
    require(re.fullmatch('[a-z0-9-]{1,80}',name) is not None,'invalid_fixture_name')
    p=BASE/name;require(p.is_dir() and not p.is_symlink(),'missing_fixture');return p

def verify(name,code):
    root=scope_path(name);receipt_file=root/'broker-native-result.json';rec=read(receipt_file)
    require(rec['result']=='PASS' and not rec['errors'] and not rec['source_drift'],'native_receipt_not_passed')
    require(rec['gateway_exit']==rec['broker_exit']==0 and rec['inference_calls']==rec['paid_calls']==0,'native_scope_or_cleanup')
    require(rec['native_admissions']==1 and rec['tool_reservations']==1,'unexpected_native_job_count')
    for path,h in rec['programs'].items():
        require(not Path(path).is_absolute() and '..' not in Path(path).parts,'invalid_source_name')
        require(filehash(code/path)==h,'native_program_version_mismatch')
    home=root/'profile';memory=home/'memories/dream-do-not-edit.txt'
    require(memory.read_bytes()==b'operator memory sentinel\n','memory_sentinel_changed')
    watched=[home/'state.db',home/'runs_idempotency.db',home/'config.yaml',root/'input.txt',memory,receipt_file]
    before={str(p):filehash(p) for p in watched}
    cfg=read(home/'config.yaml');settings=cfg['plugins']['entries']['alaz-host-gate']['settings']
    package=code/'packages/claw-hermes';dp=const(package/'dream.py','PREFIX');cp=const(package/'execution_budget.py','CLAIM')
    rp=const(package/'recovery_inspector.py','RESULT');vp=const(package/'request_view.py','PREFIX');sp=const(package/'source_capture.py','PREFIX')
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF');db.row_factory=sqlite3.Row
        admissions=[dict(r) for r in db.execute('SELECT * FROM session_admissions LIMIT 9')]
        require(len(admissions)==1,'unexpected_admission_count')
        pairs=db.execute('SELECT key,value FROM state_meta LIMIT 1001').fetchall();require(len(pairs)<=1000,'metadata_bound')
        meta={row['key']:json.loads(row['value']) for row in pairs
              if any(row['key'].startswith(prefix) for prefix in [dp,cp,rp,vp,sp])}
    batches=[v for k,v in meta.items() if k.startswith(dp)]
    claims=[v for k,v in meta.items() if k.startswith(cp)]
    views=[v for k,v in meta.items() if k.startswith(vp)]
    captures=[v for k,v in meta.items() if k.startswith(sp)]
    scenario=rec['dream']['scenario'];expected={'valid':'completed','invalid-citation':'rejected','disconnect':'unknown','disabled':'disabled'}[scenario]
    require(rec['dream']['state']==expected,'wrong_dream_scenario_result')
    details={'case':name,'scenario':scenario,'state':expected,'nativeReceiptSha256':filehash(receipt_file),
        'programFilesChecked':len(rec['programs']),'extraDreamProviderCalls':0,'candidateCount':0,
        'newAgentTasks':0,'newNativeRuns':0,'inferenceCalls':0,'paidCalls':0}
    if scenario=='disabled':
        require(not batches and rec['origin_accepted']==2,'disabled_dream_executed')
    else:
        require(len(batches)==1 and rec['origin_accepted']==3,'dream_batch_or_call_count')
        b=batches[0];sealed(b);require(b['state']==expected,'stored_state_disagrees')
        require(not b['activeMemoryChanged'] and not b['automaticTrigger'] and not b['modelInferenceQualityVerified'],'false_dream_elevation')
        require(not b['priorCandidateIds'],'probe_is_not_first_batch')
        ad=admissions[0];record=meta[rp+ad['admission_id']];rd=digest(record)
        require(ad['status']=='terminal','source_task_not_terminal')
        messages=record['result'].get('messages') or []
        input_items=[('retained_tool_result',i,m.get('content')) for i,m in enumerate(messages) if m.get('role')=='tool']
        input_items.append(('native_final_response',None,record['result'].get('final_response')))
        originals={}
        for kind,index,content in input_items:
            if type(content) is not str or not content.strip():continue
            identity={'profileBinding':b['binding'],'scope':b['scope'],'runId':ad['request_id'],
                'sessionId':ad['target_session_id'],'admissionId':ad['admission_id'],
                'executionGeneration':ad['generation'],'recordDigest':rd,'kind':kind,'index':index,
                'contentSha256':sha(content.encode())}
            originals['ev_'+digest(identity)]=(kind,content)
        sources=[]
        for ref in b['sourceRefs']:
            require(ref['evidenceId'] in originals,'source_reference_identity_mismatch')
            kind,content=originals[ref['evidenceId']];raw=content.encode('utf-8')
            require(ref['recordDigest']==rd and ref['runId']==ad['request_id'] and ref['admissionId']==ad['admission_id'],'source_record_mismatch')
            require(ref['contentSha256']==sha(raw) and ref['contentBytes']==len(raw),'source_content_mismatch')
            require(ref['credentialRedacted'] is False,'redacted_fixture_requires_separate_mapping')
            view=raw[:2048].decode('utf-8',errors='ignore');vb=view.encode()
            require(ref['viewSha256']==sha(vb) and ref['viewBytes']==len(vb) and ref['truncated']==(len(raw)>2048),'source_excerpt_mismatch')
            require(ref['goalVerified'] is False and ref['kind']==kind,'source_elevation')
            if kind=='retained_tool_result':
                matches=[c for c in captures if c['runId']==ad['request_id'] and c['outputSha256']==sha(raw) and c['outputBytes']==len(raw)]
                require(len(matches)==1 and matches[0]['sourceSha256']==filehash(root/'input.txt'),'raw_source_capture_mismatch')
                require(ref['executionAttribution']=='isolated_return_bound_to_admission','tool_execution_unbound')
            sources.append(ref|{'text':view})
        require(digest(sources)==b['inputDigest'],'review_input_digest_mismatch')
        policy={'enabled':False,'max_sources':4,'max_notes':6,'output_tokens':2048}|settings['dream']
        require(b['batchId']==digest({'sources':sources,'policy':policy,'prompt':b['promptVersion']}),'batch_identity_mismatch')
        payload={'model':settings['execution']['policy']['model'],
            'messages':[{'role':'system','content':const(package/'dream.py','SYSTEM_PROMPT')},
                        {'role':'user','content':encoded({'version':1,'maxNotes':policy['max_notes'],'sources':sources,'priorCandidates':[]}).decode()}],
            'max_tokens':policy['output_tokens'],'stream':False,'temperature':0}
        require(digest(payload)==b['requestDigest'],'reconstructed_request_mismatch')
        claim=next(c for c in claims if c['ticket']==b['providerTicket']);sealed(claim)
        require(claim['kind']=='provider' and claim['fingerprint']==b['requestDigest'] and claim['epoch']==b['epoch'],'provider_claim_unbound')
        view=next(v for v in views if v['ticket']==b['providerTicket']);sealed(view)
        origins=[o for o in rec['origin_request_views'] if o['requestSha256']==b['requestDigest']]
        require(len(origins)==1 and origins[0]['requestBytes']==len(encoded(payload))==view['requestBytes'],'origin_bytes_mismatch')
        require(view['requestDigest']==b['requestDigest'] and view['state']==('handoff_armed' if scenario=='disconnect' else 'broker_response_observed'),'request_phase_mismatch')
        require(claim['state']==('reserved' if scenario=='disconnect' else 'settled') and claim['tokens']>0,'reservation_state_mismatch')
        require(rec['dream']['secondInvocationReplayed'] and rec['dream']['extraProviderCalls']==1,'replay_caused_second_call')
        notes=b['candidates'];require(len(notes)==(1 if scenario=='valid' else 0),'candidate_count_mismatch')
        source_index={s['evidenceId']:s for s in sources}
        for note in notes:
            require(note['status']=='candidate' and all(note[k] is False for k in ['conclusionVerified','usableAsMemory','skillTransferVerified','grantsExecutionPermission']),'candidate_promoted')
            identity=digest([note['kind'],note['statement'].strip(),note['condition'].strip()])
            require(note['candidateId']=='dc_'+digest([identity,note['citations']]),'candidate_identity_mismatch')
            for cite in note['citations']:
                source=source_index[cite['evidenceId']];raw=source['text'].encode();start=cite['startByte'];end=cite['endByte']
                require(cite['sourceQuotationVerified'] is True and cite['viewSha256']==source['viewSha256'] and
                    type(start) is int and type(end) is int and 0<=start<end<=len(raw) and raw[start:end]==cite['quote'].encode(),'citation_bytes_mismatch')
        details.update(extraDreamProviderCalls=1,candidateCount=len(notes),sourceExcerptCount=len(sources),
            sourceRecordIdentityVerified=True,quoteBytesVerified=bool(notes),requestBytes=len(encoded(payload)),
            sourceToActualRequestMatched=True,reservationState=claim['state'],requestViewState=view['state'],
            activeMemoryChanged=False,automaticTrigger=False,learnedSkillVerified=False)
    absent=0
    for binding in rec['bindings']:
        ident=binding['containerId'];require(re.fullmatch('[a-f0-9]{64}',ident) is not None,'invalid_container_id')
        r=subprocess.run(['sudo','-n','docker','container','inspect',ident],capture_output=True,timeout=10)
        require(r.returncode!=0 and (b'No such object' in r.stderr or b'No such container' in r.stderr),'container_absence_unverified')
        absent+=1
    socket_path=root/'broker/egress.sock';require(not socket_path.exists(),'broker_socket_remains')
    require(before=={str(p):filehash(p) for p in watched},'application_files_changed_during_review')
    details.update(result='CORROBORATED',ownedContainersAbsent=absent,brokerSocketAbsent=True,
        watchedApplicationFilesUnchanged=True,memorySentinelUnchanged=True,filesystemSilenceClaim=False)
    return details

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--code-directory',required=True)
    parser.add_argument('--cases',required=True);args=parser.parse_args();code=scope_path(args.code_directory)
    names=args.cases.split(',');require(1<=len(names)<=8 and len(set(names))==len(names),'case_bound')
    rows=[verify(name,code) for name in names]
    result={'scope':'independent stdlib read of existing native Dream fixtures; scripted synthesis, not inference',
        'observedAt':datetime.datetime.now().astimezone().isoformat(),'result':'CORROBORATED',
        'sourceDirectory':args.code_directory,'dreamSha256':filehash(code/'packages/claw-hermes/dream.py'),
        'cases':rows,'newNativeRuns':0,'inferenceCalls':0,'paidCalls':0}
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
