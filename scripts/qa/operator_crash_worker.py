"""Test-only owned crash barriers around the actual operator's two INSERTs/COMMIT."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import time
source,repo,home,out,nonce,phase,expected=sys.argv[1:]
source,repo,home,out=map(lambda p:Path(p).resolve(),(source,repo,home,out))
assert Path(os.environ['HERMES_HOME']).resolve()==home
if phase not in ('before-index','after-commit','none'):raise ValueError('Unknown checkpoint')
def record(name,value):
    p=out/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2),encoding='utf-8');t.replace(p)
record('spawn.json',{'pid':os.getpid(),'nonce':nonce})
def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):raise PermissionError('Test disallows network')
sys.addaudithook(audit)
sys.path.insert(0,str(repo/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext
from operator_resolution import OperatorResolution
file=repo/'packages/claw-hermes/operator_resolution.py';data=file.read_bytes()
if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Product hash changed')
private=json.loads((out.parent/'private.json').read_text())
service=OperatorResolution(LocalRecoveryContext(**private['context']),source_root=source)
query=private['query'];planpath=out.parent/'plan.json'
if planpath.exists():plan=json.loads(planpath.read_text())
else:
    plan=service.prepare(command_id=private['command_id'],**query)
    planpath.write_text(json.dumps(plan),encoding='utf-8')
checkpoint=None
if phase!='none':
    cls=next(n for n in ast.parse(data).body if isinstance(n,ast.ClassDef) and n.name=='OperatorResolution')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='apply')
    inserts=[];commits=[];returns=[]
    for n in ast.walk(method):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='conn':
            if n.func.attr=='execute' and n.args and isinstance(n.args[0],ast.Constant) and str(n.args[0].value).startswith('INSERT INTO state_meta'):inserts.append(n.lineno)
            if n.func.attr=='commit':commits.append(n.lineno)
        if isinstance(n,ast.Return):returns.append(n.lineno)
    if len(inserts)!=2 or len(commits)!=1:raise ValueError('Unsupported transaction source shape')
    checkpoint=sorted(inserts)[1] if phase=='before-index' else min(n for n in returns if n>commits[0])
    def trace(frame,event,arg):
        if event=='line' and frame.f_code.co_name=='apply' and Path(frame.f_code.co_filename).resolve()==file and frame.f_lineno==checkpoint:
            record('checkpoint.json',{'pid':os.getpid(),'nonce':nonce,'phase':phase,'line':checkpoint,'source_sha256':expected})
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:time.sleep(.02)
            raise TimeoutError('Owned test checkpoint was not collected')
        return trace
    sys.settrace(trace)
try:
    result=service.apply(plan=plan,confirmation=plan['confirmationDigest'],**query)
finally:sys.settrace(None)
record('result.json',{'nonce':nonce,'pid':os.getpid(),'result':result})
