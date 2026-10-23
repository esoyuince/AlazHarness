"""Independent startup seam fixture: real native stores/start/epoch/close, explicit Windows Linux-boundary doubles."""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,traceback
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_store_startup as startup

class NativeFixture:
    def __init__(self,native,home,loop):
        self.home=home;self.loop=loop;self.stack=ExitStack();os.environ['HERMES_HOME']=str(home)
        from hermes_state import SessionDB
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.runtime_ownership import process_ownership
        self.owner=process_ownership
        self.owner.reserve([home])
        state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'))
        response=ResponseStore(db_path=str(home/'response_store.db'),canonical_state=state,max_size=100,max_identities=1000)
        def ident(name):
            s=(home/name).stat();return s.st_dev,s.st_ino
        expected=startup.live.PreparedStoreExpectation(startup.live.NATIVE_PIN,
            startup.live.schema_digest(state._conn),startup.live.schema_digest(replay._conn),
            state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0],
            state._conn.execute('PRAGMA application_id').fetchone()[0],ident('state.db'),ident('runs_idempotency.db'),0,None)
        want=startup.response_preopen.PreparedResponseExpectation(startup.response_preopen.NATIVE_FEATURE,startup.live.schema_digest(response._conn),ident('response_store.db'))
        response.close();replay.close();state.close()
        self.actor=(os.getpid(),23001,23003,threading.get_ident())
        self.mount=startup.live.mounts.ExpectedMount(11,(7,0),'/profile','/owned/profile','ext4')
        self.held=startup.live.profiles.ProfileLease.__new__(startup.live.profiles.ProfileLease)
        self.held._home=home;self.held._actor=self.actor;self.held._owner=self.owner;self.held._finished=False
        def check(lease):
            assert lease is self.held and self.owner.owns(home)
            return {'state':'NATIVE_PROFILE_RESERVED'}
        def file_identity(path,actor,wanted):
            info=path.stat();assert (info.st_dev,info.st_ino)==wanted
            return info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink
        def observation(*args):return {'mountTableSha256':'a'*64}
        self.stack.enter_context(patch.object(startup.live.profiles,'_actor',return_value=self.actor))
        self.stack.enter_context(patch.object(startup.live.profiles.ProfileLease,'check',check))
        self.stack.enter_context(patch.object(startup.layout,'inspect_profile',side_effect=lambda *a,**kw:{n:ident(n) for n in ('state.db','runs_idempotency.db','response_store.db')}))
        self.stack.enter_context(patch.object(startup.preopen,'verify_preopen',return_value={'state':'COLD_STORES_PREFLIGHT_VERIFIED'}))
        self.stack.enter_context(patch.object(startup.response_preopen,'verify_response_preopen',return_value={'state':'COLD_RESPONSE_PREFLIGHT_VERIFIED'}))
        self.stack.enter_context(patch.object(startup.live.mounts,'observe_profile_mounts',side_effect=observation))
        self.stack.enter_context(patch.object(startup.live,'_file_identity',side_effect=file_identity))
        self.stack.enter_context(patch.object(startup.response_live,'_observe',side_effect=lambda h,m,e,a:(observation(),file_identity(h/'response_store.db',a,e.identity))))
        self.startup=startup.NativeStoreStartup(self.held,self.mount,expected,instance_id='s124b1-owned',response_expected=want)
        self.start_receipt=self.startup.start()
        self.stores=(self.startup.state_store,self.startup.replay_store,self.startup.response_store)
        self.connections=tuple(s._conn for s in self.stores)
    def cleanup_fixture(self):
        # Dedicated fixture cleanup, never presented as a failed product detach success.
        for s,c in reversed(tuple(zip(self.stores,self.connections))):
            try:
                if c.in_transaction:c.rollback()
                s.close()
            except sqlite3.ProgrammingError:pass
        self.owner.close();self.stack.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
    denied=[]
    def audit(event,values):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
            raise PermissionError('s124b1_offline_fixture')
    with tempfile.TemporaryDirectory(prefix='alaz-s124b1-base-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home));sys.path.insert(0,str(native));sys.addaudithook(audit)
        from gateway.config import GatewayConfig,PlatformConfig
        from gateway.run_borrowed_state import CallerOwnedRunnerState
        from gateway.run import GatewayRunner
        from gateway.run_runtime import initialize_gateway_runtime
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores
        from gateway.platforms.api_server import APIServerAdapter
        import hermes_state_registry
        f=NativeFixture(native,home,loop)
        try:
            config=GatewayConfig(multiplex_profiles=False,write_sessions_json=False)
            state,replay,response=f.stores
            binding=CallerOwnedRunnerState(config,state,epoch=f.startup.expectation.epoch,instance_id=f.startup.expectation.instance_id)
            runner=GatewayRunner(config,caller_state=binding);loop.run_until_complete(initialize_gateway_runtime(runner))
            bundle=BorrowedAPIStores(home,state,replay,response,prepared_runner=runner)
            adapter=APIServerAdapter(PlatformConfig(extra={'key':'owned-fixture-only'}),borrowed_stores=bundle)
            before=(bundle._stage,binding._stage);f.startup.close()
            closed=0
            for c in f.connections:
                try:c.execute('SELECT 1')
                except sqlite3.ProgrammingError:closed+=1
            report={'result':'BASELINE_OWNER_HAS_NO_CONSUMER_GUARD','apiRunnerBeforeClose':before,'apiRunnerAfterClose':[bundle._stage,binding._stage],
                'closedConnectionCount':closed,'startup':f.startup.status(),'actualNativeRunnerAndStores':True,
                'nativeProductMethodsReplaced':False,'windowsLinuxLeaseMountColdBoundariesDoubled':True,
                'liveSqlStoreGatesReal':True,'linuxIsolationAccepted':False,'serviceStarted':False,'providerCalls':0,'rootWslAction':False}
            assert closed==3 and bundle._stage=='ATTACHED' and binding._stage=='PREPARED'
        finally:f.cleanup_fixture()
        report.update(profileReleased=not f.owner.homes,registry=hermes_state_registry.stats(),deniedEvents=denied)
        imports={}
        for mod in tuple(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                q=Path(name).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        report['nativeImports']=imports
    loop.run_until_complete(loop.shutdown_default_executor());loop.close()
    report['temporaryHomeRemoved']=not home.exists();report['qaSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','deniedEvents')}),flush=True)
if __name__=='__main__':main()
