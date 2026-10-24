"""Same real original owner with source-qualified native API publication.
The inherited Windows fixture doubles Linux actor/lease metadata/mount/cold helpers.
Real API admission writes are not finite-turn execution. Explicit leaf settlement
and post-effect/cleanup fault barriers are declared. No model/listener/provider.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,unittest,threading
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/qa'),str(ROOT/'packages/claw-hermes')]
import b129d6_native_active_owner as f
OBS=[]

class ApiOwnerCases(f.ActiveOwnerCases):
    def prepare(self,*,publish=True,**kw):
        c=f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True,canonical_api=True,**kw))
        if publish:self.call(c.publish_api_adapter)
        return c
    def api_admit(self,c,*,session='i133-api',request='i133-request',text='bounded payload'):
        from gateway.session_api_turn import admit_api_turn_async
        async def run():
            try:return await admit_api_turn_async(c._adapter,session_id=session,request_id=request,user_message=text,conversation_history=[])
            finally:
                await asyncio.sleep(0)
                jobs=list(getattr(c._runner.session_authority,'_mutation_tasks',()))
                if jobs:await asyncio.gather(*jobs,return_exceptions=True)
                await asyncio.sleep(0)
        return f.LOOP.run_until_complete(run())
    def snapshots(self):return [hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest() for db in self.f.connections]
    def settle_fixture(self,c,row):
        # Deliberately NOT a payload execution: guarded native leaf finalization.
        claimed=f.RT.claim_session_input(self.f.stores[0],epoch=self.o.expectation.epoch,
            session_id='i133-api',_guard=c._binding._authority._admission_gate())
        f.RT.settle_session_input(self.f.stores[0],epoch=self.o.expectation.epoch,
            admission_id=row['admission_id'],generation=claimed['generation'],outcome='completed')
    def test_canonical_selection_and_publication_are_two_explicit_steps(self):
        c=self.prepare(publish=False)
        self.assertEqual((c._publication_phase,c._bundle._publication_state),('NEW','NEW'))
        self.assertEqual(c._runner.adapters,{})
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.activate_admission)
        before=self.snapshots()
        with self.watched():r=self.call(c.publish_api_adapter);self.call(c.check)
        self.assertEqual(r['nativeFeature'],f.consumer.CANONICAL_API_FEATURE)
        self.assertEqual(r['canonicalApiPublicationState'],'PUBLISHED');self.assertFalse(r['localAdmissionOpen'])
        self.assertEqual(before,self.snapshots());self.blocked_close()
    def test_invalid_canonical_selection_refuses_before_reservation(self):
        for value in (1,0,'yes',None):
            with self.assertRaises(f.startup.StoreStartupRejected):f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True,canonical_api=value))
            self.assertIsNone(self.o._prepared_consumer)
        with self.assertRaises(f.startup.StoreStartupRejected):f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,canonical_api=True))
        self.assertIsNone(self.o._prepared_consumer)
    def test_old_local_admission_does_not_silently_select_publication_source(self):
        with self.assertRaises(f.consumer.PreparedConsumerRejected):f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True))
        self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.blocked_close()
    def test_direct_native_publication_cannot_impersonate_owner_transition(self):
        c=self.prepare(publish=False);self.call(c._bundle.publish_api_adapter)
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.check)
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.activate_admission)
        self.assertEqual(c._publication_phase,'NEW');self.assertEqual(c._bundle._publication_state,'PUBLISHED');self.blocked_close()
    def test_posteffect_publication_error_retains_unknown_and_owner(self):
        c=self.prepare(publish=False);real=c._bundle.publish_api_adapter
        def fault():real();raise RuntimeError('declared post-publication fault')
        with patch.object(c._bundle,'publish_api_adapter',side_effect=fault):
            with self.assertRaises(RuntimeError):self.call(c.publish_api_adapter)
        self.assertEqual(c._stage,'PUBLICATION_UNKNOWN');self.assertEqual(c._publication_phase,'UNKNOWN')
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.publish_api_adapter)
        self.blocked_close();self.assertEqual(len(c._runner.adapters),1)
    def test_equal_map_is_not_owned_map_and_wrong_enum_key_refuses(self):
        from gateway.config import Platform
        from gateway.platforms.api_server_borrowed import BorrowedStoreRejected
        c=self.prepare();old=c._runner.adapters
        for value in (dict(old),{'api_server':c._adapter},{Platform.API_SERVER:object()}):
            c._runner.adapters=value
            try:
                with self.assertRaises((f.consumer.PreparedConsumerRejected,BorrowedStoreRejected)):self.call(c.check)
                self.blocked_close()
            finally:c._runner.adapters=old
    def test_actual_api_admits_once_and_keeps_owner_identity(self):
        c=self.prepare();self.call(c.activate_admission);authority,ref,row=self.api_admit(c)
        self.assertIs(authority,c._binding._authority);self.assertEqual(row['status'],'queued')
        self.assertIs(c._runner._adapter_for_source(authority.sessions[ref.session_id].source),c._adapter)
        self.assertIs(c._owner,self.o);self.assertTrue(all(a is b for a,b in zip(c._stores,self.f.stores)))
        again=self.api_admit(c);self.assertEqual(again[2]['admission_id'],row['admission_id'])
        self.assertEqual(self.f.connections[0].execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],1)
        self.call(c.check);self.blocked_close()
        OBS.append({'case':self._testMethodName,'realNativeApiAdmission':True,'exactRetryOneRow':True,'sameOwnerThreeConnections':True,'payloadExecuted':False})
    def test_changed_api_payload_same_request_refuses(self):
        c=self.prepare();self.call(c.activate_admission);self.api_admit(c)
        with self.assertRaises(f.RT.RuntimeStoreError):self.api_admit(c,text='different payload')
        self.assertEqual(self.f.connections[0].execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],1)
    def test_pending_actual_api_blocks_retirement_and_finish(self):
        c=self.prepare();self.call(c.activate_admission);_,_,row=self.api_admit(c);self.call(c.begin_drain)
        for fn in (c.retire_idle_api_sessions,c.finish_drain):
            with self.assertRaises(Exception):self.call(fn)
        self.assertEqual(f.RT.get_session_admission(self.f.stores[0],admission_id=row['admission_id'])['status'],'queued')
        self.assertEqual(c._publication_phase,'PUBLISHED');self.assertTrue(c._binding._authority.sessions);self.blocked_close()
    def test_native_retirement_preserves_durable_history_then_ordered_close(self):
        c=self.prepare();self.call(c.activate_admission);_,_,row=self.api_admit(c);self.settle_fixture(c,row);self.call(c.begin_drain)
        before=self.snapshots()
        with self.watched():
            r=self.call(c.retire_idle_api_sessions);self.call(c.finish_drain);f.LOOP.run_until_complete(c.detach())
        self.assertEqual(r['retiredCount'],1);self.assertEqual(self.snapshots(),before)
        self.assertEqual(c._publication_phase,'WITHDRAWN');self.assertEqual(c._runner.adapters,{})
        self.open();self.o.close();self.assertTrue(self.f.owner.owns(self.home));self.f.owner.close()
        OBS.append({'case':self._testMethodName,'realApiAdmitted':True,'nativeLeafSettlementIsFixture':True,'retired':1,'durableHistoryUnchanged':True,'orderedClose':True})
    def test_retirement_refuses_before_drain(self):
        c=self.prepare();self.call(c.activate_admission)
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.retire_idle_api_sessions)
        self.assertEqual(c._admission_phase,'ACTIVE')
    def test_posteffect_retirement_error_retains_unknown(self):
        c=self.prepare();self.call(c.activate_admission);_,_,row=self.api_admit(c);self.settle_fixture(c,row);self.call(c.begin_drain)
        real=c._bundle.retire_idle_api_sessions
        def fault():real();raise RuntimeError('declared post-retirement fault')
        with patch.object(c._bundle,'retire_idle_api_sessions',side_effect=fault):
            with self.assertRaises(RuntimeError):self.call(c.retire_idle_api_sessions)
        self.assertEqual(c._stage,'ADMISSION_UNKNOWN');self.assertEqual(c._admission_phase,'UNKNOWN');self.blocked_close()
    def test_foreign_loop_publish_refuses_before_native_effect(self):
        c=self.prepare(publish=False)
        async def wrong():return c.publish_api_adapter()
        with self.assertRaises(f.consumer.PreparedConsumerRejected):f.OTHER.run_until_complete(wrong())
        self.assertEqual(c._publication_phase,'NEW');self.assertEqual(c._runner.adapters,{})
    def test_withdrawn_registry_replacement_blocks_final_owner_close(self):
        c=self.prepare();self.call(c.activate_admission);self.call(c.begin_drain);self.call(c.finish_drain);f.LOOP.run_until_complete(c.detach())
        old=c._runner.adapters;c._runner.adapters={}
        try:self.blocked_close()
        finally:c._runner.adapters=old
        self.o.close()
    def test_cancelled_api_cleanup_retains_registry_and_all_connections(self):
        c=self.prepare();self.call(c.activate_admission);self.call(c.begin_drain);self.call(c.finish_drain)
        entered=threading.Event();release=threading.Event();done=threading.Event();self.releases.append(release)
        old=c._adapter._memory_sessions
        class Slow:
            def close_all(inner):
                entered.set()
                try:release.wait(10)
                finally:done.set()
        c._adapter._memory_sessions=Slow()
        async def run():
            task=asyncio.create_task(c.detach())
            for _ in range(1000):
                if entered.is_set():break
                await asyncio.sleep(.002)
            self.assertTrue(entered.is_set());task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(c._stage,'CLOSE_UNKNOWN');self.assertEqual(c._bundle._publication_state,'PUBLISHED')
            self.assertFalse(done.is_set())
        try:f.LOOP.run_until_complete(run());self.blocked_close()
        finally:release.set();self.assertTrue(done.wait(5));c._adapter._memory_sessions=old
    def test_published_empty_prepared_detach_never_opens_admission(self):
        c=self.prepare();self.assertFalse(c.status()['localAdmissionOpen'])
        f.LOOP.run_until_complete(c.detach());self.assertEqual(c._publication_phase,'WITHDRAWN');self.o.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    f.NATIVE=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    f.LOOP=asyncio.new_event_loop();f.OTHER=asyncio.new_event_loop();asyncio.set_event_loop(f.LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-i133-api-owner-') as tmp:
        f.BASE=Path(tmp).resolve();home=f.BASE/'imports';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(f.BASE),USERPROFILE=str(f.BASE),APPDATA=str(f.BASE),LOCALAPPDATA=str(f.BASE))
        sys.path.insert(0,str(f.NATIVE));sys.addaudithook(f.audit)
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_runtime,hermes_state_registry
        f.Config,f.Platform,f.RT,f.Registry=GatewayConfig,PlatformConfig,hermes_state_runtime,hermes_state_registry
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(ApiOwnerCases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        f.LOOP.run_until_complete(f.LOOP.shutdown_default_executor());f.LOOP.close();f.OTHER.close()
        native={};harness={}
        for mod in tuple(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                p=Path(name).resolve()
                if p.suffix=='.py':
                    if p.is_relative_to(f.NATIVE):native[p.relative_to(f.NATIVE).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
                    elif p.is_relative_to(ROOT):harness[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        failed={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        report={'result':'PASS_SAME_OWNER_CANONICAL_API_WITH_OS_DOUBLES' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'skipped':len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],'nativeFeature':f.consumer.CANONICAL_API_FEATURE,'nativeImports':native,'harnessImports':harness,'checks':f.CHECKS,'caseEnd':f.ENDS,'races':f.RACES,'observations':OBS,'deniedEvents':f.DENIED,'actualOwnerNativeApiSql':True,'windowsLinuxBoundaryDoubles':True,'explicitPostEffectAndCleanupFaultDoubles':True,'directLeafSettlementIsFixture':True,'fullFiniteTurnExecuted':False,'linuxConfinementTested':False,'providerCalls':0,'httpListenerStarted':False}
    report['temporaryRootRemoved']=not f.BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','harnessImports','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-11000:],flush=True)
    return 0 if r.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
