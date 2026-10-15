/** Independent edge characterization, real pinned Permission and Effect, fixture dependency ports. */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {Effect,Layer,Deferred,Fiber,Exit} from 'effect';
import {Bus,Location,Agent,SessionStore,PermissionSaved,PluginHooks} from './ports.mjs';
const cfg=JSON.parse(readFileSync(process.env.ALAZ_OC_QA_CONFIG,'utf8'));
const {Permission:P}=await import(pathToFileURL(resolve(cfg.source,'packages/core/src/permission.ts')));
const rows=[];const timer=setTimeout(()=>{console.error('QA_TIMEOUT');process.exit(3)},20000);
const request=(id='per_case',sessionID='ses_a',extra={})=>({id,sessionID,action:'read',resources:['fixture/ok.txt'],...extra});
const rule=(effect,resource='*')=>({action:'read',resource,effect});
function state(){return {agents:new Map([['agent_a',{permissions:[]}]]),sessions:new Map([['ses_a',{agent:'agent_a'}],['ses_b',{agent:'agent_a'}]]),saved:[],events:[],listeners:new Set(),hookCalls:0};}
function deps(s){return Layer.mergeAll(
 Layer.succeed(Bus.Service,{publish:(type,data)=>Effect.gen(function*(){s.events.push({type:type.type,data});for(const fn of s.listeners)yield* fn(type,data);})}),
 Layer.succeed(Location.Service,{project:{id:'qa_project'}}),
 Layer.succeed(Agent.Service,{resolve:id=>Effect.sync(()=>s.agents.get(id))}),
 Layer.succeed(SessionStore.Service,{get:id=>Effect.sync(()=>s.sessions.get(id))}),
 Layer.succeed(PermissionSaved.Service,{list:({projectID})=>Effect.sync(()=>s.saved.filter(x=>x.projectID===projectID)),add:({projectID,action,resources})=>Effect.sync(()=>{for(const resource of resources)s.saved.push({projectID,action,resource})})}),
 Layer.succeed(PluginHooks.Service,{trigger:(_ns,_op,input)=>Effect.sync(()=>{s.hookCalls++;return s.hook?s.hook(input):input;})})
);}
async function test(name,fn){const s=state();try{
 const details=await Effect.runPromise(Effect.scoped(Effect.gen(function*(){const p=yield* P.Service;return yield* fn(p,s);}).pipe(Effect.provide(P.node.layer.pipe(Layer.provide(deps(s)))))));
 rows.push({name,result:'PASS',details:details??{}});
}catch(e){rows.push({name,result:'FAIL',error:String(e?.stack??e)});}console.log(name,rows.at(-1).result);}
function* waiting(p,s,input){const asked=yield* Deferred.make();const observer=(event,data)=>event.type===P.Event.Asked.type&&data.id===input.id?Deferred.succeed(asked,data).pipe(Effect.asVoid):Effect.void;
 s.listeners.add(observer);const fiber=yield* p.assert(input).pipe(Effect.exit,Effect.forkScoped);yield* Deferred.await(asked);s.listeners.delete(observer);return fiber;}
try{
 await test('deny-before-saved-and-plugin',function*(p,s){s.agents.get('agent_a').permissions=[rule('deny')];s.saved.push({projectID:'qa_project',action:'read',resource:'*'});s.hook=x=>({...x,effect:'allow'});const out=yield* p.ask(request());assert.equal(out.effect,'deny');assert.equal(s.hookCalls,0);assert.equal((yield* p.list()).length,0);return {configured_deny_preserved:true};});
 await test('empty-resources-characterization',function*(p,s){s.agents.get('agent_a').permissions=[rule('deny')];const out=yield* p.ask(request('per_empty','ses_a',{resources:[]}));assert.equal(out.effect,'allow');return {effect:out.effect,contract_gap:'host must reject empty resource list before a meaningful protected operation',full_tool_bypass_tested:false};});
 await test('pending-input-save-mutation',function*(p,s){const input=request('per_mutation','ses_a',{save:['fixture/safe/*']});yield* p.ask(input);input.save.push('fixture/expanded/*');const pending=yield* p.get(input.id);assert.equal(pending.save.length,2);yield* p.reply({requestID:input.id,reply:'always'});assert.deepEqual(s.saved.map(x=>x.resource),['fixture/safe/*','fixture/expanded/*']);return {retains_caller_array:true,saved_rules:s.saved.map(x=>x.resource),contract_gap:'host must snapshot permission inputs; no remote exploit claim'};});
 await test('returned-pending-request-is-mutable',function*(p,s){yield* p.ask(request('per_exposed','ses_a',{save:['fixture/safe/*']}));const pending=yield* p.get('per_exposed');pending.save[0]='fixture/replaced/*';yield* p.reply({requestID:'per_exposed',reply:'always'});assert.deepEqual(s.saved.map(x=>x.resource),['fixture/replaced/*']);return {returned_object_not_detached:true,host_boundary_required:true};});
 await test('selected-once-after-policy-revocation',function*(p,s){const fiber=yield* waiting(p,s,request());s.agents.get('agent_a').permissions=[rule('deny')];yield* p.reply({requestID:'per_case',reply:'once'});const outcome=yield* Fiber.join(fiber);assert(Exit.isSuccess(outcome));const now=yield* p.ask(request('per_after'));assert.equal(now.effect,'deny');return {pending_explicit_reply_allowed:true,new_request_denied:true,contract_gap:'actual tool boundary must choose revocation policy; selected reply does not re-evaluate'};});
 await test('always-rechecks-other-pending-deny',function*(p,s){s.agents.set('agent_b',{permissions:[]});s.sessions.get('ses_b').agent='agent_b';yield* p.ask(request('per_first','ses_a',{save:['fixture/*']}));yield* p.ask(request('per_other','ses_b'));s.agents.get('agent_b').permissions=[rule('deny')];yield* p.reply({requestID:'per_first',reply:'always'});assert.deepEqual((yield* p.list()).map(x=>x.id),['per_other']);return {other_pending_deny_preserved:true};});
 await test('reject-clears-same-session-not-other',function*(p,s){yield* p.ask(request('per_1'));yield* p.ask(request('per_2'));yield* p.ask(request('per_3','ses_b'));yield* p.reply({requestID:'per_1',reply:'reject'});assert.deepEqual((yield* p.list()).map(x=>x.id),['per_3']);return {same_session_batch_rejected:true,other_session_retained:true};});
 await test('duplicate-pending-is-error-original-retained',function*(p,s){yield* p.ask(request());const out=yield* p.ask(request('per_case','ses_b')).pipe(Effect.exit);assert(Exit.isFailure(out));assert.equal((yield* p.get('per_case')).sessionID,'ses_a');assert.equal((yield* p.list()).length,1);return {first_request_retained:true};});
 await test('once-reply-is-not-reusable',function*(p,s){yield* p.ask(request());yield* p.reply({requestID:'per_case',reply:'once'});const out=yield* p.reply({requestID:'per_case',reply:'once'}).pipe(Effect.exit);assert(Exit.isFailure(out));assert.equal((yield* p.list()).length,0);return {old_id_rejected:true};});
 await test('request-id-can-be-reused-after-settlement',function*(p,s){yield* p.ask(request());yield* p.reply({requestID:'per_case',reply:'once'});yield* p.ask(request('per_case','ses_a',{resources:['fixture/second.txt']}));assert.equal((yield* p.get('per_case')).sessionID,'ses_a');yield* p.reply({requestID:'per_case',reply:'once'});assert.equal((yield* p.list()).length,0);return {settled_id_reuse_allowed:true,same_session_id:true,contract_gap:'host must prevent cross-generation replay of explicit permission IDs',http_owner_check_still_required:true};});
 await test('close-rejects-waiters-and-new-asks',function*(p,s){const fiber=yield* waiting(p,s,request());yield* p.close;const out=yield* Fiber.join(fiber);assert(Exit.isFailure(out));assert.equal((yield* p.ask(request('per_late'))).effect,'deny');assert.equal((yield* p.list()).length,0);return {closed_no_allow:true};});
 await test('interrupted-waiter-removes-prompt',function*(p,s){const fiber=yield* waiting(p,s,request());yield* Fiber.interrupt(fiber);assert.equal((yield* p.list()).length,0);return {pending_cleaned:true};});
}finally{clearTimeout(timer);const out={scope:'unchanged OpenCode Permission with Effect4.0.1 and fixture dependency ports; not full application/HTTP/security acceptance',source_commit:cfg.source_commit,pid:process.pid,nonce:cfg.nonce,model_calls:0,source_loads:globalThis.__ocQaLoads,passed:rows.filter(x=>x.result==='PASS').length,failed:rows.filter(x=>x.result!=='PASS').length,cases:rows};writeFileSync(resolve(process.env.ALAZ_OC_QA_OUTPUT,'permission-results.json'),JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out,null,2));if(out.failed)process.exitCode=1;}
