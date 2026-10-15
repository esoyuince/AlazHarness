"""Actual pinned maintenance-lock probe. Does not change native managed state."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import time
source,profile,out,nonce,mode=sys.argv[1:]
source=Path(source).resolve();profile=Path(profile).resolve();out=Path(out).resolve()
if not out.is_dir() or Path(os.environ['HERMES_HOME']).resolve()!=profile:raise ValueError('Unbound test profile')
if mode not in ('try','nested','hold'):raise ValueError('Unknown test mode')

def record(name,value):
    p=out/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(value),encoding='utf-8');t.replace(p)

def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):raise PermissionError('No network in maintenance-lock worker')
sys.addaudithook(audit)
record('spawn.json',{'pid':os.getpid(),'nonce':nonce})
sys.path.insert(0,str(source))
from gateway.runtime_ownership import exclusive_maintenance,OwnershipConflict,ProfileOwnership
result={'mode':mode,'nonce':nonce,'pid':os.getpid(),'result':'pending','source':'gateway.runtime_ownership.exclusive_maintenance'}
try:
    with exclusive_maintenance([profile]):
        result['result']='acquired'
        if mode=='nested':
            with exclusive_maintenance([profile/'..'/profile.name]):result['nested_same_canonical_home']=True
            another=ProfileOwnership()
            try:
                try:another.reserve([profile]);result['independent_owner_refused']=False
                except OwnershipConflict:result['independent_owner_refused']=True
            finally:another.close()
        record('held.json',{'pid':os.getpid(),'nonce':nonce})
        if mode=='hold':
            deadline=time.monotonic()+90
            while True:
                if (out/'release.json').exists():
                    if json.loads((out/'release.json').read_text())!={'pid':os.getpid(),'nonce':nonce}:raise ValueError('Unowned release')
                    break
                if time.monotonic()>deadline:raise TimeoutError('Bounded maintenance hold expired')
                time.sleep(.02)
    result['lock_released']=True
except OwnershipConflict:result.update(result='refused',lock_released=True)
except Exception as e:result.update(result='error',error_type=type(e).__name__)
record('result.json',result)
print(json.dumps(result))
raise SystemExit(1 if result['result']=='error' else 0)
