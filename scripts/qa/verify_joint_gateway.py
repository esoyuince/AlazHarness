"""Four real Gateway scenarios with SAME-PID network + credential boundaries.

Controller, scripted origin and production broker stay trusted/host-side.
The controller uses nsenter solely for the Gateway's loopback test API.
No paid model, personal credentials, default runtime activation or main merge.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'))
from native_credential_ext4 import source_files,copy_verified,LINUX,PYTHON,SCENARIOS
PREPARED=LINUX/'source-workspace/runtime/gateway-env-af21/env'
PY_BASE=LINUX/'tools/python/cpython-3.14.3-linux-x86_64-gnu'
NODE=LINUX/'tools/bin/node'
EVIDENCE='d3b-joint-18d3'


def write_new(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def process_start(pid):
    return Path('/proc/'+str(pid)+'/stat').read_text().rsplit(') ',1)[1].split()[19]


def gateway_inside(run_id,scenario):
    import native_d2b2_full_gateway as base
    real_popen=subprocess.Popen;real_run=subprocess.run;real_http=base.http_json
    out=LINUX/'source-workspace/runtime'/('joint-18d3-'+run_id)
    inner=ROOT/'evidence/d2b2-gateway-af21'/('joint-'+run_id+'.json')
    target=ROOT/'evidence'/EVIDENCE/('inside-'+run_id+'.json')
    if out.exists() or inner.exists() or target.exists():raise ValueError('fresh_joint_run_required')
    original_namespace=os.readlink('/proc/self/ns/net')
    owner={'gateway':None,'start':None,'broker':None}
    samples=[];wrapping=[];errors=[];secret_values=[]
    with tempfile.TemporaryDirectory(prefix='alaz-joint-control-') as temporary:
        control=Path(temporary);control.chmod(0o700)
        protected=control/'broker-private.json'
        sockets=control/'sockets';sockets.mkdir(mode=0o700)
        def namespace_prefix():
            proc=owner['gateway']
            if proc is None or proc.poll() is not None or process_start(proc.pid)!=owner['start']:
                raise RuntimeError('joint_gateway_owner_not_live')
            namespace=os.readlink('/proc/'+str(proc.pid)+'/ns/net')
            status={line.split(':',1)[0]:line.split(':',1)[1].strip()
                    for line in Path('/proc/'+str(proc.pid)+'/status').read_text().splitlines() if ':' in line}
            if namespace==original_namespace or status.get('NoNewPrivs')!='1' or status.get('Seccomp')!='2':
                raise RuntimeError('joint_network_boundary_not_observed')
            if any(int(status[k],16)!=0 for k in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')):
                raise RuntimeError('joint_capabilities_not_zero')
            samples.append({'sameGatewayPid':True,'separateNetwork':True,
                            'noNewPrivs':True,'seccomp':True,'zeroCapabilities':True})
            return ['/usr/bin/nsenter','--target',str(proc.pid),'--user','--net','--preserve-credentials','--']
        def launch(command,*a,**kw):
            argv=[str(v) for v in command] if isinstance(command,(list,tuple)) else []
            if str(ROOT/'scripts/run_provider_broker.py') in argv:
                ix=argv.index('--config')+1;src=Path(argv[ix])
                if src!=out/'broker-private.json' or protected.exists():raise ValueError('unexpected_broker_config')
                private=json.loads(src.read_text())
                for key in ('upstream_bearer','signing_key'):
                    if type(private.get(key)) is str:secret_values.append(private[key])
                src.rename(protected);protected.chmod(0o600);argv[ix]=str(protected)
                proc=real_popen(argv,*a,**kw);owner['broker']=proc
                if os.readlink('/proc/'+str(proc.pid)+'/ns/net')!=original_namespace:
                    raise RuntimeError('broker_must_stay_host_side')
                wrapping.append('broker_bootstrap_outside_gateway_grants')
                return proc
            if str(ROOT/'scripts/native_gateway_worker.py') in argv:
                if not protected.is_file() or owner['gateway'] is not None:raise ValueError('joint_start_order')
                private=json.loads(protected.read_text())
                origin=urlsplit(private['upstream_base_url'])
                if origin.hostname!='127.0.0.1' or not origin.port:raise ValueError('local_scripted_origin_only')
                read=[Path('/usr'),Path('/dev/urandom'),ROOT/'scripts',ROOT/'packages',ROOT/'config',
                      LINUX/'source-workspace/vendor/hermes-agent',PREPARED,PY_BASE]
                for item in ('/etc/ld.so.cache','/etc/hosts','/etc/nsswitch.conf','/etc/resolv.conf',
                             '/etc/passwd','/etc/group','/etc/localtime','/etc/ssl/certs','/etc/mime.types'):
                    if Path(item).exists():read.append(Path(item).resolve())
                roots=sorted({str(x.resolve()) for x in read})
                roots=[p for p in roots if not any(p!=q and Path(p).is_relative_to(q) for q in roots)]
                policy={'version':1,'enabled':True,'self_process_metadata':True,
                        'readonly':roots,'writable':[str(out),str(sockets),'/dev/null'],
                        'protected':[str(protected)]}
                cfg=control/'guard.json';write_new(cfg,policy);cfg.chmod(0o600)
                write_new(out/'joint-probe-config.json',{'protected':str(protected),
                          'hostPort':origin.port,'hostNamespace':original_namespace})
                probe=[str(PYTHON),'-I','-B',str(ROOT/'scripts/qa/joint_boundary_probe.py'),
                       '--config',str(out/'joint-probe-config.json'),'--receipt',str(out/'joint-probe.json'),
                       '--',*argv]
                argv=[str(PYTHON),'-I','-B',str(ROOT/'scripts/run_joint_boundary.py'),
                      '--policy',str(cfg),'--network-receipt',str(out/'network-boundary.json'),
                      '--credential-receipt',str(out/'credential-guard.json'),'--',*probe]
                kw['env']={**kw['env'],'XDG_RUNTIME_DIR':str(sockets)}
                proc=real_popen(argv,*a,**kw);owner['gateway']=proc;owner['start']=process_start(proc.pid)
                wrapping.append('network_then_credentials_then_probe_then_original_gateway')
                return proc
            return real_popen(command,*a,**kw)
        def run(command,*a,**kw):
            argv=[str(v) for v in command] if isinstance(command,(list,tuple)) else []
            if str(ROOT/'scripts/qa/d2b2_gateway_task_client.mjs') in argv:
                return real_run(namespace_prefix()+argv,*a,**kw)
            return real_run(command,*a,**kw)
        def http(port,token,method,path,body=None,**kw):
            if not path.startswith(base.BASE+'/'):return real_http(port,token,method,path,body,**kw)
            data={'port':port,'token':token,'method':method,'path':path,'body':body,'kwargs':kw}
            reply=real_run(namespace_prefix()+[str(PYTHON),'-I','-B',str(Path(__file__).resolve()),'--http-helper'],
                           input=json.dumps(data),capture_output=True,text=True,timeout=150)
            if reply.returncode!=0:raise RuntimeError('joint_trusted_http_helper_failed')
            answer=json.loads(reply.stdout);return answer[0],answer[1]
        old_argv=sys.argv
        sys.argv=[str(ROOT/'scripts/qa/native_d2b2_full_gateway.py'),'--scenario',scenario,
                  '--source-workspace',str(LINUX/'source-workspace'),'--python',str(PYTHON),
                  '--node',str(NODE),'--output',str(out),'--public-receipt',str(inner)]
        try:
            with patch.object(subprocess,'Popen',side_effect=launch),patch.object(subprocess,'run',side_effect=run),patch.object(base,'http_json',side_effect=http):
                code=base.main()
        except Exception as error:
            code=1;errors.append(type(error).__name__)
        finally:
            sys.argv=old_argv
            # Base owns ordinary cleanup. A controller exception may only stop its own children.
            for proc in (owner['gateway'],owner['broker']):
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
                    errors.append('controller_emergency_cleanup')
        def read(name):
            p=out/name;return json.loads(p.read_text()) if p.is_file() else {}
        native=json.loads(inner.read_text()) if inner.exists() else {}
        network=read('network-boundary.json');guard=read('credential-guard.json');probe=read('joint-probe.json')
        pid=owner['gateway'].pid if owner['gateway'] is not None else None
        same_pid=bool(pid and network.get('after',{}).get('pid')==pid and probe.get('pid')==pid)
        good=(code==0 and native.get('result')=='PASS' and not errors and bool(samples)
              and same_pid and guard.get('state')=='enforced' and guard.get('protectedReadDenials')==1
              and probe.get('result')=='PASS' and all(probe.get('checks',{}).values()))
        summary={'observedAt':datetime.datetime.now().astimezone().isoformat(),
            'result':'PASS' if good else 'FAIL','scenario':scenario,'native':native,
            'network':network,'credentialGuard':guard,'jointProbe':probe,
            'samePidThroughExecChain':same_pid,'hostObservedSamples':samples,'wrapping':wrapping,
            'errors':errors,'gatewayExit':owner['gateway'].returncode if owner['gateway'] else None,
            'brokerExit':owner['broker'].returncode if owner['broker'] else None,
            'separateHostUid':False,'allUnixIpcIsolated':False,'brokerBudgetAuthorityIndependent':False,
            'fullD3B':False,'paidCalls':0,'realModelCalls':0,'broadFilesystemGrantsAdded':False}
        serialized=json.dumps(summary)
        if any(secret and secret in serialized for secret in secret_values):
            raise RuntimeError('private_test_credential_in_public_receipt')
        write_new(target,summary)
        print(json.dumps({'result':summary['result'],'scenario':scenario,'nativeErrors':native.get('errors',[]),
                          'probe':probe.get('checks',{}),'credential':guard.get('state'),'samePid':same_pid}))
        return 0 if good else 1


def main():
    if sys.argv[1:]==['--http-helper']:
        import native_d2b2_full_gateway as base
        packet=json.load(sys.stdin)
        if not packet['path'].startswith(base.BASE+'/') or packet['method'] not in ('GET','POST'):
            raise ValueError('joint_helper_scope')
        print(json.dumps(base.http_json(packet['port'],packet['token'],packet['method'],packet['path'],packet['body'],**packet['kwargs'])))
        return 0
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--scenario',choices=SCENARIOS,default='normal')
    parser.add_argument('--inside',action='store_true');args=parser.parse_args()
    import re
    if sys.platform!='linux' or not re.fullmatch('[a-z0-9-]{4,40}',args.run_id):raise ValueError('joint_linux_unique_id')
    if args.inside:return gateway_inside(args.run_id,args.scenario)
    evidence=ROOT/'evidence'/EVIDENCE;target=evidence/('gateway-'+args.run_id+'.json')
    manifest=evidence/('source-'+args.run_id+'.json')
    if not evidence.is_dir() or target.exists() or manifest.exists():raise ValueError('joint_fresh_output_required')
    before=source_files(ROOT)
    with tempfile.TemporaryDirectory(prefix='alaz-joint-source-') as temporary:
        snapshot=Path(temporary)/'code';copy_verified(ROOT,snapshot,before)
        filesystem=subprocess.check_output(['stat','-f','-c','%T',str(snapshot)],text=True).strip()
        if filesystem in ('v9fs','9p','drvfs'):raise ValueError('joint_native_filesystem_required')
        for name in (EVIDENCE,'d2b2-gateway-af21'):(snapshot/'evidence'/name).mkdir(parents=True)
        env={**os.environ,'PATH':str(LINUX/'tools/bin')+':/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
        result=subprocess.run([str(PYTHON),'-I','-B',str(snapshot/'scripts/qa/verify_joint_gateway.py'),
              '--inside','--run-id',args.run_id,'--scenario',args.scenario],cwd=snapshot,env=env,
              capture_output=True,text=True,timeout=420)
        inner=snapshot/'evidence'/EVIDENCE/('inside-'+args.run_id+'.json')
        receipt=json.loads(inner.read_text()) if inner.is_file() else {}
        unchanged=source_files(ROOT)==before and source_files(snapshot)==before
        report={'observedAt':datetime.datetime.now().astimezone().isoformat(),'runId':args.run_id,
            'scenario':args.scenario,'result':'PASS' if result.returncode==0 and receipt.get('result')=='PASS' and unchanged else 'FAIL',
            'exitCode':result.returncode,'receipt':receipt,'sourceFiles':len(before),
            'sourceBytesUnchanged':unchanged,'snapshotFilesystem':filesystem,
            'childStdoutSha256':hashlib.sha256(result.stdout.encode()).hexdigest(),
            'childStderrSha256':hashlib.sha256(result.stderr.encode()).hexdigest(),
            'childDiagnostic':result.stderr.splitlines()[-1:],
            'fullD3B':False,'realModelCalls':0,'mainMerged':False}
    report['temporarySnapshotRemoved']=not snapshot.exists()
    write_new(manifest,{'files':before,'scope':'code-only snapshot, not full test inventory'})
    write_new(target,report)
    print(json.dumps({'result':report['result'],'scenario':args.scenario,'samePid':receipt.get('samePidThroughExecChain'),
         'checks':receipt.get('jointProbe',{}).get('checks'),
         'nativeErrors':receipt.get('native',{}).get('errors'),
         'diagnostic':report['childDiagnostic'],'sourceFiles':len(before)}))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
