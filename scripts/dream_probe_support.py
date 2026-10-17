"""Opt-in scripted Dream qualification support. Not an inference model or product API.
Reuses the actual native Gateway/provider probe without replacing its engine.
"""
from contextlib import closing
import hashlib
import http.client
import json
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path


def scripted_dream(handler, body, owner, scenario):
    if not scenario or not body.get('messages') or not body['messages'][0].get('content','').startswith('Alaz Dream candidate review v1.'):
        return False
    assert not body.get('tools')
    if scenario=='disconnect':
        handler.connection.shutdown(socket.SHUT_RDWR);handler.connection.close();return True
    packet=json.loads(body['messages'][1]['content'])
    sources=[s for s in packet['sources'] if s['kind']=='retained_tool_result']
    assert len(sources)==1 and sources[0]['executionAttribution']=='isolated_return_bound_to_admission'
    s=sources[0];quote='line 2 ışık'
    assert quote in s['text']
    note={'kind':'caution','statement':'Satır sınırıyla dönen araç çıktısını dosyanın tamamı olarak değerlendirme.',
          'condition':'Sınırlı metin dosyası okumalarını incelerken.',
          'citations':[{'evidenceId':s['evidenceId'],'quote':quote}],'relatedCandidateIds':[]}
    if scenario=='invalid-citation':note['citations'][0]['quote']='bu metin kaynakta bulunmuyor'
    handler.send({'id':'dream-fixture','object':'chat.completion','model':body['model'],
        'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps({'notes':[note]},ensure_ascii=False)}}],
        'usage':{'prompt_tokens':120,'completion_tokens':40,'total_tokens':160}})
    return True


def exercise_dream(out, port, token, scenario, result, provider):
    home=out/'profile'
    rid=result['final']['run']['run_id']
    with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True)) as conn:
        keys=conn.execute('SELECT idempotency_key FROM run_idempotency WHERE run_id=?',(rid,)).fetchall()
    assert len(keys)==1
    source={'body':{'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'},
        'idempotency_key':keys[0][0],'observed':result['final']['run']}
    payload=json.dumps({'sources':[source]}).encode()
    def call(path,method='POST',raw=payload,bearer=token):
        c=http.client.HTTPConnection('127.0.0.1',port,timeout=50)
        try:
            c.request(method,path,body=raw if method=='POST' else None,
                      headers={'Authorization':'Bearer '+bearer,'Content-Type':'application/json'})
            response=c.getresponse();data=response.read(131073);assert len(data)<=131072
            return response.status,json.loads(data)
        finally:c.close()
    memory=home/'memories';memory.mkdir(exist_ok=True)
    marker=memory/'dream-do-not-edit.txt';assert not marker.exists();marker.write_bytes(b'operator memory sentinel\n')
    before=hashlib.sha256(marker.read_bytes()).hexdigest();previous=provider.accepted
    bad=call('/alaz/host/v1/dream',bearer='not-authorized')
    assert bad[0] in (401,409) and provider.accepted==previous
    first_status,first=call('/alaz/host/v1/dream')
    if scenario=='disabled':
        assert first_status==409 and provider.accepted==previous
        with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as conn:
            assert not conn.execute("SELECT 1 FROM state_meta WHERE key GLOB 'alaz.dream.candidates.v1.*'").fetchone()
        return {'scenario':scenario,'state':'disabled','extraProviderCalls':0,'memoryUnchanged':hashlib.sha256(marker.read_bytes()).hexdigest()==before,'newAgentTasks':0}
    expected={'valid':'completed','invalid-citation':'rejected','disconnect':'unknown'}[scenario]
    assert first.get('state')==expected,{'status':first_status,'response':first}
    assert provider.accepted==previous+1
    second_status,second=call('/alaz/host/v1/dream')
    assert second['batchId']==first['batchId'] and second['replayed'] and provider.accepted==previous+1
    get_status,saved=call('/alaz/host/v1/dream/'+first['batchId'],method='GET')
    assert get_status==200 and saved['state']==expected and saved['candidates']==first['candidates']
    cli_connection=out/'dream-cli-private.json';assert not cli_connection.exists()
    cli_connection.write_text(json.dumps({'base_url':f'http://127.0.0.1:{port}','token':token}));cli_connection.chmod(0o600)
    cli_output=out/'dream-cli-result.json';root=Path(__file__).resolve().parents[1]
    cli=subprocess.run([sys.executable,'-B',str(root/'scripts/dream_once.py'),
        '--connection',str(cli_connection),'--batch-id',first['batchId'],'--output',str(cli_output)],
        capture_output=True,timeout=55)
    assert cli.returncode==(0 if expected=='completed' else 2),{'cliExit':cli.returncode}
    assert json.loads(cli_output.read_text())==saved and provider.accepted==previous+1

    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as conn:
        conn.execute('PRAGMA query_only=ON')
        rows=[json.loads(v) for v, in conn.execute("SELECT value FROM state_meta WHERE key GLOB 'alaz.dream.candidates.v1.*'")]
        claims=[json.loads(v) for v, in conn.execute("SELECT value FROM state_meta WHERE key GLOB 'alaz.execution.claim.v1.*'")]
        requests=[json.loads(v) for v, in conn.execute("SELECT value FROM state_meta WHERE key GLOB 'alaz.evidence.request.v1.*'")]
    assert len(rows)==1 and rows[0]==saved
    claim=next(c for c in claims if c['ticket']==saved['providerTicket'])
    view=next(v for v in requests if v['ticket']==saved['providerTicket'])
    actual=provider.request_metadata[-1]
    assert actual['requestSha256']==view['requestDigest']==saved['requestDigest']
    assert view['state']==('handoff_armed' if scenario=='disconnect' else 'broker_response_observed')
    assert claim['kind']=='provider' and claim['tokens']>0
    assert sum(c['kind']=='read_file' for c in claims)==1
    if expected=='completed':
        assert len(saved['candidates'])==1
        n=saved['candidates'][0];assert n['status']=='candidate' and n['usableAsMemory'] is False and not n['conclusionVerified']
        assert n['citations'][0]['sourceQuotationVerified'] is True
    else:assert saved['candidates']==[]
    assert hashlib.sha256(marker.read_bytes()).hexdigest()==before
    return {'scenario':scenario,'state':expected,'batchId':first['batchId'],'candidates':first['candidates'],
            'sourceCount':len(first['sourceRefs']),'extraProviderCalls':1,'secondInvocationReplayed':True,
            'physicalRequestBytes':actual['requestBytes'],'requestViewState':view['state'],
            'reservationState':claim['state'],'reservedTokens':claim['tokens'],'memoryUnchanged':True,
            'activeMemoryChanged':False,'newAgentTasks':0,'goalVerified':False,'inferenceQualityVerified':False,'cliStatusVerified':True}
