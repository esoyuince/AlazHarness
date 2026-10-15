// REF-OC-001: source-owned Permission/EventFeed bodies, real Effect/schema;
// storage, agent config, plugin hooks and bus are explicit in-memory fixtures.
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {Effect,Layer,Deferred,Fiber,Exit,Cause,Scope,Stream} from 'effect';
import {Permission} from './permission.ts';
import {EventFeed} from './event-feed.ts';
import {Wildcard} from './wildcard.ts';
import {requireOwnedRequest} from './owned-request.ts';
import {SessionErrors} from './session-error.ts';
import {Bus,Location,Agent,SessionStore,PermissionSaved,PluginHooks} from './services.mjs';

const output=resolve(process.argv[2]);const nonce=process.argv[3];
assert.equal(output,process.cwd());assert.match(nonce,/^[a-f0-9]{32}$/);
const results=[];
const watchdog=setTimeout(()=>{console.error('PROBE_TIMEOUT');process.exit(3);},60000);
const rule=(effect,action='read',resource='*')=>({effect,action,resource});
const input=(id='per_A',sessionID='ses_A',extra={})=>({id,sessionID,action:'read',resources:['src/a.ts'],...extra});
function failed(exit,tag){assert(Exit.isFailure(exit),'expected failure');const detail=Cause.pretty(exit.cause);assert(detail.includes(tag),`Expected ${tag}; got ${detail}`);}
function state(){return {rules:[],sessionRules:[],agentPresent:true,events:[],waiters:new Map(),sessions:new Map([['ses_A',{agent:'agent',permissions:[]}],['ses_B',{agent:'agent',permissions:[]}]]),saved:[],hookCalls:0,hook:undefined,failPublish:false};}
function permission(run,setup=()=>{}){
 const s=state();setup(s);
 const dependencies=Layer.mergeAll(
  Layer.succeed(Bus.Service,{publish:(definition,data)=>Effect.suspend(()=>{
   if(s.failPublish)return Effect.fail(new Error('fixture_publish_failed'));
   s.events.push({type:definition.type,data});
   const waiter=s.waiters.get(data.id);
   return definition.type==='permission.asked'&&waiter?Deferred.succeed(waiter,data).pipe(Effect.asVoid):Effect.void;
  })}),
  Layer.succeed(Location.Service,{project:{id:'project-fixture'}}),
  Layer.succeed(Agent.Service,{resolve:id=>Effect.sync(()=>s.agentPresent?{permissions:id==='other'?[rule('deny')]:s.rules}:undefined)}),
  Layer.succeed(SessionStore.Service,{get:id=>Effect.sync(()=>s.sessions.get(id))}),
  Layer.succeed(PermissionSaved.Service,{
   list:({projectID})=>Effect.sync(()=>s.saved.filter(x=>x.projectID===projectID)),
   add:({projectID,action,resources})=>Effect.sync(()=>{for(const resource of resources)s.saved.push({projectID,action,resource});}),
  }),
  Layer.succeed(PluginHooks.Service,{trigger:(_domain,_name,event)=>Effect.sync(()=>{s.hookCalls++;return s.hook?s.hook(event):event;})}),
 );
 return Effect.gen(function*(){const service=yield* Permission.Service;return yield* run(service,s);}).pipe(
  Effect.provide(Layer.provide(Permission.node.layer,dependencies)),Effect.scoped,
 );
}
function askFiber(service,s,request){return Effect.gen(function*(){
 const barrier=yield* Deferred.make();s.waiters.set(request.id,barrier);
 const fiber=yield* service.assert(request).pipe(Effect.forkScoped);
 yield* Deferred.await(barrier);return fiber;
});}
function source(){let listener;const metrics={unsubscribed:0};return {
 metrics,
 observe:next=>Effect.sync(()=>{listener=next;return Effect.sync(()=>{if(listener===next)listener=undefined;metrics.unsubscribed++;});}),
 publish:event=>Effect.suspend(()=>listener?listener(event):Effect.void),
};}
const event=(id,type='agent.updated')=>({id:'evt_'+id,created:1,type,data:{}});
function feedTest(run){return Effect.scoped(Effect.gen(function*(){const bus=source();return yield* run(bus);}));}
const cases={
 'rules-default-ask':()=>{assert.equal(Permission.evaluate('read','x').effect,'ask');},
 'rules-last-match':()=>{assert.equal(Permission.evaluate('read','x',[rule('deny')],[rule('allow')]).effect,'allow');assert.equal(Permission.evaluate('read','x',[rule('allow'),rule('deny')]).effect,'deny');},
 'rules-action-and-resource':()=>{assert.equal(Permission.evaluate('write','x',[rule('allow')]).effect,'ask');assert.equal(Permission.evaluate('read','private/x',[rule('allow','read','public/*')]).effect,'ask');},
 'wildcard-platform-path':()=>{assert(Wildcard.match('C:\\src\\x.ts','C:/src/*.ts'));assert.equal(Wildcard.match('A.TS','a.ts'),process.platform==='win32');assert(Wildcard.match('git','git *'));assert(!Wildcard.match('gita','git *'));},
 'wildcard-not-path-sandbox':()=>{assert(Wildcard.match('src/../secret','src/*'));return {scope:'matching does not canonicalize filesystem paths'};},
 'permission-allow-deny-no-pending':()=>permission(function*(p,s){s.rules=[rule('allow')];assert.equal((yield* p.ask(input())).effect,'allow');s.rules=[rule('deny')];assert.equal((yield* p.ask(input())).effect,'deny');assert.deepEqual(yield* p.list(),[]);assert.equal(s.events.length,0);}),
 'permission-session-rule-precedence':()=>permission(function*(p,s){s.rules=[rule('deny')];s.sessions.get('ses_A').permissions=[rule('allow')];assert.equal((yield* p.ask(input())).effect,'allow');}),
 'permission-deny-before-saved-and-hook':()=>permission(function*(p,s){s.rules=[rule('deny')];s.saved.push({projectID:'project-fixture',action:'read',resource:'*'});s.hook=e=>({...e,effect:'allow'});failed(yield* p.assert(input()).pipe(Effect.exit),'Permission.BlockedError');assert.equal(s.hookCalls,0);}),
 'permission-any-resource-denied':()=>permission(function*(p,s){s.rules=[rule('allow'),rule('deny','read','secret/*')];assert.equal((yield* p.ask(input('per_A','ses_A',{resources:['src/a','secret/x']}))).effect,'deny');}),
 'permission-partial-resources-ask':()=>permission(function*(p,s){s.rules=[rule('allow','read','src/*')];assert.equal((yield* p.ask(input('per_A','ses_A',{resources:['src/a','other/x']}))).effect,'ask');assert.equal((yield* p.list()).length,1);}),
 'permission-empty-resource-characterization':()=>permission(function*(p,s){s.rules=[rule('deny')];assert.equal((yield* p.ask(input('per_A','ses_A',{resources:[]}))).effect,'allow');return {host_requirement:'nonempty resource list before tool execution; component alone allows empty list'};}),
 'permission-missing-agent-denies':()=>permission(function*(p,s){s.agentPresent=false;assert.equal((yield* p.ask(input())).effect,'deny');}),
 'permission-missing-session':()=>permission(function*(p){failed(yield* p.ask(input('per_A','ses_missing')).pipe(Effect.exit),'Session.NotFoundError');assert.deepEqual(yield* p.list(),[]);}),
 'permission-explicit-agent':()=>permission(function*(p,s){s.rules=[rule('allow')];assert.equal((yield* p.ask(input('per_A','ses_A',{agent:'other'}))).effect,'deny');}),
 'permission-hook-can-resolve-ask':()=>permission(function*(p,s){s.hook=e=>({...e,effect:'allow'});assert.equal((yield* p.ask(input())).effect,'allow');assert.equal(s.hookCalls,1);assert.deepEqual(yield* p.list(),[]);}),
 'permission-once-consumed':()=>permission(function*(p,s){const fiber=yield* askFiber(p,s,input());assert.equal((yield* p.list()).length,1);yield* p.reply({requestID:'per_A',reply:'once'});yield* Fiber.join(fiber);assert.deepEqual(yield* p.list(),[]);failed(yield* p.reply({requestID:'per_A',reply:'once'}).pipe(Effect.exit),'Permission.NotFoundError');assert.equal(s.saved.length,0);}),
 'permission-reject-session-batch':()=>permission(function*(p,s){
 const a=yield* askFiber(p,s,input('per_A'));const b=yield* askFiber(p,s,input('per_B'));const other=yield* askFiber(p,s,input('per_C','ses_B'));
 yield* p.reply({requestID:'per_A',reply:'reject'});failed(yield* Fiber.join(a).pipe(Effect.exit),'Permission.DeclinedError');failed(yield* Fiber.join(b).pipe(Effect.exit),'Permission.DeclinedError');
 assert.deepEqual((yield* p.list()).map(x=>x.id),['per_C']);yield* p.reply({requestID:'per_C',reply:'once'});yield* Fiber.join(other);
 }),
 'permission-feedback-typed':()=>permission(function*(p,s){const f=yield* askFiber(p,s,input());yield* p.reply({requestID:'per_A',reply:'reject',message:'use read-only operation'});failed(yield* Fiber.join(f).pipe(Effect.exit),'Permission.CorrectedError');}),
 'permission-always-project-wide':()=>permission(function*(p,s){
 const a=yield* askFiber(p,s,input('per_A','ses_A',{save:['src/*']}));const b=yield* askFiber(p,s,input('per_B','ses_B'));
 yield* p.reply({requestID:'per_A',reply:'always'});yield* Fiber.join(a);yield* Fiber.join(b);assert.equal(s.saved.length,1);assert.deepEqual(yield* p.list(),[]);
 return {observed:'always approval can satisfy another session in the same project'};
 }),
 'permission-always-preserves-new-deny':()=>permission(function*(p,s){
 const a=yield* askFiber(p,s,input('per_A','ses_A',{save:['src/*']}));const b=yield* askFiber(p,s,input('per_B','ses_B'));
 s.sessions.get('ses_B').permissions=[rule('deny')];yield* p.reply({requestID:'per_A',reply:'always'});yield* Fiber.join(a);assert.deepEqual((yield* p.list()).map(x=>x.id),['per_B']);yield* Fiber.interrupt(b);
 }),
 'permission-foreign-session-guard':()=>permission(function*(p,s){
 const f=yield* askFiber(p,s,input());failed(yield* requireOwnedRequest('ses_B','per_A').pipe(Effect.exit),'PermissionNotFoundError');assert.equal((yield* p.list()).length,1);
 const owned=yield* requireOwnedRequest('ses_A','per_A');yield* owned.permission.reply({requestID:'per_A',reply:'once'});yield* Fiber.join(f);
 }),
 'permission-aborted-wait-cleans-pending':()=>permission(function*(p,s){const f=yield* askFiber(p,s,input());yield* Fiber.interrupt(f);assert.deepEqual(yield* p.list(),[]);failed(yield* p.reply({requestID:'per_A',reply:'once'}).pipe(Effect.exit),'Permission.NotFoundError');}),
 'permission-close-fails-closed':()=>permission(function*(p,s){const f=yield* askFiber(p,s,input());yield* p.close;failed(yield* Fiber.join(f).pipe(Effect.exit),'Permission.DeclinedError');assert.deepEqual(yield* p.list(),[]);assert.equal((yield* p.ask(input())).effect,'deny');}),
 'permission-publish-failure-cleans-pending':()=>permission(function*(p,s){s.failPublish=true;failed(yield* p.ask(input()).pipe(Effect.exit),'fixture_publish_failed');assert.deepEqual(yield* p.list(),[]);}),
 'permission-duplicate-pending-id':()=>permission(function*(p){yield* p.ask(input());failed(yield* p.ask(input('per_A','ses_B')).pipe(Effect.exit),'Duplicate pending permission ID');assert.equal((yield* p.list())[0].sessionID,'ses_A');}),
 'event-frame-json':()=>{const e=event('newline');e.data={text:'ışık\nsecond'};const frame=EventFeed.frame(e);assert.equal(frame,'data: '+JSON.stringify(e)+'\n\n');assert(!frame.startsWith('id:'));},
 'event-encode-once-many-subscribers':()=>feedTest(function*(bus){let count=0;const feed=yield* EventFeed.make(bus.observe,{encode:e=>{count++;return e.id;}});const a=yield* feed.subscribe;const b=yield* feed.subscribe;yield* bus.publish(event('one'));assert.deepEqual(Array.from(yield* a.pipe(Stream.take(1),Stream.runCollect)),['evt_one']);assert.deepEqual(Array.from(yield* b.pipe(Stream.take(1),Stream.runCollect)),['evt_one']);assert.equal(count,1);}),
 'event-internal-filter-before-capacity':()=>feedTest(function*(bus){const feed=yield* EventFeed.make(bus.observe,{capacity:1,encode:e=>e.id});const a=yield* feed.subscribe;yield* bus.publish(event('i1','test.internal'));yield* bus.publish(event('i2','test.internal'));yield* bus.publish(event('ok'));assert.deepEqual(Array.from(yield* a.pipe(Stream.take(1),Stream.runCollect)),['evt_ok']);}),
 'event-fifo':()=>feedTest(function*(bus){const feed=yield* EventFeed.make(bus.observe,{capacity:3,encode:e=>e.id});const a=yield* feed.subscribe;for(const id of ['a','b','c'])yield* bus.publish(event(id));assert.deepEqual(Array.from(yield* a.pipe(Stream.take(3),Stream.runCollect)),['evt_a','evt_b','evt_c']);}),
 'event-only-lagging-subscriber-fails':()=>feedTest(function*(bus){
 const feed=yield* EventFeed.make(bus.observe,{capacity:1,encode:e=>e.id});const slow=yield* feed.subscribe;const fast=yield* feed.subscribe;
 const first=yield* Deferred.make();const second=yield* Deferred.make();const got=[];
 const f=yield* fast.pipe(Stream.take(3),Stream.runForEach(id=>Effect.sync(()=>got.push(id)).pipe(Effect.andThen(id==='evt_one'?Deferred.succeed(first,undefined):id==='evt_two'?Deferred.succeed(second,undefined):Effect.void))),Effect.forkScoped);
 yield* bus.publish(event('one'));yield* Deferred.await(first);yield* bus.publish(event('two'));yield* Deferred.await(second);yield* bus.publish(event('three'));yield* Fiber.join(f);
 assert.deepEqual(got,['evt_one','evt_two','evt_three']);failed(yield* slow.pipe(Stream.runCollect,Effect.exit),'EventFeed.SubscriberOverflow');
 }),
 'event-encoding-error-and-new-subscriber':()=>feedTest(function*(bus){
 const feed=yield* EventFeed.make(bus.observe,{encode:e=>{if(e.id==='evt_bad')throw new Error('fixture_encode');return e.id;}});
 const a=yield* feed.subscribe;const b=yield* feed.subscribe;yield* bus.publish(event('bad'));failed(yield* a.pipe(Stream.runCollect,Effect.exit),'EventFeed.EncodingError');failed(yield* b.pipe(Stream.runCollect,Effect.exit),'EventFeed.EncodingError');
 const next=yield* feed.subscribe;yield* bus.publish(event('good'));assert.deepEqual(Array.from(yield* next.pipe(Stream.take(1),Stream.runCollect)),['evt_good']);
 }),
 'event-no-replay-after-reconnect':()=>feedTest(function*(bus){
 const feed=yield* EventFeed.make(bus.observe,{encode:e=>e.id});yield* bus.publish(event('before-subscription'));
 const oldScope=yield* Scope.make();const old=yield* feed.subscribe.pipe(Scope.provide(oldScope));yield* bus.publish(event('old-live'));assert.deepEqual(Array.from(yield* old.pipe(Stream.take(1),Stream.runCollect)),['evt_old-live']);
 yield* Scope.close(oldScope,Exit.succeed(undefined));yield* bus.publish(event('missed'));
 const next=yield* feed.subscribe;yield* bus.publish(event('new-live'));assert.deepEqual(Array.from(yield* next.pipe(Stream.take(1),Stream.runCollect)),['evt_new-live']);return {replay:false,reconciliation_required:true};
 }),
 'event-no-encode-without-subscribers':()=>feedTest(function*(bus){let count=0;yield* EventFeed.make(bus.observe,{encode:()=>{count++;return 'x';}});yield* bus.publish(event('dropped'));assert.equal(count,0);}),
 'event-rpc-public-type':()=>feedTest(function*(bus){const feed=yield* EventFeed.make(bus.observe,{encode:e=>e.type});const a=yield* feed.subscribe;yield* bus.publish(event('rpc','rpc.fixture'));assert.deepEqual(Array.from(yield* a.pipe(Stream.take(1),Stream.runCollect)),['rpc.fixture']);}),
 'event-owner-scope-unsubscribes':()=>Effect.gen(function*(){const bus=source();yield* Effect.scoped(Effect.gen(function*(){yield* EventFeed.make(bus.observe);}));assert.equal(bus.metrics.unsubscribed,1);}),
};
try{
 for(const [name,body] of Object.entries(cases)){
  const start=performance.now();try{const value=body();const details=Effect.isEffect(value)?await Effect.runPromise(value.pipe(Effect.timeout(3000))):value;
   results.push({name,result:'PASS',elapsed_ms:Math.round(performance.now()-start),...(details===undefined?{}:{details})});
  }catch(e){results.push({name,result:'FAIL',error:String(e?.stack??e).slice(0,3500),elapsed_ms:Math.round(performance.now()-start)});}
  console.log(name,results.at(-1).result);
 }
 const receipt={scope:'original selected OpenCode bodies + real Effect/schema; external dependency fixtures',nonce,pid:process.pid,platform:process.platform,
  cases:results,total:results.length,passed:results.filter(x=>x.result==='PASS').length,failed:results.filter(x=>x.result!=='PASS').length,
  model_inference_calls:0,paid_calls:0,full_server_tested:false,http_routing_tested:false,persistent_database_tested:false,os_sandbox_claimed:false};
 writeFileSync(join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify({...receipt,cases:undefined}));if(receipt.failed)process.exitCode=1;
}finally{clearTimeout(watchdog);}
