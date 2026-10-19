"""PLAT-002A fixed, read-only WSL2 guest identity responder.

Only one bounded JSON request on stdin. Never executes caller commands,
models, network requests or arbitrary tool/file operations. This is
NOT an attestation of a secure sandbox or separate host UID.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys

VERSION=1
TYPE='alaz.wsl2.identity.v1'
MAX_REQUEST_BYTES=1024

class Refused(ValueError):
    pass

def require(ok,code):
    if not ok:raise Refused(code)

def unique(pairs):
    out={}
    for name,value in pairs:
        require(name not in out,'duplicate_json_key')
        out[name]=value
    return out

def reject_constant(value):
    raise Refused('invalid_number')

def parse(raw):
    require(type(raw) is bytes and 0<len(raw)<=MAX_REQUEST_BYTES,
            'invalid_frame_size')
    require(b'\x00' not in raw and raw.endswith(b'\n') and raw.count(b'\n')==1,
            'invalid_frame_delimiter')
    try:
        obj=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,
                       parse_constant=reject_constant)
    except (UnicodeError,json.JSONDecodeError):
        raise Refused('invalid_json') from None
    require(type(obj) is dict and
            set(obj)=={'version','operation','nonce','requestId'},
            'invalid_request_fields')
    require(type(obj['version']) is int and obj['version']==VERSION
            and obj['operation']=='identify' and type(obj['operation']) is str,
            'unsupported_request')
    for name,amount in (('nonce',64),('requestId',32)):
        value=obj[name]
        require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(amount)+'}',value),
                'invalid_request_id')
    return obj

def status_fields():
    rows=Path('/proc/self/status').read_text(encoding='utf-8').splitlines()
    selected={}
    for line in rows:
        if line.split(':',1)[0] in ('NoNewPrivs','Seccomp'):
            selected[line.split(':',1)[0]]=line.split(':',1)[1].strip()
    return selected

def respond(request):
    require(platform.system()=='Linux' and platform.machine()=='x86_64',
            'linux_x64_required')
    release=platform.release()
    require('microsoft' in release.lower() and 'wsl2' in release.lower(),
            'verified_wsl2_guest_required')
    uid,euid=os.getuid(),os.geteuid()
    require(uid!=0 and euid==uid and os.getgid()==os.getegid(),
            'unprivileged_same_identity_required')
    status=status_fields()
    namespace=Path('/proc/self/ns/user')
    mount=Path('/proc/self/ns/mnt')
    require(namespace.exists() and mount.exists(),'guest_namespace_unavailable')
    source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        'version':VERSION,'type':TYPE,
        'requestId':request['requestId'],'nonce':request['nonce'],
        'result':'GUEST_SELF_REPORTED_READ_ONLY',
        'observed':{
            'platform':'linux','arch':'x64','environment':'linux-wsl2-guest',
            'uid':uid,'euid':euid,'gid':os.getgid(),
            'pid':os.getpid(),
            'userNamespaceVisible':True,'mountNamespaceVisible':True,
            'kernelReleaseSha256':hashlib.sha256(release.encode('utf-8')).hexdigest(),
            'noNewPrivs':status.get('NoNewPrivs','unknown'),
            'seccomp':status.get('Seccomp','unknown')
        },
        'sourceSha256':source,
        'secureLaunchAuthorized':False,
        'hostFilesystemIsolated':False,
        'realModelCalls':0,
        'agentOrToolStarted':False,
        'independentHostUidVerified':False
    }

def main():
    try:
        raw=sys.stdin.buffer.readline(MAX_REQUEST_BYTES+2)
        request=parse(raw)
        require(not sys.stdin.buffer.read(1),'trailing_input_refused')
        answer=respond(request)
        sys.stdout.write(json.dumps(answer,sort_keys=True,separators=(',',':'))+'\n')
        sys.stdout.flush()
        return 0
    except Exception:
        # Never print the original payload, OS paths or sensitive command.
        sys.stdout.write('{"result":"REFUSED","code":"GUEST_PROBE_REFUSED"}\n')
        sys.stdout.flush()
        return 2

if __name__=='__main__':
    raise SystemExit(main())
