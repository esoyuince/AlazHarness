"""Prepare pinned Pi source and dependencies in a fresh directory; dry-run by default."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from run_native_pi_probe import isolated_environment, safe_source_path, source_manifest_sha256, validate_prepared

NPM_FLAGS=('ci','--ignore-scripts','--no-audit','--no-fund','--omit=dev',
           '--include-workspace-root=false','--workspace=packages/agent','--workspace=packages/coding-agent')


def verify_reference(source: Path, project: Path) -> dict:
    lock=json.loads((project/'config/pi-native-probe.lock.json').read_text(encoding='utf-8'))
    sha=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,timeout=15).strip()
    if sha!=lock['source_commit']:raise ValueError('Reference commit mismatch')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True,timeout=15).strip():
        raise ValueError('Reference must be clean')
    raw=subprocess.check_output(['git','-C',str(source),'show',sha+':package-lock.json'],timeout=15)
    if hashlib.sha256(raw).hexdigest()!=lock['package_lock_sha256']:raise ValueError('Reference lock mismatch')
    return lock


def npm_command(node: Path, explicit_cli: Path | None) -> list[str]:
    candidates=[explicit_cli] if explicit_cli is not None else [node.parent/'node_modules/npm/bin/npm-cli.js',node.parent.parent/'lib/node_modules/npm/bin/npm-cli.js',Path('/usr/share/nodejs/npm/bin/npm-cli.js')]
    cli=next((p for p in candidates if p is not None and p.is_file()),None)
    if cli is None:raise ValueError('Pass the installed npm-cli.js via --npm-cli; no bootstrap download')
    return [str(node),str(cli.resolve()),*NPM_FLAGS]


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--npm-cli',type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();project=Path(__file__).resolve().parents[1]
    source=args.reference_source.resolve();out=args.output.absolute();lock=verify_reference(source,project)
    if out.exists():raise FileExistsError('Use a fresh preparation directory')
    if out.resolve().is_relative_to(source):raise ValueError('Cannot prepare inside the reference source')
    node_path=shutil.which('node')
    if node_path is None:raise ValueError('Node required')
    node=Path(node_path).resolve();command=npm_command(node,args.npm_cli)
    version=subprocess.check_output([str(node),'--version'],text=True,timeout=10).strip()
    if int(version.lstrip('v').split('.')[0])<24:raise ValueError('Node24+ required')
    print(json.dumps({'mode':'apply' if args.apply else 'plan','source_commit':lock['source_commit'],
                      'output':str(out),'lifecycle_scripts':False,'agent_started':False}),flush=True)
    if not args.apply:return 0
    out.mkdir(parents=True);environment=isolated_environment(out);target=out/'source';target.mkdir()
    archive=out/'pi-source.tar'
    subprocess.run(['git','-C',str(source),'archive','--format=tar','--output='+str(archive),lock['source_commit']],check=True,timeout=30)
    # Extract regular files only; never follow archive links or execute lifecycle hooks.
    with tarfile.open(archive) as tar:
        members=tar.getmembers()
        if sum(m.size for m in members)>300_000_000:raise ValueError('Source archive exceeds size bound')
        for member in members:
            destination=safe_source_path(target,member.name.rstrip('/'))
            if member.isdir():destination.mkdir(parents=True,exist_ok=True);continue
            if not member.isfile():raise ValueError('Unsupported source link/type')
            destination.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as reader, destination.open('xb') as writer:shutil.copyfileobj(reader,writer)
    paths=subprocess.check_output(['git','-C',str(source),'ls-files','-z'],timeout=15).split(b'\0')
    manifest={raw.decode():hashlib.sha256(safe_source_path(target,raw.decode()).read_bytes()).hexdigest() for raw in paths if raw}
    manifest_bytes=json.dumps(manifest,indent=2).encode('utf-8')
    if len(manifest)!=lock['source_files'] or source_manifest_sha256(manifest)!=lock['source_manifest_sha256']:
        raise ValueError('Extracted source differs from the reviewed pin')
    (out/'source-files.json').write_bytes(manifest_bytes)
    for name in ('empty-user.npmrc','empty-global.npmrc'):(out/name).write_text('',encoding='utf-8')
    environment.update(NPM_CONFIG_USERCONFIG=str(out/'empty-user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(out/'empty-global.npmrc'),
                       NPM_CONFIG_CACHE=str(out/'cache'),NPM_CONFIG_REGISTRY='https://registry.npmjs.org/',NPM_CONFIG_IGNORE_SCRIPTS='true',NPM_CONFIG_UPDATE_NOTIFIER='false')
    started=time.monotonic();timed_out=False
    with (out/'install.stdout.txt').open('w',encoding='utf-8') as stdout,(out/'install.stderr.txt').open('w',encoding='utf-8') as stderr:
        try:code=subprocess.run(command,cwd=target,env=environment,stdout=stdout,stderr=stderr,timeout=300).returncode
        except subprocess.TimeoutExpired:code=-1;timed_out=True
    receipt={'scope':'isolated preparation only, not agent acceptance','source_commit':lock['source_commit'],
             'files':len(manifest),'lock_sha256':lock['package_lock_sha256'],'exit_code':code,'timed_out':timed_out,
             'elapsed_seconds':round(time.monotonic()-started,3),'scripts_disabled':True,'dev_dependencies_omitted':True}
    (out/'install-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if code==0:validate_prepared(out,project)
    print(json.dumps(receipt));return 0 if code==0 else 1

if __name__=='__main__':raise SystemExit(main())
