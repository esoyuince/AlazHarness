"""Original native SessionStore open/ownership baseline in a fresh owned profile.

The normal multi-profile SessionStore intentionally acquires a registry handle.
This is a comparison control, not a claimed upstream bug or product acceptance.
"""
import argparse,os,sys,json,tempfile,hashlib
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    events=[];watch=False
    def audit(name,values):
        if name in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):raise PermissionError('offline_owned_baseline')
        if watch and name=='sqlite3.connect':events.append(str(values[0]))
    with tempfile.TemporaryDirectory(prefix='alaz-s121s1-base-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home))
        sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.session import SessionStore
        from gateway.config import GatewayConfig
        from gateway.runtime_ownership import process_ownership
        import hermes_state_registry as registry
        process_ownership.reserve([home]);db=SessionDB(home/'state.db');store=None
        try:
            before=registry.stats();watch=True
            store=SessionStore(home/'sessions',GatewayConfig())
            watch=False;selected=store._db
            result={'originalCreatesDifferentHandle':selected is not db,'sqliteOpensDuringSessionStoreConstruction':len(events),
                'openedPaths':events,'registryBefore':before,'registryAfterConstruction':registry.stats()}
            assert selected is not db and len(events)==1
            store.close_all_db_handles();store=None
            assert db._conn.execute('SELECT 1').fetchone()[0]==1
            result['callerStateRetainedAfterDefaultCacheClose']=True
        finally:
            watch=False
            if store is not None:store.close_all_db_handles()
            db.close();process_ownership.close()
        result.update(registryAfterClose=registry.stats(),profileOwnerReleased=not process_ownership.homes)
        sources={}
        for mod in tuple(sys.modules.values()):
            f=getattr(mod,'__file__',None)
            if f:
                q=Path(f).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':sources[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        result.update(nativeSources=sources,qaSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),nativeClassesReplaced=False,defaultBehaviorIsBug=False,providerCalls=0,rootWslAction=False)
    result['temporaryProfileRemoved']=not home.exists();result['result']='BASELINE_CONFIRMED'
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='nativeSources'}),flush=True)
if __name__=='__main__':main()
