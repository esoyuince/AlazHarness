"""Opt-in real AIAgent probe. Only model HTTP responses are scripted; tools are real."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main() -> int:
    scenario = sys.argv[3] if len(sys.argv) > 3 else 'file-read'
    if scenario not in ('file-read', 'budget-summary'): raise ValueError('Unsupported probe scenario')
    source = Path(sys.argv[1]).resolve()
    work = Path(sys.argv[2]).resolve()
    home = Path(os.environ['HERMES_HOME']).resolve()
    if not home.is_relative_to(work) or Path.cwd().resolve() != work:
        raise RuntimeError('Probe requires its own cwd and profile')
    blocked = []
    def audit(event, args):
        host = None
        if event == 'socket.connect' and isinstance(args[1], tuple):
            host = args[1][0]
        elif event == 'socket.getaddrinfo':
            host = args[0]
        if host is not None and host not in ('127.0.0.1', '::1', 'localhost', b'localhost'):
            blocked.append(event)
            raise PermissionError('Probe denies non-loopback networking')
    sys.addaudithook(audit)
    fixture = work / 'input.txt'
    marker = 'ALAZ_NATIVE_' + secrets.token_hex(12)
    fixture.write_text(marker + '\nışık:42\n', encoding='utf-8')
    calls = []
    class Model(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.path.rstrip('/') == '/v1/models':
                self.respond({'object':'list','data':[{'id':'alaz-scripted','object':'model','context_length':131072}]})
            else: self.send_error(404)
        def respond(self, value):
            raw = json.dumps(value).encode()
            self.send_response(200); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_POST(self):
            length = int(self.headers.get('Content-Length','0'))
            if self.path != '/v1/chat/completions' or not 0 < length <= 2_000_000:
                self.send_error(400); return
            body = json.loads(self.rfile.read(length))
            messages = body.get('messages', [])
            tools = [m for m in messages if m.get('role') == 'tool' and m.get('tool_call_id') == 'alaz-read-1']
            names = [t.get('function',{}).get('name') for t in body.get('tools', [])]
            calls.append({'tool_names':names, 'received_real_tool_result':bool(tools), 'stream':body.get('stream',False), 'tool_choice':body.get('tool_choice')})
            if len(calls) > 4 or body.get('stream'):
                self.send_error(400,'Unexpected extra call or stream');return
            if not tools:
                if 'read_file' not in names:
                    self.send_error(400,'Native read_file not exposed');return
                message={'role':'assistant','content':None,'tool_calls':[{'id':'alaz-read-1','type':'function','function':{'name':'read_file','arguments':json.dumps({'path':str(fixture)})}}]}
                finish='tool_calls'
            else:
                content=tools[-1].get('content','')
                if marker not in str(content):
                    self.send_error(400,'Native read result missing fixture marker');return
                message={'role':'assistant','content':'Verified native file tool: '+marker};finish='stop'
            self.respond({'id':'alaz-response-'+str(len(calls)),'object':'chat.completion','created':1,'model':'alaz-scripted','choices':[{'index':0,'message':message,'finish_reason':finish}],'usage':{'prompt_tokens':120,'completion_tokens':20,'total_tokens':140}})
    server=ThreadingHTTPServer(('127.0.0.1',0),Model)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}/v1'
    config={'model':{'default':'alaz-scripted','provider':'custom','base_url':base,'streaming':False},
            'auxiliary':{'title_generation':{'enabled':False}},
            'security':{'allow_lazy_installs':False},'memory':{'provider':'none'},
            'agent':{'max_iterations':3},'checkpoints':{'enabled':False}}
    # JSON is valid YAML and avoids importing application dependencies before its bootstrap.
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    sys.path.insert(0,str(source))
    agent=None
    try:
        from run_agent import AIAgent
        from hermes_constants import get_hermes_home
        if get_hermes_home().resolve()!=home:raise RuntimeError('Profile binding changed')
        agent=AIAgent(model='alaz-scripted',provider='custom',api_mode='chat_completions',
                      base_url=base,api_key='alaz-loopback-fixture',max_iterations=1 if scenario == 'budget-summary' else 3,
                      enabled_toolsets=['file'],quiet_mode=True,verbose_logging=False,
                      skip_context_files=True,skip_memory=True,skip_background_review=True,
                      session_id='alaz-native-probe',checkpoints_enabled=False,
                      max_tokens=256,run_budget_seconds=30,cwd=str(work))
        result=agent.run_conversation('Read the provided input.txt with read_file and report its first line.')
        complete=result.get('completed') is True
        final=result.get('final_response','')
        reason=str(result.get('turn_exit_reason',''))
        real_results=[m for m in result.get('messages',[]) if m.get('role')=='tool' and m.get('tool_call_id')=='alaz-read-1']
        native_read_ok=len(real_results)==1 and marker in str(real_results[0].get('content',''))
        # An iteration cap intentionally permits a toolless summary request. This
        # characterizes upstream behavior; it does NOT accept a hard API/cost cap.
        wire_ok=len(calls)==2 and calls[-1]['received_real_tool_result']
        outcome_ok=(not complete and 'max_iterations' in reason) if scenario == 'budget-summary' else (complete and marker in final)
        ok=native_read_ok and wire_ok and outcome_ok
        receipt={'result':'PASS' if ok else 'FAIL','scope':'real_AIAgent_constructor_loop_and_file_tool_scripted_model_HTTP',
                 'scenario':scenario,'turn_exit_reason':reason,'completed':complete,'native_tool':'read_file','tool_result_seen_by_model':bool(calls and calls[-1]['received_real_tool_result']),
                 'native_read_results':len(real_results),'hard_request_budget_enforced':False,
                 'iteration_limit':1 if scenario == 'budget-summary' else 3,
                 'model_http_calls':len(calls),'model_inference_calls':0,'paid_model_calls':0,
                 'profile_bound':True,'non_loopback_attempts_blocked':len(blocked),
                 'output_sha256':hashlib.sha256(final.encode()).hexdigest(),
                 'openclaw_gateway_tested':False,'hermes_gateway_http_tested':False,
                 'os_sandbox_claimed':False,'autonomy_tested':False,
                 'result_keys':sorted(result),'model_calls':calls}
        (work/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print(json.dumps(receipt,indent=2));return 0 if ok else 1
    finally:
        try:
            if agent is not None:agent.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':raise SystemExit(main())
