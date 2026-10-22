"""Offline evidence checks, never authorizes recovery or a Gateway launch."""
import json
from n105d_recovery_probe import CASES, PIN

REQUIRED_SOURCES={'hermes_state.py','hermes_state_runtime.py','gateway/runtime_ownership.py',
                  'gateway/platforms/api_server_run_idempotency.py','hermes_state_wal.py'}
BASE_CHECKS={'actual_new_process','native_profile_lock_reacquired','session_survives_crash',
 'epoch_monotonically_advances','only_started_becomes_unknown','same_epoch_recovery_idempotent',
 'old_epoch_refused','no_stale_admission_created','reservation_commit_boundary_respected',
 'native_admission_recovery_exact','real_state_schema','state_integrity','idempotency_integrity'}
EXISTING_CHECKS={'original_run_and_owner_retained','status_not_fabricated','retry_reuses_original_run',
 'changed_request_conflicts','scope_separation','one_reservation_only'}

class ReceiptRejected(ValueError):pass

def need(ok,reason):
    if not ok:raise ReceiptRejected(reason)

def review(report,sources,probe_sha):
    need(type(report) is dict and report.get('sourcePin')==PIN,'source_pin')
    need(report.get('result')=='PASS_SCOPED_NATIVE_CRASH_RECOVERY','terminal_result')
    need(report.get('probeSha256')==probe_sha and report.get('probeUnchanged') is True,'probe_identity')
    need(report.get('temporaryProfileRemoved') is True,'cleanup')
    for key in ('nativeCodeMocked','forcedParentKill','actualConfinement','actualGatewayStarted',
                'pairedStoreAtomicRecoveryAccepted','powerLossTested'):
        need(report.get(key) is False,'scope')
    need(report.get('providerCalls')==0 and report.get('platform') in ('win32','linux'),'scope')
    rows=report.get('cases');need(type(rows) is list and len(rows)==len(CASES) and report.get('caseCount')==len(CASES),'case_count')
    need([r.get('case') for r in rows]==list(CASES),'case_order')
    def original_sources(value,full=True):
        imported=value.get('nativeSources');need(type(imported) is dict and bool(imported),'native_sources')
        if full:need(REQUIRED_SOURCES<=set(imported),'required_native_sources')
        for name,digest in imported.items():need(sources.get(name)==digest,'native_source_mismatch')
    def body(stage,code):
        need(stage.get('exitCode')==code,'process_exit')
        value=stage.get('proof');need(type(value) is dict,'process_evidence')
        try:raw=json.loads(stage['stdout'])
        except (KeyError,TypeError,ValueError):raise ReceiptRejected('raw_stdout_unreadable') from None
        need(raw==value,'raw_stdout_mismatch');return value
    transitions=[]
    for row in rows:
        name=row['case'];before=body(row.get('crash',{}),73);after=body(row.get('recover',{}),0)
        need(before.get('case')==after.get('case')==name and before.get('phase')=='CRASH_BOUNDARY','phase')
        need(after.get('result')=='PASS_NATIVE_RECOVERY_CASE','case_result')
        need(before.get('epoch')==1 and after.get('epoch')==2,'epoch')
        need(type(before.get('pid')) is int and before['pid']>0 and type(after.get('pid')) is int
             and after['pid']>0 and before['pid']!=after['pid'],'process_identity')
        need(before.get('timingInjection') is (name=='before_reservation_commit'),'commit_boundary')
        original_sources(before);original_sources(after)
        missing=name in ('before_reserve','before_reservation_commit')
        expected_checks=BASE_CHECKS|({'uncommitted_reservation_absent'} if missing else EXISTING_CHECKS)
        if name=='started':expected_checks|={'unknown_work_not_reclaimed'}
        actual=after.get('checks');need(type(actual) is dict and set(actual)==expected_checks
                                      and after.get('checkCount')==len(actual),'check_set')
        need(all(v is True for v in actual.values()),'failed_check')
        expected_admission={'queued':'queued','started':'unknown','terminal_gap':'terminal',
                            'terminal_synced':'terminal'}.get(name)
        expected_replay=None if missing else ('completed' if name=='terminal_synced' else 'running')
        need(after.get('nativeAdmissionStatus')==expected_admission and after.get('idempotencyStatus')==expected_replay,
             'native_state_transition')
        need(after.get('recoveredAdmissions')==(1 if name=='started' else 0),'recovery_count')
        need(after.get('gatewayStarted') is False and after.get('pairedStoreAtomicityClaimed') is False
             and after.get('providerCalls')==0,'case_scope')
        for value in (before,after):
            modes=value.get('journalModes')
            need(type(modes) is dict and set(modes)=={'state','idempotency'} and
                 set(modes.values())<={'delete','wal','persist','truncate'},'journal_mode')
        transitions.append({'case':name,'admission':expected_admission,'replay':expected_replay})
    fallback=body(report.get('fallback',{}),0);original_sources(fallback)
    need(fallback.get('result')=='OBSERVED_MEMORY_FALLBACK' and fallback.get('durable') is False
         and fallback.get('missingParentUnchanged') is True and fallback.get('reservationsMade')==0
         and fallback.get('nativeAdmissionImplemented') is False,'fallback')
    return {'result':'PASS_SCOPED_NATIVE_CRASH_RECOVERY','scenarioCount':len(rows),
            'processLifetimes':2*len(rows)+1,'transitions':transitions,'scope':'native stores only',
            'fullGatewayAccepted':False,'automaticRepairAuthorized':False,'pairedStoreAtomicityClaimed':False}
