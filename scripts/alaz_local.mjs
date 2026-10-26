#!/usr/bin/env node
/** Thin local operator CLI; it never launches a service or stores task results. */
import { createReadStream } from 'node:fs';
import { LocalControlClient, controlError, controlExitCode, unsupportedLifecycle } from '../packages/claw-hermes/local-control.mjs';
import { HarnessError } from '../packages/claw-hermes/hermes-runs.mjs';

const HELP = `AlazHarness local control (Node 24)

Set ALAZ_BASE_URL to the explicit loopback URL and ALAZ_API_TOKEN to its bearer.
  node scripts/alaz_local.mjs task --request-id <32hex> --model <name> --input <file|->
  node scripts/alaz_local.mjs request --request-id <32hex>
  node scripts/alaz_local.mjs status|watch|result|usage|cancel --run-id <run_32hex>
  watch/cancel: --wait-ms <10..600000> --poll-ms <1..5000>
  All connected commands: --request-timeout-ms <10..60000>

Task submission requires the configured execution boundary and provider broker.
Keep the original request ID; after a lost response, use request to locate it.
Watch timeout or Ctrl+C stops observation only. Cancel sends one native stop and
then observes; its acknowledgement alone does not confirm that work stopped.
Usage reports native counters; missing usage and cost remain unknown.
Start and close are unavailable until native listener ownership is integrated.

JSON output. Exit codes: 0 accepted/observed, 2 failed work, 3 unresolved,
64 invalid arguments or unsupported operation.
`;

function invalid(code = 'invalid_cli_arguments') { throw new HarnessError(code, { mayHaveBeenAccepted: false }); }
function parse(args) {
  const command = args[0];
  if (args.length === 0 || (args.length === 1 && ['help', '--help', '-h'].includes(command))) return { help: true };
  const specs = {
    task: ['request-id', 'model', 'input'], request: ['request-id'],
    status: ['run-id'], watch: ['run-id', 'wait-ms', 'poll-ms'],
    result: ['run-id'], usage: ['run-id'], cancel: ['run-id', 'wait-ms', 'poll-ms'],
    start: [], close: [],
  };
  if (!Object.hasOwn(specs, command)) invalid('invalid_cli_command');
  const allowed = new Set([...specs[command], ...(['start', 'close'].includes(command) ? [] : ['request-timeout-ms'])]);
  const options = {};
  for (let i = 1; i < args.length; i += 2) {
    const flag = args[i];
    if (!flag.startsWith('--') || !allowed.has(flag.slice(2)) || Object.hasOwn(options, flag.slice(2))
        || typeof args[i + 1] !== 'string' || args[i + 1].startsWith('--')) invalid();
    options[flag.slice(2)] = args[i + 1];
  }
  const required = command === 'task' ? ['request-id', 'model', 'input']
    : command === 'request' ? ['request-id'] : ['start', 'close'].includes(command) ? [] : ['run-id'];
  if (required.some(name => !options[name])) invalid('missing_cli_argument');
  if (options['request-id'] !== undefined && !/^[a-f0-9]{32}$/.test(options['request-id'])) invalid('invalid_request_id');
  if (options['run-id'] !== undefined && !/^run_[a-f0-9]{32}$/.test(options['run-id'])) invalid('invalid_run_id');
  if (options.model !== undefined && (!options.model.trim() || Buffer.byteLength(options.model) > 200)) invalid('invalid_cli_arguments');
  for (const [key, min, max] of [['wait-ms', 10, 600000], ['poll-ms', 1, 5000], ['request-timeout-ms', 10, 60000]]) {
    if (options[key] !== undefined) {
      if (!/^[0-9]{1,9}$/.test(options[key])) invalid('invalid_cli_number');
      const n = Number(options[key]);
      if (!Number.isSafeInteger(n) || n < min || n > max) invalid('invalid_cli_number');
      options[key] = n;
    }
  }
  return { command, options };
}

async function readPrompt(path, signal) {
  if (signal.aborted) invalid('input_interrupted');
  const stream = path === '-' ? process.stdin : createReadStream(path, { highWaterMark: 16384 });
  const abort = () => stream.destroy(new Error('input_interrupted'));
  signal.addEventListener('abort', abort, { once: true });
  const chunks = [];
  let total = 0;
  try {
    for await (const chunk of stream) {
      total += chunk.length;
      if (total > 65536) invalid('input_too_large');
      chunks.push(chunk);
    }
    let value;
    try { value = new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks)); }
    catch { invalid('input_not_utf8'); }
    if (!value.trim()) invalid('input_empty');
    return value;
  } catch (error) {
    if (error instanceof HarnessError) throw error;
    invalid(signal.aborted ? 'input_interrupted' : 'input_unreadable');
  } finally {
    signal.removeEventListener('abort', abort);
    stream.destroy();
  }
}

let parsed, value;
const controller = new AbortController();
const interrupted = () => controller.abort('operator_interrupted');
process.on('SIGINT', interrupted);
process.on('SIGTERM', interrupted);
try {
  parsed = parse(process.argv.slice(2));
  if (parsed.help) {
    process.stdout.write(HELP);
  } else if (['start', 'close'].includes(parsed.command)) {
    value = unsupportedLifecycle(parsed.command);
  } else {
    const { command, options } = parsed;
    if (!process.env.ALAZ_BASE_URL || !process.env.ALAZ_API_TOKEN) invalid('missing_local_connection');
    const client = new LocalControlClient({ baseUrl: process.env.ALAZ_BASE_URL, token: process.env.ALAZ_API_TOKEN,
      requestTimeoutMs: options['request-timeout-ms'] ?? 5000 });
    const signal = controller.signal;
    if (command === 'task') {
      const input = await readPrompt(options.input, signal);
      value = await client.task({ requestId: options['request-id'], model: options.model, input }, { signal });
    } else if (command === 'request') {
      value = await client.request(options['request-id'], { signal });
    } else if (command === 'watch' || command === 'cancel') {
      value = await client[command](options['run-id'], { signal,
        watchTimeoutMs: options['wait-ms'] ?? 30000, pollIntervalMs: options['poll-ms'] ?? 100 });
    } else {
      value = await client[command](options['run-id'], { signal });
    }
  }
} catch (error) {
  value = controlError(error, { command: parsed?.command ?? null,
    requestId: parsed?.options?.['request-id'], runId: parsed?.options?.['run-id'] });
} finally {
  process.removeListener('SIGINT', interrupted);
  process.removeListener('SIGTERM', interrupted);
}
if (value) {
  process.stdout.write(JSON.stringify(value) + '\n');
  process.exitCode = controlExitCode(value);
}
