/** Native Gateway probe client. Provider answers are fixtures; admission is real. */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {HostGateClient} from '../packages/claw-hermes/host-gate-client.mjs';
const [path,output]=process.argv.slice(2),c=JSON.parse(readFileSync(path,'utf8'));
const options={baseUrl:c.baseUrl,token:c.token,requestTimeoutMs:12000};
const host=new HostGateClient(options),checks=[];
async function rejected(name,fn,code) {
  try {await fn();throw new Error('Accepted forbidden operation: '+name);}
  catch(e) {if(e.code!==code)throw e;checks.push({name,code:e.code,hostCode:e.hostCode??null});}
}
async function raw(method,path,body,headers={}) {
  const res=await fetch(c.baseUrl+path,{method,redirect:'error',headers:{Authorization:'Bearer '+c.token,'Content-Type':'application/json',...headers},
    ...(body===undefined?{}:{body:JSON.stringify(body)})});return {status:res.status,body:await res.json()};
}
const intent={requestId:c.requestId,input:'Read input.txt using read_file and return its first line.',model:'alaz-scripted'};
let final=null,permit=null;
if(c.mode==='missing-plugin'||c.mode==='invalid-policy') {
  await rejected('missing-required-capability',()=>host.capabilities(),'host_http_404');
  await rejected('no-raw-fallback',()=>host.prepare(intent),'host_http_404');
} else if(c.mode==='restart') {
  await rejected('consumed-after-native-reopen',()=>host.prepare(intent),'host_dispatch_already_attempted');
  const bad=await raw('POST','/alaz/host/v1/dispatch',{input:intent.input,model:intent.model},{'Idempotency-Key':c.key});
  assert.equal(bad.status,409);checks.push({name:'raw-repeat-after-reopen',status:bad.status,code:bad.body.error.code});
  final=await host.resume(c.runId,{executionTimeoutMs:5000});assert.equal(final.run.status,'completed');
} else {
  const capabilities=await host.capabilities();assert.equal(capabilities.modelTokenOrCostBudget,false);
  permit=await host.prepare(intent);assert.ok(Object.isFrozen(permit));
  const same=await new HostGateClient(options).prepare(intent);assert.equal(same.idempotencyKey,permit.idempotencyKey);
  await rejected('changed-input',()=>new HostGateClient(options).prepare({...intent,input:'different'}),'host_http_409');
  await rejected('foreign-permit',()=>new HostGateClient(options).dispatch(permit),'foreign_host_permit');
  const unauthed=await raw('POST','/alaz/host/v1/intents',{requestId:c.requestId,body:{input:intent.input,model:intent.model}},{Authorization:'Bearer wrong'});
  assert.equal(unauthed.status,401);checks.push({name:'auth-refusal',status:401});
  for(const path of ['/v1/runs','/v1/chat/completions','/p/default/v1/runs']) {
    const refusal=await raw('POST',path,{input:intent.input,model:intent.model},{'Idempotency-Key':permit.idempotencyKey});
    assert.ok([403,404,409].includes(refusal.status));checks.push({name:'alternative-write-refused',path,status:refusal.status});
  }
  const foreign=await raw('POST','/alaz/host/v1/dispatch',{input:intent.input,model:intent.model},{'Idempotency-Key':permit.idempotencyKey,'X-Hermes-Session-Key':'foreign'});
  assert.equal(foreign.status,409);checks.push({name:'scope-header-refused',status:409});
  if(c.mode==='lost-ack') {
    // Parent starts the fault relay using this actual server-issued key.
    writeFileSync(c.permitFile,JSON.stringify({nonce:c.nonce,key:permit.idempotencyKey})+'\n');
    const deadline=Date.now()+10000;while(!readable(c.relayFile)){if(Date.now()>deadline)throw new Error('relay deadline');await new Promise(r=>setTimeout(r,20));}
    const relay=JSON.parse(readFileSync(c.relayFile,'utf8'));assert.equal(relay.nonce,c.nonce);
    const via=new HostGateClient({...options,baseUrl:relay.url});const viaPermit=await via.prepare(intent);
    await rejected('accepted-ack-lost',()=>via.dispatch(viaPermit),'host_write_outcome_unknown');
    await rejected('no-automatic-resend',()=>via.dispatch(viaPermit),'host_dispatch_already_attempted');
    await rejected('new-client-cannot-resend',()=>new HostGateClient(options).prepare(intent),'host_dispatch_already_attempted');
    writeFileSync(c.droppedFile,JSON.stringify({nonce:c.nonce})+'\n');
    const end=Date.now()+10000;while(!readable(c.runFile)){if(Date.now()>end)throw new Error('run observation deadline');await new Promise(r=>setTimeout(r,20));}
    const observed=JSON.parse(readFileSync(c.runFile,'utf8'));assert.equal(observed.nonce,c.nonce);
    final=await host.resume(observed.runId,{executionTimeoutMs:45000});
  } else {
    const clients=await Promise.all(Array.from({length:10},async()=>{
      const other=new HostGateClient(options);return {other,permit:await other.prepare(intent)};
    }));
    const attempts=await Promise.allSettled(clients.map(x=>x.other.dispatch(x.permit)));
    assert.equal(attempts.filter(x=>x.status==='fulfilled').length,1);
    for(const x of attempts.filter(x=>x.status==='rejected'))assert.equal(x.reason.code,'host_http_409');
    const accepted=attempts.find(x=>x.status==='fulfilled').value;
    checks.push({name:'ten-concurrent-dispatches',accepted:1,rejected:9});
    final=await host.resume(accepted.run_id,{executionTimeoutMs:45000});
    await rejected('consumed-id-cannot-be-prepared-again',()=>new HostGateClient(options).prepare(intent),'host_dispatch_already_attempted');
  }
  assert.equal(final.run.status,'completed');assert.ok(final.run.output.includes(c.marker));
}
function readable(path){try{readFileSync(path);return true;}catch{return false;}}
writeFileSync(output,JSON.stringify({mode:c.mode,nonce:c.nonce,result:'PASS',checks,permit,final},null,2)+'\n');
