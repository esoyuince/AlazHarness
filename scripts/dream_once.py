"""Manually request candidate-only Dream maintenance on a configured local Gateway.
Connection/source files are private. No automatic POST retry or direct model fallback.
"""
from __future__ import annotations
import argparse
import http.client
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import _load,_json


def check_connection(connection):
    if type(connection) is not dict or set(connection)!={'base_url','token'}:
        raise ValueError('invalid_dream_connection')
    value=connection['base_url']
    if type(value) is not str:raise ValueError('invalid_dream_connection')
    u=urlsplit(value)
    if u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:
        raise ValueError('local_dream_connection_required')
    token=connection['token']
    if type(token) is not str or not re.fullmatch(r'[\x21-\x7e]{1,256}',token):
        raise ValueError('invalid_dream_credential')
    return u.port,token


def invoke(connection, *, sources=None, batch_id=None):
    port,token=check_connection(connection)
    if (sources is None)==(batch_id is None):raise ValueError('one_dream_operation_required')
    if batch_id is not None and (type(batch_id) is not str or not re.fullmatch('[a-f0-9]{64}',batch_id)):
        raise ValueError('invalid_dream_batch')
    if sources is not None and (type(sources) is not list or len(sources)>8):
        raise ValueError('invalid_dream_sources')
    payload=_json({'sources':sources}).encode() if sources is not None else None
    if payload is not None and len(payload)>131072:raise ValueError('dream_body_too_large')
    # http.client does not consult environment proxies or automatically follow redirects.
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=50)
    try:
        c.request('POST' if sources is not None else 'GET','/alaz/host/v1/dream'+('' if sources is not None else '/'+batch_id),
                  body=payload,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        response=c.getresponse();raw=response.read(131073)
        if len(raw)>131072 or response.status not in (200,202,422):raise ValueError('dream_request_unconfirmed')
        value=_load(raw.decode('utf-8'),131072)
        if type(value) is not dict or value.get('state') not in ('idle','prepared','running','completed','rejected','unknown') or value.get('activeMemoryChanged') is not False:
            raise ValueError('invalid_dream_response')
        if type(value.get('candidates')) is not list or any(type(n) is not dict or n.get('usableAsMemory') is not False for n in value['candidates']):
            raise ValueError('invalid_dream_candidates')
        return value
    finally:c.close()


def read_private(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>131072:raise ValueError('invalid_dream_input')
    return _load(path.read_text(encoding='utf-8'),131072)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--connection',type=Path,required=True)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--sources',type=Path);group.add_argument('--batch-id')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        if a.output is not None and (a.output.exists() or a.output.is_symlink()):raise ValueError('dream_output_exists')
        value=invoke(read_private(a.connection),sources=read_private(a.sources) if a.sources is not None else None,batch_id=a.batch_id)
        rendered=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        if a.output is not None:
            with a.output.open('x',encoding='utf-8',newline='\n') as out:out.write(rendered)
        else:print(rendered,end='')
        return 0 if value['state'] in ('completed','idle') else 2
    except Exception:
        # A failed POST may have committed; read status, never automatically repeat it.
        print('{"state":"unknown","error":"dream_request_not_confirmed","automaticRetry":false}',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
