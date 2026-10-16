/** Actual required-isolation client against the native public Gateway. */
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {HostGateClient} from '../packages/claw-hermes/host-gate-client.mjs';
const [input,output]=process.argv.slice(2),c=JSON.parse(readFileSync(input,'utf8'));
const client=new HostGateClient({baseUrl:c.baseUrl,token:c.token,requestTimeoutMs:10000,requireIsolatedRead:true});
const answer={nonce:c.nonce};
if(['missing-isolation','wrong-backend'].includes(c.scenario)) {
  try {await client.prepare({requestId:c.requestId,input:'Use the indicated file tool and report its result.',model:'alaz-scripted'});throw new Error('Unexpected permit');}
  catch(e) {if(!['isolated_read_boundary_required','host_http_409','host_http_503'].includes(e.code))throw e;answer.refusal=e.code;}
} else {
  const cap=await client.capabilities();if(cap.isolatedReadBoundaryVersion!==1)throw new Error('Missing required isolation');
  const permit=await client.prepare({requestId:c.requestId,input:'Use the indicated file tool and report its result.',model:'alaz-scripted'});
  const accepted=await client.dispatch(permit);answer.runId=accepted.run_id;
  writeFileSync(output+'.accepted',JSON.stringify({runId:accepted.run_id,nonce:c.nonce})+'\n');
  if(c.scenario==='cancel-native') {
    const until=Date.now()+35000;
    while(!existsSync(c.cancelBarrier)){if(Date.now()>=until)throw new Error('No observed running container');await new Promise(r=>setTimeout(r,50));}
    const barrier=JSON.parse(readFileSync(c.cancelBarrier,'utf8'));
    if(barrier.nonce!==c.nonce||barrier.runId!==accepted.run_id)throw new Error('Wrong cancellation scope');
    answer.stop=await client.stop(accepted.run_id);
  }
  answer.final=await client.resume(accepted.run_id,{executionTimeoutMs:60000,pollIntervalMs:100});
}
writeFileSync(output,JSON.stringify(answer,null,2)+'\n');
