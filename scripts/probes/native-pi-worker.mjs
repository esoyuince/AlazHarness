/** Native Pi Agent + native read tool + native HTTP provider; model output alone is scripted. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { readFile, writeFile, access } from 'node:fs/promises';
import { createHash, randomBytes } from 'node:crypto';
import { resolve } from 'node:path';
import { Agent } from '@earendil-works/pi-agent-core';
import { streamSimple } from '@earendil-works/pi-ai/api/openai-completions';
import { createReadTool } from '@earendil-works/pi-coding-agent/core/tools/read.ts';
import { createProviderRequestGate } from '../../packages/hybrid-runtime/provider-request-gate.mjs';

const SCENARIOS = ['file-read','missing-file','cancelled-model','timeout-model','budget-stop',
  'retry-cap','truncated-stream','model-switch','event-barrier','permission-denied','concurrent-prompt'];
const [scenario, outputArg] = process.argv.slice(2);
assert(SCENARIOS.includes(scenario), 'Unknown scenario');
const output = resolve(outputArg);
assert.equal(process.cwd(), output, 'Worker must use its fresh output directory');
const inputPath = resolve(output, 'input.txt');
const nonce = 'ALAZ_PI_' + randomBytes(16).toString('hex');
await writeFile(inputPath, nonce + '\nışık:42\n', { flag: 'wx' });
const target = scenario === 'missing-file' ? resolve(output,'missing.txt') : inputPath;
const transcriptEvents = [], httpCalls = [], errors = [];
let agent, gate, timer, transportClosed = 0, endHeld = false, endReleased = false, blockCount = 0;
let admitResolve, endResolve, releaseEnd;
const admitted = new Promise(r => { admitResolve = r; });
const sawEnd = new Promise(r => { endResolve = r; });
const endBarrier = new Promise(r => { releaseEnd = r; });
const sockets = new Set();

function send(res, delta, finishReason) {
  const value = { id:'local-scripted', object:'chat.completion.chunk', created:1,
    model:'alaz-scripted', choices:[{index:0, delta, finish_reason:finishReason ?? null}] };
  res.write('data: ' + JSON.stringify(value) + '\n\n');
}
const server = createServer(async (req,res) => {
  try {
    assert.equal(req.url,'/v1/chat/completions'); assert.equal(req.method,'POST');
    const parts = []; let size=0;
    for await (const part of req) { size+=part.length; assert(size<2_000_000); parts.push(part); }
    const body=JSON.parse(Buffer.concat(parts)); assert.equal(body.stream,true);
    const toolMessages=body.messages.filter(m=>m.role==='tool');
    httpCalls.push({model:body.model,toolResults:toolMessages.length,stream:body.stream});
    res.on('close',()=>{transportClosed++;});
    admitResolve();
    if (scenario==='retry-cap') {
      res.writeHead(503,{'content-type':'application/json','retry-after':'0'});
      res.end(JSON.stringify({error:{message:'Synthetic retryable error',type:'server_error'}}));return;
    }
    if (['cancelled-model','timeout-model'].includes(scenario)) return;
    res.writeHead(200,{'content-type':'text/event-stream','cache-control':'no-cache'});
    send(res,{role:'assistant'});
    if (scenario==='truncated-stream') {
      send(res,{content:'INCOMPLETE_NOT_A_SUCCESS'});res.end('data: [DONE]\n\n');return;
    }
    if (!toolMessages.length) {
      send(res,{tool_calls:[{index:0,id:'pi-read-1',type:'function',function:{name:'read',arguments:JSON.stringify({path:target})}}]});
      send(res,{},'tool_calls');
    } else {
      const content=String(toolMessages.at(-1).content);
      if (scenario==='missing-file' || scenario==='permission-denied') {
        assert(!content.includes(nonce));send(res,{content:'READ_FAILED'});
      } else {
        assert(content.includes(nonce),'Native tool result must carry unpredictable nonce');
        send(res,{content:'NATIVE_READ_OK '+nonce});
      }
      send(res,{},'stop');
    }
    res.end('data: [DONE]\n\n');
  } catch (error) { errors.push(error.message);res.destroy(error); }
});
server.on('connection',socket=>{sockets.add(socket);socket.on('close',()=>sockets.delete(socket));});
server.listen(0,'127.0.0.1');await once(server,'listening');
const baseUrl=`http://127.0.0.1:${server.address().port}/v1`;
gate=createProviderRequestGate({endpoint:baseUrl+'/chat/completions',maxRequests:['budget-stop','retry-cap'].includes(scenario)?1:6});
const model={id:'alaz-scripted',name:'Scripted local provider',api:'openai-completions',provider:'alaz-loopback',
  baseUrl,reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:131072,maxTokens:256,
  compat:{supportsFinishReason:true,supportsUsageInStreaming:false}};
let receipt;
try {
  agent=new Agent({initialState:{systemPrompt:'Read only the fixture through the provided tool.',model,tools:[createReadTool(output)]},
    sessionId:'alaz-pi-native',toolExecution:'sequential',
    streamFn:(m,context,options)=>streamSimple(m,context,{...options,apiKey:'local-fixture-not-a-secret',
      maxTokens:256,maxRetries:scenario==='retry-cap'?1:0,fetch:gate.fetch,timeoutMs:5000}),
    beforeToolCall:async ({toolCall})=>{
      if (toolCall.name!=='read' || resolve(toolCall.arguments.path)!==target) throw new Error('Unexpected tool target');
      if (scenario==='permission-denied') {blockCount++;return {block:true,reason:'Fixture policy denies this read'};}
      return undefined;
    },
  });
  let promptSettled=false;
  agent.subscribe(async event=>{
    transcriptEvents.push({type:event.type,isError:event.isError??null});
    if (scenario==='event-barrier' && event.type==='agent_end') {
      endHeld=true;endResolve();await endBarrier;endReleased=true;
    }
  });
  const pending=agent.prompt('Read input.txt and report its first line.').then(()=>{promptSettled=true;});
  if (scenario==='cancelled-model') {await admitted;agent.abort();}
  if (scenario==='timeout-model') {await admitted;timer=setTimeout(()=>agent.abort(),100);}
  if (scenario==='concurrent-prompt') {
    // The first run owns the session immediately, before the first network await.
    await assert.rejects(agent.prompt('A competing run'),/already processing/);
  }
  if (scenario==='event-barrier') {
    await sawEnd;
    assert(agent.state.isStreaming);assert(!promptSettled);
    let idle=false;const idleWait=agent.waitForIdle().then(()=>{idle=true;});
    await new Promise(setImmediate);assert(!idle);releaseEnd();await idleWait;
  }
  await pending;await agent.waitForIdle();
  if (scenario==='model-switch') {
    agent.state.model={...model,id:'alaz-scripted-second'};
    await agent.prompt('Reuse the prior file result. Do not read the file again.');await agent.waitForIdle();
  }
  const assistants=agent.state.messages.filter(m=>m.role==='assistant');
  const last=assistants.at(-1);
  const toolResults=agent.state.messages.filter(m=>m.role==='toolResult');
  const successTools=toolResults.filter(m=>!m.isError);
  const nativeErrors=toolResults.filter(m=>m.isError);
  const finalText=(last?.content??[]).filter(b=>b.type==='text').map(b=>b.text).join('');
  assert(!agent.state.isStreaming);assert.equal(agent.state.pendingToolCalls.size,0);assert.equal(errors.length,0,errors.join(';'));
  let expectedOutcome;
  if (['cancelled-model','timeout-model'].includes(scenario)) {
    assert.equal(last.stopReason,'aborted');assert.equal(toolResults.length,0);assert.equal(httpCalls.length,1);expectedOutcome='cancelled';
  } else if (scenario==='budget-stop') {
    assert.equal(gate.snapshot().submitted,1);assert(gate.snapshot().denied>=1);assert.equal(httpCalls.length,1);
    assert.equal(last.stopReason,'error');assert.equal(successTools.length,1);expectedOutcome='budget_exhausted';
  } else if (scenario==='retry-cap') {
    assert.equal(gate.snapshot().submitted,1);assert(gate.snapshot().denied>=1);assert.equal(httpCalls.length,1);
    assert.equal(last.stopReason,'error');assert.equal(toolResults.length,0);expectedOutcome='budget_exhausted';
  } else if (scenario==='truncated-stream') {
    assert.equal(last.stopReason,'error');assert.equal(toolResults.length,0);assert.equal(httpCalls.length,1);expectedOutcome='provider_error';
  } else if (['missing-file','permission-denied'].includes(scenario)) {
    assert.equal(nativeErrors.length,1);assert.equal(successTools.length,0);assert.equal(finalText,'READ_FAILED');
    assert.equal(httpCalls.length,2);expectedOutcome='tool_failed';
    if(scenario==='permission-denied')assert.equal(blockCount,1);
  } else {
    assert.equal(last.stopReason,'stop');assert(finalText.includes(nonce));assert.equal(successTools.length,1);
    assert.equal(httpCalls.length,scenario==='model-switch'?3:2);expectedOutcome='completed';
    if(scenario==='event-barrier')assert(endHeld&&endReleased);
    if(scenario==='model-switch')assert.equal(httpCalls.at(-1).model,'alaz-scripted-second');
  }
  assert.equal(await readFile(inputPath,'utf8'),nonce+'\nışık:42\n');
  receipt={scenario,result:'PASS',expectedOutcome,nativeStopReason:last.stopReason,
    httpRequests:httpCalls.length,gate:gate.snapshot(),nativeReadResults:successTools.length,
    nativeToolErrors:nativeErrors.length,toolResultSeenByModel:httpCalls.some(x=>x.toolResults>0),
    fileNonceVerified:successTools.some(x=>JSON.stringify(x.content).includes(nonce)),
    settled:!agent.state.isStreaming,modelCalls:httpCalls,events:transcriptEvents,
    finalOutputSha256:createHash('sha256').update(finalText).digest('hex'),
    nativeAgent:true,nativeReadTool:true,nativeHttpProvider:true,scriptedModel:true,
    modelInferenceCalls:0,paidCalls:0,requestCapOwner:'AlazHarness injected fetch gate',
    currencyBudgetTested:false,persistenceTested:false,fullCodingAgentSdk:false,autonomy:false,osSandboxClaimed:false};
} catch(error) {
  receipt={scenario,result:'FAIL',errorType:error.name,error:error.message,gate:gate?.snapshot(),httpRequests:httpCalls.length,events:transcriptEvents};
  process.exitCode=1;
} finally {
  clearTimeout(timer);releaseEnd();agent?.abort();gate?.close();
  const closing=Array.from(sockets, socket=>new Promise(r=>{socket.once('close',r);socket.destroy();}));
  await new Promise(r=>server.close(r));await Promise.all(closing);
}
receipt.serverClosed=!server.listening;receipt.openServerSockets=sockets.size;receipt.gateAfterCleanup=gate?.snapshot();
if(!receipt.serverClosed || receipt.openServerSockets!==0){receipt.result='FAIL';receipt.cleanupFailure=true;process.exitCode=1;}
await writeFile(resolve(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(receipt));
