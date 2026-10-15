/** Portable loopback fixture tests of HostGateClient, not a native Gateway. */
import assert from 'node:assert/strict';
import http from 'node:http';
import {HostGateClient} from '../../packages/claw-hermes/host-gate-client.mjs';
const scenario=process.argv[2],requests=[],rid='a'.repeat(32),key='ah1-'+'b'.repeat(32)+'-'+rid,runId='run_'+'c'.repeat(32);
let bodyReceived=null;
const server=http.createServer(async(req,res)=>{
  const chunks=[];for await(const chunk of req)chunks.push(chunk);
  const raw=Buffer.concat(chunks).toString();const body=raw?JSON.parse(raw):null;
  requests.push({method:req.method,path:req.url});
  const send=(obj,status=200)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(obj));};
  if(scenario==='missing'){send({error:'missing'},404);return;}
  if(scenario==='redirect'){res.writeHead(302,{Location:'/v1/runs','Content-Type':'application/json'});res.end('{}');return;}
  if(scenario==='oversized'){send({content:'a'.repeat(4096)});return;}
  if(req.url.endsWith('/intents')){
    bodyReceived=body;
    send({hostGateVersion:1,requestId:scenario==='wrong-id'?'f'.repeat(32):rid,
      idempotencyKey:key,dispatchState:scenario==='consumed'?'consumed':'issued',expiresAtMs:Date.now()+50000,replayed:false,retryAllowed:false},201);return;
  }
  if(req.url.endsWith('/dispatch')){
    assert.equal(req.headers['idempotency-key'],key);bodyReceived=body;
    if(scenario==='lost-ack'){req.socket.destroy();return;}
    if(scenario==='server-refusal'){send({hostGateVersion:1,error:{code:'dispatch_limit_reached'},retryAllowed:false},409);return;}
    send({run_id:scenario==='bad-admission'?'wrong':runId,status:'started',replayed:false},202);return;
  }
  if(req.url==='/v1/runs/'+runId){send({run_id:runId,status:'completed',output:'ok'});return;}
  send({error:'unexpected path'},400);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const opts={baseUrl:'http://127.0.0.1:'+server.address().port,token:'test-bearer',maxResponseBytes:scenario==='oversized'?128:10000,requestTimeoutMs:500};
const host=new HostGateClient(opts),intent={requestId:rid,input:'Read scoped input.',model:'test-model'};
const throws=(fn,code)=>assert.rejects(fn,error=>error.code===code);
try {
  if(scenario==='accessor'){Object.defineProperty(intent,'input',{get(){throw new Error('Getter must not run');}});await throws(()=>host.prepare(intent),'invalid_host_intent');assert.equal(requests.length,0);}
  else if(scenario==='symbol'){intent[Symbol('bad')]=true;await throws(()=>host.prepare(intent),'invalid_host_intent');assert.equal(requests.length,0);}
  else if(scenario==='bad-input'){await throws(()=>host.prepare({...intent,unexpected:true}),'invalid_host_intent');assert.equal(requests.length,0);}
  else if(scenario==='preaborted'){
    const controller=new AbortController();controller.abort();await throws(()=>host.prepare(intent,{signal:controller.signal}),'aborted_before_request');assert.equal(requests.length,0);
  } else if(['missing','redirect','oversized','wrong-id','consumed'].includes(scenario)) {
    const code={'missing':'host_http_404','redirect':'host_write_outcome_unknown','oversized':'host_response_too_large','wrong-id':'invalid_host_permit','consumed':'host_dispatch_already_attempted'}[scenario];
    await throws(()=>host.prepare(intent),code);assert.equal(requests.length,1);
  } else {
    const permit=await host.prepare(intent);assert.ok(Object.isFrozen(permit));
    if(scenario==='foreign'){await throws(()=>new HostGateClient(opts).dispatch(permit),'foreign_host_permit');assert.equal(requests.length,1);}
    else if(scenario==='copied'){await throws(()=>host.dispatch({...permit}),'foreign_host_permit');assert.equal(requests.length,1);}
    else {
      intent.input='mutated after preparation';
      if(scenario==='lost-ack'){await throws(()=>host.dispatch(permit),'host_write_outcome_unknown');await throws(()=>host.dispatch(permit),'host_dispatch_already_attempted');}
      else if(scenario==='server-refusal'){await throws(()=>host.dispatch(permit),'host_http_409');await throws(()=>host.dispatch(permit),'host_dispatch_already_attempted');}
      else if(scenario==='bad-admission'){await throws(()=>host.dispatch(permit),'invalid_host_admission');await throws(()=>host.dispatch(permit),'host_dispatch_already_attempted');}
      else if(scenario==='concurrent'){
        const answers=await Promise.allSettled(Array.from({length:10},()=>host.dispatch(permit)));assert.equal(answers.filter(x=>x.status==='fulfilled').length,1);
      } else {
        const run=await host.dispatch(permit);assert.equal(run.run_id,runId);
        if(scenario==='readonly')assert.equal((await host.resume(runId)).run.output,'ok');
        await throws(()=>host.dispatch(permit),'host_dispatch_already_attempted');
      }
      assert.equal(requests.filter(x=>x.path.endsWith('/dispatch')).length,1);
      assert.equal(bodyReceived.input,'Read scoped input.');
    }
  }
  assert.equal(requests.filter(x=>x.path==='/v1/runs').length,0);
  console.log(JSON.stringify({scenario,result:'PASS',calls:requests.length,rawStartCalls:0}));
} finally {server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
