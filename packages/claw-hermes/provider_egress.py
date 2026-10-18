"""Single-use egress grants written only by the existing native ledger owner.

The broker is a trusted, separately credentialed process, not a second budget DB.
A grant commits BEFORE IPC/network and never grants refund or automatic replay.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass, field
import hashlib
import hmac
import math
from pathlib import Path
import re
import sqlite3
import time
from execution_budget import ExecutionLedger, ExecutionDenied, CONFIG, CLAIM, seal
from recovery_inspector import _json, _load
import request_view

EGRESS='alaz.execution.egress.v1.'
HEX32=re.compile(r'[a-f0-9]{32}\Z')
HEX64=re.compile(r'[a-f0-9]{64}\Z')
REQUEST_LIMIT=2_010_000
RESPONSE_LIMIT=5_700_000
GRANT_FIELDS={'version','brokerId','routeFingerprint','scope','binding','policy','ticket',
              'fingerprint','epoch','instance','expiresAtMs'}


def require(value, code):
    if not value:raise ExecutionDenied(code)


def hashed(value):return hashlib.sha256(_json(value).encode()).hexdigest()


def _hex(value, pattern, code):
    require(type(value) is str and pattern.fullmatch(value),code)
    return value


def signed(value,key,role):
    # Separate request/reply domains; caller payload is not an execution instruction.
    require(type(value) is dict and 'signature' not in value,'invalid_broker_document')
    _hex(key,HEX64,'invalid_broker_key')
    return value|{'signature':hmac.new(bytes.fromhex(key),_json({'role':role,'value':value}).encode(),hashlib.sha256).hexdigest()}


def verified(value,key,role):
    require(type(value) is dict and type(value.get('signature')) is str,'broker_authentication_required')
    content={k:v for k,v in value.items() if k!='signature'}
    expected=signed(content,key,role)['signature']
    require(hmac.compare_digest(value['signature'],expected),'broker_authentication_required')
    return content


@dataclass(frozen=True)
class BrokerLink:
    socket_path: str
    broker_id: str
    route_fingerprint: str
    signing_key: str = field(repr=False)

    def __post_init__(self):
        _hex(self.broker_id,HEX32,'invalid_broker_identity')
        _hex(self.route_fingerprint,HEX64,'invalid_broker_route')
        _hex(self.signing_key,HEX64,'invalid_broker_key')
        s=self.socket_path
        require(type(s) is str and s.startswith('/') and len(s.encode())<=100
                and not any(c in s for c in '\x00\r\n') and '..' not in s.split('/'),'invalid_broker_socket')


def authorize_egress(ledger:ExecutionLedger,link:BrokerLink,ticket:str,payload:dict,*,clock=time.time,record_view=False)->dict:
    require(type(record_view) is bool,'invalid_request_view_setting')
    require(type(ledger) is ExecutionLedger and type(link) is BrokerLink,'trusted_egress_owner_required')
    _hex(ticket,HEX32,'invalid_execution_ticket')
    frozen=_load(_json(payload),2_000_000)
    require(type(frozen) is dict and frozen.get('model')==ledger.policy.model,'broker_model_mismatch')
    fingerprint=hashed(frozen)
    now=clock()
    require(type(now) in (int,float) and math.isfinite(now) and 0<now<10**11,'invalid_broker_clock')
    grant={'version':1,'brokerId':link.broker_id,'routeFingerprint':link.route_fingerprint,
           'scope':ledger.context.scope,'binding':ledger.context.binding,'policy':ledger.policy.fingerprint,
           'ticket':ticket,'fingerprint':fingerprint,'epoch':ledger.context.epoch,
           'instance':ledger.context.instance_id,'expiresAtMs':int(now*1000)+20000}
    def commit(c):
        cfg=ledger._state(c)
        require(not cfg['quarantined'],'execution_budget_quarantined')
        found=c.execute('SELECT value FROM state_meta WHERE key=?',(ledger.prefix+ticket,)).fetchone()
        require(found is not None,'execution_claim_missing')
        claim=ledger._row(_load(found[0],16384),ticket)
        require(claim['kind']=='provider' and claim['state']=='reserved','provider_reservation_required')
        require(claim['fingerprint']==fingerprint,'egress_payload_conflict')
        require((claim['epoch'],claim['instance'])==(ledger.context.epoch,ledger.context.instance_id),'stale_execution_claim')
        key=EGRESS+ledger.context.scope+'.'+ticket
        require(c.execute('SELECT 1 FROM state_meta WHERE key=?',(key,)).fetchone() is None,'egress_already_authorized')
        c.execute('INSERT INTO state_meta(key,value) VALUES(?,?)',(key,_json(seal(grant))))
        if record_view:request_view.prepare_in_transaction(c,ledger,grant,frozen)
        return grant
    durable=ledger._write(commit)
    # No signature or sendable object is returned on an unknown COMMIT response.
    return signed({'version':1,'operation':'send','grant':durable,'payload':frozen},link.signing_key,'request')


def route_fingerprint(endpoint,model):
    require(type(endpoint) is str and re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})/v1',endpoint),'unsupported_broker_upstream')
    require(1<=int(endpoint.split(':')[2].split('/')[0])<=65535,'unsupported_broker_upstream')
    require(type(model) is str and model.strip() and len(model.encode())<=200,'invalid_broker_model')
    return hashed({'version':1,'endpoint':endpoint,'model':model})


@dataclass(frozen=True)
class BrokerConfig:
    upstream_base_url: str
    model: str
    upstream_bearer: str = field(repr=False)
    signing_key: str = field(repr=False)
    state_db: str
    scope: str
    binding: str
    policy_fingerprint: str
    budget_authority: dict | None = field(default=None,repr=False)

    def __post_init__(self):
        route_fingerprint(self.upstream_base_url,self.model)
        _hex(self.signing_key,HEX64,'invalid_broker_key')
        for value in (self.scope,self.binding,self.policy_fingerprint):_hex(value,HEX64,'invalid_broker_scope')
        token=self.upstream_bearer
        require(type(token) is str and re.fullmatch(r'[\x21-\x7e]{32,256}',token),'invalid_upstream_credential')
        require(token!=self.signing_key,'separate_upstream_credential_required')
        require(type(self.state_db) is str and Path(self.state_db).is_absolute() and Path(self.state_db).name=='state.db','invalid_broker_database')
        if self.budget_authority is not None:
            from broker_budget import validate_settings,binding_for
            object.__setattr__(self,'budget_authority',validate_settings(self.budget_authority))
            binding_for(self)

    @property
    def route(self):return route_fingerprint(self.upstream_base_url,self.model)


class PermitVerifier:
    """Bounded per-process replay barrier; a new broker ALWAYS has a new ID.

    The retained egress grant is separately checked against the live native owner.
    No durable rows, counters or claims are written by the broker.
    """
    def __init__(self,config:BrokerConfig,broker_id:str,*,clock=time.time):
        require(type(config) is BrokerConfig,'trusted_broker_config_required')
        _hex(broker_id,HEX32,'invalid_broker_identity')
        self.config=config;self.broker_id=broker_id;self.clock=clock;self.seen=set()

    def consume(self,envelope):
        doc=verified(envelope,self.config.signing_key,'request')
        require(set(doc)=={'version','operation','grant','payload'} and type(doc['version']) is int and doc['version']==1
                and doc['operation']=='send','invalid_egress_envelope')
        g=doc['grant'];body=doc['payload']
        require(type(g) is dict and set(g)==GRANT_FIELDS,'invalid_egress_grant')
        require(type(g['version']) is int and g['version']==1,'invalid_egress_grant')
        require(g['brokerId']==self.broker_id and g['routeFingerprint']==self.config.route,'stale_broker_identity')
        require((g['scope'],g['binding'],g['policy'])==(self.config.scope,self.config.binding,self.config.policy_fingerprint),'broker_scope_mismatch')
        _hex(g['ticket'],HEX32,'invalid_execution_ticket');_hex(g['fingerprint'],HEX64,'invalid_egress_fingerprint')
        require(type(g['epoch']) is int and 0<g['epoch']<10**15 and type(g['instance']) is str and 0<len(g['instance'])<=1024,'invalid_egress_epoch')
        self.check_expiry(g)
        require(type(body) is dict and body.get('model')==self.config.model and len(_json(body).encode())<=2_000_000,'broker_model_mismatch')
        require(hashed(body)==g['fingerprint'],'egress_payload_conflict')
        require(g['ticket'] not in self.seen,'broker_replay_refused')
        require(len(self.seen)<1000,'broker_lifetime_limit')
        # Synchronous: no await between replay test and consumption.
        self.seen.add(g['ticket'])
        return doc

    def check_expiry(self,g):
        now=self.clock()
        require(type(now) in (int,float) and math.isfinite(now) and 0<now<10**11,'invalid_broker_clock')
        require(type(g.get('expiresAtMs')) is int and int(now*1000)<g['expiresAtMs']<=int(now*1000)+30000,'egress_grant_expired')

    def check_authority(self,g):
        # Authority is a bounded observation, not a lease against later host writes.
        self.check_expiry(g)
        path=Path(self.config.state_db)
        require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'broker_authority_unavailable')
        identity=(path.stat().st_dev,path.stat().st_ino)
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as c:
            c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF')
            version=c.execute('PRAGMA data_version').fetchone()[0]
            c.execute('BEGIN')
            try:
                for table in ('runtime_epoch','state_meta'):
                    row=c.execute('SELECT type FROM sqlite_master WHERE name=?',(table,)).fetchone()
                    require(row is not None and row[0]=='table','broker_authority_schema')
                epoch=c.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
                require(epoch is not None and tuple(epoch)==(g['epoch'],g['instance']),'stale_egress_owner')
                row=c.execute('SELECT value FROM state_meta WHERE key=?',(EGRESS+g['scope']+'.'+g['ticket'],)).fetchone()
                require(row is not None and _load(row[0],16384)==seal(g),'unconfirmed_egress_grant')
                cfg=c.execute('SELECT value FROM state_meta WHERE key=?',(CONFIG+g['scope'],)).fetchone()
                require(cfg is not None,'broker_budget_unavailable');cfg=_load(cfg[0],16384)
                require(type(cfg) is dict and cfg.get('digest')==seal(cfg)['digest'] and cfg.get('quarantined') is False
                        and (cfg.get('scope'),cfg.get('binding'),cfg.get('policy'))==(g['scope'],g['binding'],g['policy']),'broker_budget_unavailable')
                row=c.execute('SELECT value FROM state_meta WHERE key=?',(CLAIM+g['scope']+'.'+g['ticket'],)).fetchone()
                require(row is not None,'broker_claim_unavailable');row=_load(row[0],16384)
                require(type(row) is dict and row.get('digest')==seal(row)['digest'] and
                        (row.get('ticket'),row.get('kind'),row.get('state'),row.get('fingerprint'),row.get('epoch'),row.get('instance'),row.get('scope'),row.get('binding'),row.get('policy'))==
                        (g['ticket'],'provider','reserved',g['fingerprint'],g['epoch'],g['instance'],g['scope'],g['binding'],g['policy']),'broker_claim_unavailable')
            finally:c.rollback()
            # Re-read after releasing the snapshot. Changes DURING the check are
            # rejected; concurrent revocation after return remains a separate limit.
            fresh=c.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
            require(fresh is not None and tuple(fresh)==(g['epoch'],g['instance'])
                    and c.execute('PRAGMA data_version').fetchone()[0]==version,'broker_authority_changed')
            self.check_expiry(g)
        require(path.is_file() and not path.is_symlink() and identity==(path.stat().st_dev,path.stat().st_ino),'broker_authority_replaced')
