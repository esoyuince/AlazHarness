/** Real Pi Harness/SQLite. Controlled model, failure injection and bounded local tool only. */
import assert from 'node:assert/strict';
import {readFileSync,openSync,writeSync,fsyncSync,closeSync,renameSync} from 'node:fs';
import {join,resolve,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {BACKGROUND_CONTEXT as ctx} from '@earendil-works/chord/context';
import {Harness,defineDocFamily,createRegistry,defineTool,defineExtension,ToolResultEntry} from '@earendil-works/pi-durable';
import {openNodeSqliteStorage} from '@earendil-works/pi-durable/storage/sqlite/node';
import {createModels,fauxProvider,fauxAssistantMessage,fauxToolCall,Type} from '@earendil-works/pi-ai';
import {createStrictAdmission,prepareAdmission,BINDING_KIND} from '../packages/admission/strict-admission.mjs';

const [scenario,phase,directory,nonce,source] = process.argv.slice(2);
const work=resolve(directory), project=resolve(dirname(fileURLToPath(import.meta.url)),'..');
assert.equal(work,process.cwd()); assert.match(nonce,/^[a-f0-9]{32}$/);
assert.equal(resolve(process.env.HOME),join(work,'home'));
const marker=JSON.parse(readFileSync(join(work,'probe.json'),'utf8'));
assert.equal(marker.nonce,nonce);assert.equal(marker.scenario,scenario);
const pin=JSON.parse(readFileSync(join(project,'config/admission-compatibility.lock.json'),'utf8'));
const seam=join(source,pin.seam);
assert.equal(createHash('sha256').update(readFileSync(seam)).digest('hex'),pin.seam_sha256);
const {admitSubmission}=await import(pathToFileURL(seam));
const facts={scenario,phase,nonce,pid:process.pid,modelCalls:0,checks:[],reports:[]};
function save(name,value){const path=join(work,name),tmp=path+'.tmp';const fd=openSync(tmp,'wx');
 try{writeSync(fd,JSON.stringify(value,null,2)+'\n');fsyncSync(fd);}finally{closeSync(fd);}renameSync(tmp,path);}
const keep=setInterval(()=>{},1000),deadline=setTimeout(()=>{console.error('ADMISSION_PROBE_TIMEOUT');process.exit(3);},20000);
let h,root,gate,armed=false,external;
const admitted=Promise.withResolvers();
function hang(signal){return new Promise((_,reject)=>{if(signal?.aborted)reject(signal.reason);else signal?.addEventListener('abort',()=>reject(signal.reason),{once:true});});}
function boundary(extra){save('ready.json',{...facts,...extra});return hang();}
const writeDraft=(text='original')=>({type:'write',requestId:'key-1',entry:{kind:'alaz.note',data:{text,n:7}}});
const inputDraft=()=>({type:'input',requestId:'key-1',content:'Execute the bounded fixture once.'});
async function rejectCode(action,code){await assert.rejects(action,e=>e?.code===code);facts.checks.push(code);}
async function allEntries(c=root){const page=await c.entries({},1000,undefined,ctx);assert(!page.nextCursor);return [...page.items].reverse();}
async function result(a){const settled=await a.submission.wait(ctx);await h.waitForIdle(ctx);return settled;}
try{
 const faux=fauxProvider(),models=createModels();models.setProvider(faux.provider);const registry=createRegistry();
 if(scenario==='kill-unsafe-effect'){
  external=new DatabaseSync(join(work,'external.sqlite'));
  external.exec('PRAGMA synchronous=FULL;CREATE TABLE IF NOT EXISTS effects(k INTEGER PRIMARY KEY AUTOINCREMENT,task_id INTEGER)');
  registry.install(defineExtension({name:'alaz-test',tools:[defineTool({name:'effect',description:'one bounded fixture effect',parameters:Type.Object({}),
   async execute(_args,api,context){external.prepare('INSERT INTO effects(task_id) VALUES(?)').run(api.taskId);
    await admitted.promise;
    save('ready.json',{...facts,boundary:'external-effect-no-result',rootId:root.id,effects:1});
    return await hang(context.abortSignal);
   }})]}));
 }
 const reached=Promise.withResolvers(),release=Promise.withResolvers();
 const model=async(request,options)=>{assert(++facts.modelCalls<=4);
  if(scenario==='canonical-input' && facts.modelCalls===1){reached.resolve();await Promise.race([release.promise,hang(options.signal)]);}
  if(scenario==='kill-unsafe-effect'){
   const tools=request.messages.filter(x=>x.role==='toolResult');
   if(!tools.length)return fauxAssistantMessage([fauxToolCall('effect',{}, {id:'effect-1'})],{stopReason:'toolUse'});
   assert.equal(tools.length,1);assert.equal(tools[0].isError,true);assert.match(JSON.stringify(tools[0]),/interrupted/);
   facts.uncertainEffectPreserved=true;
  }
  return fauxAssistantMessage('controlled answer');};
 faux.setResponses(Array(5).fill(model));
 const underlying=await openNodeSqliteStorage(join(work,'session.sqlite'));
 const storage=new Proxy(underlying,{get(target,key){if(key==='commit')return async(writes,context)=>{
  const sub=writes.find(x=>x.type==='submission' && x.value.requestId==='key-1');
  if(armed && sub){armed=false;
   const after=scenario.endsWith('after');
   if(after)await target.commit(writes,context);
   facts.injectionBoundary=after?'after-commit-before-ack':'before-commit';
   if(scenario.startsWith('kill-'))return await boundary({boundary:facts.injectionBoundary,rootId:root.id,submissionId:sub.value.id});
   throw new Error('ADMISSION_STORAGE_FAULT');
  }
  return target.commit(writes,context);
 };const value=Reflect.get(target,key,target);return typeof value==='function'?value.bind(target):value;}});
 h=await Harness.open(storage,{models,registry,settings:{retry:{enabled:false},compaction:{enabled:false}},onReport:e=>facts.reports.push(e.name+': '+e.message)},ctx);
 root=await h.root(ctx,{agent:{model:{provider:'faux',modelId:'faux-1'}}});
 gate=createStrictAdmission({harness:h,defineDocFamily,admitSubmission});
 const submit=(d,scope={})=>gate.submit(root.id,d,ctx,scope);
 if(phase==='resume'){
  const seeded=JSON.parse(readFileSync(join(work,'seed.json'),'utf8'));assert.equal(root.id,seeded.rootId);
  const d=scenario==='kill-unsafe-effect'?inputDraft():writeDraft();
  const mustExist=scenario!=='kill-before' && scenario!=='fault-before';
  if(mustExist)await rejectCode(()=>submit({...d,...(d.type==='input'?{content:'CHANGED'}:{entry:{kind:'alaz.note',data:{text:'CHANGED'}}})}),'request_payload_conflict');
  const accepted=await submit(d);assert.equal(accepted.reused,mustExist);facts.reused=accepted.reused;facts.submissionId=accepted.submission.id;
  await result(accepted);
  if(scenario==='kill-unsafe-effect'){
   const tools=(await allEntries()).filter(e=>ToolResultEntry.is(e));assert.equal(tools.length,1);assert(tools[0].model[0].isError);
   assert.equal(external.prepare('SELECT count(*) n FROM effects').get().n,1);
   facts.effects=1;facts.uncertainEffectPreserved=true;
  }
  facts.checks.push('same-owner-new-process-recovery');
 }else if(scenario.startsWith('fault-') || ['kill-before','kill-after'].includes(scenario)){
  save('seed.json',{rootId:root.id});armed=true;
  if(scenario.startsWith('fault-')){
   await assert.rejects(()=>submit(writeDraft()),/ADMISSION_STORAGE_FAULT/);
   const ended=await h.closed;assert.equal(ended.reason,'failed');
   await assert.rejects(()=>submit(writeDraft()),e=>e.name==='SessionFailed');
   facts.failedClosed=true;facts.checks.push('original-error-and-failed-session');
  }else await submit(writeDraft());
 }else if(scenario==='kill-unsafe-effect'){
  save('seed.json',{rootId:root.id});const a=await submit(inputDraft());admitted.resolve();await result(a);
  throw new Error('Seed should have been killed');
 }else if(scenario==='canonical-write'){
  const a=await submit(writeDraft());await result(a);const b=await submit({entry:{data:{n:7,text:'original'},kind:'alaz.note'},requestId:'key-1',type:'write'});
  assert(b.reused);assert.equal(a.submission.id,b.submission.id);
  await rejectCode(()=>submit(writeDraft('changed')),'request_payload_conflict');
  await rejectCode(()=>submit(inputDraft()),'request_payload_conflict');
  await rejectCode(()=>submit(writeDraft(),{tools:['other']}),'request_payload_conflict');
  const other=await h.createConversation({ownership:{kind:'ownerless'}},ctx);const x=await gate.submit(other.id,writeDraft(),ctx);assert.notEqual(x.submission.id,a.submission.id);
  facts.checks.push('canonical-order-same-id','scope-isolation');
 }else if(scenario==='canonical-input'){
  const a=await submit(inputDraft());await reached.promise;
  const same=await submit({...inputDraft(),whenBusy:'followUp'});assert(same.reused);assert.equal(a.submission.id,same.submission.id);
  await rejectCode(()=>submit({...inputDraft(),content:'CHANGED'}),'request_payload_conflict');
  await assert.rejects(()=>submit({...inputDraft(),requestId:'busy-key',whenBusy:'reject'}),e=>e.name==='ConversationBusy');
  release.resolve();await result(a);
  const fresh=await submit({...inputDraft(),requestId:'busy-key',whenBusy:'reject'});assert(!fresh.reused);await result(fresh);
  assert.equal(facts.modelCalls,2);facts.checks.push('input-conflict-no-model','busy-rollback-key-reusable');
 }else if(scenario.startsWith('concurrent-')){
  const second=createStrictAdmission({harness:h,defineDocFamily,admitSubmission});
  const values=await Promise.allSettled(Array.from({length:20},(_,i)=>(i%2?gate:second).submit(root.id,writeDraft(scenario==='concurrent-conflict'&&i%2?'B':'original'),ctx)));
  const passed=values.filter(v=>v.status==='fulfilled').map(v=>v.value),errors=values.filter(v=>v.status==='rejected');
  assert.equal(passed.length,scenario==='concurrent-conflict'?10:20);assert.equal(errors.length,scenario==='concurrent-conflict'?10:0);
  assert(errors.every(v=>v.reason.code==='request_payload_conflict'));assert.equal(new Set(passed.map(x=>x.submission.id)).size,1);
  assert.equal(passed.filter(x=>!x.reused).length,1);assert.equal((await allEntries()).length,1);
  facts.accepted=passed.length;facts.conflicts=errors.length;facts.checks.push('20-concurrent-calls-one-native-admission');
 }else if(scenario==='snapshot-mutation'){
  const d=writeDraft();const pending=submit(d);d.entry.data.text='CHANGED';await result(await pending);
  assert.equal((await allEntries())[0].data.text,'original');assert((await submit(writeDraft())).reused);
  await rejectCode(()=>submit(d),'request_payload_conflict');facts.checks.push('caller-mutation-cannot-change-admitted-content');
 }else if(scenario==='legacy-rejected'){
  await root.submit(writeDraft(),ctx);
  await rejectCode(()=>submit(writeDraft()),'unmanaged_or_inconsistent_admission');
  await rejectCode(()=>submit(writeDraft('changed')),'unmanaged_or_inconsistent_admission');
  facts.checks.push('no-legacy-backfill');
 }else if(scenario==='validation-rollback'){
  await assert.rejects(()=>submit({...inputDraft(),entry:{kind:'pi.forbidden'}}));
  const a=await submit(writeDraft());assert(!a.reused);await result(a);assert.equal((await allEntries()).length,1);
  facts.checks.push('native-validation-rolls-back-binding');
 }else throw new Error('Unknown scenario');
 if(!facts.failedClosed){await h.waitForIdle(ctx);facts.entryCount=(await allEntries()).length;facts.idle=true;}
 facts.rootId=root.id;facts.result='PASS';
}catch(e){facts.result='FAIL';facts.error={name:e.name,code:e.code,message:e.message};console.error(e.stack);process.exitCode=1;
}finally{
 try{if(h)await h.close(ctx);}finally{if(external)external.close();clearInterval(keep);clearTimeout(deadline);}
 save(phase+'-receipt.json',facts);console.log(JSON.stringify(facts));
}
