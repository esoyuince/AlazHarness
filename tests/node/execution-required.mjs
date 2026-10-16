import assert from 'node:assert/strict';
import http from 'node:http';
import {HostGateClient} from '../../packages/claw-hermes/host-gate-client.mjs';
const scenario=process.argv[2], counts={GET:0,POST:0},headers=[];let version=1;
const id='a'.repeat(32),key='ah1-'+'b'.repeat(32)+'-'+id;
const caps=()=>({hostGateVersion:1,dispatchPath:'/alaz/host/v1/dispatch',nativeStoreOwner:true,dispatchAtMostOnce:true,automaticRetry:false,scope:'default_profile_new_run',executionBoundaryVersion:version});
const server=http.createServer(async(req,res)=>{
  counts[req.method]=(counts[req.method]??0)+1;headers.push(req.headers['x-alaz-execution-version']);
  for await(const _ of req){}
  let status=200,value=caps();
  if(req.method==='POST'&&req.url.endsWith('/intents')){status=201;value={hostGateVersion:1,requestId:id,idempotencyKey:key,expiresAtMs:Date.now()+60000,dispatchState:'issued',replayed:false,retryAllowed:false};}
  if(req.method==='POST'&&req.url.endsWith('/dispatch')){status=202;value={run_id:'run_'+'c'.repeat(32),status:'queued',replayed:false};}
  res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value));
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const options={baseUrl:'http://127.0.0.1:'+server.address().port,token:'fixture-token',requireExecution:true};
const request={requestId:id,input:'fixture',model:'fixture-model'};
try{
  if(scenario==='invalid-option'){
    assert.throws(()=>new HostGateClient({...options,requireExecution:'yes'}),e=>e.code==='invalid_execution_requirement');assert.equal(counts.GET+counts.POST,0);
  }else{
    const client=new HostGateClient(options);
    if(scenario==='missing'||scenario==='boolean-version'){
      version=scenario==='missing'?null:true;
      await assert.rejects(client.prepare(request),e=>e.code==='execution_boundary_required');assert.equal(counts.POST,0);assert.equal(counts.GET,1);
    }else if(scenario==='downgrade'){
      const permit=await client.prepare(request);version=null;
      await assert.rejects(client.dispatch(permit),e=>e.code==='execution_boundary_required');assert.equal(counts.POST,1);assert.equal(counts.GET,2);
    }else if(scenario==='aborted'){
      const controller=new AbortController();controller.abort();await assert.rejects(client.prepare(request,{signal:controller.signal}),e=>e.code==='aborted_before_request');assert.equal(counts.POST+counts.GET,0);
    }else if(scenario==='guarded'){
      const permit=await client.prepare(request),result=await client.dispatch(permit);assert.equal(result.status,'queued');assert.equal(counts.POST,2);assert.equal(counts.GET,2);
      assert.ok(headers.every(x=>x==='1'));
    }else throw new Error('Unknown test');
  }
  console.log(JSON.stringify({scenario,checks:'PASS',counts}));
}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
