import path from 'node:path';
import { MockHybridHarness } from './mock-harness.mjs';
const [python, workRoot, scenario, text, iterations] = process.argv.slice(2);
const h = new MockHybridHarness({python, workRoot:path.resolve(workRoot)});
const run = h.start({key:'demo',text,scenario,iterationBudget:Number(iterations)});
const result = await h.wait(run);
console.log(JSON.stringify({scope:'OpenClaw/Hermes component slice; SCRIPTED peer, not AIAgent',
  capabilities:h.capabilities(),result},null,2));
process.exitCode = result.state === 'completed' ? 0 : 2;
