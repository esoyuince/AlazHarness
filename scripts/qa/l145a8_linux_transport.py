"""Fixed ordinary-user negative experiment transport: own temp files only, no installs."""
from pathlib import Path,PurePosixPath
import hashlib,io,json,os,shutil,subprocess,sys,tempfile,zipfile
assert sys.platform=='linux' and sys.executable=='/usr/bin/python3.12' and sys.flags.isolated
assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
assert len(sys.argv)==2
raw=sys.stdin.buffer.read(3*1024*1024+1);assert 0<len(raw)<=3*1024*1024 and hashlib.sha256(raw).hexdigest()==sys.argv[1]
root=Path(tempfile.mkdtemp(prefix='alaz-l145-negative-'));root.chmod(0o700);results=[];failed=False
try:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert len(z.namelist())==len(set(z.namelist()))<=80
        manifest=json.loads(z.read('manifest.json'));assert set(manifest)=={'files'}
        assert set(z.namelist())==set(manifest['files'])|{'manifest.json'}
        for name,digest in manifest['files'].items():
            p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts and str(p)==name
            assert (len(p.parts)==3 and p.parts[:2]==('packages','claw-hermes') and p.suffix=='.py') or name in ('scripts/run_retained_projected.py','scripts/qa/l145a8_linux_refusal.py')
            assert z.getinfo(name).file_size<=256*1024
            data=z.read(name);assert hashlib.sha256(data).hexdigest()==digest
            dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data);dst.chmod(0o600)
    for case in ('missing','malformed','extra-environment','foreign-pid','ordinary-unconfined'):
        r=subprocess.run(['/usr/bin/python3.12','-I','-B',str(root/'scripts/qa/l145a8_linux_refusal.py'),'--case',case],
            cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True,timeout=20)
        lines=[line.removeprefix('L145_NEGATIVE ') for line in r.stdout.decode('utf-8','replace').splitlines() if line.startswith('L145_NEGATIVE ')]
        result=json.loads(lines[-1]) if lines else None
        if result:
            for name,h in result['loadedSources'].items():assert manifest['files'][name]==h
        results.append({'case':case,'exitCode':r.returncode,'result':result,'stdout':r.stdout.decode('utf-8','replace'),'stderr':r.stderr.decode('utf-8','replace')})
        failed=failed or r.returncode!=0 or result is None
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in manifest['files'].items())
finally:
    shutil.rmtree(root)
print('L145_TRANSPORT '+json.dumps({'result':'PASS' if not failed else 'FAIL','cases':results,'sourceHashes':manifest['files'],'allTransferredSourcesUnchanged':True,'temporaryOwnedDirectoryRemoved':not root.exists(),'rootUsed':False,'kernelOrInstallActions':False}),flush=True)
raise SystemExit(1 if failed else 0)
