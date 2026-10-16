"""Scripted upstream only. The native Gateway/SDK/tools are never replaced."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import threading

class ExecutionModel:
    def __init__(self,fixture,marker,scenario,target):
        self.calls=[];self.errors=[];owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,value,status=200,typ='application/json'):
                raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_POST(self):
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if self.path!='/v1/chat/completions' or not 0<n<=2000000:raise ValueError('Unexpected request')
                    body=json.loads(self.rfile.read(n));tools=[x for x in body['messages'] if x.get('role')=='tool']
                    owner.calls.append({'path':self.path,'stream':body.get('stream',False),'model':body['model'],'tool_result':bool(tools),'tool_choice':body.get('tool_choice'),'tools_present':bool(body.get('tools')),'max_tokens':body.get('max_tokens',body.get('max_completion_tokens'))})
                    if len(owner.calls)>8:raise RuntimeError('Fixture call cap')
                    if scenario=='sdk-retry-limit':
                        if len(owner.calls)==1:self.send({'error':{'message':'transient fixture','type':'server_error'}},503);return
                        msg={'role':'assistant','content':'unexpected second physical attempt'};finish='stop'
                    elif not tools:
                        tool='write_file' if scenario=='denied-write' else 'read_file'
                        args={'path':str(target),'content':marker} if tool=='write_file' else {'path':str(fixture)}
                        msg={'role':'assistant','content':None,'tool_calls':[{'id':'execution-tool-1','type':'function','function':{'name':tool,'arguments':json.dumps(args)}}]};finish='tool_calls'
                    else:
                        contents=str(tools[-1].get('content',''))
                        if scenario in ('denied-write','tool-limit'):
                            if 'tool_not_allowed' not in contents and 'tool_attempt_limit' not in contents:raise RuntimeError('Expected guard rejection absent')
                            msg={'role':'assistant','content':'Guard refusal observed'}
                        else:
                            if marker not in contents:raise RuntimeError('Actual file marker missing')
                            msg={'role':'assistant','content':'Native execution verified '+marker}
                        finish='stop'
                    usage={'prompt_tokens':120,'completion_tokens':20,'total_tokens':140}
                    if body.get('stream'):
                        chunks=[];delta=dict(msg);delta.pop('role',None)
                        if 'tool_calls' in delta:delta['tool_calls'][0]['index']=0
                        for d,f in [({'role':'assistant'},None),(delta,None),({},finish)]:
                            value={'id':'execution-fixture','object':'chat.completion.chunk','created':1,'model':'alaz-scripted','choices':[{'index':0,'delta':d,'finish_reason':f}]}
                            if f:value['usage']=usage
                            chunks.append('data: '+json.dumps(value)+'\n\n')
                        raw=(''.join(chunks)+'data: [DONE]\n\n').encode();self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
                    else:self.send({'id':'execution-fixture','object':'chat.completion','created':1,'model':'alaz-scripted','choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':usage})
                except (BrokenPipeError,ConnectionResetError):pass
                except Exception as exc:
                    owner.errors.append(type(exc).__name__+': '+str(exc))
                    try:self.send({'error':{'message':'fixture rejected','type':'invalid_request_error'}},400)
                    except OSError:pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
    @property
    def base_url(self):return f'http://127.0.0.1:{self.server.server_port}/v1'
    def start(self):self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
