/** Explicit local experiment: real Pi Durable/SQLite, scripted faux provider, test tools only. */
import assert from 'node:assert/strict';
import { closeSync, existsSync, fsyncSync, openSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { BACKGROUND_CONTEXT as ctx } from '@earendil-works/chord/context';
import { createModels, fauxProvider, fauxAssistantMessage, fauxToolCall, Type } from '@earendil-works/pi-ai';
import { Harness, createRegistry, defineExtension, defineTool, LiveDoc, ProviderDoc, ToolResultEntry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';

const [scenario, phase] = process.argv.slice(2);
const scenarios=['admission','cancel-wait','abort-work','storage-before','storage-after','crash-pending','crash-unsafe','crash-safe','crash-committed'];
assert.ok(scenarios.includes(scenario));assert.ok(['single','before','after'].includes(phase));
const work=resolve(process.env.PI_DURABLE_OUTPUT ?? '');assert.equal(work,resolve(process.cwd()));
const db=join(work,'session.sqlite');
const metrics={modelCalls:0,toolExecutions:0,abortObserved:false,modelSawToolError:false,reports:[]};
const hold=setInterval(()=>{},1000);
let opened;
const admitted=Promise.withResolvers();
const summary={schema:1,scenario,phase,scope:'real_Pi_Durable_and_SQLite_scripted_provider_test_tool',
  modelInferenceCalls:0,paidCalls:0,osSandboxClaimed:false,powerLossTested:false,productionIntegrated:false};
function persist(name,value) {
  const target=join(work,name),tmp=target+'.tmp';const fd=openSync(tmp,'wx');
  try {writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fsyncSync(fd);} finally {closeSync(fd);}
  renameSync(tmp,target);
}
function append(name,value) {
  const fd=openSync(join(work,name),'a');try {writeFileSync(fd,JSON.stringify(value)+'\n');fsyncSync(fd);} finally {closeSync(fd);}
}
function lines(name) {return existsSync(join(work,name))?readFileSync(join(work,name),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];}
function barrier() {let release;const promise=new Promise(resolve=>{release=resolve;});return {promise,release};}
function waitAbort(signal) {return new Promise((_,reject)=>{const stop=()=>{metrics.abortObserved=true;reject(signal.reason??new Error('aborted'));};if(signal.aborted)stop();else signal.addEventListener('abort',stop,{once:true});});}
function blocked(signal) {return signal ? waitAbort(signal) : new Promise(()=>{});}
function countModel(){metrics.modelCalls++;assert.ok(metrics.modelCalls<=3,'Unplanned model call');}
function setup() {const faux=fauxProvider();const models=createModels();models.setProvider(faux.provider);return {faux,models,registry:createRegistry()};}
async function open(set,wrap) {
  const storage=await openNodeSqliteStorage(db);
  const h=await Harness.open(wrap?wrap(storage):storage,{models:set.models,registry:set.registry,
    settings:{retry:{enabled:false},compaction:{enabled:false}},
    onReport:(e)=>metrics.reports.push({name:e?.name??'Error',message:String(e?.message??e)})},ctx);
  const root=await h.root(ctx,{agent:{model:{provider:'faux',modelId:'faux-1'}}});opened=h;return {h,root};
}
async function entries(root) {const page=await root.entries({},1000,undefined,ctx);assert.ok(!page.nextCursor,'Unexpected transcript pagination');return [...page.items].reverse();}
async function close(h){await h.close(ctx);opened=undefined;}
async function idle(h,root){await h.waitForIdle(ctx);const live=await h.snapshot(LiveDoc,root.id,ctx);assert.ok(!live?.run);assert.equal(live?.tools?.length??0,0);return true;}
async function readiness(h,root,extra={}) {
  await admitted.promise;
  const ids=JSON.parse(readFileSync(join(work,'ids.json'),'utf8'));
  const provider=await h.snapshot(ProviderDoc,root.id,ctx);
  const es=await entries(root);const tasks=await root.commit(tx=>tx.scanTasks({conversationId:root.id},100),ctx);
  persist('ready.json',{scenario,phase,pid:process.pid,rootId:root.id,submissionId:ids.submissionId,
    providerId:provider?.sessionId??null,entries:es.map(e=>e.kind),taskStates:tasks.items.map(t=>({id:t.id,kind:t.kind,state:t.state})),
    attempts:lines('attempts.jsonl').length,effects:lines('effects.jsonl').length,modelCalls:metrics.modelCalls,...extra});
}
async function admission() {
  let set=setup(),{h,root}=await open(set);const rootId=root.id;
  const draft={type:'write',entry:{kind:'alaz.note',data:{text:'first'}},requestId:'same-key'};
  const first=await root.submit(draft,ctx);await first.wait(ctx);
  const same=await root.submit(draft,ctx);
  const changed=await root.submit({...draft,entry:{kind:'alaz.note',data:{text:'changed'}}},ctx);
  let typeError;try {await root.submit({type:'input',content:'different type',requestId:'same-key'},ctx);} catch(e){typeError=e.message;}
  assert.equal(same.id,first.id);assert.equal(changed.id,first.id);assert.match(typeError??'',/already identifies/);
  const other=await h.createConversation({ownership:{kind:'ownerless'}},ctx);
  const scoped=await other.submit(draft,ctx);assert.notEqual(scoped.id,first.id);
  const before=await entries(root);assert.equal(before.length,1);assert.equal(before[0].data.text,'first');
  await close(h);({h,root}=await open(set));assert.equal(root.id,rootId);
  const reacquired=await h.submission(first.id,ctx);assert.equal((await reacquired.wait(ctx)).status,'done');
  assert.equal((await root.submit(draft,ctx)).id,first.id);assert.equal((await entries(root)).length,1);
  // Also test actual INPUT admission, not just a display-only write.
  const reached=barrier(),release=barrier();
  set.faux.setResponses([async (_r,options)=>{countModel();reached.release();await Promise.race([release.promise,waitAbort(options.signal)]);return fauxAssistantMessage('input finished');}]);
  const input={type:'input',content:'input-first',requestId:'same-input-key'};
  const firstInput=await root.submit(input,ctx);await reached.promise;
  const changedInput=await root.submit({...input,content:'input-changed'},ctx);assert.equal(changedInput.id,firstInput.id);
  const inputMessages=(await entries(root)).flatMap(e=>e.model??[]).filter(m=>m.role==='user');
  assert.deepEqual(inputMessages.map(m=>m.content),['input-first']);
  release.release();assert.equal((await firstInput.wait(ctx)).status,'done');await idle(h,root);
  await close(h);({h,root}=await open(set));
  assert.equal((await root.submit({...input,content:'input-changed-again'},ctx)).id,firstInput.id);
  assert.equal((await (await h.submission(firstInput.id,ctx)).wait(ctx)).status,'done');
  Object.assign(summary,{inputChangedPayloadSameId:true,inputOriginalPayloadPreserved:true,inputDuplicateAfterReopenSameId:true,
    sameKeySameId:true,changedPayloadSameId:true,originalPayloadPreserved:true,typeMismatchRejected:true,
    conversationScopeSeparated:true,reopenIdentityPreserved:true,strictPayloadConflict:false,
    adoptionBlockers:['same_request_id_changed_payload_returns_existing_instead_of_conflict']});
  await close(h);
}
async function cancellation() {
  const set=setup(),reached=barrier(),release=barrier();
  set.faux.setResponses([async (_request,options)=>{countModel();reached.release();await Promise.race([release.promise,waitAbort(options.signal)]);return fauxAssistantMessage('finished');}]);
  const {h,root}=await open(set);const sub=await root.submit({type:'input',content:'wait',requestId:'cancel-case'},ctx);await reached.promise;
  if(scenario==='cancel-wait') {
    const controller=new AbortController();const waiting=sub.wait({...ctx,abortSignal:controller.signal}).then(()=>({resolved:true}),e=>({error:e.message}));
    controller.abort(new Error('only-stop-wait'));const outcome=await waiting;assert.equal(outcome.error,'only-stop-wait');
    assert.equal((await sub.status(ctx)).status,'placed');assert.equal(metrics.abortObserved,false);
    release.release();assert.equal((await sub.wait(ctx)).status,'done');
    Object.assign(summary,{waitCancelled:true,workContinued:true,taskCompleted:true,abortObservedImmediatelyAfterWait:false});
  } else {
    assert.equal(await sub.abort(ctx),'already_placed');await root.abort(ctx);
    const result=await sub.wait(ctx);assert.equal(result.status,'unanswered');assert.equal(metrics.abortObserved,true);
    Object.assign(summary,{submissionWithdrawalWasNotWorkAbort:true,workAborted:true,settlement:result,taskCompleted:false});
  }
  summary.idle=await idle(h,root);await close(h);
}
async function storageFailure() {
  const set=setup();let armed=false;let injectionCount=0;const failure=new Error('ALAZ_INJECTED_COMMIT_FAILURE');
  const wrap=storage=>new Proxy(storage,{get(target,key){if(key==='commit')return async (...args)=>{
    if(!armed)return target.commit(...args);armed=false;injectionCount++;
    if(scenario==='storage-after')await target.commit(...args);
    throw failure;
  };const value=Reflect.get(target,key,target);return typeof value==='function'?value.bind(target):value;}});
  let {h,root}=await open(set,wrap);const rootId=root.id;
  const draft={type:'write',entry:{kind:'alaz.storage',data:{text:'single-record'}},requestId:'fault-key'};
  armed=true;let original=false;try{await root.submit(draft,ctx);}catch(e){original=e===failure;}
  assert.equal(original,true);const end=await h.closed;opened=undefined;assert.equal(end.reason,'failed');
  let sessionFailed=false;try{await root.submit(draft,ctx);}catch(e){sessionFailed=e.name==='SessionFailed';}assert.ok(sessionFailed);
  ({h,root}=await open(set));assert.equal(root.id,rootId);const before=await entries(root);
  assert.equal(before.length,scenario==='storage-after'?1:0);
  const sub=await root.submit(draft,ctx);assert.equal((await sub.wait(ctx)).status,'done');
  const after=await entries(root);assert.equal(after.length,1);assert.equal(after[0].data.text,'single-record');
  Object.assign(summary,{injectionCount,originalErrorPreserved:original,sessionFailed,reopened:true,
    persistedBeforeRetry:before.length,recordsAfterRetry:after.length,
    injectionBoundary:scenario==='storage-after'?'after_real_commit_before_ack':'before_real_commit',
    physicalDiskFailure:false,taskCompleted:true});
  await close(h);
}
async function crash() {
  const first=phase==='before';const set=setup();let h,root;
  const safe=scenario==='crash-safe';
  const tool=defineTool({name:'alaz_effect',description:'Controlled local effect probe',parameters:Type.Object({}),
    ...(safe?{replay:'safe'}:{}),execute:async (_args,_api,toolContext)=>{
      metrics.toolExecutions++;append('attempts.jsonl',{pid:process.pid,phase});
      if(safe){
        // Genuine idempotent effect: exclusive creation keyed by this experiment.
        let fd;try{fd=openSync(join(work,'effect-key'),'wx');writeFileSync(fd,'one-effect');fsyncSync(fd);append('effects.jsonl',{key:'effect-key'});}catch(e){if(e.code!=='EEXIST')throw e;}finally{if(fd!==undefined)closeSync(fd);}
      } else append('effects.jsonl',{pid:process.pid,phase});
      if(first&&scenario!=='crash-committed') {await readiness(h,root,{cut:'effect_complete_result_uncommitted'});await blocked(toolContext.abortSignal);}
      return {output:[{type:'text',text:'effect-result'}]};
    }});
  if(scenario!=='crash-pending')set.registry.install(defineExtension({name:'alaz.effect-probe',tools:[tool]}));
  const finish=request=>{countModel();const results=request.messages.filter(m=>m.role==='toolResult');metrics.modelSawToolError=results.some(m=>m.isError);
    if(scenario!=='crash-pending')assert.equal(results.length,1,'Need actual recovered tool result');
    return fauxAssistantMessage(metrics.modelSawToolError?'Tool interrupted; outcome uncertain':'observed complete');};
  if(first&&scenario==='crash-pending')set.faux.setResponses([async (_r,options)=>{countModel();await readiness(h,root,{cut:'request_pending_no_response'});return blocked(options.signal);}]);
  else if(first)set.faux.setResponses([()=>{countModel();return fauxAssistantMessage([fauxToolCall('alaz_effect',{}, {id:'effect-call'})],{stopReason:'toolUse'});},finish]);
  else set.faux.setResponses([finish]);
  ({h,root}=await open(set));
  if(first) {
    const sub=await root.submit({type:'input',content:'bounded durable experiment',requestId:'crash-key'},ctx);
    persist('ids.json',{rootId:root.id,submissionId:sub.id});admitted.resolve();
    if(scenario==='crash-committed') {const final=await sub.wait(ctx);assert.equal(final.status,'done');await idle(h,root);await readiness(h,root,{cut:'settled_commit_before_close',settlement:final});await blocked();}
    else await sub.wait(ctx);
    throw new Error('Crash phase unexpectedly finished');
  }
  const ids=JSON.parse(readFileSync(join(work,'ids.json'),'utf8'));
  const ready=JSON.parse(readFileSync(join(work,'ready.json'),'utf8'));
  assert.equal(root.id,ids.rootId);const sub=await h.submission(ids.submissionId,ctx);assert.ok(sub);
  const provider=await h.snapshot(ProviderDoc,root.id,ctx);assert.equal(provider?.sessionId,ready.providerId);
  const final=await sub.wait(ctx);assert.equal(final.status,'done');summary.idle=await idle(h,root);
  const es=await entries(root);const results=es.filter(e=>ToolResultEntry.is(e)).map(e=>e.model[0]);
  const attempts=lines('attempts.jsonl').length,effects=lines('effects.jsonl').length;
  const toolErrors=results.filter(m=>m.isError).length;
  if(scenario==='crash-pending'){assert.equal(attempts,0);assert.equal(metrics.modelCalls,1);}
  else {assert.equal(effects,1);assert.equal(results.length,1);assert.equal(attempts,safe?2:1);
    assert.equal(toolErrors,scenario==='crash-unsafe'?1:0);
    assert.equal(metrics.modelCalls,scenario==='crash-committed'?0:1);}
  Object.assign(summary,{rootIdentityPreserved:true,submissionIdentityPreserved:true,providerIdentityPreserved:true,
    settlement:final,toolResults:results.length,toolErrors,attempts,effects,
    toolResultText:results.map(m=>m.content.filter(c=>c.type==='text').map(c=>c.text).join('')),
    taskCompleted:scenario!=='crash-unsafe',uncertainEffect:scenario==='crash-unsafe',
    safeLabelAloneGuaranteesExactlyOnce:false});
  await close(h);
}
try {
  if(scenario==='admission')await admission();
  else if(scenario.startsWith('storage-'))await storageFailure();
  else if(scenario.startsWith('crash-'))await crash();
  else await cancellation();
  Object.assign(summary,metrics,{characterization:'PASS',processCleanClose:true});
  persist('receipt.json',summary);console.log(JSON.stringify(summary));
} catch(error) {
  summary.characterization='FAIL';summary.failure={name:error.name,message:error.message};Object.assign(summary,metrics);
  persist('receipt.json',summary);console.error(error.stack);process.exitCode=1;
} finally {if(opened)await opened.close(ctx);clearInterval(hold);}
