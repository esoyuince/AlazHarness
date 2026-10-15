"""Explicit local operator closure of a reservation that never acquired canonical work.

Only an audit receipt and index are inserted in existing state.db/state_meta.
No reservation deletion, admission creation, status rewrite or provider call.
The actual native maintenance lock excludes managed Gateway owners. SQLite locks
cover both stores while revalidating, but only one database is ever written.
"""
from __future__ import annotations
from contextlib import closing,contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from recovery_inspector import LocalRecoveryContext,LocalRecoveryInspector,EvidenceError,_load,_json,request_fingerprint,PIN
from resolution_receipts import ACTION,PREFIX,HEX,HASH,digest,key_digest,run_index,read_resolution,validate_record,assert_no_recorded_work

ROOT=Path(__file__).resolve().parents[2]
PLAN_FIELDS={'planVersion','commandId','action','profileBinding','scopeHash','runId','keyHash','requestFingerprint',
             'epoch','instanceId','snapshotDigest','createdAtMs','expiresAtMs','confirmationDigest'}


class ResolutionError(ValueError):
    """Bounded machine reason; never includes request text, token or private output."""


class OperatorResolution:
    def __init__(self,context: LocalRecoveryContext,*,source_root: Path,clock=time.time):
        if type(context) is not LocalRecoveryContext:raise TypeError('trusted_local_context_required')
        self.context=context;self.source_root=Path(source_root).resolve();self.clock=clock

    def _now(self):
        value=self.clock()
        if type(value) not in (int,float) or not 0<value<10**11:raise ResolutionError('invalid_clock')
        return int(value*1000)

    def _source(self):
        src=self.source_root
        manifest=json.loads((ROOT/'config/operator-resolution/source-lock.json').read_text(encoding='utf-8'))
        if manifest['native_commit']!=PIN:raise ResolutionError('unsupported_native_source')
        try:
            head=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=10).strip()
            dirty=subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True,stderr=subprocess.DEVNULL,timeout=10).strip()
            if head!=PIN or dirty or (src/'.env').exists():raise ResolutionError('unsupported_native_source')
            for row in manifest['files']:
                path=src/row['path']
                if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
                    raise ResolutionError('unsupported_native_source')
        except (OSError,subprocess.SubprocessError):raise ResolutionError('native_source_unavailable') from None
        return src

    @contextmanager
    def _maintenance(self):
        src=self._source()
        # Caller must use the isolated prepared interpreter; no implicit environment activation.
        for name in ('gateway','gateway.runtime_ownership','gateway.status'):
            if name in sys.modules:
                origin=getattr(sys.modules[name],'__file__',None)
                if not origin or not Path(origin).resolve().is_relative_to(src):raise ResolutionError('foreign_native_module')
        sys.path.insert(0,str(src))
        try:
            ownership=importlib.import_module('gateway.runtime_ownership')
            status=importlib.import_module('gateway.status')
            if not Path(ownership.__file__).resolve().is_relative_to(src) or not Path(status.__file__).resolve().is_relative_to(src):
                raise ResolutionError('foreign_native_module')
            try:
                with ownership.exclusive_maintenance([self.context.profile_home]):
                    yield status
            except ownership.OwnershipConflict:raise ResolutionError('gateway_or_maintenance_active') from None
        finally:
            if sys.path and sys.path[0]==str(src):sys.path.pop(0)

    @contextmanager
    def _connection(self,write):
        paths=LocalRecoveryInspector(self.context)._paths()
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in paths]
        mode='rw' if write else 'ro'
        with closing(sqlite3.connect(paths[0].as_uri()+'?mode='+mode,uri=True,timeout=2,isolation_level=None)) as conn:
            conn.row_factory=sqlite3.Row
            conn.execute('ATTACH DATABASE ? AS replay',(paths[1].as_uri()+'?mode='+mode,))
            conn.execute('PRAGMA trusted_schema=OFF')
            if not write:conn.execute('PRAGMA query_only=ON')
            required=[('main','runtime_epoch'),('main','session_admissions'),('main','state_meta'),
                      ('main','sessions'),('main','messages'),('main','worker_executions'),('replay','run_idempotency')]
            for schema,name in required:
                found=conn.execute(f'SELECT type FROM {schema}.sqlite_master WHERE name=?',(name,)).fetchone()
                if found is None or found[0]!='table':raise ResolutionError('unsupported_schema')
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name='state_meta'").fetchone():
                raise ResolutionError('unsupported_state_meta_trigger')
            if write:
                # Single-written-database transaction. No journal-mode migration is performed.
                if conn.execute('PRAGMA main.journal_mode').fetchone()[0].lower() not in ('delete','truncate','persist','wal'):
                    raise ResolutionError('unsupported_journal')
                conn.execute('PRAGMA main.synchronous=FULL')
            conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            try:
                epoch=conn.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
                if epoch is None or tuple(epoch)!=(self.context.epoch,self.context.instance_id):raise ResolutionError('stale_epoch')
                if identities!=[(p.stat().st_dev,p.stat().st_ino) for p in paths]:raise ResolutionError('store_replaced')
                yield conn,paths,identities
                # All write callers explicitly commit before returning.
            finally:
                if conn.in_transaction:conn.rollback()

    def _inputs(self,body,key,observed):
        try:
            body=_load(_json(body),131072);observed=_load(_json(observed))
            fingerprint=request_fingerprint(body)
            if 'session_id' in body:raise ResolutionError('explicit_session_resolution_unsupported')
            if not isinstance(key,str) or not __import__('re').fullmatch(r'[\x21-\x7e]{1,255}',key):raise ResolutionError('invalid_key')
            if type(observed) is not dict or not isinstance(observed.get('run_id'),str) or not __import__('re').fullmatch(r'run_[a-f0-9]{32}',observed['run_id']):
                raise ResolutionError('invalid_run')
        except (EvidenceError,TypeError,ValueError,RecursionError) as exc:
            if isinstance(exc,ResolutionError):raise
            raise ResolutionError('invalid_resolution_input') from None
        return body,fingerprint,observed

    def _reservation(self,conn,key,fingerprint,observed):
        rows=conn.execute('SELECT * FROM replay.run_idempotency WHERE scope=? AND idempotency_key=? LIMIT 2',(self.context.scope,key)).fetchall()
        if len(rows)!=1:raise ResolutionError('lookup_unavailable')
        row=dict(rows[0])
        if row['fingerprint']!=fingerprint:raise ResolutionError('request_payload_conflict')
        if row['run_id']!=observed['run_id']:raise ResolutionError('run_identity_mismatch')
        saved=_load(row['status_json'])
        if type(saved) is not dict or saved.get('run_id')!=row['run_id']:raise ResolutionError('invalid_reservation')
        LocalRecoveryInspector(self.context,clock=self.clock)._retention(row,saved)
        return row,saved

    def _capture(self,conn,body,key,fingerprint,observed):
        row,saved=self._reservation(conn,key,fingerprint,observed);rid=row['run_id']
        if saved.get('status')!='interrupted' or observed.get('status')!='interrupted' or observed.get('admission_id') is not None:
            raise ResolutionError('not_an_unadmitted_reservation')
        assert_no_recorded_work(conn,rid,_load)
        from recovery_inspector import IDENTITY,_KEYS
        identity=IDENTITY+_KEYS.admission_fingerprint(canonical_target=rid,payload={'principal':'api','request':rid})
        if conn.execute('SELECT 1 FROM state_meta WHERE key=?',(identity,)).fetchone():raise ResolutionError('retired_work_exists')
        if read_resolution(conn,context=self.context,reservation=row,run_id=rid,decode=_load) is not None:
            raise ResolutionError('reservation_already_closed')
        # Context and full raw reservation are hashed; no key/token/body appears in the plan.
        snapshot={'reservation':row,'epoch':self.context.epoch,'instanceId':self.context.instance_id,
                  'canonicalAdmissionAbsent':True,'relatedSessionAbsent':True,'retiredIdentityAbsent':True}
        return row,digest(snapshot)

    def prepare(self,*,body,idempotency_key,observed,command_id):
        self._source()
        if not isinstance(command_id,str) or not HEX.fullmatch(command_id):raise ResolutionError('invalid_command_id')
        body,fingerprint,observed=self._inputs(body,idempotency_key,observed)
        try:
            with self._connection(False) as (conn,_,__):
                if conn.execute('SELECT 1 FROM state_meta WHERE key=?',(PREFIX+command_id,)).fetchone():raise ResolutionError('command_already_recorded')
                _,snapshot=self._capture(conn,body,idempotency_key,fingerprint,observed)
            now=self._now()
            plan={'planVersion':1,'commandId':command_id,'action':ACTION,'profileBinding':self.context.binding,
                  'scopeHash':self.context.scope,'runId':observed['run_id'],'keyHash':key_digest(idempotency_key),
                  'requestFingerprint':fingerprint,'epoch':self.context.epoch,'instanceId':self.context.instance_id,
                  'snapshotDigest':snapshot,'createdAtMs':now,'expiresAtMs':now+300000}
            plan['confirmationDigest']=digest(plan);return plan
        except ResolutionError:raise
        except (OSError,sqlite3.Error):raise ResolutionError('storage_unavailable') from None
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError):raise ResolutionError('malformed_evidence') from None

    def _plan(self,plan,confirmation,body,key,observed):
        try:
            plan=_load(_json(plan),16384)
            if type(plan) is not dict or set(plan)!=PLAN_FIELDS:raise ResolutionError('invalid_plan')
            if type(plan['planVersion']) is not int or plan['planVersion']!=1 or plan['action']!=ACTION:raise ResolutionError('unsupported_action')
            if not isinstance(plan['commandId'],str) or not HEX.fullmatch(plan['commandId']):raise ResolutionError('invalid_command_id')
            for name in ('profileBinding','scopeHash','keyHash','requestFingerprint','snapshotDigest','confirmationDigest'):
                if not isinstance(plan[name],str) or not HASH.fullmatch(plan[name]):raise ResolutionError('invalid_plan')
            if not isinstance(confirmation,str) or confirmation!=plan['confirmationDigest'] or confirmation!=digest({k:v for k,v in plan.items() if k!='confirmationDigest'}):
                raise ResolutionError('explicit_confirmation_required')
            if (plan['profileBinding'],plan['scopeHash'],plan['keyHash'],plan['requestFingerprint'],plan['runId'])!=(
                 self.context.binding,self.context.scope,key_digest(key),request_fingerprint(body),observed['run_id']):
                raise ResolutionError('plan_identity_mismatch')
            for name in ('epoch','createdAtMs','expiresAtMs'):
                if type(plan[name]) is not int or plan[name]<=0:raise ResolutionError('invalid_plan')
            if not isinstance(plan['instanceId'],str) or not plan['instanceId'] or len(plan['instanceId'])>1024:raise ResolutionError('invalid_plan')
            if plan['expiresAtMs']-plan['createdAtMs']!=300000:raise ResolutionError('invalid_plan_window')
            return plan
        except ResolutionError:raise
        except (ValueError,TypeError,KeyError,RecursionError):raise ResolutionError('invalid_plan') from None

    def apply(self,*,plan,confirmation,body,idempotency_key,observed):
        body,fingerprint,observed=self._inputs(body,idempotency_key,observed)
        plan=self._plan(plan,confirmation,body,idempotency_key,observed)
        try:
            with self._maintenance() as native_status:
                with self._connection(True) as (conn,paths,identities):
                    reservation,saved=self._reservation(conn,idempotency_key,fingerprint,observed)
                    previous=conn.execute('SELECT value FROM state_meta WHERE key=?',(PREFIX+plan['commandId'],)).fetchone()
                    if previous is not None:
                        record=validate_record(_load(previous[0]),context=self.context,reservation=reservation,run_id=observed['run_id'])
                        index=read_resolution(conn,context=self.context,reservation=reservation,run_id=observed['run_id'],decode=_load)
                        if index!=record or record['planDigest']!=plan['confirmationDigest']:raise ResolutionError('command_identity_conflict')
                        # Replaying an audit receipt is not permission to ignore new work.
                        assert_no_recorded_work(conn,observed['run_id'],_load)
                        if saved.get('status')!='interrupted' or observed.get('status')!='interrupted' or observed.get('admission_id') is not None:
                            raise ResolutionError('resolution_state_conflict')
                        return self._answer(record,False)
                    if (plan['epoch'],plan['instanceId'])!=(self.context.epoch,self.context.instance_id):raise ResolutionError('stale_plan_epoch')
                    now=self._now()
                    if not plan['createdAtMs']<=now<plan['expiresAtMs']:raise ResolutionError('confirmation_expired')
                    reservation,snapshot=self._capture(conn,body,idempotency_key,fingerprint,observed)
                    if snapshot!=plan['snapshotDigest']:raise ResolutionError('snapshot_changed')
                    # This is stricter than native PID-reuse matching: any live old PID refuses.
                    pid=reservation['owner_pid']
                    if type(pid) is not int or pid<=0:raise ResolutionError('unproven_old_owner')
                    if native_status._pid_exists(pid):raise ResolutionError('previous_owner_present')
                    record={'receiptVersion':1,'commandId':plan['commandId'],'action':ACTION,
                       'profileBinding':self.context.binding,'scopeHash':self.context.scope,'runId':observed['run_id'],
                       'keyHash':plan['keyHash'],'requestFingerprint':fingerprint,'epoch':self.context.epoch,
                       'instanceId':self.context.instance_id,'snapshotDigest':snapshot,
                       'planDigest':plan['confirmationDigest'],'recordedAtMs':now}
                    record['recordDigest']=digest(record)
                    conn.execute('INSERT INTO state_meta(key,value) VALUES(?,?)',(PREFIX+record['commandId'],_json(record)))
                    conn.execute('INSERT INTO state_meta(key,value) VALUES(?,?)',(run_index(self.context.scope,observed['run_id']),_json(record['commandId'])))
                    if identities!=[(p.stat().st_dev,p.stat().st_ino) for p in paths]:raise ResolutionError('store_replaced')
                    conn.commit()
                    return self._answer(record,True)
        except ResolutionError:raise
        except (OSError,sqlite3.Error):raise ResolutionError('storage_or_commit_unconfirmed') from None
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError):raise ResolutionError('malformed_evidence') from None

    @staticmethod
    def _answer(record,changed):
        return {'resolutionVersion':1,'status':'recorded' if changed else 'already_recorded',
                'receipt':record,'writesPerformed':changed,'stateMetaRowsAdded':2 if changed else 0,
                'requestClosed':True,'taskSucceeded':False,'retryAllowed':False,'repairAllowed':False,
                'admissionCreated':False,'reservationDeleted':False,'modelCalls':0}
