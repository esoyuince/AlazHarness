from pathlib import Path
import argparse,asyncio,concurrent.futures,threading,tempfile,os,sys,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--native',required=True);p.add_argument('--expected-count',type=int,required=True);a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='alaz-e118-count-') as home:
 os.environ.update(HERMES_HOME=home,HOME=home,USERPROFILE=home,APPDATA=home,LOCALAPPDATA=home)
 loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
 def audit(event,args):
  if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):raise PermissionError('offline-count-regression')
 sys.addaudithook(audit);sys.path.insert(0,a.native)
 from gateway.platforms.api_server_runs import _submit_api_worker,api_worker_live_count
 async def probe():
  pool=concurrent.futures.ThreadPoolExecutor(max_workers=1);loop.set_default_executor(pool)
  release=threading.Event();calls=[]
  blocker=loop.run_in_executor(None,lambda:release.wait(10))
  before=api_worker_live_count();f=_submit_api_worker(loop,lambda:calls.append('called'))
  submitted=api_worker_live_count();f.cancel()
  # Two explicit loop barriers let cancellation propagate to the queued executor Future.
  for _ in range(2):
   barrier=loop.create_future();loop.call_soon(barrier.set_result,None);await barrier
  release.set();await blocker;await loop.shutdown_default_executor(timeout=5)
  return {'before':before,'submitted':submitted,'afterAllThreadsDrained':api_worker_live_count(),'actualWorkCalls':len(calls),'asyncFutureCancelled':f.cancelled()}
 try:result=loop.run_until_complete(probe())
 finally:loop.close()
 result['nativeSubmitModuleSha256']=hashlib.sha256((Path(a.native)/'gateway/platforms/api_server_runs.py').read_bytes()).hexdigest()
 result['rootWslAction']=False;result['providerCalls']=0
print(json.dumps(result))
assert result['before']==0 and result['submitted']==1 and result['actualWorkCalls']==0 and result['asyncFutureCancelled']
assert result['afterAllThreadsDrained']==a.expected_count
