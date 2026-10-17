"""D2B2 native Linux Unix-socket/HTTP acceptance with a scripted local origin.

Runs the actual product ProviderBrokerServer/Client, PermitVerifier,
ExecutionLedger, request-view, D1, D2A and D2B2 code. The ONLY substituted
component is _upstream's aiohttp adapter: stdlib HTTPConnection to 127.0.0.1.
NOT a Hermes Gateway, Docker sandbox, real model, paid provider, or OS-UID
isolation acceptance. No install, user profile, credential or model API access.
"""
from __future__ import annotations
import argparse
import asyncio
from contextlib import closing
from dataclasses import asdict
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests'),str(ROOT/'scripts')]
from execution_budget import ExecutionDenied
from provider_broker import ProviderBrokerClient,ProviderBrokerServer,reject_sensitive_response
from provider_egress import BrokerConfig,signed,hashed,EGRESS
from dream_review import DreamReviewService
from dream_trial import DreamTrialService
from dream_eval import seal as seal_plan,grade
from recovery_inspector import _load,_json
from test_dream import DreamFixture
from test_dream_eval import fixture as eval_fixture
import run_provider_broker


class StdlibLocalBroker(ProviderBrokerServer):
    """TEST ONLY: exact broker security/IPC, alternate bounded localhost HTTP."""
    async def _upstream(self,payload):
        self.counts['physicalAttempts']+=1
        def post():
            port=int(self.config.upstream_base_url.split(':')[2].split('/')[0])
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            try:
                conn.request('POST','/v1/chat/completions',body=_json(payload).encode('utf-8'),
                             headers={'Authorization':'Bearer '+self.config.upstream_bearer,
                                      'Content-Type':'application/json'})
                res=conn.getresponse()
                if 300 <= res.status < 400:
                    raise ExecutionDenied('provider_redirect_refused')
                if res.status!=200:
                    return b'{}',res.status if 400<=res.status<=599 else 502,'application/json'
                ctype=res.getheader('Content-Type','').split(';')[0].lower()
                if ctype not in ('application/json','text/event-stream') or res.getheader('Content-Encoding'):
                    raise ExecutionDenied('broker_upstream_error')
                raw=res.read(4_194_305)
                if len(raw)>4_194_304:raise ExecutionDenied('broker_upstream_error')
                reject_sensitive_response(raw,ctype,self.config.upstream_bearer)
                return raw,200,ctype
            finally:conn.close()
        return await asyncio.to_thread(post)


class NoAgent:
    def __init__(self):self.cleanups=[]
    def addCleanup(self,fun):self.cleanups.append(fun)
    def close(self):
        for f in reversed(self.cleanups):f()


class Origin:
    def __init__(self,secret,scenario):
        self.secret=secret;self.scenario=scenario
        self.requests=[];self.rejections=0;self.failure=[];self.revoke=None
        self.server=None;self.thread=None

    def start(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                size=int(self.headers.get('Content-Length','0'))
                if size<=0 or size>100_000:
                    self.send_response(413);self.end_headers();return
                raw=self.rfile.read(size)
                if self.path!='/v1/chat/completions' or self.headers.get('Authorization')!='Bearer '+owner.secret:
                    owner.rejections+=1;self.send_response(401);self.end_headers();return
                try:
                    body=json.loads(raw)
                    user=json.loads(body['messages'][1]['content'])
                    if type(user) is not dict:raise ValueError('invalid user')
                    if 'sources' in user:
                        kind='dream'
                        sample=user['sources'][0]
                        quote=sample['text'][:20]
                        answers={'notes':[{'kind':'caution',
                            'statement':'Keep the observed result separate from inferred success.',
                            'condition':'When reviewing historical work.',
                            'citations':[{'evidenceId':sample['evidenceId'],'quote':quote}],
                            'relatedCandidateIds':[]}]}
                        response_text=_json(answers)
                    elif 'cases' in user:
                        kind='candidate' if user.get('lesson') is not None else 'baseline'
                        labels=('RED','AMBER','GREEN')
                        answer_list=[]
                        for i,case in enumerate(user['cases']):
                            answer=labels[i%3] if kind=='candidate' or i>=4 else 'WRONG'
                            answer_list.append({'caseId':case['caseId'],'answer':answer})
                        response_text=_json({'answers':answer_list})
                    else:
                        raise ValueError('unexpected request')
                    owner.requests.append({'kind':kind,
                        'requestSha256':hashlib.sha256(raw).hexdigest(),
                        'requestBytes':len(raw),'messageCount':len(body['messages']),
                        'hasLesson':bool(user.get('lesson')),
                        'rawBody':body})
                    if owner.scenario=='candidate-disconnect' and kind=='candidate':
                        try:self.connection.shutdown(socket.SHUT_RDWR)
                        except OSError:pass
                        self.connection.close();return
                    if owner.scenario=='review-revoked' and kind=='baseline':
                        if owner.revoke:owner.revoke()
                    resp={'model':'chosen-model',
                        'choices':[{'index':0,'finish_reason':'stop',
                                    'message':{'role':'assistant','content':response_text}}],
                        'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30}}
                    encoded=_json(resp).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except Exception as ex:
                    owner.failure.append(type(ex).__name__)
                    self.send_response(500);self.end_headers()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        return self.server.server_port

    def close(self):
        if self.server is not None:
            self.server.shutdown();self.server.server_close()
            self.thread.join(timeout=3)


def load_json(p):return json.loads(p.read_text(encoding='utf-8'))


def wait_ready(path,child,seconds=12):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if path.is_file():return load_json(path)
        if child.poll() is not None:raise RuntimeError('broker_exited_before_ready')
        time.sleep(.05)
    raise RuntimeError('broker_ready_timeout')


def run_scenario(scenario):
    report={'scenario':scenario,'result':'NOT_RUN','errors':[],
       'broker':{},'origin':{},'trial':{},'budget':{},'provenance':{},
       'scope':'real Linux private Unix-socket broker IPC/native SQLite/loopback HTTP with overridden stdlib _upstream; synthetic terminal and no Hermes Gateway',
       'nativeBrokerSocket':False,'nativeGateway':False,
       'originalAiohttpUpstream':False,'docker':False,
       'physicalModelInferenceVerified':False,'modelComprehensionVerified':False,
       'independentSkillTransferVerified':False,'activeMemoryChanged':False,
       'paidCalls':0,'actualModelCalls':0}
    agent=NoAgent();broker=None;origin=None;start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='alaz-d2b2-native-') as temp:
        home=Path(temp);configfile=home/'broker-config.json';brokerdir=home/'broker'
        stdout=home/'broker.stdout';stderr=home/'broker.stderr'
        try:
            fixture=DreamFixture(agent)
            # fixture uses a real SQLite file and native SQL writer; the
            # terminal source records are constructed from a synthetic run.
            f=fixture
            origin_key=secrets.token_hex(32);signer=secrets.token_hex(32)
            origin=Origin(origin_key,scenario);port=origin.start()
            cfg=BrokerConfig(f'http://127.0.0.1:{port}/v1',
                 f.policy.model,origin_key,signer,str(f.home/'state.db'),
                 f.context.scope,f.context.binding,f.policy.fingerprint)
            configfile.write_text(json.dumps(asdict(cfg)),encoding='utf-8')
            configfile.chmod(0o600)
            env={'PATH':'/usr/bin:/bin','HOME':str(home),'LANG':'C.UTF-8',
                 'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8',
                 'NO_PROXY':'127.0.0.1,localhost','AWS_EC2_METADATA_DISABLED':'true'}
            so=stdout.open('wb');se=stderr.open('wb')
            try:
                broker=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),
                       '--worker','--config',str(configfile),'--broker-output',str(brokerdir)],
                       cwd=home,env=env,stdin=subprocess.DEVNULL,
                       stdout=so,stderr=se,start_new_session=True)
                ready=wait_ready(brokerdir/'ready.json',broker)
                assert ready['pid']==broker.pid and ready['backend']=='linux_unix_credential_broker'
                assert (brokerdir/'egress.sock').exists() and broker.pid!=os.getpid()
                report['nativeBrokerSocket']=True
                link={'socket_path':ready['socketPath'],
                      'broker_id':ready['brokerId'],
                      'route_fingerprint':ready['routeFingerprint'],
                      'signing_key':signer}
                real_client=ProviderBrokerClient(link)
                assert asyncio.run(real_client.ready()) is True
                f.broker=real_client
                f.boundary.broker=real_client
                dream_result=f.run()
                assert dream_result['state']=='completed' and len(dream_result['candidates'])==1
                report['dreamState']='completed'
                report['candidateCount']=1
                review_config={'enabled':True,'max_events':8}
                review=DreamReviewService(review_config,f.service,
                         config_reader=lambda:review_config)
                candidate=dream_result['candidates'][0]['candidateId']
                initial=review.inspect(dream_result['batchId'])
                reviewed=review.decide(dream_result['batchId'],candidate,
                   'accept_for_testing','evidence_sufficient_to_test',initial['revision'])
                assert reviewed['evaluationStatus']=='not_run'
                report['operatorActualHumanReviewVerified']=False
                _,training,cases,gold,_,_,_=eval_fixture()
                oracle_key=secrets.token_hex(32)
                plan=seal_plan(reviewed,candidate,'synthetic_triage',
                               training,cases,gold,oracle_key)
                trial_config={'enabled':True,'max_cases':12,'output_tokens':256}
                trial=DreamTrialService(trial_config,review,
                         config_reader=lambda:trial_config)

                if scenario=='review-revoked':
                    def revoke():
                        current=review.inspect(dream_result['batchId'])
                        review.decide(dream_result['batchId'],candidate,
                           'defer','operator_deferred',current['revision'])
                    origin.revoke=revoke

                result=asyncio.run(trial.run(plan))
                final=trial.status(plan['planId'])
                assert (final['state']==result['state'] and
                    final['realModelExecutionVerified'] is False)
                report['trial']['state']=result['state']
                report['trial']['recordedArmCount']=len(result['results'])
                report['trial']['requestedArms']=[r['arm'] for r in result['results']]
                report['trial']['ticketHashes']=[hashlib.sha256(r['ticket'].encode()).hexdigest()
                                                 for r in result['results']]
                report['trial']['ledgerLinkagePreserved']=True
                report['trial']['evaluatorTruthSent']=False
                report['trial']['providerInferenceVerified']=False
                report['trial']['skillTransferVerified']=False
                report['budget']={'providerReservations':f.ledger.snapshot()['providerCalls'],
                                  'separateBudget':False}
                report['origin']={'authenticatedRequests':len(origin.requests),
                                  'rejectedNonProviderCredentials':origin.rejections,
                                  'kinds':[r['kind'] for r in origin.requests],
                                  'requestSha256':[r['requestSha256'] for r in origin.requests],
                                  'requestBytes':[r['requestBytes'] for r in origin.requests],
                                  'originExceptions':origin.failure}
                # The origin observes exact canonical payload bytes, independent
                # of product request_view metadata and its SHA-256.
                with closing(sqlite3.connect(f.home/'state.db')) as con:
                    rows=[_load(v) for v, in con.execute(
                       "SELECT value FROM state_meta WHERE key LIKE 'alaz.evidence.request.v1.%'")]
                    egress=[_load(v) for v, in con.execute(
                       "SELECT value FROM state_meta WHERE key LIKE 'alaz.execution.egress.v1.%'")]
                origin_hashes={r['requestSha256'] for r in origin.requests}
                report['provenance']={
                    'preparedRequestRows':len(rows),
                    'observedResponseRows':sum(r['state']=='broker_response_observed' for r in rows),
                    'exactWireHashMatches':sum(r['requestDigest'] in origin_hashes for r in rows),
                    'nativeEgressGrantCount':len(egress),
                    'requestViewTiedToProviderClaim':all(
                         r['requestDigest']==next(c['fingerprint'] for c in egress
                             if c['ticket']==r['ticket']) for r in rows),
                    'textStreamOnly':True,'modelProcessingVerified':False}
                assert not origin.failure and origin.rejections==0
                assert report['provenance']['exactWireHashMatches']==len(origin.requests)
                assert report['budget']['providerReservations']==len(origin.requests)
                assert all(not r['hasLesson'] for r in origin.requests if r['kind']=='baseline')
                assert all(r['hasLesson'] for r in origin.requests if r['kind']=='candidate')
                assert all('oracleKeyHex' not in _json(r['rawBody']) for r in origin.requests)
                if scenario=='normal':
                    assert result['state']=='completed'
                    assert [r['arm'] for r in result['results']]==['baseline','candidate']
                    doc=grade(plan,review.inspect(dream_result['batchId']),
                        gold,result['results'][0]['answers'],
                        result['results'][1]['answers'],oracle_key)
                    assert doc['baselineCorrect']==8 and doc['candidateCorrect']==12
                    assert doc['independentOutcomeVerified'] is False
                    report['trial']['syntheticLocalScore']={
                        'baselineCorrect':doc['baselineCorrect'],
                        'candidateCorrect':doc['candidateCorrect'],
                        'learnedSkillProven':False}
                    # Same signed grant cannot be replayed even through a new
                    # socket connection while broker process is still alive.
                    last=egress[-1]
                    grant={k:v for k,v in last.items() if k!='digest'}
                    payload=next(r['rawBody'] for r in origin.requests
                                 if hashed(r['rawBody'])==last['fingerprint'])
                    signed_envelope=signed({'version':1,'operation':'send',
                                           'grant':grant,'payload':payload},signer,'request')
                    before=len(origin.requests)
                    try:
                        asyncio.run(real_client._exchange(signed_envelope,grant['ticket']))
                        raise AssertionError('replay accepted')
                    except ExecutionDenied as ex:
                        assert str(ex)=='broker_replay_refused',str(ex)
                    assert before==len(origin.requests)
                    report['provenance']['replayRefused']=True
                elif scenario=='candidate-disconnect':
                    assert result['state']=='unknown' and len(result['results'])==1
                    assert [r['kind'] for r in origin.requests]==['dream','baseline','candidate']
                    assert len(rows)==3 and report['provenance']['observedResponseRows']==2
                elif scenario=='review-revoked':
                    assert result['state']=='unknown' and len(result['results'])==0
                    assert [r['kind'] for r in origin.requests]==['dream','baseline']
                    assert len(rows)==2 and report['provenance']['observedResponseRows']==2
                else:raise AssertionError('unknown scenario')
                assert f.memory.read_bytes()==b'user pinned memory\n'
                assert f.skill.read_bytes()==b'user pinned skill\n'
                report['memoryAndSkillUnchanged']=True
            finally:
                if broker is not None:
                    if broker.poll() is None:
                        broker.terminate()
                    try:broker.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        broker.kill();broker.wait(timeout=5);report['forcedBrokerStop']=True
                so.close();se.close()
                if (brokerdir/'shutdown.json').exists():
                    done=load_json(brokerdir/'shutdown.json')
                    report['broker']={'pidSeparate':broker.pid!=os.getpid(),
                        'exitCode':broker.returncode,
                        'socketRemoved':done['socketRemoved'],
                        'activeRequests':done['activeRequests'],
                        'counters':done['counters']}
                    assert (broker.returncode==0 and done['socketRemoved'] and
                        done['activeRequests']==0)
                elif broker is not None:
                    raise RuntimeError('broker_shutdown_missing')
        except Exception as ex:
            report['errors'].append(type(ex).__name__+':'+str(ex)[:180])
            report['diagnosticTrace']=traceback.format_exc(limit=2).splitlines()[-4:]
        finally:
            if origin is not None:origin.close()
            agent.close()
            report['elapsedSeconds']=round(time.monotonic()-start,3)
        report['result']='PASS' if (not report['errors'] and
            report['nativeBrokerSocket'] and report['broker'].get('exitCode')==0) else 'FAIL'
    report['privateTemporaryProfileRemoved']=True
    return report


def worker(config,output):
    run_provider_broker.ProviderBrokerServer=StdlibLocalBroker
    return run_provider_broker.main()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',choices=('normal','candidate-disconnect','review-revoked'))
    parser.add_argument('--output',type=Path)
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--broker-output',type=Path)
    a=parser.parse_args()
    if a.worker:
        if a.scenario is not None or a.output is not None or a.config is None or a.broker_output is None:
            return 3
        sys.argv=[sys.argv[0],'--config',str(a.config),'--output',str(a.broker_output)]
        return worker(a.config,a.broker_output)
    if a.scenario is None or a.output is None:
        return 3
    output=a.output.absolute()
    evidence=(ROOT/'evidence').resolve()
    if (output.exists() or output.is_symlink() or
       not output.parent.is_dir() or
       not output.resolve(strict=False).is_relative_to(evidence)):
        raise SystemExit('output_must_be_new_scoped_evidence_json')
    res=run_scenario(a.scenario)
    # No raw provider bodies, tokens, private file paths or oracle in this report.
    output.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scenario':a.scenario,'result':res['result'],
                      'broker':res.get('broker'),
                      'origin':{k:v for k,v in res.get('origin',{}).items()
                                if k in ('authenticatedRequests','kinds')},
                      'errors':res.get('errors')},ensure_ascii=False))
    return 0 if res['result']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
