"""Fixed new F126C1 dedicated-lab setup and one acceptance run.
Only fresh owned paths. No old cleanup/reconciliation or default distro action.
Third-party installer executes as UID23001, never root. Runtime is root-owned.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,io,json,os,shutil,stat,subprocess,sys,tempfile,zipfile

D='AlazHarness-D3B-P71C'
ROOT=Path('/opt/alaz-f126c1a6');RUN=Path('/srv/alaz-f126c1a6');GROUP=Path('/sys/fs/cgroup/alaz-f126c1a6')

def main():
    p=argparse.ArgumentParser();p.add_argument('--sha256',required=True);a=p.parse_args()
    assert os.getresuid()==(0,)*3 and os.environ.get('WSL_DISTRO_NAME')==D
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()==D and not Path('/mnt/c/Windows').exists()
    assert Path('/proc/self/uid_map').read_text().split()==['0','0','4294967295']
    assert not ROOT.exists() and not RUN.exists() and not GROUP.exists(),'new_owned_paths_must_be_absent'
    raw=sys.stdin.buffer.read(35_000_001);assert len(raw)<=35_000_000 and hashlib.sha256(raw).hexdigest()==a.sha256
    z=zipfile.ZipFile(io.BytesIO(raw));manifest=json.loads(z.read('transport-manifest.json'))
    assert len(manifest['files'])<1800 and set(z.namelist())==set(manifest['files'])|{'transport-manifest.json'}
    assert sum(i.file_size for i in z.infolist())<70_000_000
    for n,h in manifest['files'].items():
        rel=PurePosixPath(n);assert not rel.is_absolute() and '..' not in rel.parts and chr(92) not in n and ':' not in n
        assert not stat.S_ISLNK(z.getinfo(n).external_attr>>16)
        assert hashlib.sha256(z.read(n)).hexdigest()==h
    envelope=json.loads(z.read('config/prepared-consumer-s124b1-sources.json'))
    assert envelope['nativeFeature']=='1e97dd617b81120255304e472ce322befcdb9ccd'
    assert {n.removeprefix('native/'):h for n,h in manifest['files'].items() if n.startswith('native/')}==envelope['sources']
    lock=json.loads(z.read('lock.json'));expected=json.loads(z.read('accepted-installed-files.json'))
    ROOT.mkdir(mode=0o755)
    sources={}
    for n,h in manifest['files'].items():
        if not n.startswith(('native/','packages/','scripts/','config/')):continue
        dest=ROOT/n;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(z.read(n))
        dest.chmod(0o644);sources[n]=h
    setup_result={}
    with tempfile.TemporaryDirectory(prefix='alaz-f126c1-build-') as name:
        build=Path(name);os.chown(build,23001,23003);build.chmod(0o700)
        for n,h in manifest['files'].items():
            if not n.startswith(('wheels/','tools/')) and n!='requirements.txt':continue
            dest=build/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n));dest.chmod(0o644)
        for folder in ('dependencies','tmp','home'):
            p=build/folder;p.mkdir();os.chown(p,23001,23003);p.chmod(0o700)
        tool=next(v for v in lock['wheels'] if v['purpose']=='installer-tool')
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(build/'home'),'HERMES_HOME':str(build/'home'),'TMPDIR':str(build/'tmp'),'PYTHONUTF8':'1','TZ':'UTC','WSL_DISTRO_NAME':D}
        boot="import sys;sys.path.insert(0,sys.argv.pop(1));from pip._internal.cli.main import main;raise SystemExit(main(sys.argv[1:]))"
        args=[sys.executable,'-I','-B','-c',boot,str(build/'tools'/tool['filename']),'--isolated','--disable-pip-version-check','install','--no-index','--no-deps','--only-binary=:all:','--require-hashes','--no-compile','--no-warn-script-location','--find-links',str(build/'wheels'),'--target',str(build/'dependencies'),'-r',str(build/'requirements.txt')]
        r=subprocess.run(args,user=23001,group=23003,extra_groups=[],env=env,cwd=build,capture_output=True,text=True,timeout=100)
        setup_result={'exitCode':r.returncode,'stdout':r.stdout[-10000:],'stderr':r.stderr[-3000:],'installerUid':23001}
        assert r.returncode==0,setup_result
        actual={p.relative_to(build/'dependencies').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (build/'dependencies').rglob('*') if p.is_file()}
        assert actual==expected,'installed_bytes_differ_from_L125_acceptance'
        for n,h in actual.items():
            source=build/'dependencies'/n;assert not source.is_symlink()
            dest=ROOT/'dependencies'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes());dest.chmod(0o644);sources['dependencies/'+n]=h
    assert not build.exists();z.close()
    for current,folders,names in os.walk(ROOT):
        p=Path(current);assert not p.is_symlink();os.chown(p,0,0);p.chmod(0o755)
        for n in names:
            p=Path(current)/n;assert not p.is_symlink();os.chown(p,0,0);p.chmod(0o644)
    with (ROOT/'input-manifest.json').open('x',encoding='utf-8') as f:json.dump({'sources':sources,'nativePin':envelope['nativeFeature'],'transportSha256':a.sha256},f,indent=2);f.write('\n')
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in sources.items())
    sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
    import provider_egress,state_volume_supervisor  # Complete fixed controller imports before image/process creation.
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/','WSL_DISTRO_NAME':D}
    r=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/qa/f126c1_accept.py')],cwd='/',env=env,capture_output=True,text=True,timeout=300)
    result={'setup':setup_result,'nativeExitCode':r.returncode,'nativeStdout':r.stdout,'nativeStderr':r.stderr,
            'sources':sources,'transportSha256':a.sha256,'installedBytesMatchPriorAcceptedTarget':True,
            'sourceBytesUnchanged':all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in sources.items()),
            'rootSetupOnlyApprovedDedicatedLab':True,'newOwnPrefix':str(ROOT),'defaultUbuntuChanged':False}
    (ROOT/'bootstrap-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
    return 0 if r.returncode==0 and result['sourceBytesUnchanged'] else 1
if __name__=='__main__':raise SystemExit(main())
