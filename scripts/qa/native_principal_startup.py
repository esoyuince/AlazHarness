"""Unprivileged actual broker CLI smoke; not positive split-host-UID acceptance.

Only fresh owned temporary files, local AF_UNIX ping and intentional admission
refusals. No account changes, mount, elevation, HTTP send, Gateway or model.
"""
from __future__ import annotations
import argparse
import asyncio
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerClient
from execution_budget import ExecutionDenied

SOURCES=('scripts/run_provider_broker.py','packages/claw-hermes/provider_broker.py',
         'packages/claw-hermes/provider_egress.py','packages/claw-hermes/host_principal.py',
         'scripts/qa/native_principal_startup.py')

def hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def configuration(base,principal=None):
    value={'upstream_base_url':'http://127.0.0.1:1/v1','model':'owned-no-model',
           'upstream_bearer':'p'*48,'signing_key':'b'*64,'state_db':str(base/'state.db'),
           'scope':'c'*64,'binding':'d'*64,'policy_fingerprint':'e'*64}
    if principal is not None:value['principal_contract']=principal
    return value

def write_private(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream);stream.write('\n')
    path.chmod(0o600)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if (sys.platform!='linux' or os.getuid()==0 or output.exists() or output.is_symlink()
        or output.parent!=(ROOT/'evidence/d3b-principal-startup-20oct').resolve()):
        raise ValueError('unprivileged_owned_output_required')
    before=hashes();checks={};error=None;processes=[];forced=False
    uid=os.getuid();gid=os.getgid();ns=os.readlink('/proc/self/ns/user')
    alternate=uid+10000 if uid<2000000000 else uid-1
    with tempfile.TemporaryDirectory(prefix='alaz-broker-startup-') as temporary:
        base=Path(temporary);cfg=base/'config.json';out=base/'legacy'
        write_private(cfg,configuration(base));config_hash=hashlib.sha256(cfg.read_bytes()).hexdigest()
        env={'PATH':'/usr/bin:/bin','HOME':str(base),'PYTHONNOUSERSITE':'1'}
        command=[sys.executable,'-I','-B',str(ROOT/'scripts/run_provider_broker.py'),
                 '--config',str(cfg),'--output',str(out)]
        with (base/'stdout.txt').open('wb') as stdout,(base/'stderr.txt').open('wb') as stderr:
            process=subprocess.Popen(command,cwd=base,env=env,stdout=stdout,stderr=stderr,
                                     start_new_session=True)
            processes.append(process)
            try:
                deadline=time.monotonic()+20
                while not (out/'ready.json').exists():
                    if process.poll() is not None:raise RuntimeError('broker_exited_before_ready')
                    if time.monotonic()>deadline:raise TimeoutError('broker_ready_timeout')
                    time.sleep(.05)
                ready=json.loads((out/'ready.json').read_text())
                checks['ready_matches_owned_pid']=ready['pid']==process.pid
                checks['legacy_directory_0700']=stat.S_IMODE(out.stat().st_mode)==0o700
                checks['legacy_socket_0600']=stat.S_IMODE((out/'egress.sock').stat().st_mode)==0o600
                checks['private_complete_ready_receipt']=stat.S_IMODE((out/'ready.json').stat().st_mode)==0o600
                settings={'socket_path':ready['socketPath'],'broker_id':ready['brokerId'],
                          'route_fingerprint':ready['routeFingerprint'],'signing_key':'b'*64}
                checks['actual_client_ping']=asyncio.run(ProviderBrokerClient(settings).ready()) is True
                invalid={'version':1,'enabled':True,'gatewayUid':alternate,'brokerUid':uid,
                         'socketGroupGid':gid,'hostUserNamespace':ns}
                try:asyncio.run(ProviderBrokerClient(settings|{'principal_contract':invalid}).ready())
                except ExecutionDenied as exc:
                    checks['wrong_local_principal_refused']=str(exc)=='broker_gateway_principal_refused'
                else:checks['wrong_local_principal_refused']=False
                demanded={'version':1,'enabled':True,'gatewayUid':uid,'brokerUid':alternate,
                          'socketGroupGid':gid,'hostUserNamespace':ns}
                for label,prepared in (('prepared',True),('missing',False)):
                    denied=base/('denied-'+label)
                    if prepared:denied.mkdir(mode=0o710)
                    denied_config=base/('denied-'+label+'.json')
                    write_private(denied_config,configuration(base,demanded))
                    r=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/run_provider_broker.py'),
                                      '--config',str(denied_config),'--output',str(denied)],
                                     cwd=base,env=env,capture_output=True,text=True,timeout=15)
                    checks[label+'_wrong_broker_refused']=r.returncode==2
                    checks[label+'_no_socket_or_receipt']=not (denied/'egress.sock').exists() and not (denied/'ready.json').exists()
                    checks[label+'_no_provisioning']=(not denied.exists()) if not prepared else (
                        denied.stat().st_uid==uid and stat.S_IMODE(denied.stat().st_mode)==0o710
                        and not any(denied.iterdir()))
            except Exception as exc:
                error=type(exc).__name__
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                    try:process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        forced=True;process.kill();process.wait(timeout=5)
        checks['owned_process_exited_cleanly']=process.returncode==0 and not forced
        shutdown_path=out/'shutdown.json'
        if shutdown_path.is_file():
            shutdown=json.loads(shutdown_path.read_text())
            checks['shutdown_matches_owned_pid']=shutdown.get('pid')==process.pid
            checks['socket_removed']=shutdown.get('socketRemoved') is True and not (out/'egress.sock').exists()
            checks['no_active_requests']=shutdown.get('activeRequests')==0
            counts=shutdown.get('counters',{})
            checks['exactly_one_ping']=counts.get('pings')==1
            checks['zero_provider_attempts']=counts.get('physicalAttempts')==0
            checks['private_shutdown_receipt']=stat.S_IMODE(shutdown_path.stat().st_mode)==0o600
        else:
            checks['shutdown_present']=False
        checks['config_unchanged']=hashlib.sha256(cfg.read_bytes()).hexdigest()==config_hash
        diagnostics=(base/'stderr.txt').read_text(errors='replace')[-2500:] if error else ''
        checks['no_staging_files']=not out.exists() or not any(p.name.startswith('.') for p in out.iterdir())
    checks['temporary_root_removed']=not base.exists()
    after=hashes();checks['source_unchanged']=before==after
    report={'result':'PASS_SCOPED' if not error and checks and all(checks.values()) else 'FAIL',
            'scope':'actual_legacy_broker_cli_and_wrong_principal_denial_not_two_host_uids',
            'observedAt':datetime.datetime.now().astimezone().isoformat(),
            'uid':uid,'gid':gid,'userNamespace':ns,'checks':checks,'checkCount':len(checks),
            'sourceSha256':before,'sourceAfterSha256':after,'errorType':error,
            'diagnostics':diagnostics,'forcedCleanup':forced,
            'realModelCalls':0,'realGatewayTested':False,'separateHostUidVerified':False,
            'ipcV2ProjectionTested':False,'fullD3BAccepted':False}
    with output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({'result':report['result'],'checks':report['checkCount'],
                      'failedChecks':[k for k,v in checks.items() if not v],
                      'errorType':error,'separateHostUidVerified':False,'realModelCalls':0}))
    return 0 if report['result']=='PASS_SCOPED' else 1

if __name__=='__main__':raise SystemExit(main())
