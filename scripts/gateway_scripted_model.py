"""Deterministic local model, never a Gateway or tool implementation."""
from __future__ import annotations
import json
import os
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import threading

class ScriptedModel:
    def __init__(self, fixture: Path, marker: str, *, hold_directory: Path | None = None, nonce: str = ""):
        self.fixture,self.marker=fixture,marker
        self.calls=[];self.errors=[];self.lock=threading.Lock()
        self.hold_directory,self.nonce=hold_directory,nonce
        self.release=threading.Event();self.release.set();self.entered=threading.Event()
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def data(self,obj,status=200):
                raw=json.dumps(obj).encode();self.send_response(status)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
                self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                if self.path.rstrip('/')=='/v1/models':
                    self.data({'object':'list','data':[{'id':'alaz-scripted','object':'model','context_length':131072}]})
                else:self.send_error(404)
            def do_POST(self):
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if self.path!='/v1/chat/completions' or not 0<n<=2_000_000:raise ValueError('Unexpected model route/size')
                    body=json.loads(self.rfile.read(n));messages=body.get('messages',[])
                    tools=[x for x in messages if x.get('role')=='tool' and x.get('tool_call_id')=='alaz-read-1']
                    names=[x.get('function',{}).get('name') for x in body.get('tools',[])]
                    with owner.lock:
                        owner.calls.append({'tool_result':bool(tools),'tool_names':names,'stream':bool(body.get('stream'))})
                        if len(owner.calls)>8:raise ValueError('Model fixture request cap')
                    owner.entered.set()
                    if owner.hold_directory is not None:
                        pending=owner.hold_directory/'model-entered.json'
                        tmp=pending.with_suffix('.tmp');tmp.write_text(json.dumps({'nonce':owner.nonce}),encoding='utf-8');os.replace(tmp,pending)
                        deadline=time.monotonic()+12
                        while not (owner.hold_directory/'model-release.json').exists():
                            if time.monotonic()>deadline:raise TimeoutError('Model hold deadline')
                            time.sleep(.02)
                        if json.loads((owner.hold_directory/'model-release.json').read_text())!={'nonce':owner.nonce}:
                            raise ValueError('Wrong model release owner')
                    if not owner.release.wait(timeout=12):raise TimeoutError('Model fixture hold deadline')
                    if not tools:
                        if 'read_file' not in names:raise ValueError('Native read_file missing')
                        msg={'role':'assistant','content':None,'tool_calls':[{'id':'alaz-read-1','type':'function','function':{'name':'read_file','arguments':json.dumps({'path':str(owner.fixture)})}}]};finish='tool_calls'
                    else:
                        if owner.marker not in str(tools[-1].get('content','')):raise ValueError('Real tool result missing nonce')
                        msg={'role':'assistant','content':'Native Gateway verified '+owner.marker};finish='stop'
                    if body.get('stream'):
                        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                        delta=dict(msg);delta.pop('role',None)
                        if 'tool_calls' in delta:
                            delta['tool_calls'][0]['index']=0
                        for d,f in [({'role':'assistant'},None),(delta,None),({},finish)]:
                            event={'id':'alaz-fixture','object':'chat.completion.chunk','created':1,'model':'alaz-scripted','choices':[{'index':0,'delta':d,'finish_reason':f}]}
                            self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
                        self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
                    else:self.data({'id':'alaz-fixture','object':'chat.completion','created':1,'model':'alaz-scripted','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':120,'completion_tokens':20,'total_tokens':140}})
                except (BrokenPipeError,ConnectionResetError):pass
                except Exception as exc:
                    with owner.lock:owner.errors.append(type(exc).__name__+': '+str(exc))
                    try:self.data({'error':{'message':'controlled fixture refusal','type':'invalid_request_error'}},400)
                    except OSError:pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
    @property
    def base_url(self):return f'http://127.0.0.1:{self.server.server_port}/v1'
    def start(self):self.thread.start()
    def close(self):
        self.release.set();self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
