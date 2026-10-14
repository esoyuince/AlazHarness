/** Real Pi Agent + provider parser + built-in read tool; only model responses are scripted. */
import { Agent } from '@earendil-works/pi-agent-core';
import { stream as nativeStream } from '@earendil-works/pi-ai/api/openai-completions';
import { createReadTool } from '@earendil-works/pi-coding-agent/core/tools/read.ts';
import { createHash, randomBytes } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { requestGate, evaluateProbe, normalizedOutcome, SCENARIOS } from './pi_probe_contract.mjs';

const scenario = process.argv[2];
if (!SCENARIOS.includes(scenario)) throw new Error('Unknown scenario');
const work = process.cwd();
if (!process.env.PI_PROBE_OUTPUT || resolve(process.env.PI_PROBE_OUTPUT) !== work) throw new Error('Fresh probe cwd required');
const marker = 'ALAZ_PI_' + randomBytes(16).toString('hex');
const fixture = resolve(work, 'input.txt');
await writeFile(fixture, `${marker}\nışık:42\n`, { encoding: 'utf8', flag: 'wx' });
const trace = [];
const r = { scenario, scope: 'real-pi-agent-provider-and-read-tool-scripted-model',
  modelRequests: 0, modelSawMarker: false, modelSawError: false, serverErrors: [],
  beforeToolCalls: 0, finishHookEnds: 0, agentEnds: 0, cancelSocketClosed: false,
  timedOut: false, modelInferenceCalls: 0, paidCalls: 0 };
let agent;
const sockets = new Set();
function sse(res, message, finishReason) {
  res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  const chunk = (delta, reason = null, usage) => res.write(`data: ${JSON.stringify({
    id: `pi-probe-${r.modelRequests}`, object: 'chat.completion.chunk', created: 1,
    model: 'alaz-scripted', choices: [{ index: 0, delta, finish_reason: reason }], ...(usage ? { usage } : {}),
  })}\n\n`);
  chunk({ role: 'assistant' });
  chunk(message);
  chunk({}, finishReason, { prompt_tokens: 120, completion_tokens: 20, total_tokens: 140 });
  res.end('data: [DONE]\n\n');
}
const server = createServer(async (req, res) => {
  try {
    if (req.method !== 'POST' || req.url !== '/v1/chat/completions') throw new Error('Unexpected model endpoint');
    const chunks = []; let bytes = 0;
    for await (const c of req) { bytes += c.length; if (bytes > 1000000) throw new Error('Oversize request'); chunks.push(c); }
    const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    r.modelRequests++;
    trace.push({ event: 'model-request', number: r.modelRequests });
    if (r.modelRequests > 4 || body.stream !== true) throw new Error('Unexpected model request');
    if (scenario === 'cancel-model') {
      res.once('close', () => { r.cancelSocketClosed = true; });
      setTimeout(() => agent.abort(), 20); // cancel only once actual provider request was observed
      return;
    }
    const toolMessages = body.messages.filter(m => m.role === 'tool');
    if (toolMessages.length === 0) {
      const names = (body.tools ?? []).map(t => t.function?.name);
      if (names.length !== 1 || names[0] !== 'read') throw new Error('Unexpected native tool loadout');
      const path = scenario === 'missing-file' ? resolve(work, 'absent.txt') : fixture;
      sse(res, { tool_calls: [{ index: 0, id: 'pi-read-1', type: 'function', function: {
        name: 'read', arguments: JSON.stringify({ path }),
      } }] }, scenario === 'truncated-tool' ? 'length' : 'tool_calls');
    } else {
      const text = String(toolMessages.at(-1).content);
      r.modelSawMarker = text.includes(marker);
      r.modelSawError = /ENOENT|no such file|not found|truncat/i.test(text);
      if (scenario === 'file-read' && !r.modelSawMarker) throw new Error('Actual native file marker was not returned to provider');
      if (scenario === 'missing-file' && !r.modelSawError) throw new Error('Native file error was not returned');
      sse(res, { content: r.modelSawMarker ? `Verified native read: ${marker}` : 'EXPECTED_TOOL_ERROR' }, 'stop');
    }
  } catch (error) {
    r.serverErrors.push(error.message); if (!res.headersSent) res.writeHead(400); res.end();
  }
});
server.on('connection', socket => { sockets.add(socket); socket.once('close', () => sockets.delete(socket)); });
await new Promise((ok, fail) => { server.once('error', fail); server.listen(0, '127.0.0.1', ok); });
const baseUrl = `http://127.0.0.1:${server.address().port}/v1`;
const gate = requestGate(`${baseUrl}/chat/completions`, scenario === 'request-cap' ? 1 : 4);
const model = { id: 'alaz-scripted', name: 'Alaz scripted fixture', api: 'openai-completions', provider: 'alaz-probe',
  baseUrl, reasoning: false, input: ['text'], contextWindow: 131072, maxTokens: 256,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } };
let unsubscribe;
let timer;
try {
  agent = new Agent({
    initialState: { systemPrompt: 'Use only read to inspect input.txt.', model, tools: [createReadTool(work)] },
    streamFn: (m, ctx, options) => nativeStream(m, ctx, { ...options, apiKey: 'alaz-loopback-fixture',
      fetch: gate.fetch, maxRetries: 0, maxTokens: 256, cacheRetention: 'none' }),
    beforeToolCall: () => { r.beforeToolCalls++; },
    finishTurn: () => {
      if (scenario === 'one-round') { r.finishHookEnds++; return { action: 'end' }; }
      return undefined;
    },
  });
  unsubscribe = agent.subscribe(event => {
    if (event.type === 'agent_end') r.agentEnds++;
    if (event.type !== 'message_update') trace.push({ event: event.type });
  });
  timer = setTimeout(() => { r.timedOut = true; agent.abort(); }, 12000);
  await agent.prompt('Read input.txt with the read tool and report its first line.');
  await agent.waitForIdle();
  if (scenario === 'cancel-model') {
    for (let i = 0; i < 25 && !r.cancelSocketClosed; i++) await delay(10);
  }
  const tools = agent.state.messages.filter(m => m.role === 'toolResult');
  const last = agent.state.messages.filter(m => m.role === 'assistant').at(-1);
  const final = (last?.content ?? []).filter(c => c.type === 'text').map(c => c.text).join('');
  Object.assign(r, { toolResults: tools.length, toolErrors: tools.filter(m => m.isError).length,
    markerInToolResult: tools.some(m => JSON.stringify(m.content).includes(marker)), markerInFinal: final.includes(marker),
    stopReason: last?.stopReason ?? null, isStreaming: agent.state.isStreaming,
    pendingTools: agent.state.pendingToolCalls.size, gate: { ...gate.state },
    errorMessage: last?.errorMessage ?? null, finalSha256: createHash('sha256').update(final).digest('hex'),
    fixtureUnchanged: (await readFile(fixture, 'utf8')) === `${marker}\nışık:42\n`,
    taskCompleted: scenario === 'file-read' && final.includes(marker) && last?.stopReason === 'stop',
    statePersistenceTested: false, codingAgentSessionTested: false, durableHarnessTested: false,
    osSandboxClaimed: false, autonomyTested: false, trace,
  });
  r.normalizedOutcome = normalizedOutcome(r);
  const failures = evaluateProbe(r);
  if (!r.fixtureUnchanged) failures.push('fixture-mutated');
  r.failures = failures; r.result = failures.length ? 'FAIL' : 'PASS';
} finally {
  clearTimeout(timer); unsubscribe?.(); agent?.abort();
  const closed = new Promise(ok => server.close(ok));
  for (const socket of sockets) socket.destroy();
  await closed;
}
await writeFile(resolve(work, 'receipt.json'), JSON.stringify(r, null, 2) + '\n', { flag: 'wx' });
console.log(JSON.stringify(r, null, 2));
process.exitCode = r.result === 'PASS' ? 0 : 1;
