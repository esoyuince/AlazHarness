"""Explicit Linux proof for narrow self-metadata after exec; no model or network."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
CHILD=r"""
from pathlib import Path
import ctypes,errno,json,os,sqlite3,subprocess,sys
secret,readonly,runtime,parent=sys.argv[1:]
runtime=Path(runtime);checks={}
def denied(name,call):
    try:
        result=call()
        if isinstance(result,int):os.close(result)
    except OSError as ex:checks[name]=ex.errno in (errno.EACCES,errno.EPERM)
    else:checks[name]=False
for name in ('status','stat','cmdline'):
    checks['own_'+name+'_readable']=bool(Path('/proc/self/'+name).read_bytes())
denied('proc_directory_denied',lambda:os.listdir('/proc'))
denied('self_environ_denied',lambda:os.open('/proc/self/environ',os.O_RDONLY))
denied('self_memory_denied',lambda:os.open('/proc/self/mem',os.O_RDONLY))
denied('parent_status_denied',lambda:os.open('/proc/'+parent+'/status',os.O_RDONLY))
denied('parent_memory_denied',lambda:os.open('/proc/'+parent+'/mem',os.O_RDONLY))
denied('secret_read_denied',lambda:os.open(secret,os.O_RDONLY))
denied('secret_write_denied',lambda:os.open(secret,os.O_WRONLY))
checks['allowed_read']=Path(readonly).read_text()=='public synthetic marker'
(runtime/'working.txt').write_text('owned state')
checks['allowed_write']=(runtime/'working.txt').read_text()=='owned state'
with sqlite3.connect(runtime/'state.db') as c:
    c.execute('create table proof(x)');c.execute('insert into proof values (8)')
    checks['sqlite_write']=c.execute('select x from proof').fetchone()[0]==8
libc=ctypes.CDLL(None)
checks['no_new_privs']=libc.prctl(39,0,0,0,0)==1
checks['no_new_privs_irreversible']=libc.prctl(38,0,0,0,0)!=0
nested='import os,sys,errno\nfor p in sys.argv[1:]:\n try: fd=os.open(p,os.O_RDONLY)\n except OSError as e:\n  if e.errno not in (errno.EACCES,errno.EPERM):sys.exit(4)\n else:os.close(fd);sys.exit(3)\nsys.exit(0)'
r=subprocess.run([sys.executable,'-I','-B','-c',nested,secret,'/proc/self/status','/proc/self/environ'],capture_output=True,timeout=15)
checks['descendant_not_granted_own_metadata_or_secret']=r.returncode==0
out={'checks':checks,'result':'PASS' if all(checks.values()) else 'FAIL','valuesNotPublished':True}
print(json.dumps(out));sys.exit(0 if out['result']=='PASS' else 1)
"""


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--python-base',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert sys.platform=='linux' and a.python.is_file() and a.python_base.is_dir()
    out=a.output.resolve()
    assert not out.exists() and out.parent==(ROOT/'evidence/d3b-startup-b71e').resolve()
    with tempfile.TemporaryDirectory(prefix='alaz-selfmeta-') as temp:
        home=Path(temp);ro=home/'ro';rw=home/'rw';private=home/'private'
        for d in (ro,rw,private):d.mkdir(mode=0o700)
        secret=private/'broker.json';secret.write_bytes(os.urandom(48));secret.chmod(0o600)
        before=hashlib.sha256(secret.read_bytes()).hexdigest()
        source=ro/'probe.py';source.write_text(CHILD)
        canary=ro/'public.txt';canary.write_text('public synthetic marker')
        policy={'version':1,'enabled':True,'readonly':sorted({
            '/usr','/etc/ld.so.cache','/dev/urandom',str(ro),
            str(ROOT/'packages'),str(ROOT/'scripts'),
            str(a.python.resolve().parent.parent),str(a.python_base.resolve())}),
            'writable':[str(rw),'/dev/null'],'protected':[str(secret)],
            'self_metadata':['status','stat','cmdline']}
        cfg=private/'policy.json';cfg.write_text(json.dumps(policy));cfg.chmod(0o600)
        receipt=rw/'guard.json'
        args=[str(a.python),'-I','-B',str(ROOT/'scripts/run_credential_guard.py'),
            '--policy',str(cfg),'--receipt',str(receipt),'--',str(a.python),'-I','-B',
            str(source),str(secret),str(canary),str(rw),str(os.getpid())]
        r=subprocess.run(args,cwd=rw,env={'PATH':'/usr/bin:/bin','HOME':str(rw),
            'TMPDIR':str(rw),'LANG':'C.UTF-8'},capture_output=True,timeout=30)
        body=json.loads(r.stdout) if r.stdout else {}
        guard=json.loads(receipt.read_text()) if receipt.exists() else {}
        stable=hashlib.sha256(secret.read_bytes()).hexdigest()==before
        value={'result':'PASS' if r.returncode==0 and body.get('result')=='PASS'
            and stable and guard.get('procDirectoryGranted') is False else 'FAIL',
            'exitCode':r.returncode,'probe':body,'guard':guard,
            'protectedOriginalUnchanged':stable,'realModelCalls':0,
            'separateHostUid':False,'networkBoundaryVerified':False,
            'preparedInterpreterExecuted':True,
            'stderr':r.stderr.decode('utf-8','replace')[-1000:]}
    value['privateTemporaryFilesRemoved']=True
    out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value));return 0 if value['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
