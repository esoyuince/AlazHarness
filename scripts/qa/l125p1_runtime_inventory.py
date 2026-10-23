"""Import-only native runtime inventory; explicit temp home, no store/service/model."""
import argparse,hashlib,importlib.metadata,importlib.util,json,os,platform,sys,tempfile,traceback
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    denied=[]
    def audit(event,values):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]});raise PermissionError('owned_inventory_offline')
    with tempfile.TemporaryDirectory(prefix='alaz-l125p1-inventory-') as temp:
        home=Path(temp);os.environ.update(HERMES_HOME=temp,HOME=temp,USERPROFILE=temp);sys.path.insert(0,str(native));sys.addaudithook(audit)
        phases=[];error=None
        for name in ('hermes_state','gateway.config','gateway.run','gateway.platforms.api_server','gateway.platforms.api_server_prepared'):
            try:__import__(name);phases.append(name)
            except Exception as exc:
                error={'module':name,'type':type(exc).__name__,'message':str(exc)[:500],'missingName':getattr(exc,'name',None),'traceback':traceback.format_exc()[-6000:]};break
        origins={}
        for name,mod in tuple(sys.modules.items()):
            file=getattr(mod,'__file__',None)
            if file and Path(file).is_file():
                p=Path(file).resolve()
                if p.is_relative_to(native):continue
                if 'site-packages' in str(p) or 'dist-packages' in str(p):origins[name]={'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nativeBinary':p.suffix.lower() in ('.pyd','.so','.dll')}
        mapping=importlib.metadata.packages_distributions();used={dist for name in origins for dist in mapping.get(name.split('.')[0],[])}
        dists={}
        for name in sorted(used):
            d=importlib.metadata.distribution(name)
            dists[name]={'version':d.version,'requires':d.requires or [],'requiresPython':d.metadata.get('Requires-Python'),'wheel':d.read_text('WHEEL'),'metadataSha256':hashlib.sha256((d.read_text('METADATA') or '').encode()).hexdigest(),'binaryFiles':[str(p) for p in (d.files or []) if str(p).endswith(('.pyd','.so','.dll'))]}
        report={'scope':'import and dependency provenance only, not owner lifecycle or confinement','platform':sys.platform,'python':sys.version,'machine':platform.machine(),'completedImports':phases,'error':error,'thirdPartyImports':origins,'distributions':dists,'deniedDiagnostics':denied,'providerCalls':0,'serviceStarted':False,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report['temporaryHomeRemoved']=not home.exists();report['result']='PASS_IMPORT_ONLY' if error is None else 'IMPORT_BLOCKED'
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('thirdPartyImports','distributions','deniedDiagnostics')}),flush=True)
    print('DISTRIBUTIONS',json.dumps({n:{'version':v['version'],'nativeBinaryFiles':len(v['binaryFiles'])} for n,v in dists.items()}),flush=True)
    return 0 if error is None else 1
if __name__=='__main__':raise SystemExit(main())
