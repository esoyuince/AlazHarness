"""Original owner-close awareness control. Real native stores/runner/API;
Linux actor/lease/layout/cold/live verifiers explicitly doubled on Windows.
The caller deliberately omits detach in a fresh fixture; this is an integration
baseline, not permission to close real user data or a claim of Linux acceptance.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,threading,traceback
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_store_startup as startup

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);denied=[]
    def audit(event,args):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=6)]})
            raise PermissionError('c124l1_owned_offline_control')
    with tempfile.TemporaryDirectory(prefix='alaz-c124l1-control-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home));sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.runtime_ownership import process_ownership
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig,PlatformConfig
        from gateway.run_borrowed_state import CallerOwnedRunnerState
        from gateway.run_runtime import initialize_gateway_runtime
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores
        from gateway.platforms.api_server import APIServerAdapter
        import hermes_state_registry
        process_ownership.reserve([home]);state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'));response=ResponseStore(db_path=str(home/'response_store.db'),canonical_state=state,max_size=100,max_identities=1000)
        identity=lambda name:((home/name).stat().st_dev,(home/name).stat().st_ino)
        expected=startup.live.PreparedStoreExpectation(startup.live.NATIVE_PIN,startup.live.schema_digest(state._conn),startup.live.schema_digest(replay._conn),state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0],state._conn.execute('PRAGMA main.application_id').fetchone()[0],identity('state.db'),identity('runs_idempotency.db'),0,None)
        want=startup.response_preopen.PreparedResponseExpectation(startup.response_preopen.NATIVE_FEATURE,startup.response_preopen.SCHEMA_SHA256,identity('response_store.db'))
        response.close();replay.close();state.close()
        actor=(os.getpid(),23001,23003,threading.get_ident());held=startup.live.profiles.ProfileLease.__new__(startup.live.profiles.ProfileLease);held._actor=actor;held._home=home;held._owner=process_ownership
        mount=startup.live.mounts.ExpectedMount(1,(1,1),'/profile','/owned/profile','ext4')
        def lease(_):
            assert process_ownership.owns(home)
            return {'state':'NATIVE_PROFILE_RESERVED','linuxBoundaryDoubled':True}
        with ExitStack() as patches:
            patches.enter_context(patch.object(startup.live.profiles,'_actor',return_value=actor))
            patches.enter_context(patch.object(startup.live.profiles.ProfileLease,'check',lease))
            patches.enter_context(patch.object(startup.layout,'inspect_profile',side_effect=lambda *a,**k:{n:identity(n) for n in ('state.db','runs_idempotency.db','response_store.db')}))
            patches.enter_context(patch.object(startup.preopen,'verify_preopen',return_value={'state':'COLD_STORES_PREFLIGHT_VERIFIED'}))
            patches.enter_context(patch.object(startup.response_preopen,'verify_response_preopen',return_value={'state':'COLD_RESPONSE_PREFLIGHT_VERIFIED'}))
            patches.enter_context(patch.object(startup.live,'verify_live_stores',return_value={'state':'NATIVE_STORE_CONNECTIONS_VERIFIED'}))
            patches.enter_context(patch.object(startup.response_live,'verify_response_connection',return_value={'state':'NATIVE_RESPONSE_CONNECTION_VERIFIED'}))
            owner=startup.NativeStoreStartup(held,mount,expected,instance_id='c124-control',response_expected=want);owner.start()
            state,replay,response=owner.state_store,owner.replay_store,owner.response_store
            config=GatewayConfig(multiplex_profiles=False,write_sessions_json=False)
            binding=CallerOwnedRunnerState(config,state,epoch=owner.expectation.epoch,instance_id=owner.expectation.instance_id)
            runner=GatewayRunner(config,caller_state=binding);loop.run_until_complete(initialize_gateway_runtime(runner))
            bundle=BorrowedAPIStores(home,state,replay,response,prepared_runner=runner)
            adapter=APIServerAdapter(PlatformConfig(extra={'key':'fresh-control-no-service'}),borrowed_stores=bundle)
            before={'api':bundle.status()['state'],'runner':binding.status()['state'],'stores':owner.status()['state']}
            conns=(state._conn,replay._conn,response._conn);owner.close();closed=0
            for conn in conns:
                try:conn.execute('SELECT 1')
                except Exception as exc:
                    import sqlite3
                    assert isinstance(exc,sqlite3.ProgrammingError);closed+=1
            assert closed==3 and bundle.status()['state']=='ATTACHED' and binding.status()['state']=='PREPARED'
            after={'api':bundle.status()['state'],'runner':binding.status()['state'],'stores':owner.status()['state']}
            assert process_ownership.owns(home)
            result={'result':'ORIGINAL_CLOSE_AWARENESS_GAP_CONFIRMED','before':before,'after':after,'closedStoreHandles':closed,'callerLeaseRetained':True,'constructorHandlesNative':True,'nativeMethodsReplaced':False,'linuxActorLeaseLayoutColdLiveBoundariesDoubled':True,'fullLinuxAccepted':False,'serviceAdmissionOrListener':False,'upstreamDefaultBugClaimed':False,'providerCalls':0,'rootWslAction':False,'deniedOptionalDiagnostics':denied}
        process_ownership.close();loop.run_until_complete(loop.shutdown_default_executor());loop.close()
        result['nativeOwnershipReleased']=not process_ownership.homes;result['registry']=hermes_state_registry.stats()
        result['nativeImports']={}
        for mod in tuple(sys.modules.values()):
            path=getattr(mod,'__file__',None)
            if path:
                path=Path(path).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':result['nativeImports'][path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    result['temporaryProfileRemoved']=not home.exists();result['sourceHashes']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('packages/claw-hermes/gateway_store_startup.py','scripts/qa/c124l1_original_close_control.py')}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('nativeImports','deniedOptionalDiagnostics')}),flush=True)
if __name__=='__main__':main()
