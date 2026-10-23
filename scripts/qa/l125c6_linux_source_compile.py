"""Compile pinned Python source without importing or executing any candidate.
A Linux syntax check only; no proof of imports, constructors, sandbox or service.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,os,sys,time

def main():
    expected='AlazHarness-D3B-P71C'
    assert os.environ.get('WSL_DISTRO_NAME')==expected
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()==expected
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert not Path('/mnt/c/Windows').exists() and sys.flags.isolated and sys.dont_write_bytecode
    raw=sys.stdin.buffer.read(20_000_001)
    assert len(raw)<=20_000_000
    data=json.loads(raw);assert data['feature']=='1e97dd617b81120255304e472ce322befcdb9ccd'
    files=data['files'];assert type(files) is dict and 500<=len(files)<=800
    good={};bad=[];begin=time.monotonic()
    for name,item in sorted(files.items()):
        path=PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and path.parts[0] in ('native','harness') and name.endswith('.py')
        encoded=item['text'].encode('utf-8');digest=hashlib.sha256(encoded).hexdigest();assert digest==item['sha256']
        try:compile(item['text'],name,'exec',dont_inherit=True,optimize=0)
        except (SyntaxError,ValueError) as exc:
            bad.append({'path':name,'type':type(exc).__name__,'reason':str(exc),'line':getattr(exc,'lineno',None)})
        else:good[name]=digest
    out={'result':'PASS_LINUX_SYNTAX_ONLY' if not bad else 'FAIL_LINUX_SYNTAX','feature':data['feature'],
         'python':sys.version,'uid':list(os.getresuid()),'gid':list(os.getresgid()),'total':len(files),'passed':len(good),
         'failures':bad,'sourceHashes':{n:v['sha256'] for n,v in files.items()},'payloadSha256':hashlib.sha256(raw).hexdigest(),
         'elapsedSeconds':round(time.monotonic()-begin,3),'candidateImportsExecuted':False,'candidateCodeExecuted':False,
         'candidateFilesWritten':False,'rootUsed':False,'coldStartupTested':False,'mountOrIsolationTested':False,
         'providerOrModelCalled':False,'serviceActivated':False}
    print(json.dumps(out),flush=True)
    return 0 if not bad else 1
if __name__=='__main__':raise SystemExit(main())
