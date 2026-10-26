"""HYB-005A: durable at-most-one handoff through the existing native SessionDB.

This stores dispatch intent, NOT a second queue/transcript or an execution result.
A consumed intent never becomes dispatchable again, even if the response is lost.
Native code may reject the handoff; a consumed intent does not imply acceptance.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid
from recovery_inspector import LocalRecoveryContext, request_fingerprint, _load, _json, RUN
from resolution_receipts import PREFIX as CLOSURE, key_digest, digest

ROOT='alaz.host_gate.config.v1.'
INTENT='alaz.host_gate.intent.v1.'
ID=re.compile(r'[a-f0-9]{32}\Z')
KEY=re.compile(r'ah1-([a-f0-9]{32})-([a-f0-9]{32})\Z')
STATES={'issued','consumed'}

class HostGateError(ValueError):
    """Only a bounded code; never contains input, authentication or private output."""

@dataclass(frozen=True)
class HostGatePolicy:
    allowed_models: frozenset[str]
    max_issued: int = 64
    max_dispatches: int = 8
    validity_seconds: int = 300
    def __post_init__(self):
        if type(self.allowed_models) is not frozenset or not self.allowed_models or any(type(x) is not str or not x.strip() or len(x)>200 for x in self.allowed_models):
            raise ValueError('invalid_model_allowlist')
        for key,limit in [('max_issued',10000),('max_dispatches',10000),('validity_seconds',3600)]:
            v=getattr(self,key)
            if type(v) is not int or not 1<=v<=limit:raise ValueError('invalid_gate_policy')

class HostGateLedger:
    def __init__(self, db, context: LocalRecoveryContext, policy: HostGatePolicy, *, clock=time.time, admission_guard=None):
        if type(context) is not LocalRecoveryContext or type(policy) is not HostGatePolicy:raise TypeError('trusted_host_context_required')
        if not callable(getattr(db,'_execute_write',None)) or Path(db.db_path).is_symlink() or Path(db.db_path).resolve()!=context.profile_home/'state.db':raise ValueError('wrong_native_database')
        if admission_guard is not None and not callable(admission_guard):raise TypeError('trusted_admission_guard_required')
        self.db=db;self.context=context;self.policy=policy;self.clock=clock
        self._admission_guard=admission_guard
    def _now(self):
        n=self.clock()
        if type(n) not in (float,int) or not 0<n<10**11:raise HostGateError('invalid_clock')
        return int(n*1000)
    def _identity(self, request_id):
        if type(request_id) is not str or not ID.fullmatch(request_id):raise HostGateError('invalid_request_id')
        return INTENT+self.context.scope+'.'+request_id
    def _body(self, body):
        try:
            frozen=_load(_json(body),131072)
            if type(frozen) is not dict or set(frozen)!={'input','model'}:raise HostGateError('explicit_model_and_new_input_required')
            fp=request_fingerprint(frozen)
            if frozen['model'] not in self.policy.allowed_models:raise HostGateError('model_not_allowed')
            return frozen,fp
        except HostGateError:raise
        except (ValueError,TypeError,RecursionError,UnicodeError):raise HostGateError('invalid_request') from None
    def _epoch(self,conn):
        row=conn.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        if row is None or tuple(row)!=(self.context.epoch,self.context.instance_id):raise HostGateError('stale_owner_epoch')
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name='state_meta'").fetchone():raise HostGateError('unsupported_state_trigger')
    def _get(self,conn,key):
        row=conn.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()
        if row is None:return None
        value=_load(row[0],16384)
        if type(value) is not dict:raise HostGateError('malformed_gate_record')
        return value
    def _configuration(self,conn,create=False):
        key=ROOT+self.context.scope;c=self._get(conn,key)
        if c is None:
            if not create:raise HostGateError('unknown_host_namespace')
            if conn.execute('SELECT 1 FROM state_meta WHERE key GLOB ? LIMIT 1',(INTENT+self.context.scope+'.*',)).fetchone():raise HostGateError('missing_host_namespace')
            c={'version':1,'namespace':uuid.uuid4().hex,'profileBinding':self.context.binding,'scope':self.context.scope,'issued':0,'spent':0}
        if type(c) is not dict or set(c)!={'version','namespace','profileBinding','scope','issued','spent'} or type(c['version']) is not int or c['version']!=1 or type(c['namespace']) is not str or not ID.fullmatch(c['namespace']):raise HostGateError('invalid_gate_configuration')
        if c['profileBinding']!=self.context.binding or c['scope']!=self.context.scope:raise HostGateError('foreign_gate_configuration')
        if any(type(c[k]) is not int or not 0<=c[k]<=10000 for k in ['issued','spent']) or c['spent']>c['issued']:raise HostGateError('invalid_gate_counters')
        # A missing/pruned intent is not evidence of a never-sent request. The
        # namespace counters and retained rows must agree in THIS native write.
        issued=spent=bytes_seen=0
        prefix=INTENT+self.context.scope+'.'
        for stored_key,encoded in conn.execute('SELECT key,value FROM state_meta WHERE key GLOB ? LIMIT 10001',(prefix+'*',)):
            issued+=1
            if issued>10000 or type(encoded) is not str:raise HostGateError('intent_history_unverified')
            bytes_seen+=len(encoded.encode('utf-8'))
            if bytes_seen>16777216:raise HostGateError('intent_history_unverified')
            request_id=stored_key[len(prefix):]
            self._identity(request_id)
            row=self._validate(_load(encoded,16384),request_id)
            if KEY.fullmatch(row['key'])[1]!=c['namespace']:raise HostGateError('foreign_host_intent')
            spent+=row['dispatchState']=='consumed'
        if (issued,spent)!=(c['issued'],c['spent']):raise HostGateError('intent_history_inconsistent')
        return key,c
    def _validate(self,row,request_id):
        fields={'version','requestId','key','fingerprint','scope','profileBinding','epoch','instanceId','createdAtMs','expiresAtMs','dispatchState','consumedAtMs','digest'}
        if type(row) is not dict or set(row)!=fields or type(row['version']) is not int or row['version']!=1:raise HostGateError('invalid_intent')
        if row['digest']!=digest({k:v for k,v in row.items() if k!='digest'}):raise HostGateError('intent_digest_mismatch')
        if (row['requestId'],row['scope'],row['profileBinding'])!=(request_id,self.context.scope,self.context.binding):raise HostGateError('intent_scope_mismatch')
        if type(row['key']) is not str or not KEY.fullmatch(row['key']) or KEY.fullmatch(row['key'])[2]!=request_id:raise HostGateError('invalid_intent_key')
        if type(row['fingerprint']) is not str or not re.fullmatch('[a-f0-9]{64}',row['fingerprint']):raise HostGateError('invalid_intent_fingerprint')
        if type(row['dispatchState']) is not str or row['dispatchState'] not in STATES:raise HostGateError('invalid_intent_state')
        for k in ['epoch','createdAtMs','expiresAtMs']:
            if type(row[k]) is not int or row[k]<=0:raise HostGateError('invalid_intent_time')
        if not 0<row['expiresAtMs']-row['createdAtMs']<=3600000 or row['epoch']>self.context.epoch or type(row['instanceId']) is not str or not row['instanceId'] or len(row['instanceId'])>1024:raise HostGateError('invalid_intent_generation')
        if row['dispatchState']=='issued' and row['consumedAtMs'] is not None:raise HostGateError('invalid_intent_state')
        if row['dispatchState']=='consumed' and (type(row['consumedAtMs']) is not int or not row['createdAtMs']<=row['consumedAtMs']<row['expiresAtMs']):raise HostGateError('invalid_consumption')
        return row
    @staticmethod
    def _seal(row):
        row={k:v for k,v in row.items() if k!='digest'};return row|{'digest':digest(row)}
    def _history(self,conn,key):
        # The durable intent is primary even when upstream has pruned its replay key.
        # Closure receipts live in the same native state_meta; never call pruning lookup().
        total=0
        for count,(text,) in enumerate(conn.execute('SELECT value FROM state_meta WHERE key GLOB ? LIMIT 10001',(CLOSURE+'*',)),1):
            if count>10000 or type(text) is not str:raise HostGateError('history_unverified')
            total+=len(text.encode())
            if total>8388608:raise HostGateError('history_unverified')
            row=_load(text)
            if type(row) is not dict or type(row.get('scopeHash')) is not str or type(row.get('keyHash')) is not str:raise HostGateError('history_unverified')
            if row['scopeHash']==self.context.scope and row['keyHash']==key_digest(key):raise HostGateError('request_closed')
        replay=self.context.profile_home/'runs_idempotency.db'
        if not replay.is_file() or replay.is_symlink():raise HostGateError('history_unavailable')
        with closing(sqlite3.connect(replay.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.execute('PRAGMA query_only=ON')
            if db.execute('SELECT 1 FROM run_idempotency WHERE scope=? AND idempotency_key=? LIMIT 1',(self.context.scope,key)).fetchone():raise HostGateError('native_request_exists')
    def _write(self,fn):
        def guarded(conn):
            # Borrowed-service admission is checked INSIDE the original native
            # write. A queued worker must not issue/consume after drain seals
            # the owner. The guard is a pure identity/phase read: no SQL, await,
            # lifecycle operation, lock acquisition or second storage owner.
            if self._admission_guard is not None:self._admission_guard()
            return fn(conn)
        try:return self.db._execute_write(guarded)
        except HostGateError:raise
        except Exception:raise HostGateError('gate_storage_or_commit_unknown') from None

    def observe(self,request_id):
        """Locate a retained native run without issuing, consuming or repairing.

        This is a read-only two-store snapshot, not an admission/result verifier
        or permission to retry. In particular, consumed + absent replay remains
        unresolved. Native lookup/status helpers may prune or repair and must
        never be called here. The existing native HTTP observer is a separate
        operation after the caller receives a locator.
        """
        index=self._identity(request_id)
        try:return self._observe_snapshot(request_id,index)
        except HostGateError:raise
        except Exception:raise HostGateError('gate_observation_unavailable') from None

    def _observe_snapshot(self,request_id,index):
        home=self.context.profile_home
        paths=(home/'state.db',home/'runs_idempotency.db')
        for path in paths:
            if not path.is_file() or path.is_symlink() or path.resolve()!=path:
                raise HostGateError('observation_storage_unavailable')
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in paths]

        def result(classification,dispatch_state=None,run_id=None):
            actions={'not_found':'retain_request_id_no_retry',
                'issued_not_dispatched':'retain_issued_request_no_retry',
                'handoff_unresolved':'retain_consumed_request_no_retry',
                'native_run_located':'observe_existing_run'}
            return {'hostGateVersion':1,'requestObservationVersion':1,
                'requestId':request_id,'classification':classification,
                'dispatchState':dispatch_state,'runId':run_id,
                'snapshotOnly':True,'writesPerformed':False,'canonicalVerified':False,
                'retryAllowed':False,'repairAllowed':False,
                'requiresOperator':classification!='native_run_located',
                'nextAction':actions[classification]}

        with closing(sqlite3.connect(paths[0].as_uri()+'?mode=ro',uri=True,timeout=2)) as conn:
            conn.execute('ATTACH DATABASE ? AS replay',(paths[1].as_uri()+'?mode=ro',))
            conn.execute('PRAGMA query_only=ON')
            conn.execute('PRAGMA trusted_schema=OFF')
            for schema,table in (('main','runtime_epoch'),('main','state_meta'),('replay','run_idempotency')):
                row=conn.execute(f'SELECT type FROM {schema}.sqlite_master WHERE name=?',(table,)).fetchone()
                if row is None or row[0]!='table':raise HostGateError('observation_schema_unavailable')
            versions=[conn.execute(f'PRAGMA {s}.data_version').fetchone()[0] for s in ('main','replay')]
            conn.execute('BEGIN')
            try:
                self._epoch(conn)
                if self._get(conn,ROOT+self.context.scope) is None:
                    if conn.execute('SELECT 1 FROM state_meta WHERE key GLOB ? LIMIT 1',
                            (INTENT+self.context.scope+'.*',)).fetchone():
                        raise HostGateError('missing_host_namespace')
                    answer=result('not_found')
                else:
                    _,cfg=self._configuration(conn,create=False)
                    value=self._get(conn,index)
                    if value is None:answer=result('not_found')
                    else:
                        intent=self._validate(value,request_id)
                        if KEY.fullmatch(intent['key'])[1]!=cfg['namespace']:
                            raise HostGateError('foreign_host_intent')
                        rows=conn.execute('SELECT fingerprint,run_id,status_json '
                            'FROM replay.run_idempotency WHERE scope=? AND idempotency_key=? LIMIT 2',
                            (self.context.scope,intent['key'])).fetchall()
                        if len(rows)>1:raise HostGateError('ambiguous_native_reservation')
                        if intent['dispatchState']=='issued':
                            if rows:raise HostGateError('intent_native_state_conflict')
                            answer=result('issued_not_dispatched','issued')
                        elif not rows:answer=result('handoff_unresolved','consumed')
                        else:
                            fingerprint,run_id,encoded=rows[0]
                            if (type(fingerprint) is not str or not re.fullmatch('[a-f0-9]{64}',fingerprint)
                                    or not hmac.compare_digest(fingerprint,intent['fingerprint'])):
                                raise HostGateError('native_request_fingerprint_mismatch')
                            if type(run_id) is not str or not RUN.fullmatch(run_id):
                                raise HostGateError('invalid_native_run_identity')
                            saved=_load(encoded)
                            if (type(saved) is not dict or saved.get('run_id')!=run_id
                                    or type(saved.get('status')) is not str
                                    or saved['status'] not in {'queued','started','running','stopping',
                                        'waiting_for_approval','completed','failed','cancelled','interrupted','unknown'}):
                                raise HostGateError('invalid_native_reservation')
                            answer=result('native_run_located','consumed',run_id)
            finally:conn.rollback()
            self._epoch(conn)
            changed=[conn.execute(f'PRAGMA {s}.data_version').fetchone()[0] for s in ('main','replay')]
            if changed!=versions:raise HostGateError('observation_state_changed')
        if identities!=[(p.stat().st_dev,p.stat().st_ino) for p in paths]:
            raise HostGateError('observation_store_replaced')
        return answer

    def issue(self,request_id,body):
        index=self._identity(request_id);_,fp=self._body(body)
        def transaction(conn):
            self._epoch(conn);now=self._now();configkey,cfg=self._configuration(conn,True)
            old=self._get(conn,index)
            if old is not None:
                row=self._validate(old,request_id)
                if KEY.fullmatch(row['key'])[1]!=cfg['namespace']:raise HostGateError('foreign_host_intent')
                if row['fingerprint']!=fp:raise HostGateError('request_payload_conflict')
                return dict(row,replayed=True)
            if cfg['issued']>=self.policy.max_issued:raise HostGateError('intent_limit_reached')
            key='ah1-'+cfg['namespace']+'-'+request_id;self._history(conn,key)
            row=self._seal({'version':1,'requestId':request_id,'key':key,'fingerprint':fp,'scope':self.context.scope,'profileBinding':self.context.binding,
              'epoch':self.context.epoch,'instanceId':self.context.instance_id,'createdAtMs':now,'expiresAtMs':now+self.policy.validity_seconds*1000,'dispatchState':'issued','consumedAtMs':None})
            cfg['issued']+=1
            conn.execute('INSERT INTO state_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(configkey,_json(cfg)))
            conn.execute('INSERT INTO state_meta(key,value) VALUES(?,?)',(index,_json(row)))
            return dict(row,replayed=False)
        return self._write(transaction)
    def consume(self,key,body):
        if type(key) is not str or not KEY.fullmatch(key):raise HostGateError('host_intent_required')
        request_id=KEY.fullmatch(key)[2];index=self._identity(request_id);_,fp=self._body(body)
        def transaction(conn):
            self._epoch(conn);now=self._now();configkey,cfg=self._configuration(conn)
            value=self._get(conn,index)
            if value is None:raise HostGateError('unknown_host_intent')
            row=self._validate(value,request_id)
            if row['key']!=key or KEY.fullmatch(key)[1]!=cfg['namespace']:raise HostGateError('foreign_host_intent')
            if row['fingerprint']!=fp:raise HostGateError('request_payload_conflict')
            if row['dispatchState']!='issued':raise HostGateError('dispatch_already_attempted')
            if (row['epoch'],row['instanceId'])!=(self.context.epoch,self.context.instance_id):raise HostGateError('stale_intent_epoch')
            if not row['createdAtMs']<=now<row['expiresAtMs']:raise HostGateError('intent_expired')
            self._history(conn,key)
            if cfg['spent']>=self.policy.max_dispatches:raise HostGateError('dispatch_limit_reached')
            row=self._seal(row|{'dispatchState':'consumed','consumedAtMs':now});cfg['spent']+=1
            conn.execute('UPDATE state_meta SET value=? WHERE key=?',(_json(row),index))
            conn.execute('UPDATE state_meta SET value=? WHERE key=?',(_json(cfg),configkey))
            return {'handoffClaimed':True,'key':key,'requestId':request_id,'requestFingerprint':fp,'epoch':self.context.epoch,'taskSucceeded':False,'retryAllowed':False}
        return self._write(transaction)
