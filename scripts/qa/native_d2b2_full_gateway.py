"""Real pinned Hermes Gateway + ORIGINAL aiohttp broker D2B2 acceptance.

No Docker/file tools are exercised. No real model, paid provider, user profile,
autonomy or memory promotion. Only a local scripted HTTP origin is contacted.
The existing native SessionAuthority and Alaz HostGate plugin are exercised.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import os
from pathlib import Path
import re
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
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'packages/claw-hermes')]
from run_native_hermes_probe import pinned_source
from run_native_host_gate import install_probe_plugin
from execution_budget import ExecutionPolicy
from recovery_inspector import LocalRecoveryContext,_json,_load
from provider_egress import BrokerConfig,route_fingerprint
from dream_eval import seal as seal_plan,grade

BASE='/alaz/host/v1'
MODEL='alaz-scripted'
SCENARIOS=('normal','budget-limit','candidate-disconnect','review-revoked')


def scenario_policy(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('unknown_native_gateway_scenario')
    # Synthetic exposure ceiling, NOT permission to spend real provider money.
    attempts = 3 if scenario == 'budget-limit' else 4
    return ExecutionPolicy(MODEL,4,1,131072,32768,attempts*163840,
                           1_000_000,1_000_000,2_000_000)


def expected_scenario(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('unknown_native_gateway_scenario')
    return {
        'normal': ('completed',4,4,2),
        'budget-limit': ('unknown',3,3,1),
        'candidate-disconnect': ('unknown',4,3,1),
        'review-revoked': ('unknown',3,3,0),
    }[scenario]


def digest(blob):return hashlib.sha256(blob).hexdigest()
def file_json(path):return json.loads(path.read_text(encoding='utf-8'))
def safe_json(path,body):
    path.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def wait_file(path,child,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if path.exists():return file_json(path)
        if child.poll() is not None:raise RuntimeError('native_process_exited_before_ready')
        time.sleep(.06)
    raise TimeoutError('native_process_not_ready')

def available_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def http_json(port,token,method,path,body=None,*,timeout=120):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=timeout)
    try:
        raw=_json(body).encode() if body is not None else None
        conn.request(method,path,body=raw,headers={
            'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        res=conn.getresponse()
        data=res.read(131073)
        if len(data)>131072:raise ValueError('oversize_native_host_reply')
        # Origin deliberately sends an empty 401 to wrong credentials.
        # Native HostGate success/error responses remain strict JSON.
        if res.status==401 and not data:
            return res.status,{}
        return res.status,json.loads(data)
    finally:conn.close()

class LocalScriptedOrigin:
    def __init__(self,bearer,marker,scenario='normal'):
        self.bearer=bearer;self.marker=marker
        self.scenario=scenario;self.revoke=None;self.revoked=False
        self.events=[];self.errors=[];self.rejected=0
        self.server=self.thread=None
    def start(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                count=int(self.headers.get('Content-Length','0'))
                if count<=0 or count>150000:
                    self.send_response(413);self.end_headers();return
                data=self.rfile.read(count)
                if (self.path!='/v1/chat/completions' or
                    self.headers.get('Authorization')!='Bearer '+owner.bearer):
                    owner.rejected+=1
                    self.send_response(401);self.end_headers();return
                try:
                    body=json.loads(data)
                    msgs=body['messages']
                    system=msgs[0].get('content','') if msgs else ''
                    if type(system) is not str:system=''
                    if system.startswith('Alaz Dream candidate review v1.'):
                        kind='dream'
                        packet=json.loads(msgs[1]['content'])
                        source=next((s for s in packet['sources']
                                    if s['kind']=='native_final_response'),None)
                        if source is None:raise ValueError('missing native final evidence')
                        snippet=source['text']
                        if owner.marker not in snippet:raise ValueError('wrong preserved source')
                        quote=owner.marker
                        answer={'notes':[{
                          'kind':'caution',
                          'statement':'Distinguish observed evidence from independently verified learning.',
                          'condition':'When an agent says it learned from a completed task.',
                          'citations':[{'evidenceId':source['evidenceId'],'quote':quote}],
                          'relatedCandidateIds':[]}]}
                        output=_json(answer)
                    elif system.startswith('You are answering a sealed held-out classification evaluation.'):
                        req=json.loads(msgs[1]['content'])
                        kind='candidate' if req.get('lesson') is not None else 'baseline'
                        label=('RED','AMBER','GREEN')
                        output=_json({'answers':[{
                           'caseId':case['caseId'],
                           'answer':(label[i%3] if kind=='candidate' or i>=4 else 'WRONG')
                        } for i,case in enumerate(req['cases'])]})
                        if kind=='baseline' and 'lesson' in req and req['lesson'] is not None:
                            raise ValueError('baseline contains lesson')
                        if kind=='candidate' and (
                            'Distinguish observed evidence' not in _json(req['lesson'])):
                            raise ValueError('candidate missing source lesson')
                    else:
                        kind='native_agent'
                        output=(owner.marker+
                          ' — observed evidence is not proof of learning.')
                    owner.events.append({'kind':kind,'digest':digest(data),
                        'bytes':len(data),'messageCount':len(msgs),
                        'containsOracleKey':'oracleKeyHex' in _json(body),
                        'hadTools':bool(body.get('tools'))})
                    if kind=='baseline' and owner.scenario=='review-revoked':
                        if owner.revoke is None:raise RuntimeError('missing_revocation_callback')
                        owner.revoke();owner.revoked=True
                    if kind=='candidate' and owner.scenario=='candidate-disconnect':
                        try:self.connection.shutdown(socket.SHUT_RDWR)
                        except OSError:pass
                        self.connection.close();return
                    packet={'id':'scripted-local-'+kind,'object':'chat.completion',
                        'model':MODEL,'choices':[{'index':0,'finish_reason':'stop',
                          'message':{'role':'assistant','content':output}}],
                        'usage':{'prompt_tokens':96,'completion_tokens':56,
                                 'total_tokens':152}}
                    raw=_json(packet).encode()
                    self.send_response(200)
                    self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(raw)))
                    self.end_headers();self.wfile.write(raw)
                except Exception as exc:
                    owner.errors.append(type(exc).__name__+':'+str(exc)[:90])
                    self.send_response(500);self.end_headers()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        return self.server.server_port
    def close(self):
        if self.server is not None:
            self.server.shutdown();self.server.server_close()
            self.thread.join(timeout=5)

def collect_db(db_path):
    with closing(sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True)) as conn:
        conn.execute('PRAGMA query_only=ON')
        config=conn.execute('PRAGMA integrity_check').fetchone()[0]
        keys={k:[] for k in ('claims','egress','requests','dream','review','trial')}
        for key,val in conn.execute('SELECT key,value FROM state_meta'):
            categories={'claims':'alaz.execution.claim.v1.',
                        'egress':'alaz.execution.egress.v1.',
                        'requests':'alaz.evidence.request.v1.',
                        'dream':'alaz.dream.candidates.v1.',
                        'review':'alaz.dream.review.v1.',
                        'trial':'alaz.dream.trial.v1.'}
            for name,prefix in categories.items():
                if key.startswith(prefix):
                    keys[name].append(_load(val,65536))
        admissions=conn.execute('SELECT count(*) FROM session_admissions').fetchone()[0]
        return keys,admissions,config

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',choices=SCENARIOS,default='normal')
    parser.add_argument('--source-workspace',required=True,type=Path)
    parser.add_argument('--python',required=True,type=Path)
    parser.add_argument('--node',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--public-receipt',required=True,type=Path)
    args=parser.parse_args()
    source=pinned_source(ROOT,args.source_workspace)
    out=args.output.absolute()
    source_runtime=(args.source_workspace/'runtime').resolve()
    public_root=(ROOT/'evidence/d2b2-gateway-af21').resolve()
    target=args.public_receipt.resolve(strict=False)
    if (out.exists() or not out.is_relative_to(source_runtime) or
        out==source_runtime or not args.python.is_file() or
        not args.python.resolve().is_relative_to(source_runtime) or
        not args.node.is_file() or target.exists() or
        target.parent!=public_root or not public_root.is_dir()):
        raise ValueError('native_source_runtime_or_output_precondition_failed')
    out.mkdir(mode=0o700)
    report={'scenario':args.scenario,'result':'FAIL','errors':[],
       'scope':'actual pinned Hermes Gateway+SessionAuthority and original aiohttp broker; scripted localhost origin, no isolated Docker read or real model',
       'sourcePin':'eb75627faf532fa6ffbdae59a0d14b0b385fc780',
       'nativeHermesGateway':False,'originalAiohttpBroker':False,
       'nodeVersion':'26.7.0','scriptedLocalOrigin':True,
       'isolatedToolExecuted':False,'newModelInferenceVerified':False,
       'paidCalls':0,'independentSkillTransferVerified':False,
       'activeMemoryChanged':False,'runtimeDepsInstalledSystemWide':False}
    broker=gateway=None;origin=None;broker_temp=None;files=[];start=time.monotonic()
    try:
        # The source-lock records pin source modules; an upstream edit refuses.
        lock=file_json(ROOT/'config/host-gate/source-lock.json')
        for entry in lock['files']:
            assert digest((source/entry['path']).read_bytes())==entry['sha256']
        report['lockedHostModules']=len(lock['files'])
        for name in ('profile','home','temp','locks','tools','xdg-state',
                     'xdg-data','xdg-config','xdg-cache'):
            (out/name).mkdir(mode=0o700)
        marker='ALAZ_GATEWAY_DREAM_'+secrets.token_hex(10)
        nonce=secrets.token_hex(16)
        token=secrets.token_hex(32)
        sdk=secrets.token_hex(32)
        signing=secrets.token_hex(32)
        origin_secret=secrets.token_hex(32)
        assert len({token,sdk,signing,origin_secret})==4
        origin=LocalScriptedOrigin(origin_secret,marker,args.scenario)
        origin_port=origin.start()
        # NEVER put the credential for upstream provider into Gateway config.
        policy=scenario_policy(args.scenario)
        expected_state,expected_calls,expected_responses,expected_arms=expected_scenario(args.scenario)
        report['testBudget']={'tokensPerReservation':policy.tokens_per_attempt,
            'tokenExposureLimit':policy.total_token_limit,'maxProviderCalls':4,
            'reservedExposureNotMeasuredTokens':True}
        measured=[ROOT/'scripts/qa/native_d2b2_full_gateway.py',
                  ROOT/'scripts/qa/d2b2_gateway_task_client.mjs',
                  ROOT/'scripts/native_gateway_worker.py',
                  ROOT/'scripts/run_provider_broker.py']
        measured+=sorted((ROOT/'packages/claw-hermes').glob('*.py'))
        source_hashes={str(p.relative_to(ROOT)).replace(chr(92),'/'):digest(p.read_bytes()) for p in measured}
        report['programSha256']=source_hashes
        report['pythonVersion']=sys.version.split()[0]
        report['nodeVersion']=subprocess.check_output([str(args.node),'--version'],text=True).strip()

        preliminary=LocalRecoveryContext(out/'profile',token,1,
                                          'boot-before-epoch')
        private=BrokerConfig('http://127.0.0.1:'+str(origin_port)+'/v1',
             MODEL,origin_secret,signing,str(out/'profile/state.db'),
             preliminary.scope,preliminary.binding,policy.fingerprint)
        broker_cfg=out/'broker-private.json'
        safe_json(broker_cfg,asdict(private));broker_cfg.chmod(0o600)
        path=os.environ['PATH']
        env={'PATH':path,'HOME':str(out/'home'),
            'HERMES_HOME':str(out/'profile'),
            'HERMES_RUNTIME_DIR':str(out/'tools'),
            'HERMES_GATEWAY_LOCK_DIR':str(out/'locks'),
            'TMPDIR':str(out/'temp'),
            'PYTHONDONTWRITEBYTECODE':'1',
            'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8',
            'OPENAI_API_KEY':sdk,
            'NO_PROXY':'127.0.0.1,localhost',
            'AWS_EC2_METADATA_DISABLED':'true',
            'ALAZ_PROBE_PRELOAD_OPENAI':'1',
            'TERM':'dumb','NO_COLOR':'1','LANG':'C.UTF-8',
            'XDG_DATA_HOME':str(out/'xdg-data'),
            'XDG_CONFIG_HOME':str(out/'xdg-config'),
            'XDG_STATE_HOME':str(out/'xdg-state')}
        broker_env={k:env[k] for k in ('PATH','HOME','TMPDIR','LANG',
                    'PYTHONDONTWRITEBYTECODE','PYTHONUNBUFFERED')}
        # The broker must be a distinct OS process and use the production
        # aiohttp _upstream, not the stdlib test override from prior acceptance.
        # Linux AF_UNIX sockaddr path has a hard length limit. Keep the
        # broker socket in a fresh, separately owned /tmp directory, not
        # beneath the long source-workspace/runtime hierarchy.
        broker_temp=tempfile.TemporaryDirectory(prefix='alaz-gw-broker-')
        broker_output=Path(broker_temp.name)/'broker'
        assert len(str(broker_output/'egress.sock').encode())<=100
        bstdout=(out/'broker-stdout.log').open('wb')
        bstderr=(out/'broker-stderr.log').open('wb')
        files.extend([bstdout,bstderr])
        broker=subprocess.Popen([str(args.python),'-I','-B',
               str(ROOT/'scripts/run_provider_broker.py'),
               '--config',str(broker_cfg),'--output',str(broker_output)],
               cwd=out,env=broker_env,stdin=subprocess.DEVNULL,
               stdout=bstdout,stderr=bstderr,start_new_session=True)
        ready=wait_file(broker_output/'ready.json',broker,30)
        assert ready['pid']==broker.pid and ready['backend']=='linux_unix_credential_broker'
        report['originalAiohttpBroker']=True
        report['brokerSeparatePid']=broker.pid!=os.getpid()
        sock_path=ready['socketPath']
        assert Path(sock_path).exists()
        link={'socket_path':sock_path,'broker_id':ready['brokerId'],
              'route_fingerprint':ready['routeFingerprint'],
              'signing_key':signing}
        api_port=available_port()
        # No Docker config and no invocation of file tools: only no-tool agent
        # terminal completion + Dream reflection and D2B2 paired evaluation.
        protected=out/'allowed.txt'
        protected.write_text('ALAZ test-only allowed reading sentinel\n')
        host={'allowed_models':[MODEL],'max_issued':4,
              'max_dispatches':1,'validity_seconds':300}
        execution={'policy':asdict(policy),'provider_bearer':sdk,
                   'provider_broker':link,'allowed_read_files':[str(protected)],
                   'record_request_view':True}
        plugin_settings={
            'policy':host,'execution':execution,
            'dream':{'enabled':True,'output_tokens':512},
            'dream_review':{'enabled':True,'max_events':8},
            'dream_trial':{'enabled':True,'max_cases':12,'output_tokens':256}}
        profile={
          'model':{'provider':'custom',
              'base_url':'http://127.0.0.1:'+str(api_port)+'/alaz/provider/v1',
              'default':MODEL,'context_length':163840,'streaming':False,
              'api_key':sdk},
          'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1',
                                   'port':api_port,'key':token}},
          'platform_toolsets':{'api_server':['file']},
          'agent':{'max_turns':3,'api_max_retries':0},
          'gateway':{'multiplex_profiles':False,'loop_watchdog':False,
                     'api_server':{'max_concurrent_runs':1}},
          'updates':{'check':False},
          'plugins':{'enabled':['alaz-host-gate'],
                     'disabled':['hermes-achievements','kanban'],
                     'auto_update_check_hours':0,
                     'entries':{'alaz-host-gate':{'allow_tool_override':True,
                                                'settings':plugin_settings}}},
          'auxiliary':{'title_generation':{'enabled':False}},
          'security':{'allow_lazy_installs':False},
          'memory':{'provider':'none'},
          'checkpoints':{'enabled':False},
          'sessions':{'auto_archive':False,'auto_prune':False},
          'approvals':{'mode':'manual'},
          'terminal':{'backend':'local','cwd':str(out)},
          'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
        assert origin_secret not in _json(profile)
        safe_json(out/'profile/config.yaml',profile)
        sentinels=[]
        for folder in ('memories','skills'):
            dest=out/'profile'/folder/'operator-sentinel.txt'
            dest.parent.mkdir(exist_ok=True)
            dest.write_text('Alaz test operator sentinel - do not change.\n',encoding='utf-8')
            sentinels.append((dest,digest(dest.read_bytes())))
        report['plugin']=install_probe_plugin(out/'profile',host)
        for wrong in (token,sdk,signing):
            status,_=http_json(origin_port,wrong,'POST','/v1/chat/completions',{})
            assert status==401
        assert origin.rejected==3
        cstdout=(out/'gateway-stdout.log').open('wb')
        cstderr=(out/'gateway-stderr.log').open('wb')
        files.extend([cstdout,cstderr])
        gateway=subprocess.Popen([str(args.python),'-I','-B',
            str(ROOT/'scripts/native_gateway_worker.py'),
            str(source),str(out),nonce],cwd=out,env=env,
            stdin=subprocess.DEVNULL,stdout=cstdout,stderr=cstderr,
            start_new_session=True)
        gready=wait_file(out/'ready.json',gateway,180)
        assert gready['pid']==gateway.pid and gready['state']=='ready'
        assert gready['profile_bound'] and gready['api_port']==api_port
        report['nativeHermesGateway']=True
        report['gateway']={'pidSeparate':gateway.pid!=broker.pid,
             'apiHost':gready['api_host'],'versionEpoch':gready['epoch'],
             'sourceReady':True,'nativeApiAdapter':gready['adapter'],
             'aiohttpVersion':gready['aiohttp_version']}
        task_private=out/'task-private.json'
        safe_json(task_private,{'baseUrl':'http://127.0.0.1:'+str(api_port),
            'token':token,'requestId':secrets.token_hex(16),'marker':marker})
        task_result=out/'task-result.json'
        node=subprocess.run([str(args.node),
          str(ROOT/'scripts/qa/d2b2_gateway_task_client.mjs'),
          str(task_private),str(task_result)],cwd=out,env=env,
          capture_output=True,timeout=105)
        (out/'node-task-stdout.log').write_bytes(node.stdout)
        (out/'node-task-stderr.log').write_bytes(node.stderr)
        assert node.returncode==0 and task_result.is_file(), \
               'native no-tool task failed; inspect private node logs'
        task=file_json(task_result)
        assert task['status']=='completed' and marker in task['observed']['output']
        report['task']={'nativeTerminalVerified':True,
                        'runIdSha256':digest(task['runId'].encode()),
                        'providerWasToolFree':True}
        sources=[{'body':task['originalBody'],
                  'idempotency_key':task['idempotencyKey'],
                  'observed':task['observed']}]
        status,dream=http_json(api_port,token,'POST',BASE+'/dream',
                               {'sources':sources})
        assert status==200 and dream['state']=='completed', \
               ('dream_refused',status,dream.get('error'))
        assert len(dream['candidates'])==1
        note=dream['candidates'][0]
        assert marker in note['citations'][0]['quote']
        report['dream']={'state':'completed','candidateCount':1,
                         'sourceRefCount':len(dream['sourceRefs']),
                         'quoteFromActualNativeFinal':True}
        status,review=http_json(api_port,token,'GET',
                            BASE+'/dream/review/'+dream['batchId'])
        assert status==200 and review['reviewedCount']==0
        decision={'batchId':dream['batchId'],
                  'candidateId':note['candidateId'],
                  'decision':'accept_for_testing',
                  'reasonCode':'evidence_sufficient_to_test',
                  'expectedRevision':review['revision']}
        status,review=http_json(api_port,token,'POST',BASE+'/dream/review',
                                decision)
        assert status==200 and review['acceptedForIndependentEvaluation']==[note['candidateId']]
        labels=('RED','AMBER','GREEN')
        training=[f'Example {i} demonstrates imaginary machine triage {i*7}'
                  for i in range(4)]
        cases=[{'caseId':f'case_{i:02d}',
                'prompt':f'Classify synthetic probe {i} reading {13+i*9}. '
                         'Output RED, AMBER or GREEN.'} for i in range(12)]
        truth={'version':1,'answers':[
            {'caseId':case['caseId'],'answer':labels[i%3]}
            for i,case in enumerate(cases)]}
        oracle_key=secrets.token_hex(32)
        plan=seal_plan(review,note['candidateId'],'synthetic_triage',
                       training,cases,truth,oracle_key)
        assert 'answer' not in _json(plan) and oracle_key not in _json(plan)
        if args.scenario=='review-revoked':
            def revoke_review():
                code,latest=http_json(api_port,token,'GET',BASE+'/dream/review/'+dream['batchId'])
                assert code==200
                code,changed=http_json(api_port,token,'POST',BASE+'/dream/review',
                    decision|{'decision':'defer','reasonCode':'operator_deferred',
                              'expectedRevision':latest['revision']})
                assert code==200 and not changed['acceptedForIndependentEvaluation']
            origin.revoke=revoke_review
        status,trial=http_json(api_port,token,'POST',BASE+'/dream/trial',
                               {'plan':plan},timeout=125)
        assert status==(200 if expected_state=='completed' else 202) and trial['state']==expected_state,                ('trial_failed',status,trial.get('error'),trial.get('reason'))
        assert [r['arm'] for r in trial['results']]==['baseline','candidate'][:expected_arms]
        status,trial_get=http_json(api_port,token,'GET',BASE+'/dream/trial/'+plan['planId'])
        assert status==200 and trial_get['state']==expected_state and trial_get['results']==trial['results']
        before_repeat=len(origin.events)
        status,replayed=http_json(api_port,token,'POST',BASE+'/dream/trial',{'plan':plan})
        if args.scenario=='review-revoked':
            assert status==409 and not replayed.get('retryAllowed')
            assert origin.revoked
        else:
            assert status==200 if expected_state=='completed' else status==202
            assert replayed['replayed'] and replayed['newProviderReservations']==0
        assert len(origin.events)==before_repeat
        report['trial']={'state':trial['state'],
            'arms':[r['arm'] for r in trial['results']],
            'replayAddedReservations':0,'realModelInferenceVerified':False,
            'reason':trial.get('reason'),'duplicateRequestStatus':status}
        if args.scenario=='budget-limit':
            assert trial['reason']=='token_exposure_limit'
        if args.scenario=='normal':
            code,current_review=http_json(api_port,token,'GET',BASE+'/dream/review/'+dream['batchId'])
            assert code==200
            result=grade(plan,current_review,truth,trial_get['results'][0]['answers'],
                         trial_get['results'][1]['answers'],oracle_key)
            assert result['baselineCorrect']==8 and result['candidateCorrect']==12
            assert not result['independentOutcomeVerified'] and not result['skillTransferVerified']
            report['trial']['localScore']={'baselineCorrect':8,'candidateCorrect':12,
                                           'scriptedNotLearning':True}
        assert not origin.errors
        # Confidential origin content is not written to the public receipt.
        kinds=[x['kind'] for x in origin.events]
        assert kinds==['native_agent','dream','baseline','candidate'][:expected_calls],kinds
        assert not any(x['containsOracleKey'] for x in origin.events)
        report['origin']={'accepted':len(kinds),'kinds':kinds,
             'rejectedWrongCredentials':origin.rejected,
             'requestSha256':[x['digest'] for x in origin.events],
             'requestBytes':[x['bytes'] for x in origin.events]}
        report['modelInferenceCalls']=0
        report['paidCalls']=0
        report['humanReviewVerified']=False
        report['skillsOrMemoryPromotion']=False
        # Gracefully stop Gateway before reading a settled native DB snapshot.
        safe_json(out/'stop.json',{'nonce':nonce,'pid':gateway.pid})
        gateway.wait(timeout=45)
        shutdown=file_json(out/'shutdown.json')
        assert gateway.returncode==0 and shutdown['native_result'] and \
               shutdown['nonloopback_attempts_blocked']==0
        report['gateway']['exitCode']=gateway.returncode
        report['gateway']['cleanShutdown']=True
        report['gateway']['nonLoopbackAttemptsBlocked']=shutdown['nonloopback_attempts_blocked']
        records,admissions,integrity=collect_db(out/'profile/state.db')
        assert integrity=='ok' and admissions==1
        claims=records['claims']
        providers=[x for x in claims if x['kind']=='provider']
        tool_claims=[x for x in claims if x['kind']!='provider']
        assert not tool_claims and len(providers)==expected_calls
        assert len(records['requests'])==len(records['egress'])==expected_calls
        hashes={x['digest'] for x in origin.events}
        assert all(x['requestDigest'] in hashes for x in records['requests'])
        assert sum(x['state']=='broker_response_observed' for x in records['requests'])==expected_responses
        assert len(records['dream'])==len(records['review'])==len(records['trial'])==1
        report['provenance']={
            'nativeAdmissions':admissions,'providerReservations':len(providers),
            'nativeToolCalls':len(tool_claims),
            'egressGrants':len(records['egress']),
            'requestViewRows':len(records['requests']),
            'originRawByteMatches':sum(x['requestDigest'] in hashes for x in records['requests']),
            'brokerResponsesObserved':sum(x['state']=='broker_response_observed' for x in records['requests']),
            'd1CandidateRows':len(records['dream']),
            'd2aReviewRows':len(records['review']),
            'd2b2TrialRows':len(records['trial']),
            'canonicalDBIntegrity':integrity}
        assert not (out/'profile'/'MEMORY.md').exists()
        assert all(digest(p.read_bytes())==h for p,h in sentinels)
        report['operatorSentinelsUnchanged']=True
        report['codeDrift']=[n for n,h in source_hashes.items() if digest((ROOT/n).read_bytes())!=h]
        assert not report['codeDrift']
    except Exception as exc:
        report['errors'].append(type(exc).__name__+':'+str(exc)[:210])
        report['errorType']=type(exc).__name__
        (out/'private-trace.txt').write_text(traceback.format_exc(limit=5),
                                             encoding='utf-8')
    finally:
        if gateway is not None and gateway.poll() is None:
            try:
                safe_json(out/'stop.json',{'nonce':nonce,'pid':gateway.pid})
                gateway.wait(timeout=35)
                report['gatewayForced']=False
            except Exception:
                if gateway.poll() is None:
                    os.killpg(gateway.pid,signal.SIGKILL)
                    gateway.wait(timeout=10)
                    report['gatewayForced']=True
        if broker is not None:
            if broker.poll() is None:
                broker.terminate()
            try:broker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if broker.poll() is None:
                    os.killpg(broker.pid,signal.SIGKILL)
                    broker.wait(timeout=10)
                    report['brokerForced']=True
            report['brokerExit']=broker.returncode
            path=broker_output/'shutdown.json'
            if path.is_file():
                closed=file_json(path)
                report['broker']={
                    'separatePid':broker.pid!=(gateway.pid if gateway else os.getpid()),
                    'exitCode':broker.returncode,
                    'socketRemoved':closed.get('socketRemoved'),
                    'activeRequests':closed.get('activeRequests'),
                    'counters':closed.get('counters')}
        for item in files:item.close()
        if origin is not None:origin.close()
        if broker_temp is not None:broker_temp.cleanup()
        report['elapsedSeconds']=round(time.monotonic()-start,3)
    observed_expected=expected_scenario(args.scenario)
    ok=(not report['errors'] and
         report.get('nativeHermesGateway') and
         report.get('originalAiohttpBroker') and
         report.get('gateway',{}).get('cleanShutdown') and
         report.get('broker',{}).get('exitCode')==0 and
         report.get('broker',{}).get('socketRemoved') is True and
         report.get('broker',{}).get('activeRequests')==0 and
         report.get('provenance',{}).get('originRawByteMatches')==observed_expected[1] and
         report.get('provenance',{}).get('brokerResponsesObserved')==observed_expected[2] and
         report.get('trial',{}).get('state')==observed_expected[0] and
         len(report.get('trial',{}).get('arms',[]))==observed_expected[3])
    report['result']='PASS' if ok else 'FAIL'
    safe_json(target,report)
    print(_json({'result':report['result'],'nativeGateway':report['nativeHermesGateway'],
                 'originalAiohttpBroker':report['originalAiohttpBroker'],
                 'originKinds':report.get('origin',{}).get('kinds',[]),
                 'trial':report.get('trial',{}),
                 'broker':report.get('broker',{}),
                 'errors':report['errors']}),flush=True)
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
