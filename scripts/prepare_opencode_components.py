"""Prepare pinned OpenCode component fixtures. Dry-run unless --apply; no full app."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
from pi_probe_support import isolated_env, fresh_runtime_path
from opencode_probe_support import ROOT, config, check_source, materialize, verify_prepared, digest


def source_for(workspace: Path) -> Path:
    registry=json.loads((ROOT/'config/research-sources.lock.json').read_text(encoding='utf-8'))
    row=next(x for x in registry['sources'] if x['name']=='opencode')
    source=(workspace/row['local_reference_path_from_default_workspace']).resolve()
    if not source.is_relative_to(workspace.resolve()):raise ValueError('Source outside workspace')
    if row['commit']!=config()['source_commit']:raise ValueError('Reference registry mismatch')
    check_source(source)
    return source


def npm_command() -> list[str]:
    node=shutil.which('node');npm=shutil.which('npm')
    if not node or not npm:raise ValueError('Node and npm must already be installed')
    binary=Path(npm)
    cli=binary.parent/'node_modules/npm/bin/npm-cli.js' if binary.suffix.lower() in ('.cmd','.bat') else binary.resolve()
    if not cli.is_file():raise ValueError('Cannot find existing npm CLI')
    return [node,str(cli),'ci','--ignore-scripts','--no-audit','--no-fund','--registry=https://registry.npmjs.org']


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args()
    source=source_for(a.source_workspace);out=fresh_runtime_path(a.source_workspace,a.output)
    c=config();print(json.dumps({'mode':'apply' if a.apply else 'plan','source_commit':c['source_commit'],'dependencies':{'effect':c['effect_version']},'full_opencode_install':False,'lifecycle_scripts':False}))
    if not a.apply:return 0
    out.mkdir(parents=True);env=isolated_env(out)
    for name in ('package.json','package-lock.json'):shutil.copyfile(ROOT/'config/opencode-probe'/name,out/name)
    started=time.monotonic()
    process=subprocess.run(npm_command(),cwd=out,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    for name,text in [('install.stdout.txt',process.stdout),('install.stderr.txt',process.stderr)]:(out/name).write_text(text,encoding='utf-8')
    receipt={'scope':'one pinned dependency and selected-source fixture preparation','exit_code':process.returncode,'elapsed_seconds':round(time.monotonic()-started,3),'model_calls':0,'source_commit':c['source_commit'],'package_lock_sha256':digest(out/'package-lock.json')}
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if process.returncode:print(process.stderr[-3000:]);return process.returncode
    projection=materialize(source,out);verify_prepared(source,out)
    receipt.update(source_inputs=len(projection['inputs']),projection_files=len(projection['outputs']),verified=True)
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))
    return 0

if __name__=='__main__':raise SystemExit(main())
