"""P107A independent native constructor side-effect challenge.

Only fresh owned test profiles. Mutations deliberately simulate incomplete
metadata; never apply to a personal/production or preexisting lab profile.
No upstream methods patched, no model/network/root/full projection claim.
"""
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
CASES=('untouched','old_version','fts_stale','missing_backfill')


def guard():
    assert sys.platform=='linux' and os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    assert ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-p107a-native-')
    assert os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
    m=json.loads((ROOT/'manifest.json').read_text())
    assert m['pin']==PIN and all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in m['files'].items())
    return m


def child(case):
    m=guard();home=ROOT/'profiles'/case
    assert case in CASES and home.exists() and not (home/'state.db').exists()
    os.environ['HERMES_HOME']=str(home);os.umask(0o077)
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','socket.bind','subprocess.Popen','os.system'):
            raise PermissionError('p107a_offline_fixture')
    sys.addaudithook(audit)
    sys.path[:0]=[str(ROOT/'vendor-native'),str(ROOT/'dependencies'),str(ROOT/'packages/claw-hermes')]
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway import runtime_ownership as ownership
    import gateway_live_store_gate as live
    import gateway_constructor_metadata as markers
    ownership.process_ownership.reserve([home])
    state=SessionDB(home/'state.db');replay=RunIdempotencyStore(str(home/'runs_idempotency.db'))
    assert replay.durable is True
    replay.close();state.close()
    path=home/'state.db'
    def snap():
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        db=sqlite3.connect(path.as_uri()+'?mode=ro&cache=private',uri=True,isolation_level=None)
        try:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
            result={'schemaSha256':live.schema_digest(db),'schemaVersion':db.execute('SELECT version FROM main.schema_version').fetchall(),
                'applicationId':db.execute('PRAGMA main.application_id').fetchone()[0],
                'storeInstanceId':db.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0],
                'epochs':db.execute('SELECT epoch,instance_id FROM main.runtime_epoch').fetchall(),
                'migrationMarkers':db.execute("SELECT key,value FROM main.state_meta WHERE key IN ('fts_stale','message_uid_backfill','fts_rebuild_high_water','fts_optimize_available') ORDER BY key").fetchall(),
                'ftsTriggerCount':db.execute("SELECT count(*) FROM main.sqlite_schema WHERE type='trigger' AND name LIKE '%fts%'").fetchone()[0],
                'bytesSha256':before,'inode':path.stat().st_ino}
            try:
                observation=markers.verify_constructor_metadata(db,native_pin=PIN)
                result['markerGate']={'accepted':True,'receipt':observation}
            except markers.ConstructorMetadataRejected as exc:
                result['markerGate']={'accepted':False,'reason':str(exc)}
            result['observerTotalChanges']=db.total_changes
        finally:db.close()
        assert before==hashlib.sha256(path.read_bytes()).hexdigest(),'readonly_probe_mutated_input'
        return result
    initial=snap()
    if case!='untouched':
        db=sqlite3.connect(path)
        try:
            if case=='old_version':db.execute('UPDATE main.schema_version SET version=30')
            elif case=='fts_stale':db.execute("INSERT OR REPLACE INTO main.state_meta(key,value) VALUES('fts_stale','1')")
            elif case=='missing_backfill':db.execute("DELETE FROM main.state_meta WHERE key='message_uid_backfill'")
            db.commit()
        finally:db.close()
    before=snap()
    # Native writable opening is intentional ONLY in this fresh owned fixture,
    # to measure why an earlier pre-constructor qualifier is required.
    opened=None;failure=None
    try:
        opened=SessionDB(path)
        flags={'ftsStale':opened._fts_stale,'ftsEnabled':opened._fts_enabled}
    except Exception as exc:
        failure={'type':type(exc).__name__,'reason':str(exc)[:200]};flags={}
    finally:
        if opened is not None:opened.close()
    after=snap();ownership.process_ownership.close()
    assert initial['markerGate']['accepted'] is True
    assert before['markerGate']['accepted'] is (case=='untouched')
    expected={'old_version':'constructor_metadata_schema_version','fts_stale':'constructor_metadata_repair_pending','missing_backfill':'constructor_metadata_backfill_incomplete'}
    if case in expected:assert before['markerGate']['reason']==expected[case]
    assert after['markerGate']['accepted'] is True
    assert all(s['observerTotalChanges']==0 for s in (initial,before,after))
    imported={}
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            p=Path(filename).resolve()
            if p.suffix=='.py' and p.is_relative_to(ROOT):
                name=p.relative_to(ROOT).as_posix();h=hashlib.sha256(p.read_bytes()).hexdigest();assert m['files'].get(name)==h
                imported[name]=h
    keys=('schemaSha256','schemaVersion','applicationId','storeInstanceId','epochs','inode')
    print(json.dumps({'case':case,'initial':initial,'beforeWritableConstructor':before,'afterWritableConstructor':after,
        'preopenIdentityAndSchemaEqualToInitial':all(initial[k]==before[k] for k in keys),
        'constructorChangedBytes':before['bytesSha256']!=after['bytesSha256'],
        'constructorChangedSchema':before['schemaSha256']!=after['schemaSha256'],
        'constructorFailure':failure,'nativeFlags':flags,'sourceHashes':imported,
        'nativePin':PIN,'nativeMethodsReplaced':False,'ownedMutationOnly':True,'profileReleased':not ownership.process_ownership.homes}),flush=True)


def main():
    m=guard()
    if len(sys.argv)==2:return child(sys.argv[1])
    (ROOT/'profiles').mkdir(mode=0o700)
    events=[]
    for case in CASES:
        home=ROOT/'profiles'/case;home.mkdir(mode=0o700)
        env={'PATH':'/usr/bin:/bin','HOME':str(home),'HERMES_HOME':str(home),'LANG':'C.UTF-8','WSL_DISTRO_NAME':'AlazHarness-D3B-P71C'}
        r=subprocess.run([sys.executable,'-I','-B',str(Path(__file__)),case],cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
        events.append({'case':case,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode:break
    result={'result':'OBSERVATIONS_COMPLETE' if len(events)==4 and all(r['exitCode']==0 for r in events) else 'FAIL',
        'events':events,'manifest':m,'sourcesUnchanged':all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in m['files'].items()),
        'candidatePreopenGateRun':False,'rootUsed':False,'modelCalls':0,'providerCalls':0,'fullGatewayRun':False}
    print(json.dumps(result),flush=True)
    return 0 if result['result']=='OBSERVATIONS_COMPLETE' else 1
if __name__=='__main__':raise SystemExit(main())
