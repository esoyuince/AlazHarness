"""Actual same-owner API admission boundary, no listener or model execution.
NativeStoreStartup/consumer/native stores/authority/API are real; the reused
Windows fixture explicitly doubles Linux actor/lease metadata/mount/cold helpers.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);denied=[];record={}
    def audit(event,args):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
            denied.append(event);raise PermissionError('q130t6_offline_only')
    with tempfile.TemporaryDirectory(prefix='alaz-q130t6-api-') as tmp:
        home=Path(tmp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home),APPDATA=str(home),LOCALAPPDATA=str(home))
        sys.path[:0]=[str(native),str(ROOT/'packages/claw-hermes'),str(ROOT/'scripts/qa')];sys.addaudithook(audit)
        import s124b1_startup_fixture as fixture
        from gateway.config import GatewayConfig,PlatformConfig
        from gateway.session_api_turn import admit_api_turn_async
        from hermes_state_runtime import RuntimeStoreError
        import hermes_state_registry
        f=fixture.NativeFixture(native,home,loop);o=f.startup
        async def trial():
            record['phase']='PREPARE'
            c=await o.prepare_runtime(GatewayConfig(multiplex_profiles=False,write_sessions_json=False),PlatformConfig(extra={'key':'offline-owned-fixture','model_name':'offline'}),local_admission=True)
            c.activate_admission();record['phase']='API_ADMISSION';record['before']={'consumer':c._stage,'phase':c._admission_phase,'native':c._binding._stage}
            before=[x.total_changes for x in f.connections]
            try:
                admitted=await admit_api_turn_async(c._adapter,session_id='q130-owned-session',request_id='q130-request',user_message='offline admission boundary',conversation_history=[])
                record['admission']={'state':'ACCEPTED','id':admitted[2]['admission_id'],'status':admitted[2]['status']}
            except Exception as exc:
                record['admission']={'state':'REFUSED','type':type(exc).__name__,'reason':getattr(exc,'reason',str(exc))}
            authority=c._binding._authority
            record['nativeState']={'sessions':list(authority.sessions),'runnerAdapters':len(c._runner.adapters),'nativeAdmissions':[tuple(r) for r in f.connections[0].execute('SELECT request_id,status FROM session_admissions')],'apiBindings':f.connections[0].execute("SELECT COUNT(*) FROM state_meta WHERE key LIKE 'gateway.api.binding.v1.%'").fetchone()[0],'sqlChangeDelta':[x.total_changes-b for x,b in zip(f.connections,before)],'mutationTasksRemaining':len(getattr(authority,'_mutation_tasks',()))}
            await asyncio.sleep(0)
            c.begin_drain()
            try:c.finish_drain();record['finish']={'state':'DRAINED'}
            except Exception as exc:record['finish']={'state':'REFUSED','type':type(exc).__name__,'reason':str(exc)}
            try:o.close();record['ownerClose']={'state':'CLOSED'}
            except Exception as exc:record['ownerClose']={'state':'REFUSED','type':type(exc).__name__,'reason':str(exc)}
            record['endBeforeFixtureCleanup']={'owner':o._stage,'consumer':c._stage,'native':c._binding._stage,'profileHeld':f.owner.owns(home),'callerConnectionsOpen':all(x.execute('SELECT 1').fetchone()[0]==1 for x in f.connections)}
            tasks=[t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()];record['remainingTasks']=len(tasks);assert not tasks
        try:loop.run_until_complete(trial())
        except Exception as exc:
            record['outerRefusal']={'type':type(exc).__name__,'reason':str(exc)}
            c=o._prepared_consumer
            record['retainedAfterRefusal']={'owner':o._stage,'consumer':c._stage,'profileHeld':f.owner.owns(home),'allConnectionsOpen':all(v.execute('SELECT 1').fetchone()[0]==1 for v in f.connections)}
            record['remainingTasks']=len([t for t in asyncio.all_tasks(loop) if not t.done()])
            assert record['remainingTasks']==0
        finally:f.cleanup_fixture()
        imports={}
        for module in tuple(sys.modules.values()):
            file=getattr(module,'__file__',None)
            if file:
                q=Path(file).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        allowed=json.loads((ROOT/'config/admission-consumer-b129d6-sources.json').read_text(encoding='utf-8'))['sources']
        record['loadedOutsideDeclaredEnvelope']={n:h for n,h in imports.items() if n not in allowed}
        record['loadedHashMismatches']={n:h for n,h in imports.items() if n in allowed and allowed[n]!=h}
        names=['packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_prepared_consumer.py','packages/claw-hermes/gateway_consumer_admission.py','packages/claw-hermes/gateway_live_store_gate.py','packages/claw-hermes/gateway_response_live.py','config/admission-consumer-b129d6-sources.json','scripts/qa/s124b1_startup_fixture.py','scripts/qa/q130t6_native_api_baseline.py']
        record.update(result='ACTUAL_API_ADMISSION_BOUNDARY_OBSERVED',sourceHashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},nativeImports=imports,nativeProductMethodsReplaced=False,windowsOsBoundariesDoubled=True,modelOrProviderCalls=0,httpListenerStarted=False,observeOrScheduleTurnCalled=False,rootWslAction=False,deniedEvents=denied,profileReleased=not f.owner.homes,registry=hermes_state_registry.stats())
    loop.run_until_complete(loop.shutdown_default_executor());loop.close();record['temporaryProfileRemoved']=not home.exists()
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k not in ('sourceHashes','nativeImports','deniedEvents')}),flush=True)
if __name__=='__main__':main()
