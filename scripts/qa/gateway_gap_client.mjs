/** Independent observer: use the existing adapter, never fake native admission. */
import {readFileSync,writeFileSync} from 'node:fs';
import {HermesRunsClient} from '../../packages/claw-hermes/hermes-runs.mjs';
const [configPath,output]=process.argv.slice(2);
const c=JSON.parse(readFileSync(configPath,'utf8'));
const client=new HermesRunsClient({baseUrl:c.baseUrl,token:c.token,requestTimeoutMs:10000});
const status=await client.status(c.runId);
const replay=await client.start({input:c.input,idempotencyKey:c.key});
let conflict;
try {await client.start({input:c.input+' changed',idempotencyKey:c.key});conflict='not_rejected';}
catch(error) {conflict=error.code;}
const observed=await client.resume(c.runId,{executionTimeoutMs:1000,settlementTimeoutMs:1000});
writeFileSync(output,JSON.stringify({nonce:c.nonce,status,replay,conflict,observed},null,2)+'\n');
