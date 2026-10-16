/** Real required client for native broker acceptance. */
import {readFileSync,writeFileSync} from 'node:fs';
import {HostGateClient} from '../packages/claw-hermes/host-gate-client.mjs';
const [input,output]=process.argv.slice(2);const p=JSON.parse(readFileSync(input,'utf8'));
const c=new HostGateClient({baseUrl:p.baseUrl,token:p.token,requireProviderBroker:true,requireIsolatedRead:true,requestTimeoutMs:12000});
const result={scenario:p.scenario,nonce:p.nonce};
try {
 const permit=await c.prepare({requestId:p.requestId,input:'Use the indicated file tool and report its result.',model:'alaz-scripted'});
 const run=await c.dispatch(permit);result.runId=run.run_id;
 result.final=await c.resume(run.run_id,{executionTimeoutMs:60000,settlementTimeoutMs:8000});
} catch(error) {result.error={code:error.code??'unknown',hostCode:error.hostCode??null};}
writeFileSync(output,JSON.stringify(result,null,2)+'\n');
if(!result.runId&&!['missing-broker','stale-broker'].includes(p.scenario))process.exitCode=1;
