"""Deterministic selected-source projection for REF-OC-001; no application installs."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT = re.compile(r"((?:from\s+|import\s*)[\"'])(\.{1,2}/[^\"']+)\.js([\"'])")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config() -> dict:
    return json.loads((ROOT/'config/opencode-probe/source-lock.json').read_text(encoding='utf-8'))


def check_source(source: Path) -> str:
    c=config()
    for args,expected in [(('rev-parse','HEAD'),c['source_commit']), (('status','--porcelain','--untracked-files=all'),'')]:
        actual=subprocess.check_output(['git','-C',str(source),*args],text=True,encoding='utf-8',timeout=20).strip()
        if actual!=expected:raise ValueError('Reference source drift')
    if (source/'.env').exists():raise ValueError('Reference dotenv is not permitted')
    for name,expected in c['files'].items():
        if digest(source/name)!=expected:raise ValueError('Pinned source bytes changed: '+name)
    return c['source_commit']


def relative_imports(text: str) -> str:
    return IMPORT.sub(lambda m:m[1]+m[2]+'.ts'+m[3],text)


def slice_lines(source: Path, name: str, first: int, last: int, prefix: str) -> str:
    lines=(source/name).read_text(encoding='utf-8').splitlines()
    if first<1 or last>len(lines):raise ValueError('Invalid selected range')
    return prefix+'\n'.join(lines[first-1:last])+'\n'


def schema_closure(source: Path) -> set[Path]:
    root=(source/'packages/schema/src').resolve()
    files:set[Path]=set();todo=[root/'permission.ts',root/'event-manifest.ts']
    while todo:
        p=todo.pop().resolve()
        if not p.is_relative_to(root):raise ValueError('Schema import escaped root')
        if p in files:continue
        files.add(p)
        text=p.read_text(encoding='utf-8')
        for name in re.findall(r"(?:from\s+|import\s*)[\"']([^\"']+)[\"']",text):
            if name.startswith('.'):
                q=(p.parent/name).resolve()
                if q.suffix=='.js':q=q.with_suffix('.ts')
                if not q.is_file():raise ValueError('Missing schema dependency')
                todo.append(q)
            elif name not in ('effect','@standard-schema/spec'):
                raise ValueError('Unreviewed schema dependency: '+name)
    return files


def projection(source: Path) -> tuple[dict[str,str],dict[str,str]]:
    check_source(source)
    outputs:dict[str,str]={};inputs={}
    def full(path: str) -> str:
        inputs[path]=digest(source/path)
        return (source/path).read_text(encoding='utf-8')
    for p in sorted(schema_closure(source)):
        name=p.relative_to(source).as_posix()
        outputs['schema/'+p.relative_to(source/'packages/schema/src').as_posix()]=relative_imports(full(name))
    p='packages/core/src/permission.ts';text=full(p)
    prefix='export * as Permission from "./permission.ts"\nimport { makeLocationNode, Bus, Location, Agent, SessionStore, PermissionSaved, PluginHooks } from "./services.mjs"\nimport { Context, Deferred, Effect, Layer, Schema } from "effect"\nimport { Permission } from "./schema/permission.ts"\nimport { SessionErrors, SessionSchema } from "./session-error.ts"\nimport { Wildcard } from "./wildcard.ts"\n'
    if text.splitlines()[15]!='const PermissionEffect = Permission.Effect':raise ValueError('Permission slice boundary changed')
    outputs['permission.ts']=(prefix+'\n'.join(text.splitlines()[15:])+'\n').replace('"@opencode/schema/permission"','"./schema/permission.ts"')
    outputs['wildcard.ts']=relative_imports(full('packages/core/src/util/wildcard.ts'))
    outputs['event-feed.ts']=full('packages/server/src/event-feed.ts').replace('"./event-feed"','"./event-feed.ts"').replace('"@opencode/core/bus"','"./services.mjs"').replace('"@opencode/schema/event"','"./schema/event.ts"').replace('"@opencode/protocol/groups/event"','"./protocol-event.ts"')
    text=full('packages/protocol/src/groups/event.ts')
    outputs['protocol-event.ts']=re.sub(r'"@opencode/schema/([^"\n]+)"',r'"./schema/\1.ts"',text)
    full('packages/core/src/session/error.ts')
    outputs['session-error.ts']=slice_lines(source,'packages/core/src/session/error.ts',10,12,'import { Schema } from "effect"\nimport { SessionID } from "./schema/session-id.ts"\nexport const SessionSchema = {ID:SessionID}\n')+'export const SessionErrors={NotFoundError}\n'
    full('packages/protocol/src/errors.ts')
    outputs['protocol-error.ts']=slice_lines(source,'packages/protocol/src/errors.ts',209,216,'import {Schema} from "effect"\n')
    name='packages/server/src/handlers/permission.ts';full(name)
    outputs['owned-request.ts']=slice_lines(source,name,13,15,'import {Effect} from "effect"\nimport {Permission} from "./permission.ts"\nimport {PermissionNotFoundError} from "./protocol-error.ts"\n')+slice_lines(source,name,21,29,'')+'export {requireOwnedRequest}\n'
    outputs['LICENSE']=full('LICENSE')
    for name in ('opencode_services.mjs','opencode_component_worker.mjs'):
        p=ROOT/'scripts'/name
        if not p.is_file():raise ValueError('Fixture not written yet')
        outputs['services.mjs' if name=='opencode_services.mjs' else 'worker.mjs']=p.read_text(encoding='utf-8')
    return outputs,inputs



def dependency_digest(prepared: Path) -> str:
    base=prepared/'node_modules/effect'
    rows=[]
    for p in sorted(base.rglob('*')):
        if p.is_symlink():raise ValueError('Unexpected dependency symlink')
        if p.is_file() and p.suffix in ('.js','.json'):
            rows.append(p.relative_to(base).as_posix()+' '+digest(p))
    if not rows:raise ValueError('Missing dependency bytes')
    return hashlib.sha256(('\n'.join(rows)+'\n').encode()).hexdigest()


def materialize(source: Path, prepared: Path) -> dict:
    outputs,inputs=projection(source)
    target=prepared/'projected';target.mkdir(exist_ok=False)
    for name,text in outputs.items():
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')
    receipt={'scope':'selected unchanged executable bodies with explicit dependency fixtures',
             'source_commit':config()['source_commit'],'inputs':inputs,
             'outputs':{name:digest(target/name) for name in outputs},
             'effect_version':config()['effect_version'],'effect_integrity':config()['effect_integrity'],
             'dependency_tree_sha256':dependency_digest(prepared),
             'full_app_installed':False,'schemas_real':True,'dependency_services':'Bus/Location/Agent/SessionStore/PermissionSaved/PluginHooks fixtures',
             'http_middleware_tested':False,'database_persistence_tested':False}
    (prepared/'projection.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


def verify_prepared(source: Path, prepared: Path) -> dict:
    outputs,inputs=projection(source)
    recorded=json.loads((prepared/'projection.json').read_text(encoding='utf-8'))
    if recorded['inputs']!=inputs or set(recorded['outputs'])!=set(outputs):raise ValueError('Projection manifest drift')
    for name,text in outputs.items():
        expected=hashlib.sha256(text.encode()).hexdigest()
        if digest(prepared/'projected'/name)!=expected or recorded['outputs'][name]!=expected:
            raise ValueError('Projected source or fixture drift: '+name)
    lock=json.loads((prepared/'package-lock.json').read_text(encoding='utf-8'))
    if set(lock['packages'])!={'','node_modules/effect'}:raise ValueError('Unexpected dependency')
    effect=lock['packages']['node_modules/effect'];c=config()
    if effect['version']!=c['effect_version'] or effect['integrity']!=c['effect_integrity']:raise ValueError('Effect lock drift')
    if digest(prepared/'package-lock.json')!=digest(ROOT/'config/opencode-probe/package-lock.json'):raise ValueError('Install lock drift')
    actual=json.loads((prepared/'node_modules/effect/package.json').read_text())
    if actual['version']!=c['effect_version']:raise ValueError('Installed Effect version drift')
    if dependency_digest(prepared)!=recorded['dependency_tree_sha256']:raise ValueError('Dependency byte drift')
    return recorded
