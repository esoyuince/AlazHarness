/** Opt-in, real Pi Durable/SQLite probe; only model responses and failure points are fixtures. */
import assert from 'node:assert/strict';
import { openSync, writeSync, fsyncSync, closeSync, readFileSync, existsSync, renameSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { Type, createModels, fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { Harness, createRegistry, defineTool, defineExtension, ToolResultEntry, LiveDoc } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';

const [scenario, phase, directory, nonce] = process.argv.slice(2);
const scenarios=['duplicate-reopen','before-effect','unsafe-effect','safe-effect','idempotent-effect','after-result','wait-cancel','task-cancel','storage-failure'];
assert(scenarios.includes(scenario));assert(['seed','resume','single'].includes(phase));
assert.match(nonce,/^[a-f0-9]{32}$/);const work=resolve(directory);assert.equal(process.cwd(),work);
const marker=JSON.parse(readFileSync(join(work,'probe.json'),'utf8'));assert.equal(marker.nonce,nonce);assert.equal(marker.scenario,scenario);
assert.equal(resolve(process.env.HOME),join(work,'home'));assert.equal(resolve(process.env.PI_CODING_AGENT_DIR),join(work,'home','pi'));
function save(name,data) { const target=join(work,name);assert(!existsSync(target),'Refusing existing receipt');const tmp=target+'.'+process.pid+'.tmp';const fd=openSync(tmp,'wx');try {writeSync(fd,JSON.stringify(data,null,2)+'\n');fsyncSync(fd);}finally{closeSync(fd);}renameSync(tmp,target); }
const notes={scenario,phase,pid:process.pid,nonce,modelCalls:0,toolEntries:0,toolAborts:0,reports:[],modelInferenceCalls:0,paidCalls:0};
const external=new DatabaseSync(join(work,'external.sqlite'));
external.exec('PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,task_key TEXT,pid INTEGER); CREATE TABLE IF NOT EXISTS effects(effect_key TEXT PRIMARY KEY,task_key TEXT,pid INTEGER)');
function attempt(taskId) {external.prepare('INSERT INTO attempts VALUES(?,?,?)').run(randomUUID(),taskId,process.pid);}
function effect(taskId) {const key=scenario==='idempotent-effect'?taskId:randomUUID();external.prepare('INSERT OR IGNORE INTO effects VALUES(?,?,?)').run(key,taskId,process.pid);}
function counts(){return {attempts:Number(external.prepare('SELECT count(*) n FROM attempts').get().n),effects:Number(external.prepare('SELECT count(*) n FROM effects').get().n)};}
let harness,root,submission,failCommit=false;const entered=Promise.withResolvers(),release=Promise.withResolvers(),admission=Promise.withResolvers();
let readySent=false;
async function barrier(boundary) {await admission.promise;if(!readySent){save('ready.json',{...notes,boundary,rootId:root.id,submissionId:submission.id,...counts()});readySent=true;}}
function pause(signal) {return new Promise((_,reject)=>{if(signal?.aborted){reject(signal.reason);return;}signal?.addEventListener('abort',()=>{notes.toolAborts++;reject(signal.reason);},{once:true});});}
const watchdog=setTimeout(()=>{console.error('PROBE_DEADLINE');process.exit(3);},25000);
// A short-lived fixture keeps the seed process alive at its exact crash boundary.
const keepAlive=setInterval(()=>{},1000);
const faux=fauxProvider();const models=createModels();models.setProvider(faux.provider);const registry=createRegistry();
const replay=['safe-effect','idempotent-effect'].includes(scenario)?'safe':'unsafe';
const tool=defineTool({name:'ledger_effect',description:'Commit one bounded fixture effect',parameters:Type.Object({}),replay,
  async execute(_args,api,ctx){
    assert(Number.isSafeInteger(api.taskId));const taskId=String(api.taskId);notes.toolEntries++;attempt(taskId);
    if(['wait-cancel','task-cancel','storage-failure'].includes(scenario)) {
      entered.resolve();
      if(scenario==='wait-cancel') {await Promise.race([release.promise,pause(ctx.abortSignal)]);}
      else {await pause(ctx.abortSignal);}
    }
    effect(taskId);
    if(phase==='seed'&&['unsafe-effect','safe-effect','idempotent-effect'].includes(scenario)) {
      // The external transaction has committed; native result has NOT returned.
      await barrier('external-effect-before-native-result');await pause(ctx.abortSignal);
    }
    return {output:[{type:'text',text:'effect-recorded'}]};
  }
});
registry.install(defineExtension({name:'alaz-fixture',tools:[tool]}));
async function modelStep(request,options){
  notes.modelCalls++;assert(notes.modelCalls<=5,'Unbounded model sequence');
  const results=request.messages.filter(m=>m.role==='toolResult');
  if(phase==='seed'&&scenario==='before-effect'&&results.length===0){await barrier('admitted-before-model-answer');return await pause(options.signal);}
  if(phase==='seed'&&scenario==='after-result'&&results.length){await barrier('native-result-before-final-answer');return await pause(options.signal);}
  return results.length?fauxAssistantMessage('fixture-final'):fauxAssistantMessage([fauxToolCall('ledger_effect',{}, {id:'fixture-call-1'})],{stopReason:'toolUse'});
}
faux.setResponses(scenario==='duplicate-reopen'?[()=>{notes.modelCalls++;return fauxAssistantMessage('original-input-result');}]:Array(6).fill(modelStep));
async function entries(){return [...(await root.entries({},1000,undefined,context)).items].reverse();}
async function inspect(){
 const all=await entries();const results=all.filter(e=>ToolResultEntry.is(e)).map(e=>e.model[0]);
 const live=await harness.snapshot(LiveDoc,root.id,context);
 return {rootId:root.id,submissionId:submission?.id,submissionStatus:submission?(await submission.status(context)).status:null,
  entryKinds:all.map(e=>e.kind),toolResults:results.length,toolErrors:results.filter(m=>m.isError).length,
  interrupted:results.some(m=>JSON.stringify(m.content).includes('interrupted')),
  liveIdle:!live?.run&&!live?.generation&&!(live?.tools?.length),...counts()};
}
try {
 const underlying=await openNodeSqliteStorage(join(work,'session.sqlite'));
 const storage=scenario==='storage-failure'&&phase==='seed'?new Proxy(underlying,{get(target,key){
  if(key==='commit')return async(...args)=>{if(failCommit){failCommit=false;throw new Error('ALAZ_INJECTED_COMMIT_FAILURE');}return target.commit(...args);};
  const value=Reflect.get(target,key,target);return typeof value==='function'?value.bind(target):value;
 }}):underlying;
 harness=await Harness.open(storage,{models,registry,settings:{retry:{enabled:false}},onReport:e=>notes.reports.push(String(e))},context);
 root=await harness.root(context,{agent:{model:{provider:'faux',modelId:'faux-1'}}});
 if(scenario==='duplicate-reopen') {
  const draft={type:'write',requestId:'request-1',entry:{kind:'note',data:{text:'original'}}};
  if(phase==='seed') {
   submission=await root.submit(draft,context);admission.resolve();
   const duplicate=await root.submit(draft,context);assert.equal(duplicate.id,submission.id);
   const input=await root.submit({type:'input',requestId:'input-request-1',content:'ORIGINAL_INPUT'},context);
   assert.equal((await input.wait(context)).status,'done');await harness.waitForIdle(context);
   save('seed.json',{rootId:root.id,submissionId:submission.id,inputId:input.id,pid:process.pid});
   notes.samePayloadSameId=true;assert.equal(notes.modelCalls,1);
  } else {
   const seed=JSON.parse(readFileSync(join(work,'seed.json'),'utf8'));assert.equal(root.id,seed.rootId);
   const original=await root.submit(draft,context);assert.equal(original.id,seed.submissionId);submission=original;
   const changed=await root.submit({...draft,entry:{kind:'note',data:{text:'CHANGED'}}},context);
   notes.changedPayloadSameId=changed.id===original.id;notes.payloadConflictEnforced=false;
   let rejected=false;try{await root.submit({type:'input',requestId:'request-1',content:'different type'},context);}catch{rejected=true;}
   assert(rejected);notes.typeMismatchRejected=true;
   const all=await entries();assert.equal(all.filter(e=>e.kind==='note').length,1);assert.equal(all.find(e=>e.kind==='note').data.text,'original');
   assert(notes.changedPayloadSameId,'Pinned upstream contract changed');
   const inputSame=await root.submit({type:'input',requestId:'input-request-1',content:'ORIGINAL_INPUT'},context);
   const inputChanged=await root.submit({type:'input',requestId:'input-request-1',content:'CHANGED_INPUT'},context);
   assert.equal(inputSame.id,seed.inputId);assert.equal(inputChanged.id,seed.inputId);
   assert.equal((await inputChanged.wait(context)).status,'done');await harness.waitForIdle(context);
   const users=(await entries()).filter(e=>e.kind==='pi.user');assert.equal(users.length,1);
   assert(JSON.stringify(users).includes('ORIGINAL_INPUT'));assert(!JSON.stringify(users).includes('CHANGED_INPUT'));
   assert.equal(notes.modelCalls,0);notes.inputChangedPayloadSameId=true;notes.inputOriginalPreserved=true;
   notes.newModelCallsOnInputRetry=notes.modelCalls;
  }
 } else if(phase==='resume') {
  const seed=JSON.parse(readFileSync(join(work,'seed.json'),'utf8'));assert.equal(root.id,seed.rootId);
  submission=await harness.submission(seed.submissionId,context);assert(submission);admission.resolve();
  if(scenario==='storage-failure'){
   notes.phantomWrite=(await entries()).some(e=>e.kind==='uncommitted-note');assert.equal(notes.phantomWrite,false);
   const fresh=await root.submit({type:'write',entry:{kind:'recovery-note',data:{ok:true}}},context);assert.equal((await fresh.status(context)).status,'done');
  }
  await submission.wait(context);await harness.waitForIdle(context);notes.sameSubmissionAfterReopen=true;
 } else {
  submission=await root.submit({type:'input',content:'Run ledger_effect once.',requestId:'request-1'},context);admission.resolve();
  if(phase==='seed')save('seed.json',{rootId:root.id,submissionId:submission.id,pid:process.pid});
  const pending=submission.wait(context);pending.catch(()=>{});
  if(scenario==='wait-cancel') {
   await entered.promise;const abort=new AbortController();
   const waiting=submission.wait({...context,abortSignal:abort.signal});waiting.catch(()=>{});abort.abort(new Error('WAIT_ONLY_CANCEL'));
   let rejected=false;try{await waiting;}catch{rejected=true;}assert(rejected);
   assert.equal(notes.toolAborts,0);assert.equal((await submission.status(context)).status,'placed');notes.waitCancelledWorkSurvived=true;
   release.resolve();await pending;await harness.waitForIdle(context);
  } else if(scenario==='task-cancel') {
   await entered.promise;notes.submissionAbort=await submission.abort(context);assert.equal(notes.submissionAbort,'already_placed');
   assert.equal(notes.toolAborts,0);await root.abort(context);await harness.waitForIdle(context);
   const settled=await pending;notes.cancelledSubmission=settled;assert.equal(settled.status,'unanswered');assert.equal(notes.toolAborts,1);
  } else if(scenario==='storage-failure') {
   await entered.promise;failCommit=true;
   let rejected=false;try{await root.submit({type:'write',entry:{kind:'uncommitted-note',data:{mustNotExist:true}}},context);}catch{rejected=true;}
   assert(rejected);const closed=await harness.closed;assert.equal(closed.reason,'failed');notes.closedReason=closed.reason;
   let pendingRejected=false;try{await pending;}catch{pendingRejected=true;}assert(pendingRejected);
   let laterRejected=false;try{await root.submit({type:'write',entry:{kind:'later-note',data:{}}},context);}catch{laterRejected=true;}
   assert(laterRejected);assert.equal(notes.toolAborts,1);notes.rejectedAfterFailure=laterRejected;
   notes.pendingWaitRejected=pendingRejected;
   save('seed-receipt.json',{...notes,...counts(),result:'PASS',faultScope:'injected storage.commit rejection before SQLite commit, not physical disk failure'});
   await harness.close(context);harness=undefined;
  } else {await pending;await harness.waitForIdle(context);}
 }
 if(harness){
  const state=await inspect();
  save(phase+'-receipt.json',{...notes,...state,result:'PASS',powerFailureTested:false,autonomyTested:false});
 }
} finally {
 try{if(harness)await harness.close(context);}finally{external.close();clearTimeout(watchdog);clearInterval(keepAlive);}
}
