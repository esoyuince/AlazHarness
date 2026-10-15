"""Scripted provider only: optional barrier on first/second actual model HTTP call."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading

class RecoveryModel:
    def __init__(self, fixture: Path, marker: str, hold_call: int=0):
        self.fixture,self.marker,self.hold_call=fixture,marker,hold_call
        self.calls=[];self.errors=[];self.lock=threading.Lock()
        self.entered=threading.Event();self.release=threading.Event()
        self.forbid=False;owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,body,status=200):
                raw=json.dumps(body).encode();self.send_response(status)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
                self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                if self.path.rstrip('/')=='/v1/models':self.send({'data':[{'id':'alaz-scripted','object':'model','context_length':131072}]})
                else:self.send_error(404)
            def do_POST(self):
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if self.path!='/v1/chat/completions' or not 0<n<2_000_000:raise ValueError('Unexpected provider route/size')
                    body=json.loads(self.rfile.read(n));tools=[m for m in body.get('messages',[]) if m.get('role')=='tool' and m.get('tool_call_id')=='recovery-read']
                    names=[t.get('function',{}).get('name') for t in body.get('tools',[])]
                    with owner.lock:
                        owner.calls.append({'tool_result':bool(tools),'forbidden':owner.forbid,'stream':bool(body.get('stream'))})
                        call=len(owner.calls)
                    if owner.forbid or call>4:raise ValueError('Unexpected inference attempt after restart')
                    if body.get('stream'):raise ValueError('Unexpected streaming fixture')
                    if tools and owner.marker not in str(tools[-1].get('content','')):raise ValueError('Missing true read result')
                    if call==owner.hold_call:
                        owner.entered.set()
                        if not owner.release.wait(45):raise TimeoutError('Provider barrier timeout')
                    if not tools:
                        if 'read_file' not in names:raise ValueError('No real file tool exposed')
                        msg={'role':'assistant','content':None,'tool_calls':[{'id':'recovery-read','type':'function','function':{'name':'read_file','arguments':json.dumps({'path':str(owner.fixture)})}}]};finish='tool_calls'
                    else:msg={'role':'assistant','content':'Recovered result '+owner.marker};finish='stop'
                    self.send({'id':'recovery-model','object':'chat.completion','created':1,'model':'alaz-scripted','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}})
                except (BrokenPipeError,ConnectionResetError):pass
                except Exception as exc:
                    with owner.lock:owner.errors.append(type(exc).__name__+': '+str(exc))
                    try:self.send({'error':{'message':'controlled provider refusal'}},400)
                    except OSError:pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
    @property
    def base_url(self):return f'http://127.0.0.1:{self.server.server_port}/v1'
    def start(self):self.thread.start()
    def close(self):
        self.release.set();self.server.shutdown();self.server.server_close();self.thread.join(5)
