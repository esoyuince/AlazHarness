"""Fixed ordinary-user transfer for the L139 finite owner experiment.
No installs/root/system writes. Output is original child data, not an inferred PASS.
"""
import argparse,hashlib,io,json,os,stat,subprocess,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sha256',required=True);parser.add_argument('--compute-failure',action='store_true');a=parser.parse_args()
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C' and Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    assert not Path('/mnt/c/Windows').exists() and sys.flags.isolated and sys.dont_write_bytecode
    raw=sys.stdin.buffer.read(35_000_001);assert len(raw)<=35_000_000 and hashlib.sha256(raw).hexdigest()==a.sha256
    archive=zipfile.ZipFile(io.BytesIO(raw));names=archive.namelist();manifest=json.loads(archive.read('transport-manifest.json'))
    assert len(names)==len(set(names))<1300 and set(names)==set(manifest['files'])|{'transport-manifest.json'}
    assert sum(i.file_size for i in archive.infolist())<70_000_000
    for name,h in manifest['files'].items():
        rel=PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in name and ':' not in name
        assert name.startswith(('native/','harness/')) or name=='accepted-dependencies.json'
        assert not stat.S_ISLNK(archive.getinfo(name).external_attr>>16) and hashlib.sha256(archive.read(name)).hexdigest()==h
    deps=Path('/opt/alaz-f126c1a6/dependencies');expected=json.loads(archive.read('accepted-dependencies.json'))
    assert {p.relative_to(deps).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in deps.rglob('*') if p.is_file()}==expected and len(expected)==1162
    with tempfile.TemporaryDirectory(prefix='alaz-l139c6-transfer-') as folder:
        root=Path(folder);os.umask(0o077)
        for name in manifest['files']:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.read(name))
        archive.close();(root/'tmp').mkdir();(root/'envhome').mkdir()
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(root/'envhome'),'HERMES_HOME':str(root/'envhome'),'TMPDIR':str(root/'tmp'),'TMP':str(root/'tmp'),'TEMP':str(root/'tmp'),'PYTHONUTF8':'1','TZ':'UTC','WSL_DISTRO_NAME':'AlazHarness-D3B-P71C'}
        script=root/'harness/scripts/qa/l139c6_linux_owner_finite.py';out=root/'result'
        entry="import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
        cmd=[sys.executable,'-I','-B','-c',entry,str(deps),str(script),'--native',str(root/'native'),'--output',str(out)]
        if a.compute_failure:cmd.append('--compute-failure')
        r=subprocess.run(cmd,cwd=root/'envhome',env=env,capture_output=True,timeout=100)
        report={'childExitCode':r.returncode,'stdout':r.stdout.decode('utf-8','replace'),'stderr':r.stderr.decode('utf-8','replace'),'artifacts':{p.relative_to(out).as_posix():p.read_text(encoding='utf-8') for p in out.rglob('*') if p.is_file() and p.stat().st_size<2_000_000} if out.exists() else {},'bundleSha256':a.sha256,'inputBytesUnchanged':all(hashlib.sha256((root/name).read_bytes()).hexdigest()==h for name,h in manifest['files'].items()),'uid':list(os.getresuid()),'gid':list(os.getresgid()),'rootUsed':False,'installedPackages':False,'kernelIsolationTested':False}
    report['temporaryTransportRemoved']=not root.exists();print('L139_TRANSPORT '+json.dumps(report),flush=True)
    return 0 if report['childExitCode']==0 and report['inputBytesUnchanged'] and report['temporaryTransportRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
