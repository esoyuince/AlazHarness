"""Ordinary-user, offline syntax/import probe for a fixed source bundle.
No constructor instantiation, jobs, stores, model, network, root or confinement.
The audit hook bounds fixture effects; it is NOT a hostile-code sandbox.
"""
from pathlib import Path, PurePosixPath
import argparse, hashlib, importlib, io, json, os, stat, sys, tempfile, traceback, zipfile
FEATURE='d1516731308de8e87130dc68124e69aad35d6911'
DEPS=Path('/opt/alaz-f126c1a6/dependencies')

def validate_bundle(raw, expected_sha):
    if len(raw)>30_000_000 or hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('bundle_digest_or_size')
    archive=zipfile.ZipFile(io.BytesIO(raw));infos=archive.infolist();names=archive.namelist()
    if len(names)!=len(set(names)) or len(names)>1200 or sum(x.file_size for x in infos)>60_000_000:
        raise ValueError('bundle_shape')
    manifest=json.loads(archive.read('transport-manifest.json'))
    if set(names)!=set(manifest['files'])|{'transport-manifest.json'}:
        raise ValueError('bundle_file_set')
    for name,h in manifest['files'].items():
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or stat.S_ISLNK(archive.getinfo(name).external_attr>>16):
            raise ValueError('bundle_path')
        if not (name.startswith(('native/','harness/packages/claw-hermes/','harness/config/')) or name=='accepted-dependencies.json'):
            raise ValueError('bundle_section')
        if hashlib.sha256(archive.read(name)).hexdigest()!=h:
            raise ValueError('bundle_member_digest')
    return archive,manifest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sha256',required=True);a=parser.parse_args()
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert sys.flags.isolated and sys.dont_write_bytecode and not Path('/mnt/c/Windows').exists()
    raw=sys.stdin.buffer.read(30_000_001);archive,manifest=validate_bundle(raw,a.sha256)
    assert manifest['nativeFeature']==FEATURE
    expected=json.loads(archive.read('accepted-dependencies.json'))
    actual={p.relative_to(DEPS).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in DEPS.rglob('*') if p.is_file()}
    assert actual==expected and len(actual)==1162,'existing_dependency_bytes_changed'
    denied=[];compiled=[];native_imports={};dependency_imports={};other_packages={};error=None;stage='EXTRACT'
    with tempfile.TemporaryDirectory(prefix='alaz-l138a5-import-') as folder:
        root=Path(folder).resolve();home=root/'home';home.mkdir(mode=0o700);tmp=root/'tmp';tmp.mkdir(mode=0o700)
        for name in manifest['files']:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
        archive.close()
        native=root/'native';harness=root/'harness';packages=harness/'packages/claw-hermes'
        os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME=str(home),HERMES_HOME=str(home),USERPROFILE=str(home),APPDATA=str(home),LOCALAPPDATA=str(home),TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),LANG='C.UTF-8',TZ='UTC',WSL_DISTRO_NAME='AlazHarness-D3B-P71C')
        os.chdir(home);sys.path[:0]=[str(packages),str(native),str(DEPS)]
        def audit(event,args):
            if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system','os.exec','os.posix_spawn'):
                denied.append(event);raise PermissionError('l138_offline_import_only')
            if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
                mode=args[1];flags=args[2];write=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
                if write and not Path(os.fsdecode(args[0])).resolve().is_relative_to(root):
                    denied.append('write_outside_fixture');raise PermissionError('l138_fixture_write_boundary')
        sys.addaudithook(audit)
        try:
            stage='COMPILE'
            for name in sorted(manifest['files']):
                if name.endswith('.py'):
                    compile((root/name).read_bytes(),name,'exec',dont_inherit=True);compiled.append(name)
            stage='IMPORT'
            import gateway_prepared_consumer as consumer
            proof=consumer.qualify_sources(local_admission=True,canonical_api=True,finite_turn=True)
            selected=consumer.native_types();assert len(selected)==7
            for module in ('gateway.session_api_turn','gateway.session_finite','gateway.run_borrowed_cleanup','gateway.run_borrowed_goals','hermes_cli.goals'):
                importlib.import_module(module)
            stage='IMPORTED'
        except BaseException as exc:
            error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        for module in tuple(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if not filename:continue
            path=Path(filename).resolve()
            if not path.is_file():continue
            if path.is_relative_to(native):
                name=path.relative_to(native).as_posix();digest=hashlib.sha256(path.read_bytes()).hexdigest()
                assert manifest['files'].get('native/'+name)==digest,('unqualified_native_import',name)
                native_imports[name]=digest
            elif path.is_relative_to(DEPS):
                name=path.relative_to(DEPS).as_posix();digest=hashlib.sha256(path.read_bytes()).hexdigest();assert expected[name]==digest
                dependency_imports[name]=digest
            elif 'site-packages' in path.parts or 'dist-packages' in path.parts:
                other_packages[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        unchanged=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==h for name,h in manifest['files'].items())
        created=sorted(p.relative_to(root).as_posix() for folder in (home,tmp) for p in folder.rglob('*') if p.is_file())
        report={'result':'PASS_LINUX_SYNTAX_AND_IMPORT_ONLY' if stage=='IMPORTED' and error is None and unchanged and not other_packages else 'NOT_ACCEPTED_IMPORT_PREFLIGHT','stage':stage,'error':error,'nativeFeature':FEATURE,'uid':list(os.getresuid()),'gid':list(os.getresgid()),'python':sys.version,'bundleSha256':a.sha256,'compiledSourceCount':len(compiled),'compiledSources':compiled,'nativeImports':native_imports,'dependencyImports':dependency_imports,'unqualifiedSystemPackages':other_packages,'dependencyFileCount':len(actual),'inputBytesUnchanged':unchanged,'fixtureFilesCreated':created,'deniedEvents':denied,'constructorInstancesCreated':False,'nativeStoresOpened':False,'finiteWorkExecuted':False,'rootUsed':False,'confinementTested':False,'httpOrModelStarted':False,'systemPackagesInstalled':False}
        os.chdir('/')
    report['temporaryRootRemoved']=not root.exists()
    print('L138_RESULT '+json.dumps(report),flush=True)
    return 0 if report['result']=='PASS_LINUX_SYNTAX_AND_IMPORT_ONLY' and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
