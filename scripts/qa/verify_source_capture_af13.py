"""Opt-in operator check over one CLOSED scripted Linux broker probe.

No new Gateway, tool or model execution. Reads the explicitly selected fixture,
not an agent-supplied path. Does not use immutable, change retention or write DB.
Private context files stay at fresh output; only summary/reports may be published.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext, _load, _json, RESULT, PIN
from execution_budget import ExecutionPolicy
from evidence_view import EvidenceViewInspector, EvidenceSelection, render_evidence_text
from source_capture import PREFIX


def require(value,reason):
    if not value:raise ValueError(reason)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=2097152,'invalid_fixture_file')
    return _load(path.read_text(encoding='utf-8'))


def verify(fixture:Path,out:Path,receipt_sha:str):
    require(fixture.is_absolute() and out.is_absolute() and not out.exists() and
            not out.is_relative_to(fixture) and not fixture.is_relative_to(out),'fresh_separate_output_required')
    require(not any(p.is_symlink() for p in (fixture,*fixture.parents,out,*out.parents)),'linked_fixture_path')
    rp=fixture/'broker-native-result.json';require(digest(rp)==receipt_sha,'fixture_receipt_mismatch')
    rec=read(rp)
    require(rec['result']=='PASS' and rec['source_commit']==PIN and not rec['errors'] and
            not rec['source_drift'] and rec['gateway_exit']==rec['broker_exit']==0 and
            rec['inference_calls']==rec['paid_calls']==0,'native_fixture_unqualified')
    require(rec['scenario'] in ('normal','provider-limit','upstream-disconnect'),'unsupported_fixture_scenario')
    home=fixture/'profile';paths=[home/'state.db',home/'runs_idempotency.db',home/'config.yaml',rp,fixture/'input.txt']
    before={p.relative_to(fixture).as_posix():digest(p) for p in paths}
    original_files={p.relative_to(fixture).as_posix():digest(p) for p in home.glob('*') if p.is_file()}
    cfg=read(home/'config.yaml');settings=cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON');epoch,instance=db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        captures=[_load(v) for v, in db.execute('SELECT value FROM state_meta WHERE key GLOB ?',(PREFIX+'*',))]
    context=LocalRecoveryContext(home,cfg['platforms']['api_server']['key'],epoch,instance)
    policy=ExecutionPolicy(**settings['policy']);observed=rec['client']['final']['run'];rid=observed['run_id']
    with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON');keys=db.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',(context.scope,rid)).fetchall()
    require(len(keys)==1,'fixture_key_ambiguous')
    request={'body':{'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'},'idempotency_key':keys[0][0],'observed':observed}
    inspector=EvidenceViewInspector(context,policy);report=inspector.inspect(**request)
    require(report['reportStatus']=='verified_snapshot','source_report_unverified')
    section=report['evidenceView'];require(section['modelVisibility']=='unknown','model_visibility_invented')
    expected=bool(rec.get('record_source')) and rec['tool_reservations']>0
    source= (fixture/'input.txt').read_bytes()
    if expected:
        require(len(captures)==1 and len(section.get('sourceCaptures',[]))==1,'capture_missing')
        c=captures[0];entry=section['sourceCaptures'][0]
        require(c['sourceBytes']==len(source) and c['sourceSha256']==hashlib.sha256(source).hexdigest(),'source_bytes_mismatch')
        require(c['state']=='returned' and c['runId']==rid and c['admissionId']==observed['admission_id'],'capture_owner_mismatch')
        refs=[r for r in section['references'] if r['kind']=='retained_tool_result']
        require(len(refs)==1 and entry['matchedEvidenceId']==refs[0]['evidenceId'],'output_not_bound')
        ref=refs[0]
        require(ref['originalSource']['sha256']==c['sourceSha256'] and
                ref['content']['sha256']==c['outputSha256'] and ref['content']['utf8Bytes']==c['outputBytes'],'capture_output_mismatch')
        require(ref['originalSource']['coverage']=='captured_snapshot_complete' and ref['originalSource']['toolOutputCoverage']=='unknown','coverage_conflated')
        require(not ref['modelView']['understandingVerified'] and not entry['returnedOutput']['deliveryVerified'],'understanding_or_delivery_invented')
        binding=rec['bindings'][0];require(binding['ticket']==c['ticket'] and binding['inputDigest']==c['sourceSha256'],'isolated_receipt_mismatch')
        require(entry['requestedLines']['limit']==rec.get('read_limit') and entry['requestedLines']['offset'] is None,
                'explicit_pagination_mismatch')
        if rec.get('read_limit') is not None and rec['fixture_lines'] > rec['read_limit']:
            with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
                db.execute('PRAGMA query_only=ON')
                native = [_load(v[0]) for v in db.execute("SELECT content FROM messages WHERE role='tool'")]
            require(len(native)==1 and native[0]['total_lines']==rec['fixture_lines'], 'native_total_lines_mismatch')
            visible = native[0]['content']; limit=rec['read_limit']
            require(('line '+str(limit)+' ışık') in visible and ('line '+str(limit+1)+' ışık') not in visible
                    and ('line '+str(rec['fixture_lines'])+' ışık') not in visible, 'native_read_not_actually_partial')
        selection=EvidenceSelection(ref['evidenceId'],ref['content']['sha256'],0,1)
        projected=inspector.inspect(**request,selection=selection)
        require(projected['evidenceView']['localView']['coverageOfStoredContent']=='partial' and
                projected['evidenceView']['localView']['modelVisibility']=='unknown','partial_visibility_conflated')
    else:
        require(not captures and 'sourceCaptures' not in section,'unexecuted_or_disabled_capture')
        require(all(r['originalSource']['sha256'] is None for r in section['references']),'legacy_source_invented')
        projected=report
    require(all(report[k] is False for k in ('writesPerformed','executionAllowed','retryAllowed','repairAllowed')),'report_granted_authority')
    out.mkdir(parents=True,mode=0o700);private=out/'private';private.mkdir(mode=0o700)
    conf=asdict(context);conf['profile_home']=str(home);conf.pop('profile_name')
    for name,value in [('context',conf),('policy',asdict(policy)),('request',request)]:
        (private/(name+'.json')).write_text(_json(value),encoding='utf-8')
    cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(private/'context.json'),
         '--policy',str(private/'policy.json'),'--request',str(private/'request.json'),'--include-evidence']
    for fmt in ('json','text'):
        result=subprocess.run(cmd+['--format',fmt],capture_output=True,text=True,encoding='utf-8',timeout=20)
        require(result.returncode==0 and not result.stderr,'source_cli_failed')
        if fmt=='json':require(json.loads(result.stdout)==report,'source_cli_disagrees')
        else:require(result.stdout==render_evidence_text(report),'source_text_disagrees')
        require(not any(v and v in result.stdout for v in (context.api_token,settings['provider_bearer'],str(home),str(fixture/'input.txt'),request['idempotency_key'])),'private_data_reflected')
        (out/('report.'+('json' if fmt=='json' else 'txt'))).write_text(result.stdout,encoding='utf-8')
    require(before=={p.relative_to(fixture).as_posix():digest(p) for p in paths},'source_or_main_database_changed')
    after={p.relative_to(fixture).as_posix():digest(p) for p in home.glob('*') if p.is_file()}
    summary={'result':'PASS','scenario':rec['scenario'],'recordSourceEnabled':bool(rec.get('record_source')),
        'nativeReceiptSha256':receipt_sha,'sourceCaptureRows':len(captures),'sourceBytes':len(source),
        'fixtureLines':rec.get('fixture_lines'),'requestedLimit':rec.get('read_limit') if expected else None,
        'storedOutputBytes':[r['content']['utf8Bytes'] for r in section['references'] if r['kind']=='retained_tool_result'],
        'actualPartialReadVerified':expected and rec.get('read_limit') is not None and rec['fixture_lines']>rec['read_limit'],
        'matchedSource':expected,'nativeStatus':observed['status'],'modelVisibility':'unknown','understandingVerified':False,
        'applicationStateUnchanged':True,'sqliteAuxiliaryFilesChanged':[k for k in set(original_files)|set(after) if original_files.get(k)!=after.get(k)],
        'newGatewayRuns':0,'newModelCalls':0,'paidCalls':0,'cliFormatsVerified':['json','text']}
    (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt-sha256',required=True)
    a=p.parse_args();print(json.dumps(verify(a.fixture.resolve(),a.output.resolve(),a.receipt_sha256),indent=2))


if __name__=='__main__':main()
