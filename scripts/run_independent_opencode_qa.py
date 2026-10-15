"""Opt-in independent source-module checks. No installation, model, or full OpenCode bootstrap."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess
from pi_probe_support import ROOT, digest, fresh_runtime_path, isolated_env

EXPECTED = {
    'permission': ('deny-before-saved-and-plugin','empty-resources-characterization',
        'pending-input-save-mutation','returned-pending-request-is-mutable',
        'selected-once-after-policy-revocation','always-rechecks-other-pending-deny',
        'reject-clears-same-session-not-other','duplicate-pending-is-error-original-retained',
        'once-reply-is-not-reusable','request-id-can-be-reused-after-settlement',
        'close-rejects-waiters-and-new-asks','interrupted-waiter-removes-prompt'),
    'event': ('frame-json-escape-without-resume-id','encode-once-fanout',
        'no-subscribers-no-retention-or-encoding','unknown-event-does-not-fill-capacity',
        'overflow-only-lagging-subscriber','encoding-failure-all-current-fresh-subscribe-recovers',
        'disconnect-reconnect-does-not-replay-gap','feed-finalizer-removes-bus-listener'),
}
INTEGRITY='sha512-b1VlQG9g8fwxE5QnIZuPoOP/0MsqHJSRKxUijjoM80E5q95FXrX5yWtY5XI8G+GJsBQAVSDbLS458z9a++uVvw=='


def validate(value: dict, family: str, nonce: str, pid: int, code: int) -> list[str]:
    try:
        if family not in EXPECTED or not isinstance(value,dict):return ['wrong evidence family']
        errors=[]
        if type(pid) is not int or pid<=0 or type(code) is not int or code!=0:errors.append('process failure')
        if value.get('nonce')!=nonce or type(value.get('pid')) is not int or value['pid']!=pid:errors.append('receipt identity')
        rows=value['cases']
        if tuple(row['name'] for row in rows)!=EXPECTED[family]:errors.append('wrong cases/order')
        if any(row.get('result')!='PASS' for row in rows):errors.append('failed observation')
        for key,expected in [('passed',len(EXPECTED[family])),('failed',0),('model_calls',0)]:
            if type(value.get(key)) is not int or value[key]!=expected:errors.append('invalid '+key)
        if not value.get('source_loads'):errors.append('no source provenance')
        return errors
    except (KeyError,TypeError,AttributeError):return ['malformed evidence']


def tree_hash(root: Path) -> str:
    records=[]
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('Unexpected dependency symlink')
        if path.is_file() and path.suffix in ('.js','.json'):
            records.append(path.relative_to(root).as_posix()+' '+digest(path))
    if not records:raise ValueError('Missing prepared Effect')
    return hashlib.sha256(('\n'.join(records)+'\n').encode()).hexdigest()


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',type=Path,required=True)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();workspace=args.source_workspace.resolve();prepared=args.prepared.resolve()
    record=next(s for s in json.loads((ROOT/'config/research-sources.lock.json').read_text(encoding='utf-8'))['sources'] if s['name']=='opencode')
    source=workspace/record['local_reference_path_from_default_workspace']
    def check_source():
        if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=record['commit']:raise ValueError('Source pin drift')
        if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():raise ValueError('Modified source')
    check_source()
    if not prepared.is_relative_to(workspace/'runtime'):raise ValueError('Prepared dependency must be isolated in runtime')
    lock=json.loads((prepared/'package-lock.json').read_text(encoding='utf-8'))
    if set(lock['packages'])!={'','node_modules/effect'}:raise ValueError('Unexpected dependency set')
    package=lock['packages']['node_modules/effect']
    if package['version']!='4.0.1' or package['integrity']!=INTEGRITY:raise ValueError('Wrong Effect dependency pin')
    effect=prepared/'node_modules/effect'
    if json.loads((effect/'package.json').read_text(encoding='utf-8'))['version']!='4.0.1':raise ValueError('Installed Effect mismatch')
    before=tree_hash(effect)
    scripts=ROOT/'scripts/qa/opencode-independent'
    program_hashes={p.name:digest(p) for p in scripts.glob('*.mjs')}
    output=fresh_runtime_path(workspace,args.output);output.mkdir(parents=True)
    node=shutil.which('node')
    if not node:raise ValueError('Node required')
    families=[]
    for family in EXPECTED:
        work=output/family;work.mkdir();nonce=secrets.token_hex(16)
        cfg={'source':str(source),'dependency_home':str(prepared),'source_commit':record['commit'],'nonce':nonce}
        config=work/'config.json';config.write_text(json.dumps(cfg),encoding='utf-8')
        env=isolated_env(work);env.update(ALAZ_OC_QA_CONFIG=str(config),ALAZ_OC_QA_OUTPUT=str(work),NO_COLOR='1')
        command=[node,'--import',(scripts/'source-loader.mjs').as_uri(),str(scripts/(family+'-edge-cases.mjs'))]
        timed_out=False
        with (work/'stdout.txt').open('w',encoding='utf-8') as out,(work/'stderr.txt').open('w',encoding='utf-8') as err:
            child=subprocess.Popen(command,cwd=work,env=env,stdout=out,stderr=err)
            try:child.wait(timeout=35)
            except subprocess.TimeoutExpired:timed_out=True
            finally:
                if child.poll() is None:child.kill()
                child.wait(timeout=5)
        receipt=work/(family+'-results.json');data=None
        if receipt.is_file() and receipt.stat().st_size<=262144:
            try:data=json.loads(receipt.read_text(encoding='utf-8'))
            except ValueError:pass
        errors=validate(data,family,nonce,child.pid,child.returncode)
        if timed_out:errors.append('timeout')
        if data:
            if data.get('source_commit')!=record['commit']:errors.append('source identity')
            for loaded in data.get('source_loads',[]):
                from urllib.parse import urlparse,unquote
                raw=unquote(urlparse(loaded['url']).path)
                if len(raw)>2 and raw[0]=='/' and raw[2]==':':raw=raw[1:]
                path=Path(raw).resolve()
                if not path.is_relative_to(source.resolve()) or digest(path)!=loaded['sha256']:errors.append('source changed during execution')
                loaded['path']=path.relative_to(source.resolve()).as_posix();loaded.pop('url',None)
        families.append({'family':family,'exit_code':child.returncode,'timed_out':timed_out,'reaped':child.poll() is not None,'result':'FAIL' if errors else 'PASS','errors':errors,'receipt':data})
        print(family,families[-1]['result'],errors,flush=True)
    check_source()
    drift=before!=tree_hash(effect) or program_hashes!={p.name:digest(p) for p in scripts.glob('*.mjs')}
    summary={'scope':'independent unchanged OpenCode component bodies, real Effect/schema and fixture service ports; no full HTTP/server/storage acceptance',
             'source_commit':record['commit'],'dependency_tree_sha256':before,'program_hashes':program_hashes,
             'families':families,'observations':sum(len(v) for v in EXPECTED.values()),'source_or_program_drift':drift,
             'model_calls':0,'product_adoption':False,'result':'PASS' if not drift and all(f['result']=='PASS' for f in families) else 'FAIL'}
    (output/'independent-qa.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='families'},indent=2))
    return 0 if summary['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
