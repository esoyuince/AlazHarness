"""Broker-owned irreversible provider exposure, independent of Gateway SQLite.

Trusted bootstrap only. Missing state is NOT recreated by a running broker.
A private native directory plus OS confinement is required to exclude Gateway
writes; this module does not protect against the trusted host administrator.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
from execution_budget import ExecutionPolicy, ExecutionDenied, seal
from recovery_inspector import _json, _load

VERSION=1
SETTINGS={'version','enabled','directory','budget_id','policy'}
MAX_ROWS=1000
ATTEMPT_FIELDS={'version','sequence','ticket','brokerId','payloadSha256','epoch',
                'instanceSha256','reservedTokens','reservedCostMicrousd','previous'}
RESPONSE_FIELDS={'version','ticket','httpStatus','responseBytes','responseSha256','contentType'}
PAYLOAD_FIELDS={'model','messages','max_tokens','stream','temperature','top_p','stop',
    'tools','tool_choice','parallel_tool_calls','stream_options','seed',
    'frequency_penalty','presence_penalty','response_format','n',
    'user','reasoning_effort','verbosity','max_completion_tokens'}


def require(ok,code):
    if not ok:raise ExecutionDenied(code)


def hexdigest(value):return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def ishex(value,n=64):
    return type(value) is str and re.fullmatch('[a-f0-9]{'+str(n)+'}',value) is not None


def validate_settings(value):
    require(type(value) is dict and set(value)==SETTINGS,'broker_private_budget_settings')
    require(type(value['version']) is int and value['version']==1 and value['enabled'] is True,
            'broker_private_budget_optin')
    directory=value['directory']
    require(type(directory) is str and 0<len(directory)<=4096 and '\x00' not in directory,
            'broker_private_budget_path')
    path=Path(directory)
    require(path.is_absolute() and str(path)==directory and '..' not in path.parts
            and len(path.parts)>=3,'broker_private_budget_path')
    require(ishex(value['budget_id'],32),'broker_private_budget_identity')
    require(type(value['policy']) is dict,'broker_private_budget_policy')
    try:policy=ExecutionPolicy(**value['policy'])
    except TypeError:raise ExecutionDenied('broker_private_budget_policy') from None
    return {'version':1,'enabled':True,'directory':directory,
            'budget_id':value['budget_id'],'policy':asdict(policy)}


def binding_for(config):
    settings=validate_settings(config.budget_authority)
    policy=ExecutionPolicy(**settings['policy'])
    require(policy.model==config.model and policy.fingerprint==config.policy_fingerprint,
            'broker_private_budget_policy_mismatch')
    directory=Path(settings['directory'])
    gateway=Path(config.state_db).parent
    require(not directory.is_relative_to(gateway) and not gateway.is_relative_to(directory),
            'broker_private_budget_not_separate')
    value={'version':1,'budgetId':settings['budget_id'],'scope':config.scope,
           'principalBinding':config.binding,'routeFingerprint':config.route,
           'executionPolicy':asdict(policy),'policyFingerprint':policy.fingerprint}
    return directory,policy,value


def _identity(path,directory=False):
    require(path.exists() and not any(p.is_symlink() for p in (path,*path.parents)),
            'broker_private_budget_missing_or_linked')
    st=path.stat()
    require(stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode),
            'broker_private_budget_file_type')
    if not directory:
        require(st.st_nlink==1 and 0<st.st_size<=8_388_608,'broker_private_budget_file_bounds')
    if os.name=='posix':
        require(st.st_uid==os.getuid() and stat.S_IMODE(st.st_mode)==(0o700 if directory else 0o600),
                'broker_private_budget_permissions')
    return st.st_dev,st.st_ino


def _connect(path):
    # rw refuses accidental recreation; DELETE/FULL avoids treating a missing
    # WAL sidecar as an empty approved budget. Native SQLite storage is required.
    connection=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=2,isolation_level=None)
    connection.execute('PRAGMA trusted_schema=OFF')
    connection.execute('PRAGMA synchronous=FULL')
    require(connection.execute('PRAGMA journal_mode').fetchone()[0]=='delete',
            'broker_private_budget_journal_mode')
    return connection


def initialize(config):
    """Explicit trusted-host provisioning, refuses any existing directory.

    A partial failed create is kept for investigation, not silently retried.
    Running servers NEVER call this function implicitly.
    """
    directory,policy,binding=binding_for(config)
    require(not directory.exists() and not directory.is_symlink()
            and directory.parent.is_dir()
            and not any(p.is_symlink() for p in directory.parents),
            'broker_private_budget_fresh_directory_required')
    directory.mkdir(mode=0o700)
    path=directory/'budget.sqlite3'
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        with closing(_connect(path)) as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('CREATE TABLE budget_state(singleton INTEGER PRIMARY KEY CHECK(singleton=1),binding TEXT NOT NULL,counter INTEGER NOT NULL,head TEXT NOT NULL)')
            c.execute('CREATE TABLE attempts(sequence INTEGER PRIMARY KEY,ticket TEXT NOT NULL UNIQUE,record TEXT NOT NULL)')
            c.execute('CREATE TABLE responses(ticket TEXT PRIMARY KEY,record TEXT NOT NULL)')
            c.execute('INSERT INTO budget_state VALUES(1,?,0,?)',(_json(binding),hexdigest(binding)))
            c.commit()
        if os.name=='posix':
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        return BrokerBudget(config).snapshot()
    except ExecutionDenied:raise
    except Exception:raise ExecutionDenied('broker_private_budget_initialization_unconfirmed') from None


class BrokerBudget:
    """Private durable cap across broker lifetimes; no refunds or public reset."""
    def __init__(self,config):
        self.directory,self.policy,self.binding=binding_for(config)
        self.path=self.directory/'budget.sqlite3'
        self.directory_identity=_identity(self.directory,True)
        self.file_identity=_identity(self.path)
        self.snapshot()

    def _paths(self):
        require(_identity(self.directory,True)==self.directory_identity and
                _identity(self.path)==self.file_identity,'broker_private_budget_replaced')
        journal=Path(str(self.path)+'-journal')
        if journal.exists():
            info=journal.lstat()
            require(not journal.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_nlink==1,
                    'broker_private_budget_journal_linked')
            if os.name=='posix':
                require(info.st_uid==os.getuid() and not stat.S_IMODE(info.st_mode)&0o077,
                        'broker_private_budget_journal_permissions')

    def _read(self,c):
        schema=c.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        require(set(schema)=={('table','budget_state'),('table','attempts'),('table','responses')},
                'broker_private_budget_schema')
        cfg=c.execute('SELECT singleton,binding,counter,head FROM budget_state').fetchall()
        require(len(cfg)==1 and cfg[0][0]==1 and cfg[0][1]==_json(self.binding)
                and type(cfg[0][2]) is int and 0<=cfg[0][2]<=MAX_ROWS
                and ishex(cfg[0][3]),'broker_private_budget_binding_changed')
        rows=c.execute('SELECT sequence,ticket,record FROM attempts ORDER BY sequence LIMIT 1001').fetchall()
        require(len(rows)<=MAX_ROWS and len(rows)==cfg[0][2],'broker_private_budget_history')
        head=hexdigest(self.binding);tickets=set()
        for seq,(index,ticket,record) in enumerate(rows,1):
            value=_load(record,8192)
            require(type(value) is dict and set(value)==ATTEMPT_FIELDS|{'digest'}
                    and value==seal(value) and index==seq and type(value['sequence']) is int
                    and value['sequence']==seq and value['version']==1
                    and value['ticket']==ticket and ishex(ticket,32)
                    and ticket not in tickets and ishex(value['brokerId'],32)
                    and ishex(value['payloadSha256']) and ishex(value['instanceSha256'])
                    and type(value['epoch']) is int and 0<value['epoch']<10**15
                    and value['previous']==head
                    and type(value['reservedTokens']) is int
                    and value['reservedTokens']==self.policy.tokens_per_attempt
                    and type(value['reservedCostMicrousd']) is int
                    and value['reservedCostMicrousd']==self.policy.cost_per_attempt,
                    'broker_private_budget_history')
            head=value['digest'];tickets.add(ticket)
        require(head==cfg[0][3],'broker_private_budget_history')
        count=len(rows)
        require(count<=self.policy.max_provider_calls and
                count*self.policy.tokens_per_attempt<=self.policy.total_token_limit and
                count*self.policy.cost_per_attempt<=self.policy.total_cost_microusd,
                'broker_private_budget_history')
        replies=c.execute('SELECT ticket,record FROM responses LIMIT 1001').fetchall()
        require(len(replies)<=count,'broker_private_budget_response_history')
        for ticket,record in replies:
            value=_load(record,8192)
            require(type(value) is dict and set(value)==RESPONSE_FIELDS|{'digest'}
                    and value==seal(value) and value['version']==1
                    and value['ticket']==ticket and ticket in tickets
                    and type(value['httpStatus']) is int and (value['httpStatus']==200 or 400<=value['httpStatus']<=599)
                    and type(value['responseBytes']) is int and 0<=value['responseBytes']<=4_194_304
                    and ishex(value['responseSha256']) and value['contentType'] in ('application/json','text/event-stream'),
                    'broker_private_budget_response_history')
        return {'version':1,'budgetId':self.binding['budgetId'],
            'bindingSha256':hexdigest(self.binding),'providerReservations':count,
            'reservedTokens':count*self.policy.tokens_per_attempt,
            'reservedCostMicrousd':count*self.policy.cost_per_attempt,
            'observedHttpResponses':len(replies),'noAutomaticRefunds':True,
            'gatewayDatabaseIsBudgetAuthority':False,'measuredInvoiceVerified':False,
            'hostFilesystemConfinementVerified':False,'head':head},tickets

    def _commit(self,c):
        c.commit()

    def _transaction(self,fn):
        try:
            self._paths()
            with closing(_connect(self.path)) as c:
                c.execute('BEGIN IMMEDIATE')
                try:
                    state,tickets=self._read(c)
                    value=fn(c,state,tickets)
                    self._paths()
                    self._commit(c)
                    self._paths()
                    return value
                except BaseException:
                    c.rollback();raise
        except ExecutionDenied:raise
        except Exception:raise ExecutionDenied('broker_private_budget_storage_unconfirmed') from None

    def snapshot(self):return self._transaction(lambda c,state,tickets:state)

    def validate_payload(self,payload):
        require(type(payload) is dict and {'model','messages'}<=set(payload)
                and set(payload)<=PAYLOAD_FIELDS,'broker_private_budget_payload')
        require(payload['model']==self.policy.model and type(payload['messages']) is list
                and 1<=len(payload['messages'])<=256,'broker_private_budget_payload')
        require(('max_tokens' in payload) != ('max_completion_tokens' in payload),
                'broker_private_budget_output_limit')
        maximum=payload['max_tokens'] if 'max_tokens' in payload else payload['max_completion_tokens']
        require(type(maximum) is int and 1<=maximum<=self.policy.output_ceiling_tokens,
                'broker_private_budget_output_limit')
        require('n' not in payload or type(payload['n']) is int and payload['n']==1,
                'broker_private_budget_single_completion')
        require('stream' not in payload or type(payload['stream']) is bool,
                'broker_private_budget_payload')
        # Conservative serialized-byte cap, NOT exact model tokenization.
        # Do not assume four bytes per token: punctuation or compact inputs may
        # consume substantially more tokens than that heuristic predicts.
        # Provider-specific overhead and measured invoices remain unverified.
        require(len(_json(payload).encode('utf-8'))<=min(2_000_000,self.policy.input_ceiling_tokens),
                'broker_private_budget_input_bytes')
        for message in payload['messages']:
            require(type(message) is dict and message.get('role') in
                    ('system','user','assistant','tool','developer'),
                    'broker_private_budget_payload')

    def reserve(self,grant,payload):
        self.validate_payload(payload)
        require(type(grant) is dict and
                (grant.get('scope'),grant.get('binding'),grant.get('policy'),grant.get('routeFingerprint'))==
                (self.binding['scope'],self.binding['principalBinding'],self.policy.fingerprint,self.binding['routeFingerprint']),
                'broker_private_budget_scope')
        ticket=grant.get('ticket');fingerprint=hexdigest(payload)
        require(ishex(ticket,32) and ishex(grant.get('brokerId'),32)
                and grant.get('fingerprint')==fingerprint and type(grant.get('epoch')) is int
                and 0<grant['epoch']<10**15 and type(grant.get('instance')) is str
                and 0<len(grant['instance'])<=1024,'broker_private_budget_grant')
        def tx(c,state,tickets):
            require(ticket not in tickets,'broker_private_budget_replay')
            require(state['providerReservations']<self.policy.max_provider_calls,
                    'broker_private_budget_attempt_limit')
            require(state['reservedTokens']+self.policy.tokens_per_attempt<=self.policy.total_token_limit,
                    'broker_private_budget_token_limit')
            require(state['reservedCostMicrousd']+self.policy.cost_per_attempt<=self.policy.total_cost_microusd,
                    'broker_private_budget_cost_limit')
            count=state['providerReservations']+1
            row=seal({'version':1,'sequence':count,'ticket':ticket,
                 'brokerId':grant['brokerId'],'payloadSha256':fingerprint,
                 'epoch':grant['epoch'],'instanceSha256':hexdigest(grant['instance']),
                 'reservedTokens':self.policy.tokens_per_attempt,
                 'reservedCostMicrousd':self.policy.cost_per_attempt,'previous':state['head']})
            c.execute('INSERT INTO attempts VALUES(?,?,?)',(count,ticket,_json(row)))
            c.execute('UPDATE budget_state SET counter=?,head=? WHERE singleton=1',(count,row['digest']))
            return row
        return self._transaction(tx)

    def observe(self,ticket,raw,status,content_type):
        require(ishex(ticket,32) and type(raw) is bytes and len(raw)<=4_194_304
                and type(status) is int and (status==200 or 400<=status<=599)
                and content_type in ('application/json','text/event-stream'),
                'broker_private_budget_response')
        row=seal({'version':1,'ticket':ticket,'httpStatus':status,'responseBytes':len(raw),
                  'responseSha256':hashlib.sha256(raw).hexdigest(),'contentType':content_type})
        def tx(c,state,tickets):
            require(ticket in tickets,'broker_private_budget_reservation_missing')
            old=c.execute('SELECT record FROM responses WHERE ticket=?',(ticket,)).fetchone()
            if old is not None:
                require(old[0]==_json(row),'broker_private_budget_response_conflict')
            else:c.execute('INSERT INTO responses VALUES(?,?)',(ticket,_json(row)))
            return row
        return self._transaction(tx)
