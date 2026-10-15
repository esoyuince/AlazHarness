"""Independent read-only native records and fail-closed integration receipt checks."""
from __future__ import annotations
from contextlib import closing
import json
import re
from pathlib import Path
import sqlite3

CHECKS={
 'normal':['real-tool-result','duplicate-same-id','changed-payload-409','read-only-resume','unauthorized-401'],
 'lost-ack':['lost-ack-is-unknown-not-failure','real-tool-result','duplicate-same-id','changed-payload-409','read-only-resume','unauthorized-401'],
 'stop':['stop-request-reached-native','terminal-stop-separately-confirmed','duplicate-same-id','changed-payload-409','read-only-resume','unauthorized-401'],
}

def database_evidence(home: Path, final: dict, marker: str) -> dict:
    run_id=final['run_id'];session=final['session_id']
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        admissions=[dict(row) for row in db.execute('SELECT admission_id,request_id,target_session_id,status,outcome,owner_epoch,generation FROM session_admissions LIMIT 3')]
        messages=[dict(row) for row in db.execute('SELECT role,tool_call_id,tool_name,content FROM messages WHERE session_id=? LIMIT 100',(session,))]
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        journal=db.execute('PRAGMA journal_mode').fetchone()[0]
    with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.row_factory=sqlite3.Row
        runs=[dict(row) for row in db.execute('SELECT run_id FROM run_idempotency LIMIT 3')]
    tools=[m for m in messages if m['role']=='tool']
    return {'read_only':True,'after_process_exit':True,'integrity':integrity,'journal_mode':journal,
            'admissions':admissions,'run_records':runs,'user_messages':sum(m['role']=='user' for m in messages),
            'tool_results':len(tools),'tool_names':[m['tool_name'] for m in tools],
            'tool_contains_marker':len(tools)==1 and marker in (tools[0]['content'] or ''),
            'assistant_contains_marker':any(m['role']=='assistant' and marker in (m['content'] or '') for m in messages)}

def validate(report: dict) -> list[str]:
    try:
        errors=[];scenario=report['scenario'];ready=report['ready'];client=report['client'];db=report['database'];final=client['final']
        if scenario not in CHECKS:return ['unknown scenario']
        if not isinstance(report['nonce'],str) or not re.fullmatch(r'[0-9a-f]{32}',report['nonce']):errors.append('invalid nonce')
        for key in ('client_exit','child_exit','launcher_pid'):
            if type(report.get(key)) is not int:errors.append('invalid integer '+key)
        if type(ready.get('pid')) is not int or ready['pid']<=0 or type(ready.get('epoch')) is not int or ready['epoch']<=0:errors.append('invalid native identity')
        for key in ('user_messages','tool_results'):
            if type(db.get(key)) is not int:errors.append('invalid independent counter')
        if client.get('nonce')!=report['nonce'] or ready.get('nonce')!=report['nonce']:errors.append('identity mismatch')
        if client.get('scenario')!=scenario or client.get('result')!='PASS' or client.get('checks')!=CHECKS[scenario]:errors.append('client assertions missing')
        if ready.get('runner')!='gateway.run.GatewayRunner' or ready.get('adapter')!='gateway.platforms.api_server.APIServerAdapter' or ready.get('authority')!='gateway.session_authority.SessionAuthority':errors.append('not native runtime')
        if ready.get('state')!='ready' or ready.get('profile_bound') is not True or ready.get('api_host')!='127.0.0.1':errors.append('unqualified readiness')
        if report.get('child_exit')!=0 or report.get('client_exit')!=0 or report.get('child_reaped') is not True or report.get('gateway_reaped') is not True:errors.append('unclean child lifetime')
        chain=report.get('ownership_chain',[])
        if not chain or chain[0]!=ready.get('pid') or chain[-1]!=report.get('launcher_pid'):errors.append('unowned process')
        shutdown=report.get('shutdown',{})
        if shutdown.get('nonce')!=report['nonce'] or shutdown.get('pid')!=ready['pid'] or shutdown.get('native_result') is not True or shutdown.get('lifecycle_completed') is not True:errors.append('no native shutdown proof')
        if db.get('read_only') is not True or db.get('after_process_exit') is not True or db.get('integrity')!='ok':errors.append('no independent store proof')
        if len(db['admissions'])!=1 or len(db['run_records'])!=1:return errors+['duplicate/missing native admission']
        row=db['admissions'][0]
        if (row['request_id'],row['target_session_id'],row['admission_id'],row['owner_epoch'],row['generation'])!=(client['run_id'],final['session_id'],final['admission_id'],ready['epoch'],final['execution_generation']):errors.append('native identity mismatch')
        if row['status']!='terminal' or db['run_records'][0]['run_id']!=client['run_id']:errors.append('unsettled/mismatched run')
        if db['user_messages']!=1:errors.append('input duplicated')
        calls=report['model_calls']
        if scenario=='stop':
            if final.get('status') not in ('cancelled','interrupted') or row['outcome'] not in ('cancelled','interrupted'):errors.append('native stop not confirmed')
            if db['tool_results']!=0 or len(calls)!=1:errors.append('work after stop')
        else:
            if final.get('status')!='completed' or row['outcome']!='completed':errors.append('native completion absent')
            if db['tool_results']!=1 or db['tool_names']!=['read_file'] or db['tool_contains_marker'] is not True or db['assistant_contains_marker'] is not True:errors.append('no actual tool/transcript proof')
            if len(calls)!=2 or calls[0].get('tool_result') is not False or calls[1].get('tool_result') is not True:errors.append('unexpected model chain')
        if scenario=='lost-ack':
            relay=report.get('relay',{})
            if relay.get('dropped_run')!=client['run_id'] or client.get('lost_error')!='write_outcome_unknown' or client['admission'].get('replayed') is not True:errors.append('lost acknowledgement not proved')
        if report.get('fixture_errors') or report.get('source_or_program_drift') is not False:errors.append('fixture/drift failure')
        for key in ('model_inference_calls','paid_calls'):
            if type(report.get(key)) is not int or report[key]!=0:errors.append('unexpected inference')
        return errors
    except (KeyError,TypeError,IndexError,AttributeError):return ['malformed evidence']
