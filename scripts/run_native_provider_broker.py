"""Real Linux Gateway+Unix credential broker+native isolated read; scripted authenticated origin.
No personal key, real model inference, install, image pull, firewall change or second DB.
"""
from __future__ import annotations
import argparse
import asyncio
import io
from contextlib import closing
from dataclasses import asdict
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'));sys.path.insert(0,str(ROOT/'scripts'))
from execution_budget import ExecutionPolicy
from recovery_inspector import LocalRecoveryContext
from isolated_tool import ToolSandboxPolicy
from run_native_isolated_read import read,digest,stamp,wait_file,snapshot,PIN
from run_native_host_gate import install_probe_plugin
from execution_model_fixture import ExecutionModel
from provider_egress import BrokerConfig,hashed,signed
from provider_broker import ProviderBrokerClient

CASES=('normal','missing-broker','stale-broker','provider-limit','upstream-disconnect')

class AuthenticatedModel(ExecutionModel):
    def __init__(self,fixture,marker,scenario,secret,target,*,read_limit=None):
        super().__init__(fixture,marker,'normal',target,read_limit=read_limit);original=self.server.RequestHandlerClass;owner=self
        self.rejected=0;self.accepted=0;self.received_payloads=[]
        class Guarded(original):
            def do_POST(self):
                if self.headers.get('Authorization')!='Bearer '+secret:
                    self.rfile.read(min(int(self.headers.get('Content-Length','0')),2000000))
                    owner.rejected+=1;self.send({'error':'unauthorized'},401);return
                owner.accepted+=1
                if scenario=='upstream-disconnect':
                    self.rfile.read(min(int(self.headers.get('Content-Length','0')),2000000))
                    owner.calls.append({'path':self.path,'authenticated':True,'response':'disconnected'})
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                raw=self.rfile.read(min(int(self.headers.get('Content-Length','0')),2000000))
                owner.received_payloads.append(json.loads(raw));self.rfile=io.BytesIO(raw)
                return super().do_POST()
        self.server.RequestHandlerClass=Guarded


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','python','node','output'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--image',required=True);p.add_argument('--scenario',choices=CASES,required=True)
    p.add_argument('--record-source',action='store_true',help='Opt in to trusted input capture; not model visibility')
    p.add_argument('--fixture-lines',type=int,default=2,help='Bounded native pagination fixture, 2..500')
    p.add_argument('--read-limit',type=int,default=None,help='Explicit read_file limit; omitted native default is not assumed')
    a=p.parse_args()
    assert 2 <= a.fixture_lines <= 500
    assert a.read_limit is None or 1 <= a.read_limit <= 1000
    out=a.output.absolute();source=a.source.resolve()
    assert os.name=='posix' and not out.exists() and len(str(out/'broker/egress.sock').encode())<=100
    manifest=read(source/'alaz-source-manifest.json');assert manifest['sourceCommit']==PIN
    assert all(digest(source/n)==h for n,h in manifest['files'].items())
    programs={p.relative_to(ROOT).as_posix():digest(p) for folder in ('packages','scripts','config') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.mjs','.ts','.json')}
    out.mkdir(parents=True,mode=0o700)
    for name in ('home','profile','temp','locks','tools','capsules','receipts','xdg-data','xdg-config','xdg-cache'):(out/name).mkdir()
    token=secrets.token_hex(32);sdk=secrets.token_hex(32);signer=secrets.token_hex(32);origin_secret=secrets.token_hex(32);nonce=secrets.token_hex(16)
    assert len({token,sdk,signer,origin_secret})==4
    marker='BROKER_NATIVE_'+secrets.token_hex(12);fixture=out/'input.txt';fixture.write_bytes((marker+'\n'+''.join('line '+str(i)+' ışık\n' for i in range(2,a.fixture_lines+1))).encode('utf-8'))
    provider=AuthenticatedModel(fixture,marker,a.scenario,origin_secret,out/'must-not-exist.txt',read_limit=a.read_limit);provider.start()
    policy=ExecutionPolicy('alaz-scripted',1 if a.scenario in ('provider-limit','upstream-disconnect') else 3,1,131072,32768,491520,1000000,1000000,2000000)
    context=LocalRecoveryContext(out/'profile',token,1,'unused-before-boot')
    private=BrokerConfig(provider.base_url,'alaz-scripted',origin_secret,signer,str(out/'profile/state.db'),context.scope,context.binding,policy.fingerprint)
    cfgfile=out/'broker-private.json';cfgfile.write_text(json.dumps(asdict(private)));cfgfile.chmod(0o600)
    env={'PATH':'/usr/bin:/bin','HOME':str(out/'home'),'HERMES_HOME':str(out/'profile'),'HERMES_RUNTIME_DIR':str(out/'tools'),
         'HERMES_GATEWAY_LOCK_DIR':str(out/'locks'),'TMPDIR':str(out/'temp'),'HERMES_DISABLE_LAZY_INSTALLS':'1',
         'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8','OPENAI_API_KEY':sdk,
         'NO_PROXY':'127.0.0.1,localhost','AWS_EC2_METADATA_DISABLED':'true','ALAZ_PROBE_PRELOAD_OPENAI':'1',
         'TERM':'dumb','NO_COLOR':'1','LANG':'C.UTF-8','XDG_DATA_HOME':str(out/'xdg-data'),'XDG_CONFIG_HOME':str(out/'xdg-config'),'XDG_CACHE_HOME':str(out/'xdg-cache')}
    broker_env={k:env[k] for k in ('PATH','HOME','TMPDIR','LANG','PYTHONDONTWRITEBYTECODE','PYTHONUNBUFFERED')}
    # Toxic parent proxy demonstrates that neither broker nor Gateway inherits it.
    report={'scenario':a.scenario,'source_commit':PIN,'errors':[],'programs':programs,'inference_calls':0,'paid_calls':0,
            'scope':'native Gateway/owner/Unix broker/isolated read, authenticated scripted origin; not general OS egress isolation'}
    broker=child=None;files=[];start=time.monotonic();bstamp=ctstamp=None
    try:
        bo=(out/'broker-stdout.txt').open('wb');be=(out/'broker-stderr.txt').open('wb');files += [bo,be]
        broker=subprocess.Popen([str(a.python),'-I','-B',str(ROOT/'scripts/run_provider_broker.py'),'--config',str(cfgfile),'--output',str(out/'broker')],
          cwd=out,env=broker_env,stdin=subprocess.DEVNULL,stdout=bo,stderr=be,start_new_session=True)
        bstamp=stamp(broker.pid);wait_file(out/'broker/ready.json',broker,20);br=read(out/'broker/ready.json')
        assert br['pid']==broker.pid and stamp(broker.pid)==bstamp;report['broker_ready']=br
        link={'socket_path':br['socketPath'],'broker_id':br['brokerId'],'route_fingerprint':br['routeFingerprint'],'signing_key':signer}
        if a.scenario=='missing-broker':link['socket_path']=str(out/'absent/egress.sock')
        if a.scenario=='stale-broker':link['broker_id']='0'*32
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        execution={'policy':asdict(policy),'provider_bearer':sdk,'provider_broker':link,'allowed_read_files':[str(fixture)],
                   'isolated_read':{'capsule_root':str(out/'capsules'),'receipt_root':str(out/'receipts'),
                      'policy':asdict(ToolSandboxPolicy(a.image)),'use_sudo':True}}
        if a.record_source:execution['isolated_read']['record_source']=True
        report['record_source']=a.record_source;report['fixture_lines']=a.fixture_lines;report['read_limit']=a.read_limit
        hp={'allowed_models':['alaz-scripted'],'max_issued':4,'max_dispatches':1,'validity_seconds':300}
        cfg={'model':{'provider':'custom','base_url':f'http://127.0.0.1:{port}/alaz/provider/v1','default':'alaz-scripted','context_length':163840,'streaming':False,'api_key':sdk},
             'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},'platform_toolsets':{'api_server':['file']},
             'agent':{'max_turns':3,'api_max_retries':0},'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
             'updates':{'check':False},'plugins':{'enabled':['alaz-host-gate'],'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0,
                'entries':{'alaz-host-gate':{'allow_tool_override':True,'settings':{'policy':hp,'execution':execution}}}},
             'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},'memory':{'provider':'none'},
             'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},'approvals':{'mode':'manual'},
             'terminal':{'backend':'alaz_isolated_read','cwd':'/workspace'},'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
        assert origin_secret not in json.dumps(cfg)+json.dumps(env)
        (out/'profile/config.yaml').write_text(json.dumps(cfg));install_probe_plugin(out/'profile',hp)
        # The actual origin rejects all three non-provider keys before reading a model request.
        rejects=[]
        for wrong in (token,sdk,signer):
            connection=http.client.HTTPConnection('127.0.0.1',provider.server.server_port,timeout=2)
            connection.request('POST','/v1/chat/completions',body='{}',headers={'Authorization':'Bearer '+wrong,'Content-Type':'application/json'})
            response=connection.getresponse();rejects.append(response.status);response.read();connection.close()
        assert rejects==[401,401,401];report['non_provider_credentials_http']=rejects
        co=(out/'gateway-stdout.txt').open('wb');ce=(out/'gateway-stderr.txt').open('wb');files += [co,ce]
        child=subprocess.Popen([str(a.python),'-I','-B',str(ROOT/'scripts/native_gateway_worker.py'),str(source),str(out),nonce],
          cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=co,stderr=ce,start_new_session=True)
        ctstamp=stamp(child.pid);wait_file(out/'ready.json',child,180);ready=read(out/'ready.json')
        assert ready['pid']==child.pid and ready['nonce']==nonce and ready['profile_bound'] and stamp(child.pid)==ctstamp
        report['ready']=ready
        params={'baseUrl':f'http://127.0.0.1:{port}','token':token,'nonce':nonce,'requestId':secrets.token_hex(16),'scenario':a.scenario}
        (out/'client-private.json').write_text(json.dumps(params))
        cli=subprocess.run([str(a.node),str(ROOT/'scripts/native_provider_broker_client.mjs'),str(out/'client-private.json'),str(out/'client-result.json')],
            env=env,cwd=out,capture_output=True,timeout=90)
        (out/'client-stderr.txt').write_bytes(cli.stderr);report['client_exit']=cli.returncode
        assert cli.returncode==0,'native client failed'
        result=read(out/'client-result.json');assert result['nonce']==nonce;report['client']=result
        (out/'stop.json').write_text(json.dumps({'nonce':nonce,'pid':child.pid}));child.wait(timeout=40)
        shutdown=read(out/'shutdown.json');assert child.returncode==0 and shutdown['native_result'] is True and shutdown['nonloopback_attempts_blocked']==0
        report['shutdown']=shutdown
        data=snapshot(out/'profile')
        with closing(sqlite3.connect((out/'profile/state.db').as_uri()+'?mode=ro',uri=True)) as db:
            db.execute('PRAGMA query_only=ON');grants=[json.loads(r[0]) for r in db.execute("SELECT value FROM state_meta WHERE key LIKE 'alaz.execution.egress.v1.%'")]
        if a.scenario=='normal':
            # Explicit test replay of the exact observed provider message/grant;
            # the production client never retries it. Do not create a new claim.
            grant={k:v for k,v in grants[0].items() if k!='digest'}
            payload=next(body for body in provider.received_payloads if hashed(body)==grant['fingerprint'])
            envelope=signed({'version':1,'operation':'send','grant':grant,'payload':payload},signer,'request')
            prior=provider.accepted
            try:asyncio.run(ProviderBrokerClient(link)._exchange(envelope,grant['ticket']));raise AssertionError('broker replay accepted')
            except Exception as exc:assert str(exc)=='broker_replay_refused',type(exc).__name__
            assert provider.accepted==prior
            report['explicit_same_grant_replay']={'refused':True,'reason':'broker_replay_refused','extra_origin_requests':0}
        # Close broker only after the native work and its budget writer are closed.
        assert stamp(broker.pid)==bstamp;broker.terminate();broker.wait(timeout=15);assert broker.returncode==0
        end=read(out/'broker/shutdown.json');assert end['pid']==broker.pid and end['brokerId']==br['brokerId'] and end['socketRemoved'] and end['activeRequests']==0
        report['broker_shutdown']=end
        providers=[x for x in data['claims'] if x['kind']=='provider'];tools=[x for x in data['claims'] if x['kind']=='read_file'];messages=[x for x in data['messages'] if x['role']=='tool']
        bindings=[read(p) for p in (out/'receipts').glob('*/bridge-binding.json')]
        report.update(provider_reservations=len(providers),egress_grants=len(grants),tool_reservations=len(tools),origin_accepted=provider.accepted,
                      origin_rejected=provider.rejected,native_admissions=len(data['admissions']),bindings=bindings,integrity=data['integrity'],
                      gateway_upstream_credential_absent=True,distinct_broker_pid=broker.pid!=child.pid)
        assert data['integrity']=='ok' and not provider.errors
        assert end['counters']['physicalAttempts']==provider.accepted==len(grants)==len(providers)
        assert {g['ticket'] for g in grants}=={x['ticket'] for x in providers}
        assert all(g['brokerId']==br['brokerId'] and g['epoch']==ready['epoch'] and g['instance']==ready['instance_id'] for g in grants)
        assert all(b.get('exited') and b.get('removed') for b in bindings)
        if a.scenario in ('missing-broker','stale-broker'):
            assert not providers and not tools and not grants and not data['admissions'] and not provider.accepted and not bindings and 'error' in result
        elif a.scenario=='normal':
            assert len(providers)==2 and len(tools)==1 and len(data['admissions'])==1 and len(messages)==1 and len(bindings)==1
            assert marker in messages[0]['content'] and result['final']['run']['status']=='completed'
            assert all(x['state']=='settled' for x in providers) and bindings[0]['outcome']=='completed'
        elif a.scenario=='provider-limit':
            assert len(providers)==1 and len(tools)==1 and len(data['admissions'])==1 and len(bindings)==1
            assert result['final']['run']['status']!='completed'
        else:
            assert len(providers)==1 and len(grants)==1 and not tools and not bindings and len(data['admissions'])==1
            assert providers[0]['state']=='reserved' and providers[0]['usage'] is None and result['final']['run']['status']!='completed'
        # Canary scan is explicit and bounded, not a general secret scanner.
        for path in list((out/'profile').glob('*.yaml'))+list((out/'capsules').rglob('*'))+[out/'gateway-stdout.txt',out/'gateway-stderr.txt',out/'client-result.json']:
            if path.is_file():assert origin_secret.encode() not in path.read_bytes(),'upstream credential leaked'
    except Exception as exc:report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        if child is not None and child.poll() is None:
            try:
                assert stamp(child.pid)==ctstamp
                (out/'stop.json').write_text(json.dumps({'nonce':nonce,'pid':child.pid}));child.wait(timeout=40)
            except Exception:
                if child.poll() is None and stamp(child.pid)==ctstamp:os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=10);report['forced_gateway_cleanup']=True
        if broker is not None and broker.poll() is None:
            assert stamp(broker.pid)==bstamp;broker.terminate()
            try:broker.wait(timeout=15)
            except subprocess.TimeoutExpired:broker.kill();broker.wait(timeout=5);report['forced_broker_cleanup']=True
        for f in files:f.close()
        provider.close()
    report['gateway_exit']=child.returncode if child else None;report['broker_exit']=broker.returncode if broker else None
    report['source_drift']=[n for n,h in programs.items() if digest(ROOT/n)!=h]
    report['elapsed_seconds']=round(time.monotonic()-start,3)
    report['result']='PASS' if not report['errors'] and not report['source_drift'] and report['gateway_exit']==report['broker_exit']==0 else 'FAIL'
    (out/'broker-native-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('programs','client','ready','shutdown')},indent=2),flush=True)
    return 0 if report['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
