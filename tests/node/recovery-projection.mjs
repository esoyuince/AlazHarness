import assert from 'node:assert/strict';
import {classifyRunRecovery} from '../../packages/claw-hermes/run-recovery.mjs';
const name=process.argv[2];
const canonical={run_id:'run_'+'a'.repeat(32),status:'completed',session_id:'session',admission_id:'b'.repeat(32),execution_generation:1};
const result=(changes={})=>classifyRunRecovery({...canonical,...changes});
let r;
switch(name){
 case 'completed':r=result();assert.equal(r.classification,'canonical_terminal_reported');assert(r.backendConfirmed);break;
 case 'missing-admission':r=result({admission_id:undefined});break;
 case 'bad-admission':r=result({admission_id:'not-an-id'});break;
 case 'missing-session':r=result({session_id:undefined});break;
 case 'empty-session':r=result({session_id:''});break;
 case 'missing-generation':r=result({execution_generation:undefined});break;
 case 'bool-generation':r=result({execution_generation:true});break;
 case 'negative-generation':r=result({execution_generation:-1});break;
 case 'unsafe-generation':r=result({execution_generation:Number.MAX_SAFE_INTEGER+1});break;
 case 'interrupted-unverified':r=result({status:'interrupted',admission_id:undefined});break;
 case 'cancelled-unverified':r=result({status:'cancelled',admission_id:undefined});break;
 case 'failed-unverified':r=result({status:'failed',admission_id:undefined});break;
 case 'unknown':r=result({status:'unknown'});assert.equal(r.classification,'execution_unknown');assert(r.requiresOperator);break;
 case 'approval':r=result({status:'waiting_for_approval'});assert.equal(r.classification,'approval_required');assert(r.requiresOperator);break;
 case 'in-progress':r=result({status:'running'});assert.equal(r.classification,'in_progress');break;
 case 'immutable':r=result();assert.throws(()=>r.retryAllowed=true,TypeError);break;
 case 'untrusted-flags-ignored':r=result({canonicalVerified:true,retryAllowed:true,repairAllowed:true});break;
 case 'invalid':for(const x of [null,[],{}, {...canonical,run_id:'../other'}, {...canonical,status:'invented'}])assert.throws(()=>classifyRunRecovery(x),TypeError);break;
 default:throw Error('Unknown test');
}
if(r){
 assert.equal(r.recoveryContractVersion,1);assert.equal(r.canonicalVerified,false);
 assert.equal(r.retryAllowed,false);assert.equal(r.repairAllowed,false);assert(Object.isFrozen(r));
 if(['missing-admission','bad-admission','missing-session','empty-session','missing-generation','bool-generation','negative-generation','unsafe-generation','interrupted-unverified','cancelled-unverified','failed-unverified'].includes(name)){
  assert.equal(r.classification,'terminal_unverified');assert.equal(r.backendConfirmed,false);assert.equal(r.transportConfirmed,true);assert(r.requiresOperator);
 }
}
console.log(JSON.stringify({name,result:'PASS'}));
