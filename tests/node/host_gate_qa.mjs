/** Independent client contract tests; fetch is a fixture, no native server/model. */
import assert from 'node:assert/strict';
import {HostGateClient} from '../../packages/claw-hermes/host-gate-client.mjs';
const ID='a'.repeat(32),KEY='ah1-'+'b'.repeat(32)+'-'+ID,RUN='run_'+'c'.repeat(32);
const input={requestId:ID,input:'Original scoped input',model:'test-model'};
const options={baseUrl:'http://127.0.0.1:9876',token:'fixture-token'};
const issued={hostGateVersion:1,requestId:ID,idempotencyKey:KEY,dispatchState:'issued',expiresAtMs:1900000000000,replayed:false,retryAllowed:false};
const accepted={run_id:RUN,status:'queued',replayed:false};
const calls=[];
let reply=(url,options)=>url.endsWith('/intents')?new Response(JSON.stringify(issued),{status:201,headers:{'Content-Type':'application/json'}}):new Response(JSON.stringify(accepted),{status:202,headers:{'Content-Type':'application/json'}});
globalThis.fetch=async(url,options)=>{calls.push({url:String(url),method:options.method,body:options.body});return reply(String(url),options);};
const failCode=(code)=>e=>e.code===code;
const cases={
  async missing_plugin_no_fallback(){
    reply=()=>new Response('{}',{status:404,headers:{'Content-Type':'application/json'}});
    await assert.rejects(new HostGateClient(options).prepare(input),failCode('host_http_404'));
    assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('/alaz/host/v1/intents'));
    assert.ok(!calls.some(c=>c.url.endsWith('/v1/runs')));
  },
  async foreign_permit_no_network(){await assert.rejects(new HostGateClient(options).dispatch({requestId:ID,idempotencyKey:KEY}),failCode('foreign_host_permit'));assert.equal(calls.length,0);},
  async mutation_after_prepare_snapshotted(){
    const host=new HostGateClient(options),request={...input};const pending=host.prepare(request);request.input='MUTATED';const permit=await pending;
    assert.ok(Object.isFrozen(permit));await host.dispatch(permit);assert.equal(JSON.parse(calls[1].body).input,input.input);
  },
  async foreign_client_permit_no_dispatch(){
    const h=new HostGateClient(options),permit=await h.prepare(input);await assert.rejects(new HostGateClient(options).dispatch(permit),failCode('foreign_host_permit'));assert.equal(calls.length,1);
  },
  async one_permit_not_twice(){
    const h=new HostGateClient(options),permit=await h.prepare(input);await h.dispatch(permit);await assert.rejects(h.dispatch(permit),failCode('host_dispatch_already_attempted'));assert.equal(calls.length,2);
  },
  async two_permits_one_local_dispatch(){
    const h=new HostGateClient(options);const [a,b]=await Promise.all([h.prepare(input),h.prepare(input)]);const results=await Promise.allSettled([h.dispatch(a),h.dispatch(b)]);
    assert.equal(results.filter(r=>r.status==='fulfilled').length,1);assert.equal(calls.filter(c=>c.url.endsWith('/dispatch')).length,1);
  },
  async transport_loss_never_refunds(){
    const h=new HostGateClient(options),permit=await h.prepare(input);reply=()=>{throw new Error('fixture connection loss');};
    await assert.rejects(h.dispatch(permit),e=>e.code==='host_write_outcome_unknown'&&e.retryAllowed===false);
    await assert.rejects(h.dispatch(permit),failCode('host_dispatch_already_attempted'));assert.equal(calls.length,2);
  },
  async abort_before_dispatch_does_not_consume(){
    const h=new HostGateClient(options),permit=await h.prepare(input),c=new AbortController();c.abort();
    await assert.rejects(h.dispatch(permit,{signal:c.signal}),failCode('aborted_before_request'));assert.equal(calls.length,1);await h.dispatch(permit);assert.equal(calls.length,2);
  },
  async consumed_document_cannot_dispatch(){
    reply=()=>new Response(JSON.stringify({...issued,dispatchState:'consumed'}),{status:201,headers:{'Content-Type':'application/json'}});
    await assert.rejects(new HostGateClient(options).prepare(input),failCode('host_dispatch_already_attempted'));assert.equal(calls.length,1);
  },
  async invalid_key_binding_refused(){
    reply=()=>new Response(JSON.stringify({...issued,idempotencyKey:'ah1-'+'b'.repeat(32)+'-'+'d'.repeat(32)}),{status:201,headers:{'Content-Type':'application/json'}});
    await assert.rejects(new HostGateClient(options).prepare(input),failCode('invalid_host_permit'));assert.equal(calls.length,1);
  },
  async contradictory_completed_admission_refused(){
    const h=new HostGateClient(options),permit=await h.prepare(input);
    reply=()=>new Response(JSON.stringify({...accepted,status:'completed',completed:false,partial:true,output:'not-final'}),{status:202,headers:{'Content-Type':'application/json'}});
    await assert.rejects(h.dispatch(permit),failCode('invalid_host_admission'));
  },
  async invalid_output_type_refused(){
    const h=new HostGateClient(options),permit=await h.prepare(input);
    reply=()=>new Response(JSON.stringify({...accepted,status:'completed',output:{pretend:'success'}}),{status:202,headers:{'Content-Type':'application/json'}});
    await assert.rejects(h.dispatch(permit),failCode('invalid_host_admission'));
  },
};
const name=process.argv[2];if(!Object.hasOwn(cases,name))throw new Error('Unknown QA case');
await cases[name]();console.log(JSON.stringify({name,result:'PASS',fetch_fixture_calls:calls.length,native_gateway:false}));
