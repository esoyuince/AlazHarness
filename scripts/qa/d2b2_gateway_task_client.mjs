/** Tool-free native Hermes task used only to produce an authentic terminal run.
 * No replay after uncertain dispatch, no provider/service credential in report. */
import {readFileSync,writeFileSync} from 'node:fs';
import {HostGateClient} from '../../packages/claw-hermes/host-gate-client.mjs';
const [config,output]=process.argv.slice(2);
const c=JSON.parse(readFileSync(config,'utf8'));
if (!c || typeof c.baseUrl!=='string' || typeof c.token!=='string'
    || typeof c.requestId!=='string' || typeof c.marker!=='string') throw Error('invalid owned fixture');
const prompt='Reply with the exact synthetic caution marker '+c.marker+
  ' and state that observed evidence is not proof of learning. Do not use tools.';
const intent={requestId:c.requestId,input:prompt,model:'alaz-scripted'};
const host=new HostGateClient({baseUrl:c.baseUrl,token:c.token,
  requireProviderBroker:true,requestTimeoutMs:18000});
const permit=await host.prepare(intent);
const accepted=await host.dispatch(permit);
const result=await host.resume(accepted.run_id,{executionTimeoutMs:90000,settlementTimeoutMs:12000});
if (result.run.status!=='completed' || !result.run.output.includes(c.marker))
  throw Error('native terminal not completed with marker');
writeFileSync(output,JSON.stringify({
  status:result.run.status,runId:accepted.run_id,
  idempotencyKey:permit.idempotencyKey,observed:result.run,originalBody:{input:prompt,model:'alaz-scripted'},
  source:'real_native_gateway_terminal',extraDispatches:0,
  skillTransferVerified:false
},null,2)+'\n');
