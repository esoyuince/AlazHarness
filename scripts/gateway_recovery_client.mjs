/** One bounded real HermesRunsClient action; writes explicit errors, never retries. */
import {readFileSync,writeFileSync} from 'node:fs';
import {HermesRunsClient} from '../packages/claw-hermes/hermes-runs.mjs';
const [input,output]=process.argv.slice(2);
const c=JSON.parse(readFileSync(input,'utf8'));
const client=new HermesRunsClient({baseUrl:c.baseUrl,token:c.token,requestTimeoutMs:15000});
let receipt={nonce:c.nonce,action:c.action};
try {
 if(c.action==='start') receipt.value=await client.start({input:c.input,idempotencyKey:c.key,...(c.sessionId?{sessionId:c.sessionId}:{})});
 else if(c.action==='status')receipt.value=await client.status(c.runId);
 else if(c.action==='resume')receipt.value=await client.resume(c.runId,{executionTimeoutMs:25000,pollIntervalMs:50,settlementTimeoutMs:5000});
 else if(c.action==='stop')receipt.value=await client.stop(c.runId);
 else throw Error('Unknown recovery client action');
 receipt.ok=true;
} catch(e) {receipt.ok=false;receipt.code=e.code||e.name;receipt.mayHaveBeenAccepted=e.mayHaveBeenAccepted===true;}
writeFileSync(output,JSON.stringify(receipt,null,2)+'\n');
