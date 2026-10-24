"""Original owner boundaries: selected native generation and idle-only SQL.
Real native constructors and harness SQL; explicit existing Windows OS-boundary
fixture, not Linux or active runtime acceptance. Deliberate SQL fixtures only.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,sqlite3
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[2];native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);checks={}
    with tempfile.TemporaryDirectory(prefix='alaz-q129-baseline-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home),APPDATA=str(home),LOCALAPPDATA=str(home))
        def audit(name,args):
            if name in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):raise PermissionError('offline_owner_control')
        sys.path[:0]=[str(root/'packages/claw-hermes'),str(root/'scripts/qa'),str(native)];sys.addaudithook(audit)
        import s124b1_startup_fixture as fixture
        import gateway_prepared_consumer as consumer
        from gateway.config import GatewayConfig,PlatformConfig
        f=fixture.NativeFixture(native,home,loop);o=f.startup
        try:
            try:loop.run_until_complete(o.prepare_runtime(GatewayConfig(multiplex_profiles=False,write_sessions_json=False),PlatformConfig(extra={'key':'test'})))
            except consumer.PreparedConsumerRejected as exc:checks['default_prepared_pin_refuses_1b7']=str(exc)=='consumer_source_unqualified'
            else:checks['default_prepared_pin_refuses_1b7']=False
            try:o.close()
            except consumer.PreparedConsumerRejected:checks['failed_source_retains_original_owner']=o._stage=='VERIFIED' and o._prepared_consumer._stage=='FAILED_UNKNOWN'
            else:checks['failed_source_retains_original_owner']=False
            state,replay,response=f.stores
            state.create_session('q129-owned','api_server')
            import hermes_state_runtime as rt
            row=rt.admit_session_input(state,epoch=o.expectation.epoch,principal_id='api',session_id='q129-owned',request_id='baseline-pending',payload={'text':'owned SQL baseline'})
            try:fixture.startup.live.verify_live_stores(f.held,f.mount,state,replay,o.expectation)
            except fixture.startup.live.LiveStoreRejected as exc:checks['clean_only_gate_refuses_queued_admission']=str(exc)=='live_store_unresolved_admissions'
            else:checks['clean_only_gate_refuses_queued_admission']=False
            response._conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('pending',?,1,'null')",('c'*64,));response._conn.commit()
            try:fixture.startup.response_live.verify_response_connection(f.held,f.mount,state,response,o._response_live_expectation())
            except fixture.startup.response_live.ResponseLiveRejected as exc:checks['clean_only_response_refuses_pending_identity']=str(exc)=='response_live_unsettled_identity'
            else:checks['clean_only_response_refuses_pending_identity']=False
            checks['pending_records_not_changed']=rt.get_session_admission(state,admission_id=row['admission_id'])['status']=='queued' and response._conn.execute('SELECT settled_at FROM response_keys').fetchone()[0] is None
            checks['caller_connections_and_lease_retained']=all(c.execute('SELECT 1').fetchone()[0]==1 for c in f.connections) and f.owner.owns(home)
            assert len(checks)==6 and all(checks.values()),checks
        finally:f.cleanup_fixture()
        imports={}
        for mod in tuple(sys.modules.values()):
            path=getattr(mod,'__file__',None)
            if path:
                q=Path(path).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        names=('packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_prepared_consumer.py','packages/claw-hermes/gateway_live_store_gate.py','packages/claw-hermes/gateway_response_live.py','scripts/qa/s124b1_startup_fixture.py','scripts/qa/q129c6_owner_baseline.py')
        result={'result':'PASS_ORIGINAL_OWNER_BOUNDARY_CONTROL','checks':checks,'sourceHashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},'nativeImports':imports,'nativeFeature':'1b7b31e14451baf1d56c3edbfa2cea69a8f7940c','boundaryDoubles':'Windows actor/lease metadata/mount/layout/cold helper only via existing s124 fixture','actualNativeOwnerAndSql':True,'sourceDefaultNotBug':True,'fullLinuxAcceptance':False,'providerCalls':0,'activeWorkExecuted':False,'profileReleased':not f.owner.homes}
    loop.run_until_complete(loop.shutdown_default_executor());loop.close();result['temporaryProfileRemoved']=not home.exists()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('sourceHashes','nativeImports')}),flush=True)
if __name__=='__main__':main()
