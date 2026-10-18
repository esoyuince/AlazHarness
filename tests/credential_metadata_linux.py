"""Opt-in native Linux checks for self metadata, without a Gateway/model call."""
import argparse
import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from credential_guard import apply,self_metadata_paths
LINUX=Path('/home/ender/alaz-harness-d2b2-gateway-af21')
ENV=LINUX/'source-workspace/runtime/gateway-env-af21/env'
PYTHON=ENV/'bin/python-local'


def child(config):
    c=json.loads(Path(config).read_text())
    guard=apply(c['policy'])
    checks={}
    for index,path in enumerate(self_metadata_paths(os.getpid())):
        try:
            fd=os.open(path,os.O_RDONLY);os.close(fd);allowed=True
        except PermissionError:allowed=False
        checks['metadata_'+str(index)+'_'+path.rsplit('/',1)[-1]]=allowed==c['enabled']
    for label,path in [('protected',c['secret']),('own_environ','/proc/self/environ'),
            ('own_mem','/proc/self/mem'),('parent_mem','/proc/'+str(c['parentPid'])+'/mem'),
            ('parent_status','/proc/'+str(c['parentPid'])+'/status')]:
        try:fd=os.open(path,os.O_RDONLY)
        except OSError as exc:checks[label+'_denied']=exc.errno in (errno.EACCES,errno.EPERM)
        else:os.close(fd);checks[label+'_denied']=False
    try:os.listdir('/proc')
    except PermissionError:checks['proc_listing_denied']=True
    else:checks['proc_listing_denied']=False
    if c['enabled']:
        import psutil
        checks['psutil_pid_exists']=psutil.pid_exists(os.getpid())
        checks['psutil_status']=bool(psutil.Process().status())
        checks['psutil_start_time']=psutil.Process().create_time()>0
        checks['psutil_cmdline']=bool(psutil.Process().cmdline())
    probe='import os,sys\ntry:fd=os.open(sys.argv[1],os.O_RDONLY)\nexcept PermissionError:raise SystemExit(0)\nelse:os.close(fd);raise SystemExit(5)'
    for label,path in [('child_secret',c['secret']),('child_self_metadata','/proc/self/stat')]:
        r=subprocess.run([str(PYTHON),'-I','-B','-c',probe,path],capture_output=True,timeout=10)
        checks[label+'_denied']=r.returncode==0
    print(json.dumps({'result':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'guard':guard}))
    return 0 if all(checks.values()) else 1


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--child');parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    if a.child:return child(a.child)
    import tempfile  # Controller only: this portable build caches an urandom FD on import.
    assert sys.platform=='linux' and a.output and not a.output.exists()
    assert a.output.resolve().parent==(ROOT/'evidence/d3b-credential-fix-a613').resolve()
    records=[]
    with tempfile.TemporaryDirectory(prefix='alaz-metadata-a613-') as temporary:
        root=Path(temporary);secret=root/'secret';secret.write_bytes(os.urandom(32));original=hashlib.sha256(secret.read_bytes()).hexdigest()
        for enabled in (False,True):
            work=root/str(enabled);work.mkdir()
            policy={'version':1,'enabled':True,'self_process_metadata':enabled,
                'readonly':['/usr','/dev/urandom',str(ENV),str(LINUX/'tools/python/cpython-3.14.3-linux-x86_64-gnu')],
                'writable':[str(work),'/dev/null'],'protected':[str(secret)]}
            config=root/('config-'+str(enabled)+'.json');config.write_text(json.dumps({'policy':policy,'enabled':enabled,'secret':str(secret),'parentPid':os.getpid()}))
            bootstrap="import sys;from pathlib import Path;p=sys.argv[1];c=sys.argv[2];source=Path(p).read_text();sys.argv=[p,'--child',c];exec(compile(source,p,'exec'),{'__name__':'__main__','__file__':p})"
            r=subprocess.run([str(PYTHON),'-I','-B','-c',bootstrap,str(Path(__file__).resolve()),str(config)],cwd=work,
                env={'PATH':'/usr/bin:/bin','HOME':str(work),'TMPDIR':str(work),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=25)
            records.append({'enabled':enabled,'exitCode':r.returncode,'result':json.loads(r.stdout) if r.stdout else {},
                'stderrSha256':hashlib.sha256(r.stderr.encode()).hexdigest(), 'stderrDiagnostic':r.stderr.splitlines()[-1:] })
        unchanged=hashlib.sha256(secret.read_bytes()).hexdigest()==original
    result={'observedAt':datetime.datetime.now().astimezone().isoformat(),
        'result':'PASS' if unchanged and all(r['exitCode']==0 and r['result'].get('result')=='PASS' for r in records) else 'FAIL',
        'records':records,'protectedUnchanged':unchanged,'temporaryDataRemoved':True,
        'guardSourceSha256':hashlib.sha256((ROOT/'packages/claw-hermes/credential_guard.py').read_bytes()).hexdigest(),
        'realModelCalls':0,'scope':'two fresh Linux children, self metadata opt-in; no Gateway or network test'}
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result));return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
