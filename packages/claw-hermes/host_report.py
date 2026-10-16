"""HYB-005C: read-only host report, reusing the native recovery/ledger validators.

All sections are captured inside LocalRecoveryInspector's existing two-store
read transaction and checked for concurrent change afterwards. The v1 execution
ledger is profile/principal-scoped, NOT attributable to an individual run. No
network request, state creation, claim, settlement, refund or retry occurs here.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
import re
import sqlite3
import time
from execution_budget import ExecutionDenied, ExecutionLedger, ExecutionPolicy
from recovery_inspector import LocalRecoveryContext, LocalRecoveryInspector, EvidenceError, RESULT, PIN, _load, _json


@dataclass(frozen=True)
class _NoWriteOwner:
    """Path-only validation adapter. Never masquerades as a native write owner."""
    db_path: str

    def _execute_write(self, callback):
        raise ExecutionDenied('report_writes_forbidden')


def _counter(value):
    return type(value) is int and 0 <= value <= 10**15


def _native_usage(value):
    """Missing or invalid measurements are not silently replaced with zero."""
    result={'source':'native_run_aggregate','scope':'run','coverage':'unavailable',
            'inputTokens':None,'outputTokens':None,'totalTokens':None,
            'physicalAttemptCoverageVerified':False,'billedAmount':None}
    if type(value) is not dict:
        return result
    fields={'input_tokens':'inputTokens','output_tokens':'outputTokens','total_tokens':'totalTokens'}
    if any(k in value and not _counter(value[k]) for k in fields):
        return result | {'coverage':'invalid'}
    for key,field in fields.items():
        if key in value:result[field]=value[key]
    i,o,t=(result[k] for k in ('inputTokens','outputTokens','totalTokens'))
    if i is not None and o is not None and t is not None and i+o!=t:
        return result | {'coverage':'invalid'}
    result['coverage']='complete_fields' if i is not None and o is not None and t is not None else 'partial_fields'
    if not any(k in value for k in fields):result['coverage']='unavailable'
    return result


def _execution_snapshot(conn,context,policy):
    # Reuse EXACTLY the production v1 consistency/identity/cap validators. The
    # adapter provides no write operation; _state/_row below issue SELECT only.
    validator=ExecutionLedger(_NoWriteOwner(str(context.profile_home/'state.db')),context,policy)
    cfg=validator._state(conn)
    rows=conn.execute('SELECT key,value FROM state_meta WHERE key GLOB ? ORDER BY key LIMIT 2001',
                      (validator.prefix+'*',)).fetchall()
    claims=[validator._row(_load(text,16384),key[len(validator.prefix):]) for key,text in rows]
    providers=[row for row in claims if row['kind']=='provider']
    tools=[row for row in claims if row['kind']=='read_file']
    known=[row['usage'] for row in providers if row['usage'] is not None]
    unknown=len(providers)-len(known)
    # A nonempty usage value on an error/unknown outcome cannot prove an observed
    # successful response. The ledger preserves it; the report refuses to label it.
    if any(row['usage'] is not None and row['outcome']!='response' for row in providers):
        raise ExecutionDenied('usage_outcome_not_reportable')
    sums={'inputTokens':sum(v['input_tokens'] for v in known),
          'outputTokens':sum(v['output_tokens'] for v in known)} if known or not providers else {'inputTokens':None,'outputTokens':None}
    sums['totalTokens']=sum(sums.values()) if sums['inputTokens'] is not None else None
    coverage='no_reserved_attempts' if not providers else 'complete_for_retained_claims' if unknown==0 else 'partial' if known else 'unknown'
    return {'available':True,'source':'execution_ledger_v1','scope':'profile_principal',
            'runAttribution':'unavailable','attributedToThisRun':False,
            'validatedRetainedHistory':True,'policyFingerprint':policy.fingerprint,'model':policy.model,
            'snapshotDigest':cfg['digest'],'quarantined':cfg['quarantined'],
            'providerAttempts':{'reserved':len(providers),
                'settled':sum(row['state']=='settled' for row in providers),
                'unsettled':sum(row['state']=='reserved' for row in providers),
                'usageKnown':len(known),'usageUnknown':unknown,
                'transportErrors':sum(row['outcome']=='transport_error' for row in providers),
                'wireDeliveryCount':None,'wireDeliveryProof':'reservation_is_not_delivery'},
            'observedUsage':dict(sums,coverage=coverage,source='provider_reported_usage_in_retained_claims',
                                 tokenizerVerified=False,includesUnconfiguredProviders=False),
            'toolAttempts':{'reserved':len(tools),'handlerReturns':sum(row['outcome']=='tool_return' for row in tools),
                            'successfulEffects':None},
            'reservedExposure':{'tokens':cfg['reservedTokens'],'costMicrousd':cfg['reservedCostMicrousd'],
                                'currency':'USD','basis':'configured_maximum_per_attempt','isInvoice':False,
                                'actualBilledMicrousd':None,'tariffVerified':False,'automaticRefund':False},
            'configuredLimits':{'providerCalls':policy.max_provider_calls,'toolCalls':policy.max_tool_calls,
                                'tokens':policy.total_token_limit,'costMicrousd':policy.total_cost_microusd},
            'remainingReservedCapacity':{'providerCalls':policy.max_provider_calls-cfg['providerCalls'],
                                         'toolCalls':policy.max_tool_calls-cfg['toolCalls'],
                                         'tokens':policy.total_token_limit-cfg['reservedTokens'],
                                         'costMicrousd':policy.total_cost_microusd-cfg['reservedCostMicrousd'],
                                         'grantsExecutionPermission':False}}


def unavailable_report(reason='unverified_evidence'):
    return {'hostReportVersion':1,'reportStatus':'unverified','reason':reason,'snapshotOnly':True,
            'writesPerformed':False,'retryAllowed':False,'repairAllowed':False,'executionAllowed':False,
            'task':{'classification':'unverified','canonicalVerified':False,'taskSucceeded':False,'requiresOperator':True},
            'nativeReportedUsage':{'available':False},'execution':{'available':False},
            'usageComparison':{'comparable':False,'reason':'evidence_unverified'},'sourceCommit':PIN}


class HostReportInspector(LocalRecoveryInspector):
    """Trusted co-located host API. Policy/context NEVER come from an agent grant."""
    def __init__(self,context:LocalRecoveryContext,policy:ExecutionPolicy,*,clock=time.time):
        if type(context) is not LocalRecoveryContext or type(policy) is not ExecutionPolicy:
            raise TypeError('trusted_report_context_required')
        super().__init__(context,clock=clock)
        self.policy=policy

    def inspect(self,*,body:dict,idempotency_key:str,observed:dict)->dict:
        checked=super().inspect(body=body,idempotency_key=idempotency_key,observed=observed)
        # _read only returns _report after BOTH snapshots survive epoch/version
        # and path-identity checks. Failed checks never expose a partial section.
        if '_report' not in checked:
            return unavailable_report(checked.get('reason','unverified_evidence'))
        return checked['_report']

    def inspect_scope(self)->dict:
        """Explicit scope-only observation for auxiliary calls with no selected run.

        Only the existing state.db is inspected; no synthetic task/replay row is
        created. The trusted credential/policy must match the retained ledger.
        """
        try:
            path=self.context.profile_home/'state.db'
            if not path.is_file() or path.is_symlink() or path.resolve().parent!=self.context.profile_home:
                raise EvidenceError('storage_unavailable')
            identity=(path.stat().st_dev,path.stat().st_ino)
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as conn:
                conn.execute('PRAGMA query_only=ON');conn.execute('PRAGMA trusted_schema=OFF')
                for table in ('state_meta','runtime_epoch'):
                    row=conn.execute('SELECT type FROM sqlite_master WHERE name=?',(table,)).fetchone()
                    if row is None or row[0]!='table':raise EvidenceError('unsupported_schema')
                version=conn.execute('PRAGMA data_version').fetchone()[0]
                conn.execute('BEGIN')
                try:execution=_execution_snapshot(conn,self.context,self.policy)
                finally:conn.rollback()
                epoch=conn.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
                if epoch is None or tuple(epoch)!=(self.context.epoch,self.context.instance_id) or conn.execute('PRAGMA data_version').fetchone()[0]!=version:
                    raise EvidenceError('concurrent_state_change')
            if identity!=(path.stat().st_dev,path.stat().st_ino):raise EvidenceError('store_replaced')
            warnings=['scope_only_no_task_selected','reserved_exposure_is_not_an_invoice']
            if execution['providerAttempts']['usageUnknown']:warnings.append('some_reserved_attempts_have_unknown_usage')
            if execution['quarantined']:warnings.append('execution_budget_quarantined')
            return {'hostReportVersion':1,'reportStatus':'verified_scope_snapshot','scopeOnly':True,
                'snapshotOnly':True,'writesPerformed':False,'retryAllowed':False,'repairAllowed':False,'executionAllowed':False,
                'sourceCommit':PIN,'profileBinding':self.context.binding,'epoch':self.context.epoch,
                'task':{'classification':'not_selected','canonicalVerified':False,'taskSucceeded':False,
                        'requiresOperator':False,'goalAchievementIndependentlyVerified':False},
                'nativeReportedUsage':{'available':False,'coverage':'no_task_selected'},'execution':execution,
                'usageComparison':{'comparable':False,'reason':'no_task_selected','numericDifference':None},'warnings':warnings}
        except (ExecutionDenied,EvidenceError) as exc:
            reason=str(exc) if re.fullmatch('[a-z_]{1,80}',str(exc)) else 'unverified_evidence'
            return unavailable_report(reason)
        except (OSError,sqlite3.Error):return unavailable_report('storage_unavailable')
        except (ValueError,TypeError,KeyError,IndexError,RecursionError,OverflowError,AttributeError):
            return unavailable_report('malformed_evidence')

    def _classify(self,conn,row,reservation,saved,body,http,target):
        known_statuses={'queued','running','waiting_for_approval','stopping','completed','failed','cancelled','interrupted','unknown'}
        status=http.get('status')
        admission_outcome=row.get('outcome') if type(row) is dict else None
        if type(status) is not str or status not in known_statuses:
            raise EvidenceError('unsupported_report_status')
        if admission_outcome is not None and (type(admission_outcome) is not str or admission_outcome not in {'completed','failed','cancelled','interrupted'}):
            raise EvidenceError('unsupported_report_outcome')
        checked=super()._classify(conn,row,reservation,saved,body,http,target)
        task={k:checked[k] for k in ('runId','classification','canonicalVerified','requiresOperator',
              'admissionId','sessionId','executionGeneration','outcome','resultDigest','requestClosed') if k in checked}
        task.setdefault('canonicalVerified',False);task.setdefault('requiresOperator',True)
        task['taskSucceeded']=checked.get('taskSucceeded',False)
        task['successBasis']='native_terminal_contract'
        task['goalAchievementIndependentlyVerified']=False
        task['nativeStatus']=http.get('status')
        task['nativeAdmissionOutcome']=row.get('outcome') if row else None
        task['admissionOutcomeIsTaskSuccess']=False
        task['completionReason']=None
        if checked.get('classification')=='canonical_terminal_verified':
            record=conn.execute('SELECT value FROM state_meta WHERE key=?',(RESULT+checked['admissionId'],)).fetchone()
            reason=_load(record[0])['result'].get('turn_exit_reason')
            # Do not leak arbitrary diagnostic/user/provider text as a "reason".
            if type(reason) is str and (reason in {'completed','failed','interrupted','cancelled','budget_exhausted'}
                 or re.fullmatch(r'max_iterations_reached\([0-9]{1,9}/[0-9]{1,9}\)',reason)):
                task['completionReason']=reason
        warnings=['execution_totals_not_attributed_to_run','reserved_exposure_is_not_an_invoice',
                  'native_completion_is_not_independent_goal_verification']
        try:
            execution=_execution_snapshot(conn,self.context,self.policy)
        except ExecutionDenied as exc:
            code=str(exc) if re.fullmatch('[a-z_]{1,80}',str(exc)) else 'execution_evidence_invalid'
            execution={'available':False,'reason':code,'scope':'profile_principal','attributedToThisRun':False}
        except (ValueError,TypeError,KeyError,IndexError,RecursionError,OverflowError):
            execution={'available':False,'reason':'execution_evidence_invalid','scope':'profile_principal','attributedToThisRun':False}
        terminal=checked.get('classification')=='canonical_terminal_verified'
        native=_native_usage(http.get('usage')) if terminal else {'available':False,'coverage':'unverified_live_usage',
            'inputTokens':None,'outputTokens':None,'totalTokens':None,'source':'native_run_aggregate','scope':'run'}
        if execution['available'] and execution['providerAttempts']['usageUnknown']:
            warnings.append('some_reserved_attempts_have_unknown_usage')
        if execution.get('quarantined'):warnings.append('execution_budget_quarantined')
        if not execution['available']:warnings.append('execution_evidence_unavailable')
        if not checked.get('canonicalVerified'):warnings.append('task_canonical_record_not_verified')
        if native.get('coverage') in ('invalid','unavailable','partial_fields'):warnings.append('native_usage_not_complete')
        result={'hostReportVersion':1,'reportStatus':'verified_snapshot' if execution['available'] and checked.get('canonicalVerified') else 'partial_snapshot',
                'snapshotOnly':True,'writesPerformed':False,'retryAllowed':False,'repairAllowed':False,'executionAllowed':False,
                'sourceCommit':PIN,'profileBinding':self.context.binding,'epoch':self.context.epoch,
                'requestFingerprint':checked['requestFingerprint'],'task':task,'nativeReportedUsage':native,
                'execution':execution,'usageComparison':{'comparable':False,'reason':'v1_claims_have_no_trusted_run_binding',
                  'numericDifference':None},'warnings':warnings}
        return {**checked,'_report':result}


def render_text(report:dict)->str:
    """Plain host console view; deliberately contains no prompt, output or secrets."""
    unknown='UNKNOWN'
    def show(value):return unknown if value is None else str(value)
    task=report['task'];native=report['nativeReportedUsage'];execution=report['execution']
    lines=['AlazHarness host report v1',
           'Snapshot: '+report['reportStatus'],
           'Native task result: '+show(task.get('nativeStatus'))+'; nativeCompleted='+str(task.get('taskSucceeded',False)).lower(),
           'Task evidence: '+task['classification'],
           'Completion reason: '+show(task.get('completionReason')),
           'Native run usage (input/output/total): '+ '/'.join(show(native.get(k)) for k in ('inputTokens','outputTokens','totalTokens'))]
    if execution.get('available'):
        usage=execution['observedUsage'];attempts=execution['providerAttempts'];reserve=execution['reservedExposure']
        lines+=['Profile/principal observed usage (input/output/total): '+ '/'.join(show(usage[k]) for k in ('inputTokens','outputTokens','totalTokens')),
                'Usage coverage: '+usage['coverage']+'; unknown attempts='+str(attempts['usageUnknown']),
                'Reserved provider attempts: '+str(attempts['reserved'])+'; wire delivery count: UNKNOWN',
                'Reserved exposure: '+str(reserve['tokens'])+' tokens; '+str(reserve['costMicrousd'])+' micro-USD (NOT an invoice)']
    else:lines+=['Execution usage/budget: UNKNOWN ('+execution.get('reason','unverified')+')']
    lines+=['Native completion is NOT independent verification of the requested goal.',
            'Scope totals are NOT attributed to this task; numeric comparison unavailable.',
            'Read-only snapshot. No execution permission, retry, repair or automatic refund.']
    return '\n'.join(lines)+'\n'
