"""Re-execute unchanged C120 native tests with explicit observer source choice.
Only the C119 test-fixture constructor argument is adapted. No native method,
observation implementation, worker registry or admission guard is replaced.
Runner credential/delivery facade and model computation remain C120 fixtures.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'scripts/qa')]
import c120a_native_turnrunner as original
import c119v1_native_canonical as base
import gateway_canonical_run_binding as binding
import gateway_live_store_gate as live

class ExplicitSourceFixture:
    def __init__(self,feature):self.feature=feature
    def NativeCanonicalBinding(self,*args,**kwargs):
        return binding.NativeCanonicalBinding(*args,**kwargs,native_feature=self.feature)
    def __getattr__(self,name):return getattr(binding,name)

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--feature',choices=(binding.NATIVE_FEATURE,binding.CURRENT_NATIVE_FEATURE),required=True);p.add_argument('--case');a=p.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    base.binding=ExplicitSourceFixture(a.feature)  # test fixture only, no production mutation
    with tempfile.TemporaryDirectory(prefix='alaz-o127-turn-') as tmp:
        home=Path(tmp);os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home),APPDATA=str(home),LOCALAPPDATA=str(home),HERMES_AGENT_TIMEOUT='0',HERMES_AGENT_TIMEOUT_WARNING='0')
        sys.path.insert(0,str(native));sys.addaudithook(base.audit)
        from gateway.config import GatewayConfig,PlatformConfig
        from gateway.session import SessionStore
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.session_authority import SessionAuthority
        from gateway.session_results import execution_result
        from gateway.runtime_ownership import process_ownership
        from gateway.run_turn_runner import TurnRunner
        from gateway.turn_context import TurnContext
        from gateway.run import GatewayRunner
        from gateway.run_turn import GatewayTurnMixin
        from gateway.session_runtime_workers import physical_workers
        import hermes_state_runtime as runtime
        import hermes_state_registry as registry
        import gateway.status as gateway_status
        for name,value in dict(SessionStore=SessionStore,GatewayConfig=GatewayConfig,PlatformConfig=PlatformConfig,APIServerAdapter=APIServerAdapter,SessionAuthority=SessionAuthority,execution_result=execution_result,ownership=process_ownership,runtime=runtime,registry=registry,gateway_status=gateway_status).items():setattr(base,name,value)
        for name,value in dict(TurnRunner=TurnRunner,TurnContext=TurnContext,GatewayRunner=GatewayRunner,GatewayTurnMixin=GatewayTurnMixin,physical_workers=physical_workers).items():setattr(original,name,value)
        control=home/'schema-control';control.mkdir();os.environ['HERMES_HOME']=str(control);process_ownership.reserve([control])
        store=SessionStore(control/'sessions',GatewayConfig());db=store._db
        adapter=APIServerAdapter(PlatformConfig(enabled=True,extra={'key':'owned-control','model_name':'owned'}))
        runtime.begin_runtime_epoch(db,instance_id='schema-control');binding._qualified_source(a.feature)
        base.SCHEMAS=(live.schema_digest(db._conn),live.schema_digest(adapter._run_idempotency_store._conn))
        adapter._response_store.close();adapter._run_idempotency_store.close();registry.close_all_under(control);process_ownership.close()
        suite=unittest.TestSuite([original.TurnRunnerCases(a.case)]) if a.case else unittest.defaultTestLoader.loadTestsFromTestCase(original.TurnRunnerCases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        imports={}
        for mod in tuple(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                path=Path(name).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        names=('packages/claw-hermes/gateway_canonical_run_binding.py','packages/claw-hermes/gateway_canonical_turn_observation.py','scripts/qa/c119v1_native_canonical.py','scripts/qa/c120a_native_turnrunner.py','scripts/qa/o127b6_native_turn_source.py')
        failed={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        report={'result':'PASS_EXPLICIT_SOURCE_NATIVE_TURN_OBSERVATION' if r.wasSuccessful() else 'FAIL','nativeFeature':a.feature,
            'total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
            'nativeImports':imports,'sourceHashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'observations':original.OBS,'caseEnd':original.CASE_END,'canonicalObservations':base.OBS,'audit':base.AUDIT,
            'originalC120TestBodiesUnchanged':True,'fixtureConstructorArgumentExplicit':True,'actualNativeTurnRunnerAdoptionAndPhysicalTracking':True,'nativeMethodsOrObserverMethodsReplaced':False,
            'runnerFacadeAndModelComputationDoubled':True,'borrowedActiveWorkQualified':False,'completeAIAgentTested':False,'kernelIsolationTested':False,'httpListenerStarted':False,'providerCalls':0,'rootOrWslAction':False,
            'ownershipReleased':not process_ownership.homes,'registry':registry.stats()}
    report['temporaryImportHomeRemoved']=not home.exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','sourceHashes','observations','caseEnd','canonicalObservations','audit')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-14000:],flush=True)
    return 0 if r.wasSuccessful() and report['ownershipReleased'] and report['temporaryImportHomeRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
