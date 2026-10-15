/** Existing HermesRunsClient against the real native Gateway. */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,existsSync,renameSync} from 'node:fs';
import {setTimeout as sleep} from 'node:timers/promises';
import {HermesRunsClient} from '../packages/claw-hermes/hermes-runs.mjs';
const [configPath,output]=process.argv.slice(2);
const c=JSON.parse(readFileSync(configPath,'utf8'));
const client=new HermesRunsClient({baseUrl:c.baseUrl,token:c.token,requestTimeoutMs:8000});
const draft={input:c.input,idempotencyKey:c.key};
const checks=[];let lostError;
if(c.scenario==='lost-ack') {
  await assert.rejects(()=>client.start(draft),e=>{lostError=e.code;return e.code==='write_outcome_unknown'&&e.mayHaveBeenAccepted===true;});
  checks.push('lost-ack-is-unknown-not-failure');
}
// An explicit same-key reoffer by this test, never an automatic adapter retry.
const admitted=await client.start(draft);
if(c.scenario==='lost-ack')assert(admitted.replayed);
let done;
if(c.scenario==='stop') {
  const end=Date.now()+15000;
  while(!existsSync(c.entered)) {if(Date.now()>end)throw Error('No native model request');await sleep(20);}
  assert.equal(JSON.parse(readFileSync(c.entered,'utf8')).nonce,c.nonce);
  const stopAck=await client.stop(admitted.run_id);checks.push('stop-request-reached-native');
  writeFileSync(c.release+'.tmp',JSON.stringify({nonce:c.nonce}));renameSync(c.release+'.tmp',c.release);
  done=await client.observe(admitted.run_id,{executionTimeoutMs:20000,settlementTimeoutMs:10000,pollIntervalMs:50});
  assert(['cancelled','interrupted'].includes(done.run.status));assert(done.backendConfirmed);
  checks.push('terminal-stop-separately-confirmed');
} else {
  done=await client.observe(admitted.run_id,{executionTimeoutMs:40000,settlementTimeoutMs:10000,pollIntervalMs:50});
  assert.equal(done.run.status,'completed');assert(done.backendConfirmed);assert(done.run.output.includes(c.marker));
  checks.push('real-tool-result');
}
const same=await client.start(draft);assert.equal(same.run_id,admitted.run_id);assert(same.replayed);checks.push('duplicate-same-id');
await assert.rejects(()=>client.start({...draft,input:draft.input+' changed'}),e=>e.code==='http_409');checks.push('changed-payload-409');
const resumed=await client.resume(admitted.run_id);assert.equal(resumed.run.status,done.run.status);checks.push('read-only-resume');
const wrong=new HermesRunsClient({baseUrl:c.baseUrl,token:'wrong-test-token'});
await assert.rejects(()=>wrong.start({...draft,idempotencyKey:c.key+'-unauthorized'}),e=>e.code==='http_401');checks.push('unauthorized-401');
writeFileSync(output,JSON.stringify({nonce:c.nonce,scenario:c.scenario,result:'PASS',run_id:admitted.run_id,
 admission:admitted,final:done.run,checks,...(lostError?{lost_error:lostError}:{})},null,2)+'\n');
