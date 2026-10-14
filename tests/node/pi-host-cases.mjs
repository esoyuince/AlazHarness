/** Host-contract unit tests; no Pi dependency or provider network required. */
import assert from 'node:assert/strict';
import { requestGate, evaluateProbe, normalizedOutcome } from '../../scripts/pi_probe_contract.mjs';
const endpoint = 'http://127.0.0.1:12345/v1/chat/completions';
const sample = () => ({ scenario: 'file-read', isStreaming: false, pendingTools: 0, agentEnds: 1, timedOut: false,
  serverErrors: [], gate: {admitted: 2, budgetDenied: 0, endpointDenied: 0}, modelInferenceCalls: 0, paidCalls: 0,
  toolResults: 1, toolErrors: 0, markerInToolResult: true, modelRequests: 2, modelSawMarker: true,
  markerInFinal: true, stopReason: 'stop', modelSawError: false, cancelSocketClosed: false,
  beforeToolCalls: 1, finishHookEnds: 0, taskCompleted: true });
const cases = {
  async concurrent_cap() {
    let called = 0; const gate = requestGate(endpoint, 1, async () => { called++; return new Response('{}'); });
    const result = await Promise.allSettled([gate.fetch(endpoint, {method:'POST'}),gate.fetch(endpoint, {method:'POST'})]);
    assert.equal(called,1);assert.equal(result.filter(x => x.status === 'fulfilled').length,1);assert.equal(gate.state.budgetDenied,1);
  },
  async bad_endpoint() {
    const credentialed = new URL('http://127.0.0.1/x');
    credentialed.username = 'synthetic';
    credentialed.password = 'synthetic';
    for (const url of ['https://127.0.0.1/x','http://example.org/x',credentialed.href,'http://127.0.0.1/x?q=1']) assert.throws(() => requestGate(url,1));
  },
  async bad_limit() { for (const n of [0,-1,1.5,NaN,Infinity,9]) assert.throws(() => requestGate(endpoint,n)); },
  async wrong_target() {
    const gate=requestGate(endpoint,1,async () => { throw new Error('Must never invoke provider'); });
    await assert.rejects(gate.fetch(endpoint+'/else',{method:'POST'}),/ENDPOINT_DENIED/);
    await assert.rejects(gate.fetch(endpoint,{method:'GET'}),/ENDPOINT_DENIED/);assert.equal(gate.state.admitted,0);
  },
  async redirect_not_followed() {
    let seen;const gate=requestGate(endpoint,1,async (_url, options) => {seen=options;return new Response('{}');});
    await gate.fetch(endpoint,{method:'POST',redirect:'follow'});assert.equal(seen.redirect,'error');
  },
  async valid_receipt() {assert.deepEqual(evaluateProbe(sample()),[]);},
  async missing_marker_rejected() {const r=sample();r.markerInToolResult=false;assert.ok(evaluateProbe(r).length);},
  async false_idle_rejected() {const r=sample();r.isStreaming=true;assert.ok(evaluateProbe(r).length);},
  async malformed_receipt_rejected() {
    for (const value of [null,{}, {gate:{},serverErrors:[]}, {...sample(),modelRequests:NaN}]) assert.ok(evaluateProbe(value).length);
  },
  async budget_cause_preserved() {
    const r=sample();r.gate.budgetDenied=1;r.stopReason='error';r.errorMessage='Connection error.';r.taskCompleted=false;
    assert.equal(normalizedOutcome(r),'request_budget_exhausted');
  },
};
const name=process.argv[2];
if (!Object.hasOwn(cases,name)) throw new Error('Unknown unit scenario');
await cases[name]();console.log(JSON.stringify({name,result:'PASS',scope:'host-contract-unit-only'}));
