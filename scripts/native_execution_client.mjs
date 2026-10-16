/** Actual host/Gateway path; provider is a separately instrumented fixture. */
import {readFileSync,writeFileSync} from 'node:fs';
import {HostGateClient} from '../packages/claw-hermes/host-gate-client.mjs';
const [input,output]=process.argv.slice(2),c=JSON.parse(readFileSync(input,'utf8'));
const h=new HostGateClient({baseUrl:c.baseUrl,token:c.token,requestTimeoutMs:10000,requireExecution:true});
let data={nonce:c.nonce};
if(c.scenario==='unknown-price'){
  try{await h.prepare({requestId:c.requestId,input:'Read the fixture',model:'alaz-scripted'});throw new Error('Unexpected permission');}
  catch(e){if(e.code!=='host_http_404')throw e;data.refusal=e.code;}
}else{
  const capability=await h.capabilities();if(capability.executionBoundaryVersion!==1)throw new Error('Missing execution boundary');
  const p=await h.prepare({requestId:c.requestId,input:'Use the indicated file tool and report its result.',model:'alaz-scripted'});
  const accepted=await h.dispatch(p);data.runId=accepted.run_id;
  data.final=await h.resume(accepted.run_id,{executionTimeoutMs:60000,pollIntervalMs:100});
}
writeFileSync(output,JSON.stringify(data,null,2)+'\n');
