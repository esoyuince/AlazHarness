"""QA adapter: original full-Gateway acceptance with only Gateway in new netns.

Trusted host controller joins the child namespace for localhost API calls.
The broker and scripted origin stay in the original host namespace. This is
not a filesystem or separate host UID sandbox. No real model API is called.
"""
from pathlib import Path
import json,os,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import native_d2b2_full_gateway as base
REAL_POPEN=subprocess.Popen
REAL_RUN=subprocess.run
ORIGINAL_HTTP=base.http_json
GATEWAY_PID=None
SAMPLES=[]

def namespace_prefix():
    assert GATEWAY_PID is not None
    pid=GATEWAY_PID
    network=os.readlink(f'/proc/{pid}/ns/net')
    assert network!=os.readlink('/proc/self/ns/net')
    info={line.split(':',1)[0]:line.split(':',1)[1].strip()
          for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line}
    assert info['NoNewPrivs']=='1' and info['Seccomp']=='2'
    assert all(int(info[k],16)==0 for k in ('CapEff','CapPrm','CapBnd','CapInh','CapAmb'))
    SAMPLES.append({'networkNamespaceSeparate':True,'noNewPrivs':True,
                    'seccomp':True,'capabilitiesZero':True})
    return ['/usr/bin/nsenter','--target',str(pid),'--user','--net','--preserve-credentials','--']

def launch(args,*a,**kw):
    global GATEWAY_PID
    items=[str(x) for x in args] if isinstance(args,(list,tuple)) else []
    if str(ROOT/'scripts/native_gateway_worker.py') in items:
        work=Path(items[-2])
        wrapped=[items[0],'-I','-B',str(ROOT/'scripts/run_in_network_namespace.py'),
                 '--receipt',str(work/'network-boundary.json'),'--',*items]
        process=REAL_POPEN(wrapped,*a,**kw)
        GATEWAY_PID=process.pid
        return process
    return REAL_POPEN(args,*a,**kw)

def run(args,*a,**kw):
    items=[str(x) for x in args] if isinstance(args,(list,tuple)) else []
    if str(ROOT/'scripts/qa/d2b2_gateway_task_client.mjs') in items:
        return REAL_RUN(namespace_prefix()+items,*a,**kw)
    return REAL_RUN(args,*a,**kw)

def http(port,token,method,path,body=None,**kw):
    if not path.startswith(base.BASE+'/'):
        return ORIGINAL_HTTP(port,token,method,path,body,**kw)
    packet={'port':port,'token':token,'method':method,'path':path,'body':body,'kwargs':kw}
    reply=REAL_RUN(namespace_prefix()+[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--http-helper'],
                   input=json.dumps(packet),capture_output=True,text=True,timeout=150)
    if reply.returncode!=0:raise RuntimeError('trusted_namespace_controller_failed:'+reply.stderr[-400:])
    result=json.loads(reply.stdout)
    return result[0],result[1]

def main():
    if sys.argv[1:]==['--http-helper']:
        data=json.load(sys.stdin)
        assert data['path'].startswith(base.BASE+'/') and data['method'] in ('GET','POST')
        print(json.dumps(ORIGINAL_HTTP(data['port'],data['token'],data['method'],data['path'],data['body'],**data['kwargs'])))
        return 0
    args=sys.argv[1:]
    ix=args.index('--public-receipt')+1
    target=Path(args[ix]).resolve()
    assert target.parent==(ROOT/'evidence/d3b-netns-4e62').resolve() and not target.exists()
    # Preserve the original test runner's strict output directory contract.
    # Move only our own new receipt byte-for-byte to this work's evidence.
    temp=ROOT/'evidence/d2b2-gateway-af21'/('d3b-'+target.name)
    assert not temp.exists()
    args[ix]=str(temp)
    sys.argv=[str(HERE/'native_d2b2_full_gateway.py'),*args]
    subprocess.Popen=launch;subprocess.run=run;base.http_json=http
    result=base.main()
    subprocess.Popen=REAL_POPEN;subprocess.run=REAL_RUN;base.http_json=ORIGINAL_HTTP
    if temp.exists():temp.rename(target)
    data=json.loads(target.read_text())
    summary={'result':'PASS' if result==0 and SAMPLES else 'FAIL',
       'gatewayNetworkBoundarySamples':SAMPLES,'gatewayInSeparateNetworkNamespace':bool(SAMPLES),
       'productionBrokerAndOriginInHostNamespace':True,
       'controllerJoinsForLocalApiOnly':True,'originalGatewayResult':data['result'],
       'completeD3B':False,'hostFilesystemSeparated':False,'separateHostUid':False,
       'realModelCalls':0,'errors':data.get('errors',[])}
    out=target.with_name(target.stem+'-boundary.json')
    with out.open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2);f.write('\n')
    print(json.dumps(summary),flush=True)
    return 0 if summary['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
