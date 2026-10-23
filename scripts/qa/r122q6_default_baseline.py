"""Genuine default GatewayRunner baseline in an isolated temporary profile.
The normal standalone bootstrap owns a new epoch; it is a control, not a bug.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    watch=False;opens=[];denied=[]
    def audit(event,values):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
            raise PermissionError('r122q6_offline_baseline')
        if watch and event=='sqlite3.connect':opens.append(str(values[0]))
    async def scenario(home):
        nonlocal watch
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig
        from hermes_state import SessionDB
        from gateway.runtime_ownership import process_ownership
        from gateway.session_authority import initialize_session_authority
        from gateway.session_cron import unbind_owner
        import hermes_state_registry as registry
        import hermes_state_runtime as runtime
        process_ownership.reserve([home]);state=SessionDB(home/'state.db');runner=None;authority=None
        try:
            epoch=runtime.begin_runtime_epoch(state,instance_id='r122q6-caller')
            config=GatewayConfig(multiplex_profiles=False,write_sessions_json=False);watch=True
            runner=GatewayRunner(config=config);watch=False
            assert type(runner) is GatewayRunner
            own=runner.session_store._db
            assert own is not state and runner._session_db._db is own
            before=state._conn.execute('SELECT epoch FROM main.runtime_epoch').fetchone()[0]
            authority=await initialize_session_authority(runner,profile_id=str(home),instance_id='r122q6-default')
            after=state._conn.execute('SELECT epoch FROM main.runtime_epoch').fetchone()[0]
            assert after==before+1 and authority.epoch==after and authority.db is own
            report={'defaultRunnerIsReal':True,'callerEpochBefore':epoch,'defaultAuthorityEpochAfter':after,
                    'defaultIncrementsEpoch':True,'defaultRunnerUsesDifferentState':True,
                    'runnerAndSessionStoreShareDefaultRegistryState':True,'constructorSQLiteOpens':len(opens),
                    'registryDuring':registry.stats(),'defaultBehaviorIsBug':False}
        finally:
            watch=False
            if authority is not None:unbind_owner(authority)
            if runner is not None:
                runner.session_store.close_all_db_handles();runner.close_all_session_db_handles()
            assert state._conn.execute('SELECT 1').fetchone()[0]==1
            state.close();process_ownership.close()
        report.update(registryAfter=registry.stats(),profileReleased=not process_ownership.homes)
        return report
    with tempfile.TemporaryDirectory(prefix='alaz-r122q6-baseline-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home),LOCALAPPDATA=str(home/'local'),APPDATA=str(home/'roaming'))
        sys.path.insert(0,str(native))
        # Create the test event loop before the offline guard; this is not an HTTP listener.
        loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);sys.addaudithook(audit)
        try:report=loop.run_until_complete(scenario(home))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens());loop.run_until_complete(loop.shutdown_default_executor());loop.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            f=getattr(mod,'__file__',None)
            if f:
                q=Path(f).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        report.update(nativeImports=imports,deniedExternalProbes=denied,qaSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),providerCalls=0,httpListenerStarted=False,nativeMethodsReplaced=False)
    report.update(temporaryProfileRemoved=not home.exists(),result='DEFAULT_RUNNER_BASELINE_CONFIRMED')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','deniedExternalProbes')}),flush=True)
if __name__=='__main__':main()
