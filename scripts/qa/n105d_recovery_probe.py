"""Actual pinned native-store crash/replay audit in fresh owned profiles.

Ordinary-user QA, no Gateway/server/provider/mount/repair action. Child process
exit73 deliberately omits Python/native cleanup. Journal modes are observed,
not forced. Native methods and SQLite are NOT mocked. No production admission
is provided by this probe. All imports use their original standard loaders.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
CASES=('before_reserve','before_reservation_commit','reservation_only','queued',
       'started','terminal_gap','terminal_synced','aged_running')
ROOT=Path(__file__).resolve().parents[2]
SCOPE='n105d-owned';KEY='n105d-key';FINGERPRINT='a'*64;SESSION='n105d-session'


def sha(data):return hashlib.sha256(data).hexdigest()


def jsonout(value):
    print(json.dumps(value,sort_keys=True),flush=True)


def native_imports(source, manifest):
    """Validate each original source before its normal import; never rewrite it."""
    seen={}
    class PinnedFinder:
        def find_spec(self,fullname,path=None,target=None):
            spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
            filename=getattr(spec,'origin',None)
            if filename and filename.endswith('.py'):
                file=Path(filename).resolve()
                if file.is_relative_to(source):
                    name=file.relative_to(source).as_posix();data=file.read_bytes()
                    oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                    if manifest.get(name)!=oid:raise ImportError('n105d_source_pin_mismatch:'+name)
                    seen[name]=sha(data)
            return spec
    sys.meta_path.insert(0,PinnedFinder())
    sys.path.insert(0,str(source))
    return seen


def child(args):
    home=args.home.resolve();source=args.source.resolve()
    assert home.parent.name.startswith('alaz-n105d-case-') and home.name=='profile'
    assert (home.parent/'.n105d-owned').read_text()=='disposable-fixture'
    assert os.environ.get('HERMES_HOME')==str(home)
    if sys.platform=='linux':assert os.getuid()==os.geteuid()==23001
    else:assert sys.platform=='win32'
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    assert manifest['pin']==PIN
    imported=native_imports(source,manifest['gitBlobs'])
    blocked=[]
    def audit(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            blocked.append(event)
            raise PermissionError('n105d_external_effect_not_allowed')
    sys.addaudithook(audit)
    from hermes_state import SessionDB
    from hermes_state_runtime import (begin_runtime_epoch,recover_session_inputs,
        admit_session_input,claim_session_input,settle_session_input,get_session_admission,RuntimeStoreError)
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.runtime_ownership import process_ownership
    from gateway.status import get_process_start_time
    def provenance():
        # Only original normal imports, each already checked BEFORE exec_module.
        for name,want in imported.items():assert sha((source/name).read_bytes())==want
        return dict(sorted(imported.items()))
    if args.mode=='fallback':
        missing=home/'does-not-exist'/'runs_idempotency.db'
        assert not missing.parent.exists()
        store=RunIdempotencyStore(str(missing))
        try:
            assert store.durable is False
            assert store._conn.execute('PRAGMA database_list').fetchone()[2]==''
            assert store._conn.execute('SELECT COUNT(*) FROM run_idempotency').fetchone()[0]==0
            result={'result':'OBSERVED_MEMORY_FALLBACK','durable':False,'missingParentUnchanged':not missing.parent.exists(),
                    'reservationsMade':0,'nativeAdmissionImplemented':False,'pid':os.getpid(),'nativeSources':provenance()}
        finally:store.close()
        jsonout(result);return 0
    process_ownership.reserve([home]);db=None;store=None
    try:
        assert process_ownership.owns(home)
        db=SessionDB(home/'state.db');store=RunIdempotencyStore(str(home/'runs_idempotency.db'))
        assert store.durable is True
        assert Path(db._conn.execute('PRAGMA database_list').fetchone()[2]).resolve()==home/'state.db'
        assert Path(store._conn.execute('PRAGMA database_list').fetchone()[2]).resolve()==home/'runs_idempotency.db'
        journals={'state':db._conn.execute('PRAGMA journal_mode').fetchone()[0],
                  'idempotency':store._conn.execute('PRAGMA journal_mode').fetchone()[0]}
        assert set(journals.values()) <= {'delete','wal','persist','truncate'}
        run='n105d-run-'+args.case
        if args.mode=='crash':
            epoch=begin_runtime_epoch(db,instance_id='n105d-first-'+args.case)
            assert epoch==1;db.create_session(SESSION,'api_server')
            state={'case':args.case,'phase':'CRASH_BOUNDARY','pid':os.getpid(),'epoch':epoch,
                   'runId':run,'admissionId':None,'journalModes':journals,'timingInjection':False}
            def die():
                state['nativeSources']=provenance();state['blockedExternalAttempts']=len(blocked)
                jsonout(state);os._exit(73)
            if args.case=='before_reserve':die()
            if args.case=='before_reservation_commit':
                arm={'insert':False}
                def trace(sql):
                    text=sql.lstrip().upper()
                    if text.startswith('INSERT INTO RUN_IDEMPOTENCY'):arm['insert']=True
                    if text=='COMMIT' and arm['insert']:
                        state['timingInjection']=True;die()
                store._conn.set_trace_callback(trace)
            outcome,record=store.reserve(SCOPE,KEY,FINGERPRINT,run,{'status':'running'},
                owner_pid=os.getpid(),owner_started=get_process_start_time(os.getpid()) or 0)
            assert outcome=='created' and not store._conn.in_transaction
            if args.case=='before_reservation_commit':raise AssertionError('commit_trace_not_reached')
            if args.case=='reservation_only':die()
            if args.case=='aged_running':
                now=time.time()
                store._conn.execute('UPDATE run_idempotency SET updated_at=?,retention_until=?',
                                    (now-3*store.RETENTION_SECONDS,now-60));store._conn.commit();die()
            admission=admit_session_input(db,epoch=epoch,principal_id='n105d-principal',session_id=SESSION,
                                         request_id='n105d-request',payload={'text':'inert native-store fixture'})
            state['admissionId']=admission['admission_id'];assert admission['status']=='queued'
            if args.case=='queued':die()
            claimed=claim_session_input(db,epoch=epoch,session_id=SESSION)
            assert claimed['status']=='started' and claimed['admission_id']==admission['admission_id']
            if args.case=='started':die()
            settled=settle_session_input(db,epoch=epoch,admission_id=admission['admission_id'],
                                        generation=claimed['generation'],outcome='completed')
            assert settled['status']=='terminal' and settled['outcome']=='completed'
            if args.case=='terminal_synced':store.update_status(run,{'status':'completed'})
            die()
        prior=json.loads(args.prior.read_text(encoding='utf-8'))
        assert prior['case']==args.case and prior['epoch']==1
        checks={}
        def check(name,value):
            checks[name]=bool(value)
            if not value:raise AssertionError(name)
        check('actual_new_process',os.getpid()!=prior['pid'])
        check('native_profile_lock_reacquired',process_ownership.owns(home))
        check('session_survives_crash',db.get_session(SESSION)['id']==SESSION)
        epoch=begin_runtime_epoch(db,instance_id='n105d-second-'+args.case)
        check('epoch_monotonically_advances',epoch==2)
        recovered=recover_session_inputs(db,epoch=epoch)
        check('only_started_becomes_unknown',recovered==(1 if args.case=='started' else 0))
        check('same_epoch_recovery_idempotent',recover_session_inputs(db,epoch=epoch)==0)
        try:admit_session_input(db,epoch=prior['epoch'],principal_id='n105d-principal',session_id=SESSION,
                               request_id='never-created-stale',payload={'text':'must not write'})
        except RuntimeStoreError as exc:check('old_epoch_refused',exc.reason=='stale_epoch')
        else:check('old_epoch_refused',False)
        check('no_stale_admission_created',db._conn.execute("SELECT COUNT(*) FROM session_admissions WHERE request_id='never-created-stale'").fetchone()[0]==0)
        outcome,record=store.lookup(SCOPE,KEY,FINGERPRINT)
        expect_missing=args.case in ('before_reserve','before_reservation_commit')
        check('reservation_commit_boundary_respected',outcome==('missing' if expect_missing else 'reused'))
        if not expect_missing:
            check('original_run_and_owner_retained',record['run_id']==prior['runId'] and record['owner_pid']==prior['pid'])
            check('status_not_fabricated',record['status']['status']==('completed' if args.case=='terminal_synced' else 'running'))
            reused,replay=store.reserve(SCOPE,KEY,FINGERPRINT,'must-not-be-created',{'status':'queued'},owner_pid=os.getpid())
            check('retry_reuses_original_run',reused=='reused' and replay['run_id']==prior['runId'])
            conflict,conflicted=store.reserve(SCOPE,KEY,'b'*64,'conflicting-run',{'status':'queued'})
            check('changed_request_conflicts',conflict=='conflict' and conflicted['run_id']==prior['runId'])
            check('scope_separation',store.lookup('another-scope',KEY,FINGERPRINT)==('missing',None))
            check('one_reservation_only',store._conn.execute('SELECT COUNT(*) FROM run_idempotency').fetchone()[0]==1)
        else:
            check('uncommitted_reservation_absent',record is None and store._conn.execute('SELECT COUNT(*) FROM run_idempotency').fetchone()[0]==0)
        expected={'queued':'queued','started':'unknown','terminal_gap':'terminal','terminal_synced':'terminal'}.get(args.case)
        admission=get_session_admission(db,admission_id=prior['admissionId']) if prior['admissionId'] else None
        check('native_admission_recovery_exact',(admission['status'] if admission else None)==expected)
        if args.case=='started':
            try:claim_session_input(db,epoch=epoch,session_id=SESSION)
            except RuntimeStoreError as exc:check('unknown_work_not_reclaimed',exc.reason=='unknown_execution')
            else:check('unknown_work_not_reclaimed',False)
        check('real_state_schema',{'runtime_epoch','session_admissions','worker_executions'} <=
              {r[0] for r in db._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
        for label,conn in (('state',db._conn),('idempotency',store._conn)):
            check(label+'_integrity',conn.execute('PRAGMA integrity_check').fetchall()[0][0]=='ok')
        result={'result':'PASS_NATIVE_RECOVERY_CASE','case':args.case,'pid':os.getpid(),'epoch':epoch,
                'checks':checks,'checkCount':len(checks),'recoveredAdmissions':recovered,
                'nativeAdmissionStatus':expected,'idempotencyStatus':record['status']['status'] if record else None,
                'nativeSources':provenance(),'journalModes':journals,'blockedExternalAttempts':len(blocked),
                'gatewayStarted':False,'pairedStoreAtomicityClaimed':False,'providerCalls':0}
    finally:
        if store is not None:store.close()
        if db is not None:db.close()
        process_ownership.close()
    jsonout(result);return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--mode',choices=('main','crash','recover','fallback'),default='main')
    parser.add_argument('--home',type=Path);parser.add_argument('--case',choices=CASES)
    parser.add_argument('--prior',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.mode!='main':return child(args)
    assert args.output is not None and not args.output.exists()
    source=args.source.resolve();manifest=args.manifest.resolve();cases=[]
    before=sha(Path(__file__).read_bytes());base=ROOT/'scratch';base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='alaz-n105d-case-',dir=base) as tmp:
        top=Path(tmp);(top/'.n105d-owned').write_text('disposable-fixture')
        def run(case,mode,prior=None):
            home=top/'profile';home.mkdir(mode=0o700,exist_ok=True)
            env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT')}
            env.update(HOME=str(top),USERPROFILE=str(top),HERMES_HOME=str(home),
                HERMES_TEST_ISOLATION='1',HERMES_GATEWAY_LOCK_DIR=str(top/'locks'),
                TEMP=str(top),TMP=str(top),TMPDIR=str(top),LANG='C.UTF-8')
            cmd=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--source',str(source),
                 '--manifest',str(manifest),'--mode',mode,'--home',str(home)]
            if case:cmd+=['--case',case]
            if prior:cmd+=['--prior',str(prior)]
            p=subprocess.run(cmd,cwd=top,env=env,capture_output=True,timeout=50)
            try:value=json.loads(p.stdout)
            except ValueError:value=None
            result={'exitCode':p.returncode,'stdout':p.stdout.decode('utf-8','replace'),
                    'stderr':p.stderr.decode('utf-8','replace'),'proof':value}
            return result
        for case in CASES:
            # Each case is a completely fresh profile; no state from other cases.
            home=top/'profile'
            if home.exists():
                import shutil
                shutil.rmtree(home)
            first=run(case,'crash');item={'case':case,'crash':first};cases.append(item)
            if first['exitCode']!=73 or first['proof'] is None:break
            prior=top/(case+'.json');prior.write_text(json.dumps(first['proof']),encoding='utf-8')
            item['recover']=run(case,'recover',prior)
            if item['recover']['exitCode']!=0:break
        fallback=run(None,'fallback')
    ok=(len(cases)==len(CASES) and all(c['crash']['exitCode']==73 and
        c.get('recover',{}).get('exitCode')==0 for c in cases) and fallback['exitCode']==0)
    report={'result':'PASS_SCOPED_NATIVE_CRASH_RECOVERY' if ok else 'FAIL',
        'sourcePin':PIN,'platform':sys.platform,'sqliteVersion':sqlite3.sqlite_version,
        'cases':cases,'caseCount':len(cases),'fallback':fallback,
        'probeSha256':before,'probeUnchanged':sha(Path(__file__).read_bytes())==before,
        'temporaryProfileRemoved':not top.exists(),'nativeCodeMocked':False,
        'forcedParentKill':False,'actualConfinement':False,'actualGatewayStarted':False,
        'pairedStoreAtomicRecoveryAccepted':False,'powerLossTested':False,'providerCalls':0}
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    jsonout({'result':report['result'],'cases':len(cases),'failed':[c['case'] for c in cases if c.get('recover',{}).get('exitCode')!=0],
             'sourcePin':PIN,'temporaryProfileRemoved':report['temporaryProfileRemoved']})
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
