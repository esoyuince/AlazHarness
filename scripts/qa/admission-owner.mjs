import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {BACKGROUND_CONTEXT as ctx} from '@earendil-works/chord/context';
import {createModels} from '@earendil-works/pi-ai';
import {Harness,createRegistry,defineDocFamily} from '@earendil-works/pi-durable';
import {openNodeSqliteStorage} from '@earendil-works/pi-durable/storage/sqlite/node';
const [target,source,out]=process.argv.slice(2);
const checksum=()=>createHash('sha256').update(readFileSync(target)).digest('hex');const initial=checksum();
const {createStrictAdmission,prepareAdmission,canonicalJson}=await import(pathToFileURL(target));
const {admitSubmission}=await import(pathToFileURL(join(source,'packages/durable/src/harness/submissions.ts')));
const handles=[]; const results=[];
async function make(name){const h=await Harness.open(await openNodeSqliteStorage(join(out,name+'.sqlite')),{models:createModels(),registry:createRegistry()},ctx);handles.push(h);return {h,root:await h.root(ctx),guard:createStrictAdmission({harness:h,defineDocFamily,admitSubmission})};}
const draft=(id,text)=>({type:'write',requestId:id,entry:{kind:'qa.note',data:{text}}});
async function test(name,fn){try{results.push({name,status:'PASS',details:await fn()});}catch(e){results.push({name,status:'FAIL',error:{name:e.name,message:e.message,code:e.code}});}}
try{
 await test('same-key-conflict-and-reuse',async()=>{const a=await make('same');const first=await a.guard.submit(a.root.id,draft('x','original'),ctx);const same=await a.guard.submit(a.root.id,draft('x','original'),ctx);assert.equal(same.submission.id,first.submission.id);await assert.rejects(a.guard.submit(a.root.id,draft('x','changed'),ctx),e=>e.code==='request_payload_conflict');return {id:first.submission.id};});
 await test('concurrent-same-owner',async()=>{const a=await make('concurrent');const values=await Promise.all(Array.from({length:12},()=>a.guard.submit(a.root.id,draft('k','same'),ctx)));assert.equal(new Set(values.map(x=>x.submission.id)).size,1);assert.equal(values.filter(x=>!x.reused).length,1);return {requests:12,admissions:1};});
 await test('legacy-fails-closed',async()=>{const a=await make('legacy');const old=await a.root.submit(draft('k','old'),ctx);await assert.rejects(a.guard.submit(a.root.id,draft('k','old'),ctx),e=>e.code==='unmanaged_or_inconsistent_admission');return {legacy:old.id};});
 await test('foreign-harness-handle-isolation',async()=>{const a=await make('owner-a'),b=await make('owner-b');
  await a.guard.submit(a.root.id,draft('first','a'),ctx);await b.guard.submit(b.root.id,draft('first','b'),ctx);
  const victim=await a.guard.submit(a.root.id,draft('second','A-existing'),ctx);
  let result,error;try{result=await a.guard.submit(b.root,draft('foreign','B-new'),ctx);}catch(e){error={code:e.code,message:e.message};}
  const ae=(await a.root.entries({},100,undefined,ctx)).items,be=(await b.root.entries({},100,undefined,ctx)).items;
  const observation={expected:'reject foreign handle without writing B or returning unrelated A job',returnedId:result?.submission.id,victimId:victim.submission.id,rejected:error??null,aEntries:ae.map(e=>e.data),bEntries:be.map(e=>e.data)};
  writeFileSync(join(out,'foreign-handle-observation.json'),JSON.stringify(observation,null,2));
  assert.ok(error,'Foreign conversation was accepted; another store changed and an unrelated local submission was returned');
  assert.equal(be.length,1,'Foreign store changed before failure');return observation;});
 await test('caller-mutation-snapshotted',async()=>{const a=await make('mutation');const hold=Promise.withResolvers(),entered=Promise.withResolvers();const blocked=a.root.commit(async()=>{entered.resolve();await hold.promise;},ctx);await entered.promise;const d=draft('mutable','initial');const waiting=a.guard.submit(a.root.id,d,ctx);d.entry.data.text='modified';hold.resolve();await blocked;await waiting;const es=(await a.root.entries({},100,undefined,ctx)).items;assert.equal(es[0].data.text,'initial');return {stored:'initial'};});
 await test('scope-participates-in-fingerprint',async()=>{const a=await make('scope');await a.guard.submit(a.root.id,draft('k','same'),ctx,{policy:'read'});await assert.rejects(a.guard.submit(a.root.id,draft('k','same'),ctx,{policy:'write'}),e=>e.code==='request_payload_conflict');});
}finally{for(const h of handles)await h.close(ctx);}
const summary={scope:'independent native SQLite checks against concurrent candidate; no production edits',module_sha256:initial,unchanged_during_run:initial===checksum(),model_calls:0,tests:results,passed:results.filter(x=>x.status==='PASS').length,failed:results.filter(x=>x.status==='FAIL').length};
writeFileSync(join(out,'qa-results.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));process.exitCode=summary.failed?1:0;
