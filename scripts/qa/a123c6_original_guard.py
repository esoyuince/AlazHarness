"""Original prepared runner/API conflict control, using fresh real native stores.
The old guard is intentional; this does not claim a defect in the default path.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,traceback
from pathlib import Path
WATCH=False
OPENS=[]
DENIED=[]
def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
        raise PermissionError('a123c6_offline_native_baseline')
    if WATCH and event=='sqlite3.connect':OPENS.append(str(args[0]));raise AssertionError('extra SQLite open')
def main():
    global WATCH
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-a123c6-baseline-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home),APPDATA=str(home/'roaming'),LOCALAPPDATA=str(home/'local'))
        sys.path.insert(0,str(native));loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.run import GatewayRunner
        from gateway.run_runtime import initialize_gateway_runtime
        from gateway.run_borrowed_state import CallerOwnedRunnerState
        from gateway.config import GatewayConfig,PlatformConfig
        from gateway.runtime_ownership import process_ownership
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        import hermes_state_runtime as runtime,hermes_state_registry as registry
        process_ownership.reserve([home]);state=SessionDB(home/'state.db');epoch=runtime.begin_runtime_epoch(state,instance_id='a123c6-baseline')
        replay=RunIdempotencyStore(str(home/'runs_idempotency.db'));response=ResponseStore(db_path=str(home/'response_store.db'),canonical_state=state)
        config=GatewayConfig(multiplex_profiles=False,write_sessions_json=False)
        before=tuple(c._conn.total_changes for c in (state,replay,response));before_epoch=tuple(state._conn.execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone())
        WATCH=True
        try:
            owner=CallerOwnedRunnerState(config,state,epoch=epoch,instance_id='a123c6-baseline')
            runner=GatewayRunner(config,caller_state=owner);authority=loop.run_until_complete(initialize_gateway_runtime(runner))
            bundle=BorrowedAPIStores(home,state,replay,response)
            adapter=APIServerAdapter(PlatformConfig(enabled=True,extra={'key':'owned-fixture-not-a-secret','model_name':'fixture','host':'127.0.0.1','port':8642}),borrowed_stores=bundle)
            assert adapter._ensure_session_db() is state
            adapter.gateway_runner=runner  # Explicit old-boundary negative fixture, not a product attachment.
            reason=None
            try:adapter._ensure_session_db()
            except BorrowedStoreRejected as exc:reason=str(exc)
            finally:adapter.gateway_runner=None
            assert reason=='borrowed_runner_conflict',reason
            result={'existingRunnerConflictRefused':True,'refusalReason':reason,'authorityStillRetiring':authority.retiring,
                    'sameCallerStateOnBothSides':runner.session_store._db is state and adapter._session_db is state,
                    'localEpochMapPresent':hasattr(runner.session_store,'_local_authority_epochs'),
                    'sqliteOpensInConstructionAndSelection':len(OPENS),'callerEpoch':epoch}
            loop.run_until_complete(adapter.disconnect());runner.close_all_session_db_handles()
            assert all(s._conn.execute('SELECT 1').fetchone()[0]==1 for s in (state,replay,response))
            assert tuple(c._conn.total_changes for c in (state,replay,response))==before
            assert tuple(state._conn.execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone())==before_epoch
            result.update(allCallerStoresOpenAfterFacadeDetach=True,epochAndRowsUnchanged=True)
        finally:
            WATCH=False
            for s in (response,replay,state):s.close()
            process_ownership.close();loop.run_until_complete(loop.shutdown_asyncgens());loop.run_until_complete(loop.shutdown_default_executor());loop.close()
        imports={}
        for module in tuple(sys.modules.values()):
            f=getattr(module,'__file__',None)
            if f:
                q=Path(f).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        result.update(nativeImports=imports,qaSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            actualNativeClasses=True,nativeMethodsReplaced=False,defaultConflictIsBug=False,registryAfter=registry.stats(),
            profileReleased=not process_ownership.homes,providerCalls=0,httpListenerStarted=False,rootWslAction=False,
            deniedOptionalImportProbes=DENIED)
    result.update(temporaryProfileRemoved=not home.exists(),result='PREPARED_RUNNER_CONFLICT_BASELINE_CONFIRMED')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('nativeImports','deniedOptionalImportProbes')}),flush=True)
if __name__=='__main__':main()
