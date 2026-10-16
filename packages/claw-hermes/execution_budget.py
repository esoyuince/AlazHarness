"""Conservative physical-attempt reservations in the existing native state_meta.

Tokens and micro-USD are RESERVED EXPOSURE under declared provider ceilings,
not a tokenizer or a measured invoice. Nothing is refunded automatically.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
import uuid
from recovery_inspector import LocalRecoveryContext, _load, _json

CONFIG='alaz.execution.config.v1.'
CLAIM='alaz.execution.claim.v1.'
HEX32=re.compile(r'[a-f0-9]{32}\Z')
HEX64=re.compile(r'[a-f0-9]{64}\Z')

class ExecutionDenied(ValueError):
    """Bounded reason only; never caller content or a credential."""


def integer(value, name, maximum=10**15, minimum=0):
    if type(value) is not int or not minimum<=value<=maximum:
        raise ExecutionDenied('invalid_'+name)
    return value


def seal(value):
    data={k:v for k,v in value.items() if k!='digest'}
    return data|{'digest':hashlib.sha256(_json(data).encode()).hexdigest()}


@dataclass(frozen=True)
class ExecutionPolicy:
    model: str
    max_provider_calls: int
    max_tool_calls: int
    input_ceiling_tokens: int
    output_ceiling_tokens: int
    total_token_limit: int
    total_cost_microusd: int
    input_rate_microusd_per_million: int
    output_rate_microusd_per_million: int

    def __post_init__(self):
        if type(self.model) is not str or not self.model.strip() or len(self.model.encode())>200:
            raise ExecutionDenied('invalid_model')
        for n in ('max_provider_calls','max_tool_calls'):integer(getattr(self,n),n,1000)
        for n in ('input_ceiling_tokens','output_ceiling_tokens'):integer(getattr(self,n),n,2_000_000,1)
        for n in ('total_token_limit','total_cost_microusd','input_rate_microusd_per_million','output_rate_microusd_per_million'):
            integer(getattr(self,n),n)
        if self.input_ceiling_tokens+self.output_ceiling_tokens>2_000_000:
            raise ExecutionDenied('invalid_context_ceiling')

    @property
    def fingerprint(self):return seal(asdict(self))['digest']
    @property
    def tokens_per_attempt(self):return self.input_ceiling_tokens+self.output_ceiling_tokens
    @property
    def cost_per_attempt(self):
        raw=(self.input_ceiling_tokens*self.input_rate_microusd_per_million+
             self.output_ceiling_tokens*self.output_rate_microusd_per_million)
        return (raw+999999)//1000000


class ExecutionLedger:
    """One profile/principal budget, not a second work scheduler or per-turn queue."""
    def __init__(self,db,context:LocalRecoveryContext,policy:ExecutionPolicy):
        if type(context) is not LocalRecoveryContext or type(policy) is not ExecutionPolicy:
            raise ExecutionDenied('trusted_execution_context_required')
        path=Path(db.db_path)
        if not callable(getattr(db,'_execute_write',None)) or path.is_symlink() or path.resolve()!=context.profile_home/'state.db':
            raise ExecutionDenied('wrong_execution_database')
        self.db,self.context,self.policy=db,context,policy
        self.key=CONFIG+context.scope;self.prefix=CLAIM+context.scope+'.'

    def _write(self,fn):
        try:return self.db._execute_write(fn)
        except ExecutionDenied:raise
        except Exception:raise ExecutionDenied('execution_storage_unconfirmed') from None

    def _epoch(self,c):
        row=c.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        if row is None or tuple(row)!=(self.context.epoch,self.context.instance_id):raise ExecutionDenied('stale_execution_owner')
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name='state_meta'").fetchone():
            raise ExecutionDenied('unsupported_execution_trigger')

    def _checked(self,obj,fields):
        if type(obj) is not dict or set(obj)!=set(fields)|{'digest'} or obj.get('digest')!=seal(obj)['digest']:
            raise ExecutionDenied('execution_history_invalid')
        if type(obj.get('version')) is not int or obj['version']!=1:raise ExecutionDenied('execution_history_invalid')
        if obj.get('scope')!=self.context.scope or obj.get('binding')!=self.context.binding or obj.get('policy')!=self.policy.fingerprint:
            raise ExecutionDenied('execution_policy_or_scope_changed')
        return obj

    def _row(self,obj,ticket):
        row=self._checked(obj,('version','scope','binding','policy','ticket','kind','fingerprint','epoch','instance',
             'state','tokens','costMicrousd','usage','outcome'))
        if type(ticket) is not str or not HEX32.fullmatch(ticket) or row['ticket']!=ticket:raise ExecutionDenied('invalid_execution_ticket')
        if type(row['kind']) is not str or row['kind'] not in ('provider','read_file'):raise ExecutionDenied('invalid_execution_kind')
        if type(row['fingerprint']) is not str or not HEX64.fullmatch(row['fingerprint']):raise ExecutionDenied('invalid_execution_fingerprint')
        integer(row['epoch'],'epoch',self.context.epoch,1)
        if type(row['instance']) is not str or not row['instance'] or len(row['instance'])>1024:raise ExecutionDenied('invalid_execution_instance')
        provider=row['kind']=='provider'
        if type(row['tokens']) is not int or row['tokens']!=(self.policy.tokens_per_attempt if provider else 0):raise ExecutionDenied('invalid_token_reservation')
        if type(row['costMicrousd']) is not int or row['costMicrousd']!=(self.policy.cost_per_attempt if provider else 0):raise ExecutionDenied('invalid_cost_reservation')
        if row['state']=='reserved':
            if row['usage'] is not None or row['outcome'] is not None:raise ExecutionDenied('invalid_unsettled_claim')
        elif row['state']=='settled':
            if row['outcome'] not in ('response','transport_error','tool_return','unknown_usage'):raise ExecutionDenied('invalid_execution_outcome')
            allowed=('response','transport_error','unknown_usage') if provider else ('tool_return',)
            if row['outcome'] not in allowed:raise ExecutionDenied('execution_kind_outcome_conflict')
            self._usage(row['usage'],provider=provider)
        else:raise ExecutionDenied('invalid_execution_state')
        return row

    def _usage(self,value,*,provider=True):
        if value is None:return None
        if not provider or type(value) is not dict or set(value)!={'input_tokens','output_tokens'}:
            raise ExecutionDenied('invalid_observed_usage')
        integer(value['input_tokens'],'input_usage',self.policy.input_ceiling_tokens)
        integer(value['output_tokens'],'output_usage',self.policy.output_ceiling_tokens)
        return dict(value)

    def _state(self,c,*,initialize=False):
        self._epoch(c)
        stored=c.execute('SELECT value FROM state_meta WHERE key=?',(self.key,)).fetchone()
        rows=c.execute('SELECT key,value FROM state_meta WHERE key GLOB ? LIMIT 2001',(self.prefix+'*',)).fetchall()
        if len(rows)>2000:raise ExecutionDenied('execution_history_limit')
        if stored is None:
            if rows or not initialize:raise ExecutionDenied('execution_budget_missing')
            cfg=seal({'version':1,'scope':self.context.scope,'binding':self.context.binding,'policy':self.policy.fingerprint,
                 'providerCalls':0,'toolCalls':0,'reservedTokens':0,'reservedCostMicrousd':0,'quarantined':False})
        else:cfg=self._checked(_load(stored[0],16384),('version','scope','binding','policy','providerCalls','toolCalls','reservedTokens','reservedCostMicrousd','quarantined'))
        counts={'providerCalls':0,'toolCalls':0,'reservedTokens':0,'reservedCostMicrousd':0};bytes_seen=0
        for key,text in rows:
            if type(text) is not str:raise ExecutionDenied('execution_history_invalid')
            bytes_seen+=len(text.encode())
            if bytes_seen>8388608:raise ExecutionDenied('execution_history_limit')
            row=self._row(_load(text,16384),key[len(self.prefix):])
            counts['providerCalls' if row['kind']=='provider' else 'toolCalls']+=1
            counts['reservedTokens']+=row['tokens'];counts['reservedCostMicrousd']+=row['costMicrousd']
        for k,v in counts.items():
            if type(cfg[k]) is not int or cfg[k]!=v:raise ExecutionDenied('execution_history_inconsistent')
        if type(cfg['quarantined']) is not bool:raise ExecutionDenied('execution_history_invalid')
        if counts['providerCalls']>self.policy.max_provider_calls or counts['toolCalls']>self.policy.max_tool_calls or counts['reservedTokens']>self.policy.total_token_limit or counts['reservedCostMicrousd']>self.policy.total_cost_microusd:
            raise ExecutionDenied('execution_limits_inconsistent')
        return cfg

    def initialize(self):
        def tx(c):
            cfg=self._state(c,initialize=True)
            c.execute('INSERT OR IGNORE INTO state_meta(key,value) VALUES(?,?)',(self.key,_json(cfg)))
            return dict(cfg)
        return self._write(tx)

    def snapshot(self):
        # Serialized read under the native owner; no SQL data mutation or budget reset.
        return self._write(lambda c:dict(self._state(c)))

    def claim(self,kind,fingerprint):
        if type(kind) is not str or kind not in ('provider','read_file'):raise ExecutionDenied('invalid_execution_kind')
        if type(fingerprint) is not str or not HEX64.fullmatch(fingerprint):raise ExecutionDenied('invalid_execution_fingerprint')
        def tx(c):
            cfg=self._state(c)
            if cfg['quarantined']:raise ExecutionDenied('execution_budget_quarantined')
            provider=kind=='provider';counter='providerCalls' if provider else 'toolCalls'
            limit=self.policy.max_provider_calls if provider else self.policy.max_tool_calls
            if cfg[counter]>=limit:raise ExecutionDenied('provider_attempt_limit' if provider else 'tool_attempt_limit')
            tokens=self.policy.tokens_per_attempt if provider else 0;cost=self.policy.cost_per_attempt if provider else 0
            if cfg['reservedTokens']+tokens>self.policy.total_token_limit:raise ExecutionDenied('token_exposure_limit')
            if cfg['reservedCostMicrousd']+cost>self.policy.total_cost_microusd:raise ExecutionDenied('cost_exposure_limit')
            ticket=uuid.uuid4().hex
            row=seal({'version':1,'scope':self.context.scope,'binding':self.context.binding,'policy':self.policy.fingerprint,
                'ticket':ticket,'kind':kind,'fingerprint':fingerprint,'epoch':self.context.epoch,'instance':self.context.instance_id,
                'state':'reserved','tokens':tokens,'costMicrousd':cost,'usage':None,'outcome':None})
            cfg[counter]+=1;cfg['reservedTokens']+=tokens;cfg['reservedCostMicrousd']+=cost
            c.execute('INSERT INTO state_meta(key,value) VALUES(?,?)',(self.prefix+ticket,_json(row)))
            c.execute('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(cfg)),self.key))
            return dict(row)
        return self._write(tx)

    def quarantine(self):
        def tx(c):
            cfg=self._state(c);cfg['quarantined']=True
            c.execute('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(cfg)),self.key))
            return {'quarantined':True,'retryAllowed':False}
        return self._write(tx)

    def settle(self,ticket,usage,outcome):
        if type(ticket) is not str or not HEX32.fullmatch(ticket):raise ExecutionDenied('invalid_execution_ticket')
        if type(outcome) is not str or outcome not in ('response','transport_error','tool_return','unknown_usage'):
            raise ExecutionDenied('invalid_execution_outcome')
        # Freeze caller data before entering a retriable native transaction.
        try:frozen=_load(_json(usage),16384)
        except Exception:raise ExecutionDenied('invalid_observed_usage') from None
        def tx(c):
            cfg=self._state(c)
            found=c.execute('SELECT value FROM state_meta WHERE key=?',(self.prefix+ticket,)).fetchone()
            if found is None:raise ExecutionDenied('execution_claim_missing')
            row=self._row(_load(found[0],16384),ticket)
            if row['epoch']!=self.context.epoch or row['instance']!=self.context.instance_id:raise ExecutionDenied('stale_execution_claim')
            allowed=('response','transport_error','unknown_usage') if row['kind']=='provider' else ('tool_return',)
            if outcome not in allowed:raise ExecutionDenied('execution_kind_outcome_conflict')
            try:value=self._usage(frozen,provider=row['kind']=='provider')
            except ExecutionDenied:
                cfg['quarantined']=True
                c.execute('UPDATE state_meta SET value=? WHERE key=?',(_json(seal(cfg)),self.key))
                return {'rejectedUsage':True,'retryAllowed':False}
            if row['state']=='settled':
                if row['usage']!=value or row['outcome']!=outcome:raise ExecutionDenied('execution_settlement_conflict')
                return dict(row)
            row=seal(row|{'state':'settled','usage':value,'outcome':outcome})
            c.execute('UPDATE state_meta SET value=? WHERE key=?',(_json(row),self.prefix+ticket))
            return dict(row)
        result=self._write(tx)
        if result.get('rejectedUsage'):raise ExecutionDenied('provider_usage_out_of_contract')
        return result
