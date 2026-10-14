import assert from 'node:assert/strict';
import { createProviderRequestGate } from '../../packages/hybrid-runtime/provider-request-gate.mjs';
const endpoint='http://127.0.0.1:49111/v1/chat/completions';
const good=()=>Promise.resolve(new Response('{}',{status:200}));
const make=(maxRequests=1,fetchImpl=good)=>createProviderRequestGate({endpoint,maxRequests,fetchImpl});
const call=(gate,options={})=>gate.fetch(endpoint,{method:'POST',...options});
const denied=(code)=>error=>error.code===code;
const cases={
  'success':async()=>{const g=make();assert.equal((await call(g)).status,200);assert.equal(g.snapshot().submitted,1);},
  'zero-budget':async()=>{const g=make(0);await assert.rejects(call(g),denied('REQUEST_BUDGET_EXHAUSTED'));assert.equal(g.snapshot().submitted,0);},
  'invalid-limits':async()=>{for(const n of [-1,1.5,NaN,Infinity,1001,'1',null])assert.throws(()=>make(n),TypeError);},
  'invalid-endpoints':async()=>{
    for(const url of ['https://127.0.0.1/v1/chat/completions','http://example.org/v1/chat/completions',endpoint+'?x=1',endpoint+'#x','http://'+'user:pass@127.0.0.1/v1/chat/completions','http://127.0.0.1/other'])
      assert.throws(()=>createProviderRequestGate({endpoint:url,maxRequests:1}),TypeError);
  },
  'wrong-target':async()=>{const g=make();await assert.rejects(g.fetch(endpoint.replace('49111','49112'),{method:'POST'}),denied('TARGET_NOT_ALLOWED'));assert.equal(g.snapshot().submitted,0);},
  'wrong-method':async()=>{const g=make();await assert.rejects(g.fetch(endpoint),denied('TARGET_NOT_ALLOWED'));assert.equal(g.snapshot().submitted,0);},
  'pre-abort':async()=>{const g=make();const c=new AbortController();c.abort();await assert.rejects(call(g,{signal:c.signal}),denied('ABORTED_BEFORE_DISPATCH'));assert.equal(g.snapshot().submitted,0);},
  'concurrent-reservation':async()=>{
    let release,calls=0;const pending=new Promise(r=>{release=r;});const g=make(2,async()=>{calls++;await pending;return new Response('{}');});
    const results=Promise.allSettled(Array.from({length:8},()=>call(g)));
    assert.equal(calls,2);assert.equal(g.snapshot().submitted,2);release();
    const done=await results;assert.equal(done.filter(x=>x.status==='fulfilled').length,2);assert.equal(g.snapshot().denied,6);
  },
  'uncertain-not-refunded':async()=>{const g=make(1,async()=>{throw new Error('wire lost');});await assert.rejects(call(g),/wire lost/);await assert.rejects(call(g),denied('REQUEST_BUDGET_EXHAUSTED'));assert.equal(g.snapshot().submitted,1);assert.equal(g.snapshot().failedTransports,1);},
  'http-error-consumes':async()=>{const g=make(1,async()=>new Response('{}',{status:503}));assert.equal((await call(g)).status,503);await assert.rejects(call(g),denied('REQUEST_BUDGET_EXHAUSTED'));},
  'redirect-denied':async()=>{let cancelled=false,seen;const g=make(2,async(_i,init)=>{seen=init.redirect;return new Response(new ReadableStream({cancel(){cancelled=true;}}),{status:302,headers:{Location:'http://example.org/'}});});await assert.rejects(call(g,{redirect:'follow'}),denied('REDIRECT_NOT_ALLOWED'));assert.equal(seen,'manual');assert(cancelled);assert.equal(g.snapshot().submitted,1);},
  'closed-no-revival':async()=>{const g=make();g.close();g.close();await assert.rejects(call(g),denied('GATE_CLOSED'));assert.equal(g.snapshot().submitted,0);},
  'snapshot-isolated':async()=>{const g=make();const old=g.snapshot();assert(Object.isFrozen(old));assert.throws(()=>{old.submitted=99;},TypeError);await call(g);assert.equal(old.submitted,0);assert.equal(g.snapshot().submitted,1);},
  'request-object':async()=>{const g=make();await g.fetch(new Request(endpoint,{method:'POST',body:'{}'}));assert.equal(g.snapshot().submitted,1);},
  'request-signal':async()=>{const c=new AbortController();const req=new Request(endpoint,{method:'POST',signal:c.signal});c.abort();const g=make();await assert.rejects(g.fetch(req),denied('ABORTED_BEFORE_DISPATCH'));assert.equal(g.snapshot().submitted,0);},
  'invalid-fetch':async()=>{assert.throws(()=>make(1,1),TypeError);},
};
const selected=process.argv[2];assert(Object.hasOwn(cases,selected),'Unknown test');await cases[selected]();
console.log(JSON.stringify({case:selected,result:'PASS',scope:'request gate unit; no upstream or network calls'}));
