"""Fixed ordinary-user Linux bundle probe. Offline wheel target only, no system install.
Input is an exact SHA256-bound archive from the checked-in source/wheel manifests.
The executed modes remain import/prerequisite-native only, never confinement proof.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,io,json,os,platform,stat,subprocess,sys,tempfile,zipfile

def main():
    p=argparse.ArgumentParser();p.add_argument('--sha256',required=True);p.add_argument('--mode',choices=('import','prepared','owner'),required=True);args=p.parse_args()
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    assert os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3 and not Path('/mnt/c').exists()
    assert sys.version_info[:2]==(3,12) and platform.machine()=='x86_64'
    raw=sys.stdin.buffer.read(50_000_001);assert len(raw)<=50_000_000 and hashlib.sha256(raw).hexdigest()==args.sha256
    report={'mode':args.mode,'bundleSha256':args.sha256,'uid':os.getresuid(),'gid':os.getresgid(),'python':sys.version,'kernel':platform.release(),'rootUsed':False,'globalInstallPerformed':False,'namespaceConfinementTested':False}
    with tempfile.TemporaryDirectory(prefix='alaz-l125p1-bundle-') as temp:
        root=Path(temp);archive=zipfile.ZipFile(io.BytesIO(raw));names=archive.namelist()
        assert len(names)==len(set(names)) and len(names)<=2000
        manifest=json.loads(archive.read('transport-manifest.json'));assert set(names)==set(manifest['files'])|{'transport-manifest.json'}
        assert sum(i.file_size for i in archive.infolist())<100_000_000
        for name,h in manifest['files'].items():
            rel=PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in name
            assert rel.parts[0] in ('native','harness','wheels','tools') or name in ('requirements.txt','lock.json')
            info=archive.getinfo(name);assert not stat.S_ISLNK(info.external_attr>>16)
            data=archive.read(name);assert hashlib.sha256(data).hexdigest()==h
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        archive.close()
        deps=root/'dependencies';deps.mkdir();scratch=root/'tmp';scratch.mkdir();home=root/'home';home.mkdir()
        lock=json.loads((root/'lock.json').read_text());pip=next(x for x in lock['wheels'] if x['purpose']=='installer-tool')
        pipwheel=root/'tools'/pip['filename'];assert hashlib.sha256(pipwheel.read_bytes()).hexdigest()==pip['sha256']
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(home),'USERPROFILE':str(home),'HERMES_HOME':str(home),'TMPDIR':str(scratch),'PYTHONUTF8':'1','TZ':'UTC','WSL_DISTRO_NAME':'AlazHarness-D3B-P71C'}
        boot="import sys;sys.path.insert(0,sys.argv.pop(1));from pip._internal.cli.main import main;raise SystemExit(main(sys.argv[1:]))"
        install=[sys.executable,'-I','-B','-c',boot,str(pipwheel),'--isolated','--disable-pip-version-check','install','--no-index','--no-deps','--only-binary=:all:','--require-hashes','--no-compile','--no-warn-script-location','--find-links',str(root/'wheels'),'--target',str(deps),'-r',str(root/'requirements.txt')]
        done=subprocess.run(install,cwd=root,env=env,capture_output=True,text=True,timeout=100)
        report['offlineInstall']={'exitCode':done.returncode,'stdout':done.stdout[-10000:],'stderr':done.stderr[-4000:]}
        if done.returncode==0:
            paths={'import':'l125p1_runtime_inventory.py','prepared':'b123a6_native_prepared_api.py','owner':'f126c1_layout_probe.py'}
            script=root/'harness/scripts/qa'/paths[args.mode];assert script.is_file()
            output=root/'result'
            driver="import sys,runpy;deps,script=sys.argv[1:3];sys.path.insert(0,deps);sys.argv=sys.argv[2:];runpy.run_path(script,run_name='__main__')"
            command=[sys.executable,'-I','-B','-c',driver,str(deps),str(script),'--native',str(root/'native'),'--output',str(output)]
            run=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=210)
            report['execution']={'exitCode':run.returncode,'stdout':run.stdout[-16000:],'stderr':run.stderr[-16000:]}
            report['artifacts']={p.relative_to(output).as_posix():p.read_text(encoding='utf-8') for p in output.rglob('*') if p.is_file() and p.stat().st_size<2_000_000} if output.exists() else {}
            loaded=json.loads(report['artifacts']['result.json']) if 'result.json' in report['artifacts'] else None
            report['childResult']=None if loaded is None else {k:v for k,v in loaded.items() if k not in ('nativeImports','sourceHashes','thirdPartyImports','distributions','deniedDiagnostics','deniedEvents','checks','caseEnd','observations')}
            installed={}
            for metadata in deps.glob('*.dist-info/METADATA'):
                import email
                m=email.message_from_bytes(metadata.read_bytes());installed[m['Name']]=m['Version']
            report['installedDistributions']=installed
            report['inputBytesUnchanged']=all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in manifest['files'].items())
            depfiles={p.relative_to(deps).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in deps.rglob('*') if p.is_file()}
            report['installedFileCount']=len(depfiles);report['installedFileManifestSha256']=hashlib.sha256(json.dumps(depfiles,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            report['installedFileHashes']=depfiles
    report['temporaryRootRemoved']=not root.exists()
    report['result']='PASS_'+args.mode.upper()+'_PREREQUISITE_ONLY' if report['offlineInstall']['exitCode']==0 and report.get('execution',{}).get('exitCode')==0 and report.get('inputBytesUnchanged') and report['temporaryRootRemoved'] else 'FAIL'
    print(json.dumps(report),flush=True)
    return 0 if report['result'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
