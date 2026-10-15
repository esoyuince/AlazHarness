import assert from 'node:assert/strict';
import {canonicalJson,prepareAdmission,AdmissionError,createStrictAdmission} from '../../packages/admission/strict-admission.mjs';
const d=()=>({type:'input',requestId:'a',content:'hello'});
const fp=x=>prepareAdmission(x).fingerprint;
const bad=f=>assert.throws(f,e=>e instanceof AdmissionError);
const cases={
 'canonical_order':()=>assert.equal(canonicalJson({b:{d:1,c:2},a:3}),canonicalJson({a:3,b:{c:2,d:1}})),
 'array_order':()=>assert.notEqual(canonicalJson([1,2]),canonicalJson([2,1])),
 'unicode_exact':()=>assert.notEqual(fp({...d(),content:'ş'}),fp({...d(),content:'s'})),
 'unicode_no_normalization':()=>assert.notEqual(fp({...d(),content:'é'}),fp({...d(),content:'e\u0301'})),
 'scope_changes_fingerprint':()=>assert.notEqual(prepareAdmission(d(),{tools:['read']}).fingerprint,prepareAdmission(d(),{tools:['write']}).fingerprint),
 'key_not_fingerprint':()=>assert.equal(fp(d()),fp({...d(),requestId:'b'})),
 'key_scope_stable':()=>assert.equal(prepareAdmission(d()).key,prepareAdmission({...d(),content:'other'}).key),
 'default_followup':()=>assert.equal(fp(d()),fp({...d(),whenBusy:'followUp'})),
 'whitespace_matters':()=>assert.notEqual(fp(d()),fp({...d(),content:'hello '})),
 'snapshot_detached':()=>{const x={type:'write',requestId:'a',entry:{kind:'note',data:{n:1}}};const a=prepareAdmission(x);x.entry.data.n=2;assert.equal(a.draft.entry.data.n,1);},
 'reject_undefined':()=>bad(()=>canonicalJson({a:undefined})),
 'reject_nan':()=>bad(()=>canonicalJson({a:NaN})),
 'reject_infinity':()=>bad(()=>canonicalJson(Infinity)),
 'reject_bigint':()=>bad(()=>canonicalJson(2n)),
 'reject_function':()=>bad(()=>canonicalJson(()=>1)),
 'reject_symbol':()=>bad(()=>canonicalJson({[Symbol('a')]:1})),
 'reject_date':()=>bad(()=>canonicalJson(new Date())),
 'reject_getter_without_call':()=>{let called=false;bad(()=>canonicalJson({get a(){called=true;return 1;}}));assert(!called);},
 'reject_cycle':()=>{const x={};x.x=x;bad(()=>canonicalJson(x));},
 'reject_sparse':()=>bad(()=>canonicalJson(Array(2))),
 'reject_extra_array_property':()=>{const a=[1];a.extra=1;bad(()=>canonicalJson(a));},
 'reject_lone_surrogate':()=>bad(()=>canonicalJson('\ud800')),
 'reject_missing_id':()=>{const x=d();delete x.requestId;bad(()=>prepareAdmission(x));},
 'reject_empty_id':()=>bad(()=>prepareAdmission({...d(),requestId:''})),
 'reject_big_id':()=>bad(()=>prepareAdmission({...d(),requestId:'a'.repeat(257)})),
 'reject_unknown_field':()=>bad(()=>prepareAdmission({...d(),silent:true})),
 'reject_type':()=>bad(()=>prepareAdmission({...d(),type:'other'})),
 'reject_busy_value':()=>bad(()=>prepareAdmission({...d(),whenBusy:'anything'})),
 'reject_busy_null':()=>bad(()=>prepareAdmission({...d(),whenBusy:null})),
 'reject_depth':()=>bad(()=>canonicalJson({x:{y:1}},{maxDepth:1})),
 'reject_bytes':()=>bad(()=>canonicalJson({x:'abc'},{maxBytes:4})),
 'reject_escaped_byte_overflow':()=>bad(()=>canonicalJson('\n\n',{maxBytes:4})),
 'reject_hidden_property':()=>{const x={};Object.defineProperty(x,'a',{value:1,enumerable:false});bad(()=>canonicalJson(x));},
 'proto_key_is_data':()=>assert.equal(canonicalJson(JSON.parse('{"__proto__":{"x":1}}')),'{"__proto__":{"x":1}}'),
 'minus_zero_json_semantics':()=>assert.equal(canonicalJson(-0),canonicalJson(0)),
 'reject_nonobject_scope':()=>bad(()=>prepareAdmission(d(),[])),
};

cases.reject_foreign_handle = async () => {
  let touched = false;
  const h={submission(){},resume(){},async conversation(){touched=true;}};
  const guard=createStrictAdmission({harness:h,defineDocFamily:x=>x,admitSubmission(){}});
  await assert.rejects(()=>guard.submit({id:1,commit(){touched=true;}},d(),{}),e=>e.code==='invalid_conversation');
  assert(!touched);
};
cases.reject_unknown_owned_conversation = async () => {
  const h={submission(){},resume(){},async conversation(){return undefined;}};
  const guard=createStrictAdmission({harness:h,defineDocFamily:x=>x,admitSubmission(){}});
  await assert.rejects(()=>guard.submit(1,d(),{}),e=>e.code==='invalid_conversation');
};
const name=process.argv[2];if(!Object.hasOwn(cases,name))throw new Error('Unknown test');await cases[name]();console.log(JSON.stringify({case:name,result:'PASS'}));
