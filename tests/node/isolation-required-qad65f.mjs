/** Real HostGateClient/fetch against loopback HTTP fixtures; not Hermes. */
import assert from 'node:assert/strict';
import http from 'node:http';
import {HostGateClient} from '../../packages/claw-hermes/host-gate-client.mjs';
const scenario=process.argv[2];
const allowed=new Set(['invalid-option','conflicting-execution','missing-isolation','wrong-backend','boolean-version','missing-execution','downgrade','guarded']);
assert(allowed.has(scenario));
const requests=[];let capCalls=0;
const rid='b'.repeat(32),key='ah1-'+'a'.repeat(32)+'-'+rid;
const server=http.createServer(async(req,res)=>{
 let raw='';for await(const chunk of req){raw+=chunk;if(raw.length>100000){req.destroy();return;}}
 requests.push({method:req.method,url:req.url,headers:req.headers});
 let code=200,value;
 if(req.url==='/alaz/host/v1/capabilities'){
  capCalls++;
  value={hostGateVersion:1,dispatchPath:'/alaz/host/v1/dispatch',nativeStoreOwner:true,dispatchAtMostOnce:true,automaticRetry:false,
   scope:'default_profile_new_run',executionBoundaryVersion:1,isolatedReadBoundaryVersion:1,isolatedReadBackend:'linux_docker_native_terminal'};
  if(scenario==='missing-isolation'||scenario==='downgrade'&&capCalls>1)delete value.isolatedReadBoundaryVersion;
  if(scenario==='boolean-version')value.isolatedReadBoundaryVersion=true;
  if(scenario==='wrong-backend')value.isolatedReadBackend='host';
  if(scenario==='missing-execution')delete value.executionBoundaryVersion;
 }else if(req.url==='/alaz/host/v1/intents'){
  code=201;value={hostGateVersion:1,requestId:rid,idempotencyKey:key,retryAllowed:false,replayed:false,expiresAtMs:Date.now()+60000,dispatchState:'issued'};
 }else if(req.url==='/alaz/host/v1/dispatch'){
  code=202;value={run_id:'run_'+'c'.repeat(32),status:'queued',replayed:false};
 }else{code=404;value={};}
 res.writeHead(code,{'Content-Type':'application/json'});res.end(JSON.stringify(value));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
try{
 const opts={baseUrl:'http://127.0.0.1:'+server.address().port,token:'qa-only-no-account-token',requireIsolatedRead:true,requestTimeoutMs:3000};
 if(scenario==='invalid-option'){
  assert.throws(()=>new HostGateClient({...opts,requireIsolatedRead:1}),e=>e.code==='invalid_isolation_requirement');
 }else if(scenario==='conflicting-execution'){
  assert.throws(()=>new HostGateClient({...opts,requireExecution:false}),e=>e.code==='isolation_requires_execution_boundary');
 }else{
  const client=new HostGateClient(opts);const intent={requestId:rid,input:'fixture only',model:'fixture-model'};
  if(['missing-isolation','wrong-backend','boolean-version','missing-execution'].includes(scenario)){
   await assert.rejects(client.prepare(intent),e=>e.code===(scenario==='missing-execution'?'execution_boundary_required':'isolated_read_boundary_required'));
   assert.equal(requests.filter(r=>r.method==='POST').length,0);
  }else{
   const permit=await client.prepare(intent);
   if(scenario==='downgrade'){
    await assert.rejects(client.dispatch(permit),e=>e.code==='isolated_read_boundary_required');
    assert.equal(requests.filter(r=>r.url.endsWith('/dispatch')).length,0);
   }else{
    const result=await client.dispatch(permit);assert.equal(result.status,'queued');
    await assert.rejects(client.dispatch(permit),e=>e.code==='host_dispatch_already_attempted');
    assert.equal(requests.filter(r=>r.url.endsWith('/dispatch')).length,1);
   }
  }
 }
 assert(!requests.some(r=>r.url==='/v1/runs'),'raw host admission fallback');
 for(const request of requests){assert.equal(request.headers['x-alaz-execution-version'],'1');assert.equal(request.headers['x-alaz-isolated-read-version'],'1');}
 if(['invalid-option','conflicting-execution'].includes(scenario))assert.equal(requests.length,0);
 console.log(JSON.stringify({scenario,result:'PASS',requests:requests.length,raw_start_fallback:false,native_gateway_runs:0,paid_calls:0}));
}finally{
 server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
}
