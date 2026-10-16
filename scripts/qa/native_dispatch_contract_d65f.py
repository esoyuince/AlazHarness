"""Actual pinned model_tools dispatch/context, with a recording registry port.
No registry handler, Gateway, AIAgent, external network or provider is executed.
Only the selected _execute_tool function is exercised; middleware is not tested.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

PINS={
 'model_tools.py':'fbb40d0058e3edd6c4e1608b8db9e922aaf38d2c9d0438c3811c6d6b01b45340',
 'tools/registry.py':'eecf43c6578e2a0bb78e5d795cba150e00e704395d37490bf2217ab55a923296',
 'tools/approval_context.py':'9ffa125caadc2253165b069375bcae0065949131baa92a7f2b13fea4c2827ae4'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.source_workspace.resolve();source=root/'vendor/hermes-agent';out=args.output.resolve()
    if not out.is_relative_to(root/'runtime') or out.exists():raise ValueError('Fresh runtime output required')
    for name,digest in PINS.items():
        p=source/name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('Source pin mismatch')
    out.mkdir();os.environ['HERMES_HOME']=str(out/'profile')
    denied=[]
    def audit(event,args):
        if event in ('socket.connect','socket.connect_ex','subprocess.Popen','os.system'):
            denied.append(event);raise PermissionError('QA dispatch probe does not execute network or subprocess')
    sys.addaudithook(audit)
    sys.path.insert(0,str(source))
    import model_tools as native
    from tools import approval_context as context
    if Path(native.__file__).resolve()!=source/'model_tools.py':raise ValueError('Wrong native module')
    ids=native._CallIds(task_id='native-task-fixture',session_id='run_'+'a'*32,
        tool_call_id='call_qa_fixture',turn_id='turn_qa_fixture',api_request_id='request_qa_fixture')
    observations=[]
    def recording_handler(name,args,**kwargs):
        observations.append({'name':name,'argument_fields':sorted(args),'kwargs_fields':sorted(kwargs),
          'session_matches':kwargs.get('session_id')==ids.session_id,'task_matches':kwargs.get('task_id')==ids.task_id,
          'parent_agent_supplied':'parent_agent' in kwargs,
          'context_session_matches':context._approval_session_id.get()==ids.session_id,
          'context_call_matches':context._approval_tool_call_id.get()==ids.tool_call_id})
        return 'recording-port-result'
    body={'path':'/fixture/not-read.txt','offset':1,'limit':10}
    with patch.object(native.registry,'dispatch',recording_handler):
        result=native._execute_tool('read_file',body,dict(body),ids,user_task='no content read',enabled_tools=['read_file'],skip_tool_execution_middleware=True)
    observation=observations[0]
    verified=(len(observations)==1 and result=='recording-port-result'
      and observation['kwargs_fields']==['session_id','task_id','user_task']
      and observation['parent_agent_supplied'] is False and observation['context_session_matches']
      and observation['context_call_matches'] and observation['task_matches'] and observation['session_matches'])
    stable=all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in PINS.items())
    report={'scope':'actual pinned model_tools._execute_tool and approval ContextVars; only registry.dispatch is recording port; not full agent integration',
       'source_commit':'eb75627faf532fa6ffbdae59a0d14b0b385fc780','source_files':PINS,'observations':observations,
       'context_restored':context._approval_tool_call_id.get()=='','source_unchanged':stable,
       'blocked_attempt_types':sorted(set(denied)),'blocked_attempt_count':len(denied),
       'actual_registry_handler_calls':0,'gateway_executions':0,'container_runs':0,'provider_calls':0,'paid_calls':0,
       'result':'OBSERVATION_CONFIRMED' if verified and stable and not denied else 'FAIL'}
    (out/'dispatch-observation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));return 0 if report['result']=='OBSERVATION_CONFIRMED' else 1

if __name__=='__main__':raise SystemExit(main())
