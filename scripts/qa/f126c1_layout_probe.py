"""Unprivileged original-code profile delta diagnosis, no layout rule change."""
from pathlib import Path
import argparse,asyncio,hashlib,json,os,sys,tempfile,traceback

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    assert sys.platform=='linux' and os.getresuid()==(23001,)*3
    root=Path(__file__).resolve().parents[2];native=a.native.resolve();sys.path[:0]=[str(root/'packages/claw-hermes'),str(native)]
    os.umask(0o077);loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
    snapshots=[];denied=[];owned=None;error=None
    def audit(event,args):
        if event in ('socket.bind','socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append(event);raise PermissionError('fixed_offline_layout_diagnosis')
    with tempfile.TemporaryDirectory(prefix='alaz-f126c1-layout-') as d:
        home=Path(d).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home));sys.addaudithook(audit)
        def snapshot(label):
            entries={p.relative_to(home).as_posix():{'type':'directory' if p.is_dir() else 'file','mode':oct(p.lstat().st_mode&0o777),'bytes':p.stat().st_size if p.is_file() else None} for p in home.rglob('*')}
            snapshots.append({'phase':label,'entries':entries})
        from hermes_state import SessionDB
        from gateway.runtime_ownership import process_ownership
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        import hermes_state_runtime as runtime
        import gateway_native_layout as layout
        process_ownership.reserve([home]);state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'));response=ResponseStore(db_path=str(home/'response_store.db'),canonical_state=state)
        snapshot('seeded_three_stores')
        epoch=runtime.begin_runtime_epoch(state,instance_id='layout-diagnostic')
        from gateway.config import GatewayConfig,PlatformConfig
        snapshot('config_imported')
        from gateway.run_borrowed_state import CallerOwnedRunnerState
        from gateway.run_runtime import initialize_gateway_runtime
        from gateway.run import GatewayRunner
        snapshot('runner_imported')
        try:
            config=GatewayConfig(multiplex_profiles=False,write_sessions_json=False)
            binding=CallerOwnedRunnerState(config,state,epoch=epoch,instance_id='layout-diagnostic');runner=GatewayRunner(config,caller_state=binding)
            snapshot('runner_constructed')
            authority=loop.run_until_complete(initialize_gateway_runtime(runner));snapshot('authority_prepared')
            from gateway.platforms.api_server_borrowed import BorrowedAPIStores
            from gateway.platforms.api_server import APIServerAdapter
            snapshot('api_imported')
            bundle=BorrowedAPIStores(home,state,replay,response,prepared_runner=runner)
            adapter=APIServerAdapter(PlatformConfig(extra={'key':'owned-layout-diagnostic','model_name':'offline'}),borrowed_stores=bundle)
            snapshot('api_prepared')
            loop.run_until_complete(adapter.disconnect());runner.close_all_session_db_handles();snapshot('consumer_detached')
            response.close();replay.close();state.close();snapshot('stores_closed')
            try:layout.inspect_profile(home,uid=23001,gid=23003,device=home.stat().st_dev,include_response=True)
            except layout.NativeLayoutRejected as ex:failure=str(ex)
            else:failure=None
            allowed=layout.ALLOWED|{'response_store.db','response_store.db-journal','response_store.db-wal','response_store.db-shm'}
            unexpected={n:v for n,v in snapshots[-1]['entries'].items() if n not in allowed}
        except Exception as ex:
            error={'type':type(ex).__name__,'reason':str(ex),'traceback':traceback.format_exc()[-6000:]};failure=None;unexpected={}
        finally:
            for store in (response,replay,state):
                try:store.close()
                except Exception:pass
            process_ownership.close();loop.run_until_complete(loop.shutdown_default_executor());loop.close()
        result={'result':'DIAGNOSIS_COMPLETE_NOT_ACCEPTANCE' if error is None else 'FAIL','uid':list(os.getresuid()),'snapshots':snapshots,'layoutRefusal':failure,'unexpectedFinalPaths':unexpected,'error':error,'deniedEvents':denied,'productOrPolicyModified':False,'namespaceConfinementTested':False,'rootUsed':False,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    result['temporaryRootRemoved']=not home.exists();(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='snapshots'}),flush=True)
    return 0 if error is None else 1
if __name__=='__main__':raise SystemExit(main())
