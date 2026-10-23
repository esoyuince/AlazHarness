"""Actual Linux cold/profile/mount/owner-consumer lifecycle, NOT namespace confinement.
No patching/mocking or source-pin changes. Trusted fixture seeds only fresh dummy
stores; real fixed helper processes and existing product checks run unchanged.
"""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,traceback
from pathlib import Path
from dataclasses import replace,asdict
ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    assert sys.platform=='linux' and os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    os.umask(0o077);loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
    events=[];denied=[];children=[];connections=[];checks={};error=None;held=owner=None;phase='INITIAL'
    before_mounts=Path('/proc/self/mountinfo').read_bytes()
    before_ns={name:os.readlink('/proc/self/ns/'+name) for name in ('mnt','net','ipc','user')}
    watch=False;opens=[]
    def audit(event,values):
        if event=='subprocess.Popen':
            command=values[1]
            allowed=[sys.executable,'-I','-B']
            if isinstance(command,(list,tuple)) and list(command[:3])==allowed and len(command)==4 and command[3] in (str(ROOT/'scripts/run_store_preopen.py'),str(ROOT/'scripts/run_response_preopen.py')):
                children.append({'commandName':Path(command[3]).name,'scope':'existing fixed cold read-only helper'});return
            denied.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=6)]});raise PermissionError('unqualified_subprocess')
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','os.system'):
            denied.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=6)]});raise PermissionError('owned_lifecycle_offline')
        if watch and event=='sqlite3.connect':raise AssertionError('consumer_opened_fourth_connection')
        if watch and event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(values[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                opens.append(name);raise AssertionError('consumer_raw_database_open')
    with tempfile.TemporaryDirectory(prefix='alaz-l125p1-owner-') as temp:
        home=Path(temp).resolve();home.chmod(0o700);os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home))
        sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(native)];sys.addaudithook(audit)
        try:
            phase='TRUSTED_FIXTURE_SEED'
            from gateway.runtime_ownership import process_ownership
            from hermes_state import SessionDB
            from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
            from gateway.platforms.api_server_response_store import ResponseStore
            import gateway_store_startup as startup
            import gateway_profile_lease as lease
            import gateway_storage_mounts as mounts
            import gateway_native_layout as layout
            import gateway_prepared_consumer as consumer
            (home/'gateway.lock').touch(mode=0o600,exist_ok=False);process_ownership.reserve([home])
            state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'));response=ResponseStore(db_path=str(home/'response_store.db'),canonical_state=state,max_size=100,max_identities=1000)
            def identity(name):
                info=(home/name).stat();return info.st_dev,info.st_ino
            expected=startup.live.PreparedStoreExpectation(startup.live.NATIVE_PIN,startup.live.schema_digest(state._conn),startup.live.schema_digest(replay._conn),state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0],state._conn.execute('PRAGMA application_id').fetchone()[0],identity('state.db'),identity('runs_idempotency.db'),0,None)
            response_expected=startup.response_preopen.PreparedResponseExpectation(startup.response_preopen.NATIVE_FEATURE,startup.response_preopen.SCHEMA_SHA256,identity('response_store.db'))
            checks['trusted_fresh_seed_schema_matches_fixed_response']=startup.live.schema_digest(response._conn)==response_expected.schema_sha256
            response.close();replay.close();state.close();process_ownership.close()
            phase='ACTUAL_MOUNT_AND_LEASE'
            record=mounts.select_mount(mounts.parse_mountinfo(mounts._read_mountinfo()),str(home))
            mount=mounts.ExpectedMount(record.mount_id,record.device,record.root,record.mount_point,record.filesystem)
            held=lease.reserve_profile(home,mount);checks['actual_native_linux_lease']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
            checks['actual_qualified_filesystem']=mount.filesystem=='ext4'
            inventory=layout.inspect_profile(home,uid=23001,gid=23003,device=home.stat().st_dev,include_response=True)
            checks['actual_finite_layout']=set(inventory)==layout.REQUIRED|{'profile','response_store.db'}
            phase='WRONG_COLD_SCHEMA_CONTROL'
            wrong=startup.NativeStoreStartup(held,mount,replace(expected,state_schema_sha256='f'*64),instance_id='l125p1-refused',response_expected=response_expected)
            try:wrong.start()
            except startup.StoreStartupRejected:checks['wrong_schema_refused_before_parent_open']=wrong._state is None and not wrong._epoch_attempted
            else:raise AssertionError('wrong_schema_was_accepted')
            wrong.close();checks['negative_preserves_lease']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
            phase='ACTUAL_COLD_START'
            owner=startup.NativeStoreStartup(held,mount,expected,instance_id='l125p1-owner',response_expected=response_expected)
            started=owner.start();events.append({'phase':'owner_started','receipt':started})
            checks['actual_all_cold_and_live_checks']=started['completedChecks']==['preflight','response_preflight','before_epoch','response_before_epoch','after_epoch','response_after_epoch']
            checks['accepted_epoch_once']=owner.expectation.epoch==1
            stores=(owner.state_store,owner.replay_store,owner.response_store);connections=tuple(store._conn for store in stores)
            from gateway.config import GatewayConfig,PlatformConfig
            phase='PREPARED_CONSUMER'
            async def lifecycle():
                nonlocal watch
                initial=[c.total_changes for c in connections];watch=True
                try:
                    c=await owner.prepare_runtime(GatewayConfig(multiplex_profiles=False,write_sessions_json=False),PlatformConfig(extra={'key':'owned-linux-fixture','model_name':'offline'}))
                    c.check();events.append({'phase':'consumer_attached','receipt':c.status()})
                    checks['same_three_connections']=all(a is b for a,b in zip(c._connections,connections))
                    checks['no_second_epoch']=owner.state_store._conn.execute('SELECT epoch FROM runtime_epoch').fetchone()[0]==1
                    try:owner.close()
                    except (startup.StoreStartupRejected,consumer.PreparedConsumerRejected):checks['original_close_blocks_attached_consumer']=owner._stage=='VERIFIED'
                    else:raise AssertionError('owner_closed_attached_consumer')
                    for conn in connections:
                        watch=False;conn.execute('BEGIN IMMEDIATE');watch=True
                        try:
                            try:await c.detach()
                            except (startup.StoreStartupRejected,consumer.PreparedConsumerRejected):assert conn.in_transaction and c._stage=='ATTACHED'
                            else:raise AssertionError('transaction_was_discarded')
                        finally:watch=False;conn.rollback();watch=True
                    checks['all_three_transactions_retained']=True
                    await c.detach();checks['api_then_runner_detached']=(c._bundle._stage,c._binding._stage,c._stage)==('DETACHED','DETACHED','DETACHED')
                    checks['same_handles_alive_after_detach']=all(conn.execute('SELECT 1').fetchone()[0]==1 for conn in connections)
                    checks['consumer_zero_row_changes']=initial==[conn.total_changes for conn in connections]
                    checks['consumer_no_raw_database_opens']=not opens
                finally:watch=False
                events.append({'phase':'consumer_detached','receipt':c.status()})
                original=connections[2].execute('PRAGMA application_id').fetchone()[0];connections[2].execute('PRAGMA application_id=7')
                try:
                    try:owner.close()
                    except (startup.StoreStartupRejected,consumer.PreparedConsumerRejected):checks['postdetach_header_drift_blocks_close']=owner._stage=='VERIFIED'
                    else:raise AssertionError('postdetach_drift_accepted')
                finally:connections[2].execute('PRAGMA application_id='+str(original))
                owner.close();events.append({'phase':'stores_closed','receipt':owner.status()})
            loop.run_until_complete(lifecycle());phase='CLOSED_LEASE_RETAINED'
            closed=0
            for conn in connections:
                try:conn.execute('SELECT 1')
                except sqlite3.ProgrammingError:closed+=1
            checks['all_three_closed']=closed==3;checks['lease_retained_after_stores']=held.check()['state']=='NATIVE_PROFILE_RESERVED'
            held.finish();checks['profile_released_only_by_caller']=not process_ownership.homes
            checks['same_mount_table']=Path('/proc/self/mountinfo').read_bytes()==before_mounts
            checks['no_namespace_reconfiguration']={name:os.readlink('/proc/self/ns/'+name) for name in before_ns}==before_ns
            checks['no_model_or_service_authority']=not started['runtimeAdmissionAuthorized']
            phase='COMPLETE'
        except BaseException as exc:
            error={'phase':phase,'type':type(exc).__name__,'message':str(exc)[:600],'traceback':traceback.format_exc()[-12000:]}
        finally:
            watch=False
            loop.run_until_complete(loop.shutdown_default_executor());loop.close()
            # Diagnostic fixture-only cleanup; never a successful product close on failure.
            for store in reversed(locals().get('stores',())):
                try:store.close()
                except sqlite3.ProgrammingError:pass
            if 'process_ownership' in locals():process_ownership.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            file=getattr(mod,'__file__',None)
            if file:
                path=Path(file).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        report={'result':'PASS_REAL_LINUX_OWNER_LIFECYCLE_NOT_CONFINEMENT' if error is None and all(checks.values()) else 'FAIL','phase':phase,'checks':checks,'checkCount':len(checks),'error':error,'events':events,'coldHelpers':children,'deniedDiagnostics':denied,'nativeImports':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'actualLinuxActorLeaseMountLayoutColdHelpersAndLiveSql':True,'productOrNativeMethodsDoubled':False,'namespaceConfinementTested':False,'physicalDurabilityTested':False,'serviceOrAdmissionActivated':False,'rootUsed':False,'providerCalls':0,'fixtureCleanupAfterFailure':error is not None}
    report['temporaryProfileRemoved']=not home.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','events','deniedDiagnostics')}),flush=True)
    return 0 if report['result'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
