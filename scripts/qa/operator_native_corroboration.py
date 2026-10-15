"""Independently read retained current operator Gateway proofs. No new native run or mutation."""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryInspector,LocalRecoveryContext
from resolution_receipts import PREFIX,INDEX


def inspect(base):
    checked=[]
    expected={'after-reserve':'reservation_abandoned_verified','completed':'canonical_terminal_verified','before-model':'execution_unknown'}
    for scenario,wanted in expected.items():
        case=base/('final-'+scenario);path=case/'operator-probe.json';raw=path.read_bytes();r=json.loads(raw)
        if r['result']!='PASS' or r['errors'] or r['scenario']!=scenario:raise ValueError('Unaccepted native fixture')
        for name,digest in r['code_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Native proof source mismatch '+name)
        for stage,key in [('first','native_first_exit'),('second','native_second_exit')]+([('third','third_exit')] if scenario=='after-reserve' else []):
            on_disk=json.loads((case/stage/'exit-observation.json').read_text(encoding='utf-8'))
            if on_disk!=r[key] or not on_disk['native_reaped'] or not on_disk['launcher_reaped']:raise ValueError('Native exit proof mismatch')
            if stage=='first':
                if not on_disk['hard_kill'] or on_disk['exit_code']==0:raise ValueError('No actual initial crash')
            elif on_disk['exit_code']!=0 or on_disk['shutdown']['native_result'] is not True:raise ValueError('No native shutdown')
        private=case/'operator-local';context=json.loads((private/'context.json').read_text(encoding='utf-8'));query=json.loads((private/'request.json').read_text(encoding='utf-8'))
        home=case/'profile'
        if Path(context['profile_home']).resolve()!=home.resolve():raise ValueError('Wrong local context')
        files=[p for p in home.iterdir() if p.name.endswith(('.db','-wal','-shm','-journal'))]
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        result=LocalRecoveryInspector(LocalRecoveryContext(**context)).inspect(**query)
        if result['classification']!=wanted or result['retryAllowed'] is not False:raise ValueError('Wrong classification')
        if result['taskSucceeded'] is not (scenario=='completed'):raise ValueError('Task outcome confused with closure')
        with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
            db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('State integrity')
            admissions=[dict(x) for x in db.execute('SELECT admission_id,request_id,status,outcome FROM session_admissions')]
            tools=[dict(x) for x in db.execute("SELECT tool_name,content FROM messages WHERE role='tool'")]
            users=[x[0] for x in db.execute("SELECT content FROM messages WHERE role='user'")]
            records=[(x['key'],x['value']) for x in db.execute('SELECT key,value FROM state_meta WHERE key GLOB ?',(PREFIX+'*',))]
            indexes=[(x['key'],x['value']) for x in db.execute('SELECT key,value FROM state_meta WHERE key GLOB ?',(INDEX+'*',))]
        with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True)) as db:
            db.execute('PRAGMA query_only=ON')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Replay integrity')
            replay=db.execute('SELECT run_id,status_json FROM run_idempotency').fetchall()
        if len(replay)!=1 or replay[0][0]!=query['observed']['run_id']:raise ValueError('Replay identity')
        marker=(case/'input.txt').read_text(encoding='utf-8').splitlines()[0]
        if any(marker in str(u) for u in users):raise ValueError('Marker was in prompt')
        if scenario=='after-reserve':
            if admissions or tools or users or len(records)!=1 or len(indexes)!=1:raise ValueError('Wrong closure side effects')
            record=json.loads(records[0][1]);pointer=json.loads(indexes[0][1])
            if pointer!=record['commandId'] or record!=r['applied']['value']['receipt'] or record!=r['repeated']['value']['receipt']:raise ValueError('Receipt replay identity')
            if record!=r['new_epoch_replay']['value']['receipt']:raise ValueError('Receipt lost across native owner epoch')
            if r['active_owner_refusal']['value']['reason']!='gateway_or_maintenance_active':raise ValueError('Active owner not excluded')
            if r['native_same_key_replay']['run_id']!=replay[0][0] or r['native_same_key_replay']['replayed'] is not True:raise ValueError('Replay key lost')
        else:
            if records or indexes or len(admissions)!=1 or len(users)!=1:raise ValueError('Refusal changed audit state')
            if r['preview']['exit_code']!=2:raise ValueError('Protected work not refused')
            if scenario=='completed':
                if len(tools)!=1 or tools[0]['tool_name']!='read_file' or marker not in tools[0]['content'] or admissions[0]['outcome']!='completed':raise ValueError('Completed tool proof')
            elif tools or admissions[0]['status']!='unknown':raise ValueError('Unknown execution was changed')
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        if after!=before or r['new_model_http_calls']!=0:raise ValueError('Unexpected mutation or inference')
        checked.append({'scenario':scenario,'classification':result['classification'],'canonical_admissions':len(admissions),'tool_results':len(tools),'operator_receipts':len(records),'operator_indexes':len(indexes),'new_model_requests':0,'profile_bytes_unchanged':True,'source_receipt_sha256':hashlib.sha256(raw).hexdigest(),'result':'CORROBORATED'})
    return {'scope':'retrospective readonly corroboration of THREE existing final primary native operator runs, not new executions','count':len(checked),'checks':checked,'new_gateway_processes':0,'model_calls':0,'result':'PASS'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve();runtime=(a.source_workspace.resolve()/'runtime').resolve()
    if out.exists() or not out.is_relative_to(runtime):raise ValueError('New private runtime output required')
    result=inspect(runtime/'hyb004c-4cff');out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
