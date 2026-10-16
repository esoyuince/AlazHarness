"""Explicit no-download test image fixture: delay Python startup for cancellation.
This is TEST preparation, never an agent-selected image build or runtime fallback.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-image',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    if not re.fullmatch('sha256:[a-f0-9]{64}',a.base_image) or not a.output.is_absolute() or a.output.exists():raise ValueError('Pinned image/fresh output required')
    if not a.apply:print(json.dumps({'base_image':a.base_image,'network':'none','download':False,'mode':'plan'}));return 0
    a.output.mkdir(mode=0o700);(a.output/'docker-config').mkdir();(a.output/'home').mkdir()
    env={'PATH':'/usr/bin:/bin','HOME':str(a.output/'home'),'LANG':'C.UTF-8'}
    base=['/usr/bin/sudo','-n','/usr/bin/docker','--host=unix:///var/run/docker.sock','--config',str(a.output/'docker-config')]
    def docker(args):return subprocess.check_output(base+args,env=env,timeout=30).decode().strip()
    owner=uuid.uuid4().hex;name='alaz-slow-fixture-'+owner;cid=None;image=None
    (a.output/'ownership.json').write_text(json.dumps({'owner':owner,'name':name,'base_image':a.base_image,'automatic_retry':False}))
    command="set -eu; test -x /usr/bin/python3; mv /usr/bin/python3 /usr/bin/alaz-real-python3; printf '%s\\n' '#!/bin/sh' '/bin/sleep 8' 'exec /usr/bin/alaz-real-python3 \"$@\"' > /usr/bin/python3; chmod 0755 /usr/bin/python3"
    try:
        cid=docker(['create','--pull=never','--network=none','--cap-drop=ALL','--security-opt=no-new-privileges',
            '--pids-limit=32','--memory=134217728','--name='+name,'--label=org.alaz.harness.preparation='+owner,
            '--no-healthcheck','--entrypoint=/bin/sh',a.base_image,'-c',command])
        inspect=json.loads(docker(['inspect',cid]))[0]
        if inspect['Image']!=a.base_image or inspect['State']['Running'] or inspect['Config']['Labels']['org.alaz.harness.preparation']!=owner:raise ValueError('Unowned preparation')
        docker(['start','--attach',cid]);inspect=json.loads(docker(['inspect',cid]))[0]
        if inspect['State']['Running'] or inspect['State']['ExitCode']!=0:raise ValueError('Preparation failed')
        image=docker(['commit','--change','LABEL org.alaz.harness.slow-fixture='+owner,cid])
        inspected=json.loads(docker(['image','inspect',image]))[0]
        if inspected['Id']!=image or inspected['Config']['Labels']['org.alaz.harness.slow-fixture']!=owner:raise ValueError('Image identity mismatch')
        result={'base_image':a.base_image,'image':image,'owner':owner,'downloaded':False,'test_only':True,
            'delay_seconds':8,'preparation_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    finally:
        if cid:
            raw=json.loads(docker(['inspect',cid]))[0]
            if raw['Id']!=cid or raw['Name']!='/'+name:raise ValueError('Cleanup ownership mismatch')
            if raw['State']['Running']:docker(['kill',cid])
            docker(['rm',cid])
    result['preparation_container_removed']=not bool(docker(['ps','-aq','--filter=id='+cid]))
    (a.output/'image-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0

if __name__=='__main__':raise SystemExit(main())
