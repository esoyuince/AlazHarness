"""Test-only line checkpoint before/after native reservation; no source mutation."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import threading


def reservation_line(text: str, phase: str) -> int:
    tree=ast.parse(text)
    function=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_handle_runs')
    calls=[]
    for node in ast.walk(function):
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='reserve':
            calls.append(node)
    if len(calls)!=1:raise ValueError('Ambiguous pinned reservation checkpoint')
    reserve=calls[0]
    if phase=='before-reserve':return reserve.lineno
    if phase=='after-reserve':
        nodes=[n for n in ast.walk(function) if isinstance(n,ast.If) and n.lineno>reserve.end_lineno]
        return min(n.lineno for n in nodes)
    raise ValueError('Unknown checkpoint')


def main() -> None:
    source,work=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()
    nonce,phase,expected=sys.argv[3:6]
    original=Path(__file__).with_name('native_gateway_worker.py')
    native=source/'gateway/platforms/api_server_runs.py'
    raw=native.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('Pinned checkpoint source changed')
    if phase not in ('none','before-reserve','after-reserve'):raise ValueError('Invalid mode')
    fired=False
    if phase!='none':
        line=reservation_line(raw.decode('utf-8'),phase)
        canonical=str(native).casefold()
        def trace(frame,event,arg):
            nonlocal fired
            if frame.f_code.co_filename.casefold()!=canonical or frame.f_code.co_name!='_handle_runs':return None
            if event=='line' and frame.f_lineno==line and not fired:
                if frame.f_locals.get('idempotency_key')!='recovery-'+nonce:return trace
                if phase=='after-reserve' and frame.f_locals.get('outcome')!='created':raise RuntimeError('No newly committed reservation')
                fired=True
                value={'phase':phase,'nonce':nonce,'pid':os.getpid(),'run_id':frame.f_locals['run_id'],
                       'line':line,'source_sha256':expected,'scope':'timing-only fault checkpoint; no HTTP ACK claimed'}
                p=work/'fault-checkpoint.json';tmp=p.with_suffix('.tmp')
                tmp.write_text(json.dumps(value),encoding='utf-8');os.replace(tmp,p)
                threading.Event().wait(35)
                raise RuntimeError('Parent failed to terminate owned process at checkpoint')
            return trace
        sys.settrace(trace)
    sys.argv=[str(original),str(source),str(work),nonce]
    runpy.run_path(str(original),run_name='__main__')

if __name__=='__main__':main()
