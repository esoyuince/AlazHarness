import argparse,asyncio,os,sys,tempfile,json,hashlib,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();native=args.native.resolve();out=args.output.resolve();out.mkdir(exist_ok=False,parents=True)
watch=False;events=[];blocked=[]
def audit(event,values):
 if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
  blocked.append(event);raise PermissionError('r122_offline')
 if watch and event=='sqlite3.connect':events.append(event);raise AssertionError('extra_db_open')
with tempfile.TemporaryDirectory(prefix='alaz-r122-smoke-') as temp:
 home=Path(temp).resolve();os.environ.update(HERMES_HOME=str(home),HOME=str(home),USERPROFILE=str(home));sys.path.insert(0,str(native));sys.addaudithook(audit)
 from gateway.run import GatewayRunner
 from gateway.config import GatewayConfig
 from gateway.run_borrowed_state import CallerOwnedRunnerState
 from gateway.run_runtime import initialize_gateway_runtime
 from gateway.runtime_ownership import process_ownership
 from hermes_state import SessionDB
 from hermes_state_runtime import begin_runtime_epoch
 import hermes_state_registry as registry
 process_ownership.reserve([home]);state=SessionDB(home/'state.db');epoch=begin_runtime_epoch(state,instance_id='r122-smoke')
 config=GatewayConfig(sessions_dir=home/'sessions',multiplex_profiles=False,write_sessions_json=False)
 before=state._conn.total_changes;runner=None;result={}
 try:
  watch=True;binding=CallerOwnedRunnerState(config,state,epoch=epoch,instance_id='r122-smoke');runner=GatewayRunner(config,caller_state=binding)
  assert runner.session_store._db is state and runner._session_db._db is state
  watch=False
  # Event-loop setup uses private interpreter wakeup sockets, not a service.
  loop=asyncio.new_event_loop();asyncio.set_event_loop(loop);watch=True
  try:authority=loop.run_until_complete(initialize_gateway_runtime(runner))
  finally:watch=False;loop.close();asyncio.set_event_loop(None)
  assert authority.db is state and authority.epoch==epoch and authority.retiring
  assert state._conn.total_changes==before and registry.stats()['total_refcounts']==0
  watch=True;runner.close_all_session_db_handles();watch=False
  assert state._conn.execute('SELECT 1').fetchone()[0]==1 and process_ownership.owns(home)
  result={'result':'PASS_CONSTRUCTION_SMOKE','extraSQLiteOpens':len(events),'stateChanges':state._conn.total_changes-before,'epoch':epoch,'binding':binding.status(),'nativeRunnerClass':type(runner).__module__+'.'+type(runner).__name__,'registry':registry.stats(),'serviceStarted':False}
 except BaseException as exc:
  result={'result':'FAIL','errorType':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()};raise
 finally:
  watch=False;state.close();process_ownership.close()
  result['blockedNetworkOrProcess']=blocked
  result['nativeImports']={}
  for mod in tuple(sys.modules.values()):
   path=getattr(mod,'__file__',None)
   if path:
    p=Path(path).resolve()
    if p.is_relative_to(native) and p.suffix=='.py':result['nativeImports'][p.relative_to(native).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='nativeImports'}),flush=True)
