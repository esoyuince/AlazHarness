/** Independent adapter tests. Real local HTTP; scripted status, no agent or model. */
import assert from 'node:assert/strict';
import http from 'node:http';
import {HermesRunsClient} from '../../packages/claw-hermes/hermes-runs.mjs';
import {classifyRunRecovery} from '../../packages/claw-hermes/run-recovery.mjs';
const scenario=process.argv[2];
const rid='run_'+'a'.repeat(32), aid='b'.repeat(32);
const terminal={run_id:rid,status:'completed',admission_id:aid,session_id:'owned-session',execution_generation:1,output:'known-output'};
const direct={
  'contradictory-classifier':()=>assert.throws(()=>classifyRunRecovery({...terminal,failed:true})),
  'blank-session-classifier':()=>assert.equal(classifyRunRecovery({...terminal,session_id:' '}).backendConfirmed,false),
  'coerced-id-classifier':()=>assert.throws(()=>classifyRunRecovery({...terminal,run_id:{toString:()=>rid}})),
  'classifier-no-retry':()=>{for(const status of ['completed','failed','cancelled','interrupted','unknown','queued','running','waiting_for_approval']){
    const r=classifyRunRecovery({...terminal,status});assert.equal(r.retryAllowed,false);assert.equal(r.repairAllowed,false);assert.equal(r.canonicalVerified,false);assert(Object.isFrozen(r));}},
};
if(direct[scenario]){direct[scenario]();console.log(JSON.stringify({scenario,result:'PASS',scope:'pure classifier; no HTTP'}));}
else {
 const requests=[];let response={...terminal};let status=200,delay=0,badJSON=false;
 switch(scenario){
  case 'terminal-without-proof':response={run_id:rid,status:'interrupted'};break;
  case 'partial-native-tuple':delete response.execution_generation;break;
  case 'invalid-generation':response.execution_generation=true;break;
  case 'unknown':response.status='unknown';break;
  case 'approval':response.status='waiting_for_approval';break;
  case 'retained-failed':response.status='failed';break;
  case 'queued-single-read':response.status='queued';break;
  case 'missing-run':status=404;response={error:{message:'PRIVATE_SENTINEL',code:'run_not_found'}};break;
  case 'denied-run':status=401;response={error:{message:'PRIVATE_SENTINEL'}};break;
  case 'server-failure-no-retry':status=500;response={error:{message:'PRIVATE_SENTINEL'}};break;
  case 'malformed-response':badJSON=true;break;
  case 'wrong-run-id':response.run_id='run_'+'c'.repeat(32);break;
  case 'contradictory-http':response.failed=true;break;
  case 'resume-deadline-no-post':case 'resume-abort-no-post':response.status='running';delay=150;break;
  case 'preaborted-resume':response.status='running';break;
  case 'observer-cannot-resolve':response.status='unknown';break;
  case 'valid-terminal':break;
  default:throw Error('Unknown test '+scenario);
 }
 const timers=new Set();
 const server=http.createServer((req,res)=>{
  requests.push({method:req.method,path:req.url,auth:req.headers.authorization});
  const reply=()=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(badJSON?'not-json':JSON.stringify(response));};
  if(delay){const t=setTimeout(reply,delay);timers.add(t);}else reply();
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try {
  const client=new HermesRunsClient({baseUrl:`http://127.0.0.1:${server.address().port}`,token:'qa-local-token',requestTimeoutMs:500});
  if(scenario==='preaborted-resume'){
   const control=new AbortController();control.abort();
   await assert.rejects(()=>client.resume(rid,{signal:control.signal}),e=>e.code==='observation_interrupted'&&e.stopRequested===false);
   assert.equal(requests.length,0);
  }else if(scenario==='resume-deadline-no-post'||scenario==='resume-abort-no-post'){
   const control=new AbortController();let t;
   if(scenario==='resume-abort-no-post')t=setTimeout(()=>control.abort(),30);
   try {await assert.rejects(()=>client.resume(rid,{executionTimeoutMs:scenario==='resume-deadline-no-post'?25:500,signal:control.signal}),e=>e.code==='observation_interrupted'&&e.stopRequested===false);}
   finally{clearTimeout(t);}
   assert(requests.length<=1);
  }else if(['missing-run','denied-run','server-failure-no-retry','malformed-response','wrong-run-id','contradictory-http'].includes(scenario)){
   const code={'missing-run':'http_404','denied-run':'http_401','server-failure-no-retry':'http_500','malformed-response':'invalid_json_response','wrong-run-id':'invalid_run_response','contradictory-http':'contradictory_terminal_response'}[scenario];
   await assert.rejects(()=>client.reconcile(rid),e=>e.code===code&&e.mayHaveBeenAccepted!==true&&!JSON.stringify(e).includes('PRIVATE_SENTINEL'));
   assert.equal(requests.length,1);
  }else {
   const result=scenario==='observer-cannot-resolve'?await client.resume(rid,{onStatus:s=>{s.status='completed';s.output='tampered';}}):await client.reconcile(rid);
   assert.equal(result.retryAllowed,false);assert.equal(result.repairAllowed,false);assert.equal(result.canonicalVerified,false);assert.equal(result.stopRequested,false);
   assert.equal(requests.length,1);
   if(['terminal-without-proof','partial-native-tuple','invalid-generation'].includes(scenario)){
    assert.equal(result.classification,'terminal_unverified');assert.equal(result.backendConfirmed,false);assert.equal(result.requiresOperator,true);
   }else if(['unknown','observer-cannot-resolve'].includes(scenario)){
    assert.equal(result.classification,'execution_unknown');assert.equal(result.requiresOperator,true);assert.equal(result.run.status,'unknown');
   }else if(scenario==='approval'){assert.equal(result.classification,'approval_required');assert.equal(result.requiresOperator,true);}
   else if(scenario==='queued-single-read'){assert.equal(result.classification,'in_progress');assert.equal(result.backendConfirmed,false);}
   else {assert.equal(result.classification,'canonical_terminal_reported');assert.equal(result.backendConfirmed,true);assert.equal(result.run.output,'known-output');}
  }
  for(const request of requests){assert.equal(request.method,'GET');assert.equal(request.path,'/v1/runs/'+rid);assert.equal(request.auth,'Bearer qa-local-token');}
  console.log(JSON.stringify({scenario,result:'PASS',scope:'actual adapter; controlled HTTP statuses',requests:requests.length,writeRequests:requests.filter(x=>x.method!=='GET').length}));
 }finally {for(const t of timers)clearTimeout(t);server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
}
