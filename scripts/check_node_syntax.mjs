// Parse without executing source. Native --check extension handling differs across
// Node builds; explicitly strip erasable TypeScript, then check the resulting ESM.
import fs from 'node:fs';
import path from 'node:path';
import { stripTypeScriptTypes } from 'node:module';
import { spawnSync } from 'node:child_process';
const file=process.argv[2];
if (!file || !['.mjs','.ts'].includes(path.extname(file))) throw new Error('Expected .mjs or .ts source');
const original=fs.readFileSync(file,'utf8');
const javascript=path.extname(file)==='.ts'
  ? stripTypeScriptTypes(original,{mode:'strip',sourceUrl:file}) : original;
const check=spawnSync(process.execPath,['--check','--input-type=module'],{
  input:javascript,encoding:'utf8',timeout:10000,shell:false,
});
if (check.stderr) process.stderr.write(check.stderr);
if (check.error) process.stderr.write('Syntax checker process failed\n');
process.exitCode=check.status ?? 1;
