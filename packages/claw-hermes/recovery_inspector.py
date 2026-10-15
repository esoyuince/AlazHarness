"""Pinned, co-located read-only reconciliation. No replay, deletion or execution authority.

Context is trusted host configuration, NEVER fields accepted from a network caller.
This supports only the default-profile bearer /v1/runs path of the pinned Hermes.
Two-store observations are snapshots, not atomic-admission or future-action leases.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass, field
import hashlib
import hmac
import importlib.util
import json
import math
from pathlib import Path
import re
import sqlite3
import time
from typing import Callable

PIN = 'eb75627faf532fa6ffbdae59a0d14b0b385fc780'
TERMINAL = {'completed','failed','cancelled','interrupted'}
RESULT = 'gateway.admission.result.v1.'
IDENTITY = 'gateway.terminal_identity.v1.'
ARCHIVE = 'gateway.terminal_admission.v1.'
RUN = re.compile(r'run_[a-f0-9]{32}\Z')
HEX = re.compile(r'[a-f0-9]{32}\Z')
HASH = re.compile(r'[a-f0-9]{64}\Z')


def _helper(name):
    path=Path(__file__).resolve().parents[1]/'upstream/hermes'/(name+'.py')
    spec=importlib.util.spec_from_file_location('alaz_reconcile_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

_KEYS=_helper('hermes_state_keys')
_TERMINAL=_helper('terminal_status')


class EvidenceError(ValueError):
    pass


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise EvidenceError('duplicate_json_key')
        value[key]=item
    return value


def _load(value, maximum=2_097_152):
    if not isinstance(value,str) or len(value.encode('utf-8'))>maximum:raise EvidenceError('oversized_evidence')
    return json.loads(value,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(EvidenceError('nonfinite_json')))


def _json(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _digest(value):return hashlib.sha256(_json(value).encode()).hexdigest()


def _numeric(value):
    return type(value) in (int,float) and math.isfinite(value)


def request_fingerprint(body):
    if type(body) is not dict or not set(body)<= {'input','model','session_id'} or 'input' not in body:
        raise EvidenceError('unsupported_request_shape')
    for key,value in body.items():
        maximum={'input':65536,'model':200,'session_id':256}[key]
        if not isinstance(value,str) or not value.strip() or len(value.encode('utf-8'))>maximum:
            raise EvidenceError('invalid_request')
    # Existing HermesRunsClient has no X-Hermes-Session-Key; never silently infer it.
    return _digest({'body':body,'gateway_session_key':''})


@dataclass(frozen=True)
class LocalRecoveryContext:
    profile_home: Path
    api_token: str = field(repr=False)
    epoch: int
    instance_id: str
    profile_name: str = 'default'

    def __post_init__(self):
        if self.profile_name!='default':raise ValueError('unsupported_profile_scope')
        if type(self.epoch) is not int or self.epoch<=0:raise ValueError('invalid_epoch')
        if not isinstance(self.instance_id,str) or not self.instance_id or len(self.instance_id)>1024:
            raise ValueError('invalid_instance')
        if not isinstance(self.api_token,str) or not re.fullmatch(r'[\x21-\x7e]{1,4096}',self.api_token):
            raise ValueError('invalid_auth_context')
        object.__setattr__(self,'profile_home',Path(self.profile_home).resolve())

    @property
    def scope(self):return hashlib.sha256((self.profile_name+'\0'+self.api_token).encode()).hexdigest()

    @property
    def binding(self):return hashlib.sha256(str(self.profile_home).encode()).hexdigest()


class LocalRecoveryInspector:
    def __init__(self, context: LocalRecoveryContext, *, clock: Callable[[],float]=time.time):
        if not isinstance(context,LocalRecoveryContext):raise TypeError('trusted_context_required')
        self.context=context;self.clock=clock

    def inspect(self, *, body: dict, idempotency_key: str, observed: dict) -> dict:
        # Result is informational and cannot be passed back as a capability to repair.
        answer={'contractVersion':1,'classification':'unverified','canonicalVerified':False,
                'requiresOperator':True,'retryAllowed':False,'repairAllowed':False,
                'writesPerformed':False,'taskSucceeded':False,'snapshotOnly':True,'sourceCommit':PIN,
                'profileBinding':self.context.binding,'epoch':self.context.epoch,
                'nextAction':'retain_request_and_obtain_authoritative_evidence'}
        try:
            body=_load(_json(body),131072);observed=_load(_json(observed))
            fingerprint=request_fingerprint(body)
            if not isinstance(idempotency_key,str) or not re.fullmatch(r'[\x21-\x7e]{1,255}',idempotency_key):
                raise EvidenceError('invalid_key')
            if type(observed) is not dict or not isinstance(observed.get('run_id'),str) or not RUN.fullmatch(observed['run_id']):
                raise EvidenceError('invalid_run')
            result=self._read(body,idempotency_key,fingerprint,observed)
            answer.update(result)
        except EvidenceError as exc:answer['reason']=str(exc)
        except (OSError,sqlite3.Error):answer['reason']='storage_unavailable'
        except (ValueError,TypeError,KeyError,IndexError,OverflowError,RecursionError,AttributeError):answer['reason']='malformed_evidence'
        return answer

    def _paths(self):
        home=self.context.profile_home
        paths=[home/'state.db',home/'runs_idempotency.db']
        for path in paths:
            if not path.is_file() or path.is_symlink() or path.resolve().parent!=home:
                raise EvidenceError('storage_unavailable')
        return paths

    def _read(self,body,key,fingerprint,observed):
        state,runs=self._paths()
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in (state,runs)]
        with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True,timeout=2)) as conn:
            conn.row_factory=sqlite3.Row
            conn.execute('ATTACH DATABASE ? AS replay',(runs.as_uri()+'?mode=ro',))
            conn.execute('PRAGMA query_only=ON');conn.execute('PRAGMA trusted_schema=OFF')
            for schema,table in [('main','runtime_epoch'),('main','session_admissions'),('main','state_meta'),('replay','run_idempotency')]:
                row=conn.execute(f'SELECT type FROM {schema}.sqlite_master WHERE name=?',(table,)).fetchone()
                if row is None or row[0]!='table':raise EvidenceError('unsupported_schema')
            versions=[conn.execute(f'PRAGMA {s}.data_version').fetchone()[0] for s in ('main','replay')]
            conn.execute('BEGIN')
            try:
                epoch=conn.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
                if epoch is None or tuple(epoch)!=(self.context.epoch,self.context.instance_id):raise EvidenceError('stale_epoch')
                rows=conn.execute('SELECT * FROM replay.run_idempotency WHERE scope=? AND idempotency_key=? LIMIT 2',
                                  (self.context.scope,key)).fetchall()
                if len(rows)!=1:raise EvidenceError('lookup_unavailable')
                reservation=dict(rows[0])
                if not isinstance(reservation['fingerprint'],str) or not HASH.fullmatch(reservation['fingerprint']):raise EvidenceError('invalid_fingerprint')
                if not hmac.compare_digest(reservation['fingerprint'],fingerprint):raise EvidenceError('request_payload_conflict')
                rid=observed['run_id']
                if reservation['run_id']!=rid:raise EvidenceError('run_identity_mismatch')
                saved=_load(reservation['status_json'])
                if type(saved) is not dict or saved.get('run_id')!=rid:raise EvidenceError('invalid_reservation')
                self._retention(reservation,saved)
                live=conn.execute("SELECT * FROM session_admissions WHERE principal_id='api' AND request_id=? LIMIT 2",(rid,)).fetchall()
                if len(live)>1:raise EvidenceError('ambiguous_admission')
                target=body.get('session_id',rid)
                identity=IDENTITY+_KEYS.admission_fingerprint(canonical_target=target,payload={'principal':'api','request':rid})
                retired_id=conn.execute('SELECT value FROM state_meta WHERE key=?',(identity,)).fetchone()
                archived=None
                if retired_id:
                    aid=_load(retired_id[0])
                    if not isinstance(aid,str) or not HEX.fullmatch(aid):raise EvidenceError('invalid_retired_identity')
                    retired=conn.execute('SELECT value FROM state_meta WHERE key=?',(ARCHIVE+aid,)).fetchone()
                    if retired is None:raise EvidenceError('missing_retired_admission')
                    archived=_load(retired[0])
                    if type(archived) is not dict:raise EvidenceError('invalid_retired_admission')
                if live and archived:raise EvidenceError('ambiguous_admission')
                row=dict(live[0]) if live else archived
                evidence=self._classify(conn,row,reservation,saved,body,observed,target)
            finally:conn.rollback()
            fresh=conn.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
            changed=[conn.execute(f'PRAGMA {s}.data_version').fetchone()[0] for s in ('main','replay')]
            if fresh is None or tuple(fresh)!=(self.context.epoch,self.context.instance_id) or changed!=versions:
                raise EvidenceError('concurrent_state_change')
        if identities!=[(p.stat().st_dev,p.stat().st_ino) for p in (state,runs)]:raise EvidenceError('store_replaced')
        return evidence

    def _retention(self,row,saved):
        now=self.clock()
        if not _numeric(now) or now<0:raise EvidenceError('invalid_clock')
        for name in ('created_at','updated_at','retention_until'):
            if not _numeric(row[name]) or row[name]<0:raise EvidenceError('invalid_retention')
        ack=row['acknowledged_at'];until=row['retention_until']
        if ack is not None and (not _numeric(ack) or ack<0):raise EvidenceError('invalid_retention')
        if saved.get('status') in TERMINAL and ((ack is not None and ack<=now-86400)
            or (until>0 and until<=now) or (until<=0 and row['updated_at']<now-86400)):
            raise EvidenceError('retention_expired')

    def _classify(self,conn,row,reservation,saved,body,http,target):
        rid=http['run_id'];base={'runId':rid,'requestFingerprint':reservation['fingerprint']}
        if row is None:
            # This includes a transient live reservation. No dead-owner/atomicity claim.
            if http.get('status')!=saved.get('status'):raise EvidenceError('projection_mismatch')
            if http.get('admission_id') is not None:raise EvidenceError('projection_mismatch')
            return {**base,'classification':'reservation_without_admission_observed',
                    'reason':'canonical_admission_absent_at_snapshot','nextAction':'operator_reconcile_reservation',
                    'canonicalAbsentAtSnapshot':True,'canonicalVerified':False}
        if type(row) is not dict:raise EvidenceError('invalid_admission')
        if (row['request_id'],row['principal_id'],row['target_session_id'])!=(rid,'api',target):
            raise EvidenceError('admission_identity_mismatch')
        if not isinstance(row['admission_id'],str) or not HEX.fullmatch(row['admission_id']):raise EvidenceError('invalid_admission')
        payload=_load(row['payload_json'])
        if type(payload) is not dict or type(payload.get('api_turn_v1')) is not dict:
            raise EvidenceError('invalid_admission_payload')
        api=payload['api_turn_v1'];scope=api.get('run_owner_scope')
        settings=api.get('settings',{})
        if type(settings) is not dict:raise EvidenceError('invalid_admission_settings')
        # Only direct bare-model requests are supported. Alias/provider/options
        # need a trusted model-route resolver, not a guessed equivalence.
        if any(settings.get(k) is not None for k in ('route','requested_provider','model_options')):
            raise EvidenceError('unsupported_model_routing')
        expected_model=body['model'].strip() if 'model' in body else None
        if settings.get('requested_model')!=expected_model:
            raise EvidenceError('request_model_mismatch')
        if not isinstance(scope,str) or not hmac.compare_digest(scope,self.context.scope):raise EvidenceError('scope_mismatch')
        if payload.get('text')!=body['input']:raise EvidenceError('request_payload_conflict')
        digest=_KEYS.admission_fingerprint(canonical_target=target,payload={'input':payload,'intent':row['intent']})
        if not hmac.compare_digest(digest,row['payload_digest']):raise EvidenceError('admission_digest_mismatch')
        if type(row['owner_epoch']) is not int or not 0<row['owner_epoch']<=self.context.epoch:raise EvidenceError('invalid_admission_epoch')
        generation=row['generation']
        if generation is not None and (type(generation) is not int or generation<=0):raise EvidenceError('invalid_generation')
        if generation is not None and type(http.get('execution_generation')) is not int:
            raise EvidenceError('projection_identity_mismatch')
        if (http.get('admission_id'),http.get('session_id'),http.get('execution_generation'))!=(row['admission_id'],target,generation):
            raise EvidenceError('projection_identity_mismatch')
        base.update(admissionId=row['admission_id'],sessionId=target,executionGeneration=generation,
                    canonicalVerified=True,requiresOperator=False)
        status=row['status']
        if status=='unknown':
            if http['status']!='unknown':raise EvidenceError('projection_mismatch')
            return {**base,'classification':'execution_unknown','requiresOperator':True,'nextAction':'operator_reconcile_execution'}
        if status in ('queued','started'):
            if http['status'] not in ({'queued'} if status=='queued' else {'running','waiting_for_approval','stopping'}):raise EvidenceError('projection_mismatch')
            return {**base,'classification':'in_progress','requiresOperator':http['status']=='waiting_for_approval','nextAction':'observe_existing_run'}
        if status!='terminal':raise EvidenceError('unsupported_admission_state')
        record=conn.execute('SELECT value FROM state_meta WHERE key=?',(RESULT+row['admission_id'],)).fetchone()
        if record is None:raise EvidenceError('missing_terminal_result')
        result=_load(record[0]);value=result['result']
        if type(value) is not dict or type(result.get('usage',{})) is not dict:raise EvidenceError('invalid_terminal_result')
        outcome=row['outcome']
        if outcome=='interrupted' or value.get('interrupted'):expected='cancelled'
        elif outcome=='failed' or value.get('failed') or value.get('error'):expected='failed'
        elif outcome=='completed':expected=_TERMINAL.terminal_run_status(value)[0]
        elif outcome=='cancelled':expected='cancelled'
        else:raise EvidenceError('unsupported_terminal_outcome')
        if http.get('status')!=expected or http.get('output','')!=value.get('final_response','') or _json(http.get('usage',{}))!=_json(result.get('usage',{})):
            raise EvidenceError('terminal_result_mismatch')
        return {**base,'classification':'canonical_terminal_verified','outcome':expected,
                'taskSucceeded':expected=='completed','nextAction':'retain_verified_outcome',
                'resultDigest':_digest({'output':http.get('output',''),'usage':http.get('usage',{})})}
