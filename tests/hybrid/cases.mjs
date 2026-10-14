import assert from 'node:assert/strict';
import path from 'node:path';
import { MockHybridHarness, isolatedEnvironment } from '../../packages/hybrid-runtime/mock-harness.mjs';
import { createAgentHarnessAttemptCancellation } from '../../packages/upstream/openclaw/attempt-cancellation.ts';
import { createAgentHarnessAttemptDeadlineController } from '../../packages/upstream/openclaw/attempt-deadlines.ts';
import { deferred, boundedWait } from '../../packages/hybrid-runtime/common.mjs';
const harnesses = [];
function make(python = process.env.ALAZ_PYTHON) {
  const h = new MockHybridHarness({ python, workRoot: process.env.ALAZ_TEST_WORK });
  harnesses.push({ h, ids: [] }); return h;
}
function start(h, input) {
  const id = h.start({ key: 'test', text: 'fixture', ...input });
  harnesses.find(x => x.h === h).ids.push(id); return id;
}
async function run(scenario, options = {}) {
  const h = make(); const id = start(h, { scenario, ...options });
  return [await h.wait(id), h, id];
}
async function observed(h, id, event) {
  const until = performance.now() + 4000;
  while (performance.now() < until) {
    if (h.events(id).some(e => e.type === event)) return;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.fail('Expected event not observed: ' + event);
}
function finished(r, state) {
  assert.equal(r.state, state, JSON.stringify(r));
  assert.equal(r.process?.reaped, true);
  assert.equal(r.mock, true); assert.equal(r.modelCalls, 0);
}
const cases = {
  async tool_round() {
    const [r] = await run('tool-round'); finished(r, 'completed');
    assert.deepEqual(JSON.parse(r.response), {value: 5, iterations: 2, model_calls: 0, scripted: true});
    assert.ok(r.events.some(e => e.type === 'tool.complete'));
  },
  async budget() {
    const [r] = await run('tool-round', { iterationBudget: 1 }); finished(r, 'failed');
    assert.equal(r.code, 'NATIVE_FAILURE'); assert.equal(r.response, null);
  },
  async unicode_echo() {
    const text = 'Türkçe ışık şğü — 🚀\n"quoted"; $(must-not-execute)';
    const [r] = await run('echo', { text }); finished(r, 'completed'); assert.equal(r.response, text);
  },
  async idempotency_and_busy() {
    const h=make(); const input={key:'same',text:'a',scenario:'hang'}; const id=start(h,input);
    assert.equal(h.start(input),id);
    assert.throws(()=>h.start({...input,text:'b'}), {code:'IDEMPOTENCY_CONFLICT'});
    assert.throws(()=>h.start({...input,key:'other'}), {code:'BUSY'});
    await observed(h,id,'accepted'); assert.equal(h.cancel(id),true); assert.equal(h.cancel(id),false);
    const result=await h.wait(id); finished(result,'cancelled');
    assert.equal(h.start(input),id); assert.equal(h.cancel(id),false);
    const other=start(h,{key:'second',scenario:'echo'}); finished(await h.wait(other),'completed');
  },
  async cancel_before_start() {
    const h=make(); const id=start(h,{scenario:'hang'}); h.cancel(id);
    const r=await h.wait(id); assert.equal(r.state,'cancelled'); assert.equal(r.process,null);
    assert.equal(r.submitted,false);
  },
  async cooperative_cancel() {
    const h=make(); const id=start(h,{scenario:'hang'}); await observed(h,id,'status.update');
    h.cancel(id); const r=await h.wait(id); finished(r,'cancelled'); assert.equal(r.process.killSent,false);
  },
  async uncooperative_cancel() {
    const h=make(); const id=start(h,{scenario:'ignore-interrupt'}); await observed(h,id,'status.update');
    h.cancel(id); const r=await h.wait(id); finished(r,'cancelled'); assert.equal(r.process.killSent,true);
  },
  async deadline() {
    const [r]=await run('hang',{timeoutMs:1000}); finished(r,'timed_out'); assert.equal(r.code,'TIMED_OUT');
  },
  async settlement_deadline() {
    const [r]=await run('settlement-hang'); finished(r,'timed_out'); assert.equal(r.process.killSent,true);
  },
  async crash_is_unknown() {
    const [r,h,id]=await run('crash'); finished(r,'unknown'); assert.equal(r.response,null);
    assert.throws(()=>h.resume(id),{code:'UNSUPPORTED_RESUME'});
    assert.equal(r.process.exitCode,7);
  },
  async nonzero_exit_is_not_success() {
    const [r]=await run('exit-nonzero'); finished(r,'unknown'); assert.equal(r.process.exitCode,9);
  },
  async malformed() {
    const [r]=await run('malformed'); finished(r,'failed'); assert.equal(r.code,'MALFORMED_FRAME');
  },
  async oversized() {
    const [r]=await run('oversized'); finished(r,'failed'); assert.equal(r.code,'FRAME_LIMIT');
  },
  async frame_flood() {
    const [r]=await run('frame-flood'); finished(r,'failed'); assert.equal(r.code,'FRAME_LIMIT');
    assert.ok(r.events.length <= 160);
  },
  async wrong_session() {
    const [r]=await run('wrong-session'); finished(r,'failed'); assert.equal(r.code,'SESSION_MISMATCH');
  },
  async missing_terminal_status() {
    const [r]=await run('no-status'); finished(r,'failed'); assert.equal(r.code,'UNPROVEN_TERMINAL');
  },
  async partial_is_not_success() {
    const [r]=await run('partial'); finished(r,'failed'); assert.equal(r.code,'NATIVE_FAILURE');
  },
  async duplicate_terminal() {
    const [r]=await run('duplicate-terminal'); finished(r,'completed');
    assert.equal(r.events.filter(e=>e.type==='native_terminal').length,1);
  },
  async conflicting_terminal() {
    const [r]=await run('conflicting-terminal'); finished(r,'failed'); assert.equal(r.code,'CONFLICTING_TERMINAL');
  },
  async queued_is_not_completed() {
    const [r]=await run('queued'); finished(r,'failed'); assert.equal(r.code,'SUBMISSION_NOT_EXCLUSIVE');
  },
  async approval_denied() {
    const [r]=await run('approval'); finished(r,'completed'); const result=JSON.parse(r.response);
    assert.deepEqual(result.reply.result,{choice:'deny'}); assert.equal(result.executed,false);
    assert.ok(r.events.some(e=>e.type==='approval_denied'));
  },
  async unsupported_request_denied() {
    const [r]=await run('unsupported-request'); finished(r,'completed'); const result=JSON.parse(r.response);
    assert.equal(result.reply.error.code,-32601); assert.equal(result.executed,false);
  },
  async terminal_before_ack() {
    const [r]=await run('early-terminal'); finished(r,'completed');
    assert.equal(r.events.filter(e=>e.type==='accepted').length,1);
  },
  async isolated_environment() {
    process.env.ALAZ_TEST_SECRET='synthetic-marker';
    const [r]=await run('environment'); finished(r,'completed'); const detail=JSON.parse(r.response);
    assert.equal(detail.credential_present,false); assert.equal(detail.upstream_entry_imported,false);
    assert.equal(detail.home,detail.cwd); assert.equal(detail.hermes_home,path.join(detail.home,'hermes'));
    const env=isolatedEnvironment('/isolated',{API_KEY:'marker',PATH:'do-not-inherit',NODE_OPTIONS:'bad',SystemRoot:'system'});
    assert.equal(env.API_KEY,undefined); assert.equal(env.PATH,undefined); assert.equal(env.NODE_OPTIONS,undefined);
    assert.equal(env.SystemRoot,'system'); delete process.env.ALAZ_TEST_SECRET;
  },
  async snapshots_and_capabilities() {
    const [r,h,id]=await run('echo'); const snapshot=h.status(id); snapshot.events[0].type='mutated';
    assert.equal(h.events(id)[0].type,'queued'); assert.ok(h.events(id,2).every(e=>e.seq>2));
    assert.equal(h.capabilities().actualAIAgent,false); assert.equal(h.capabilities().resume,false);
    assert.throws(()=>h.status('missing'),{code:'UNKNOWN_RUN'});
  },
  async input_validation() {
    const h=make();
    for(const input of [{key:'../x',text:'x'},{key:'x',text:'x',iterationBudget:true},
      {key:'x',text:'x',timeoutMs:Infinity},{key:'x',text:'x',scenario:'shell'},
      {key:'x',text:'x',command:'no'},{key:'x',text:'x'.repeat(9000)}]) assert.throws(()=>h.start(input));
    assert.throws(()=>h.resume(),{code:'UNSUPPORTED_RESUME'});
  },
  async canonical_wire_rejected() {
    const [r]=await run('canonical-wire'); finished(r,'failed');
    assert.equal(r.code,'UNSUPPORTED_WIRE');assert.equal(r.submitted,false);
  },
  async untrusted_event_name_not_logged() {
    const [r]=await run('untrusted-event-name'); finished(r,'completed');
    assert.equal(JSON.stringify(r.events).includes('do-not-log-untrusted-text'),false);
    assert.ok(r.events.some(e=>e.type==='peer_notification'));
  },
  async bounded_records() {
    const h=make();
    for(let i=0;i<64;i++) {const id=start(h,{key:'bound-'+i});h.cancel(id);await h.wait(id);}
    assert.throws(()=>h.start({key:'overflow',text:'x'}),{code:'RECORD_LIMIT'});
  },
  async spawn_failure() {
    const h=make(path.join(process.env.ALAZ_TEST_WORK,'missing-python'));
    const id=start(h,{scenario:'echo'}); const r=await h.wait(id); finished(r,'failed'); assert.equal(r.code,'SPAWN_ERROR');
  },
  async openclaw_cancellation_contract() {
    const state={explicitCancellationObserved:false,terminalOutcomeFrozen:false,sharedAbortAllowedAfterTerminalOutcome:false};
    let calls=0;const source=new AbortController();
    const owner=createAgentHarnessAttemptCancellation({upstreamSignal:source.signal,state,onAttemptAbort:()=>calls++});
    source.abort('first'); owner.abortExplicitly('second');
    assert.equal(calls,1);assert.equal(owner.controller.signal.reason,'first');assert.equal(state.explicitCancellationReason,'first');
    owner.freezeTerminalOutcome();owner.abortExplicitly('third');assert.equal(calls,1);owner.dispose();
  },
  async openclaw_deadline_contract() {
    const fired=deferred();const abort=new AbortController();
    const controller=createAgentHarnessAttemptDeadlineController({startedAtMs:Date.now(),startedAtMonotonicMs:performance.now(),
      timeoutMs:30,settlementTimeoutMs:30,signal:abort.signal,onTimeout:value=>fired.resolve(value)});
    const value=await boundedWait(fired.promise,1000);assert.equal(value.kind,'execution');controller.dispose();
    const stopped=deferred();const abort2=new AbortController();
    const second=createAgentHarnessAttemptDeadlineController({startedAtMs:Date.now(),startedAtMonotonicMs:performance.now(),
      timeoutMs:1000,settlementTimeoutMs:30,signal:abort2.signal,onTimeout:value=>stopped.resolve(value)});
    second.beginSettlement(Date.now());const value2=await boundedWait(stopped.promise,1000);
    assert.equal(value2.kind,'settlement');second.dispose();
  },
};
const selected=process.argv[2];
try {
  assert.equal(typeof cases[selected],'function','Unknown case');
  await cases[selected](); console.log(JSON.stringify({case:selected,result:'PASS',realModel:false}));
} finally {
  for(const {h,ids} of harnesses) for(const id of new Set(ids)) {h.cancel(id);await h.wait(id);}
}
