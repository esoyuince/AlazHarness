"""Opt-in SDK wire-count control. Not a full agent or execution-gate acceptance."""
from __future__ import annotations
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();source=a.source.resolve();out=a.output.resolve()
    if out.exists():raise FileExistsError('Fresh output required')
    if not out.is_relative_to(Path(os.environ['HERMES_HOME']).resolve().parent):raise ValueError('Isolated profile required')
    import subprocess
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,timeout=15).strip()!=PIN:raise ValueError('Unpinned source')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True,timeout=15).strip():raise ValueError('Modified source')
    digest=hashlib.sha256((source/'agent/auxiliary_client.py').read_bytes()).hexdigest()
    out.mkdir(parents=True);blocked=[]
    def audit(event,args):
        host=None
        if event=='socket.connect' and isinstance(args[1],tuple):host=args[1][0]
        elif event=='socket.getaddrinfo':host=args[0]
        if host is not None and host not in ('127.0.0.1','::1','localhost',b'localhost'):
            blocked.append(event);raise PermissionError('QA denies non-loopback network')
    sys.addaudithook(audit);sys.path.insert(0,str(source))
    from agent.auxiliary_client import _create_openai_client
    counts={};errors=[];rows=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=8192:self.send_error(400);return
            body=json.loads(self.rfile.read(n));model=body.get('model');counts[model]=counts.get(model,0)+1
            if counts[model]==1:
                status=503;value={'error':{'type':'server_error','message':'controlled transient response'}}
            else:
                status=200;value={'id':'fixture','object':'chat.completion','created':1,'model':model,'choices':[{'index':0,'message':{'role':'assistant','content':'done'},'finish_reason':'stop'}],'usage':{'prompt_tokens':2,'completion_tokens':1,'total_tokens':3}}
            raw=json.dumps(value).encode();self.send_response(status)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Retry-After','0.01');self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        for label,kwargs,expected,ok in [('native-default',{},1,False),('explicit-sdk-retry',{'max_retries':1},2,True)]:
            client=_create_openai_client(api_key='fixture-not-secret',base_url=f'http://127.0.0.1:{server.server_port}/v1',timeout=3,**kwargs)
            error=None;success=False
            try:
                result=client.chat.completions.create(model=label,messages=[{'role':'user','content':'fixture'}],max_tokens=1)
                success=result.choices[0].message.content=='done'
            except Exception as exc:error=type(exc).__name__
            finally:client.close()
            row={'scenario':label,'sdk_method_invocations':1,'server_http_requests':counts.get(label,0),'success':success,'exception_type':error,'passed':counts.get(label,0)==expected and success is ok}
            rows.append(row)
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    report={'scope':'native auxiliary OpenAI client factory + real SDK + loopback503 fixture; not Gateway, AIAgent, host-budget or inference acceptance','source_commit':PIN,'source_sha256':digest,'cases':rows,'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows),'source_changed':digest!=hashlib.sha256((source/'agent/auxiliary_client.py').read_bytes()).hexdigest(),'nonloopback_attempts_blocked':len(blocked),'model_inference_calls':0,'paid_calls':0,'interpretation':'Native default retries are off. Explicit SDK retry override yields two physical requests from one SDK invocation; a logical-call counter alone is insufficient.'}
    (out/'wire-count.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
    return 0 if report['failed']==0 and not report['source_changed'] and not blocked else 1

if __name__=='__main__':raise SystemExit(main())
