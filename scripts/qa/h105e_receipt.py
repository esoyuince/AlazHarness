"""Pure H105E evidence consistency checks; NEVER runtime launch authority."""
from __future__ import annotations
import json
import re

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
CASES=('reservation_only','started_pair','state_terminal_replay_running',
       'replay_completed_state_started','uncommitted_reservation','memory_fallback')
CLASSIFICATIONS=(
    'REPLAY_WITHOUT_ADMISSION_REQUIRES_RECONCILIATION','UNKNOWN_EXECUTION_BLOCKED',
    'STATE_TERMINAL_REPLAY_RUNNING_REQUIRES_RECONCILIATION',
    'REPLAY_COMPLETED_STATE_UNKNOWN_REQUIRES_RECONCILIATION',
    'UNCOMMITTED_REPLAY_ROLLED_BACK','VOLATILE_STORE_NOT_ADMITTED')
REQUIRED_IMPORTS={'vendor-native/hermes_state.py','vendor-native/hermes_state_runtime.py',
    'vendor-native/gateway/platforms/api_server_run_idempotency.py',
    'vendor-native/gateway/runtime_ownership.py'}

class ReceiptRejected(ValueError):pass

def require(ok,reason):
    if not ok:raise ReceiptRejected(reason)

def load(text):
    require(type(text) is str and 0<len(text.encode('utf-8'))<=8*1024*1024,'receipt_size')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate_key');result[key]=value
        return result
    try:
        return json.loads(text,object_pairs_hook=pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(ReceiptRejected('nonfinite')))
    except (ValueError,TypeError) as exc:
        if isinstance(exc,ReceiptRejected):raise
        raise ReceiptRejected('invalid_json') from None

def true_checks(value):
    require(type(value) is dict and bool(value) and all(v is True for v in value.values()),'failed_or_missing_check')

def verify(outer,manifest):
    """Compare raw outcomes, source identity and scope; no new native execution."""
    try:
        require(type(outer) is dict and type(manifest) is dict,'receipt_type')
        require(type(outer['exitCode']) is int and outer['exitCode']==0,'transport_exit')
        require(outer['sourceUnchanged'] is True and outer['temporaryRootRemoved'] is True,'transport_cleanup')
        require(outer['rootUsed'] is False and outer['uid']==23001,'transport_scope')
        require(outer['stderr']=='','parent_error')
        require(outer['sourceSha256']==manifest and REQUIRED_IMPORTS<=set(manifest),'transport_sources')
        require(all(type(h) is str and re.fullmatch('[0-9a-f]{64}',h) for h in manifest.values()),'source_digest')
        proof=load(outer['stdout'])
        require(proof['result']=='PASS_NATIVE_CRASH_BOUNDARIES' and proof['error'] is None,'native_result')
        require(proof['nativePin']==PIN and proof['sourceSha256']==manifest,'native_pin')
        require((proof['uid'],proof['gid'])==(23001,23003),'native_identity')
        for key in ('rootUsed','mountsChanged','nativeMethodsMocked','powerLossTested',
                    'pairedTransactionAtomicityClaimed','fullConfinementTested','realGatewayStarted','fullD3BAccepted'):
            require(proof[key] is False,'scope_expansion')
        require(proof['providerCalls']==0,'provider_call')
        true_checks(proof['checks']);events=proof['events']
        require(type(events) is list and len(events)==12,'twelve_children_required')
        all_pids=set();recovered=[]
        for index,case in enumerate(CASES):
            pair=[]
            for offset,phase in enumerate(('crash','recover')):
                event=events[2*index+offset]
                require((event['case'],event['phase'])==(case,phase),'case_order')
                require(type(event['exitCode']) is int and event['exitCode']==(73 if offset==0 else 0),'child_exit')
                child=load(event['stdout']);pair.append(child)
                require((child['case'],child['phase'])==(case,phase),'child_binding')
                require(child['state']==('CRASH_CHECKPOINT' if offset==0 else 'RECOVERED_OBSERVATION'),'child_state')
                pid=child['pid'];require(type(pid) is int and pid>0 and pid not in all_pids,'distinct_child_pid');all_pids.add(pid)
                true_checks(child['checks'])
                require(type(child['checkCount']) is int and child['checkCount']==len(child['checks']),'child_check_count')
                require(child['checks']['real_native_profile_owned'] is True,'profile_unowned')
                require(child['checks']['native_state_connection_on_file'] is True,'state_not_on_disk')
                require(child['nativePin']==PIN,'child_pin')
                for key in ('nativeFunctionsReplaced','rootUsed','fullConfinementTested','httpAdmissionTested','realGatewayStarted'):
                    require(child[key] is False,'child_scope_expansion')
                require(child['providerCalls']==0,'child_provider_call')
                imported=child['sourceHashes'];require(REQUIRED_IMPORTS<=set(imported),'native_import_missing')
                require(all(manifest.get(n)==h for n,h in imported.items()),'import_hash_mismatch')
                d=child['data'];require(d['journals']['state'] in ('delete','truncate','persist','wal'),'state_journal')
                require(d['journals']['replay']==('memory' if case=='memory_fallback' else 'delete'),'replay_journal')
                require(all(type(v) is int and v>=2 for v in d['synchronous'].values()),'sync_contract')
                require(type(child['lockInode']) is int and child['lockInode']>0,'lock_identity')
                require(child['replayTransactionOpen'] is (case=='uncommitted_reservation' and phase=='crash'),'transaction_checkpoint')
                erows=child['epochRows']
                if case=='memory_fallback':require(erows==[],'volatile_epoch_advanced')
                else:
                    require(len(erows)==1 and erows[0]['epoch']==offset+1,'epoch_exact_increment')
                    require(erows[0]['instanceId']=='h105e-'+case+('-old' if offset==0 else '-new'),'instance_binding')
                replay=child['replayRows']
                if case=='memory_fallback' and offset==1:require(replay==[],'volatile_record_retained')
                else:
                    wanted='completed' if case=='replay_completed_state_started' else 'running'
                    require(replay==[{'runId':'run_'+('1'*32),'fingerprint':'a'*64,'status':{'status':wanted}}],'replay_rows_changed')
            first,last=pair;recovered.append(last['data']['classification'])
            require(first['lockInode']==last['lockInode'],'lock_replaced')
            require(last['checks']['native_profile_released_after_stores_close'] is True,'close_order')
            require(last['checks']['lock_inode_not_replaced'] is True,'lock_replaced')
            require(last['data']['classification']==CLASSIFICATIONS[index],'wrong_classification')
            require(last['data']['retryAuthorized'] is False,'retry_authorized')
            if case=='memory_fallback':
                require(last['checks']['volatile_reservation_lost_after_exit'] is True,'volatile_loss_not_proven')
                require(first['stateRows']==last['stateRows']==[],'volatile_admission_created')
                continue
            require(last['data']['beforeRecoveryRows']==first['stateRows'],'before_after_rows_mismatch')
            require(last['data']['epoch']==2 and last['data']['recovered']==(1 if case in ('started_pair','replay_completed_state_started') else 0),'recovery_count')
            require(last['checks']['stale_epoch_write_refused'] is True,'stale_epoch_not_refused')
            require(last['checks']['state_integrity_ok'] is True and last['checks']['replay_integrity_ok'] is True,'integrity_not_checked')
            if case in ('reservation_only','uncommitted_reservation'):
                require(first['stateRows']==last['stateRows']==[],'missing_admission_synthesized')
                if case=='uncommitted_reservation':
                    require(first['checks']['native_insert_not_committed'] is True,'uncommitted_boundary_missing')
                    require(last['checks']['uncommitted_insert_rolled_back'] is True,'rollback_not_proven')
                    require(first['data']['checkpointSourceSha256']==manifest['vendor-native/gateway/platforms/api_server_run_idempotency.py'],'checkpoint_source')
                    require(type(first['data']['checkpointLine']) is int and first['data']['checkpointLine']>0,'checkpoint_line')
            else:
                require(len(first['stateRows'])==len(last['stateRows'])==1,'admission_count')
                a,b=first['stateRows'][0],last['stateRows'][0]
                require(all(a[k]==b[k] for k in ('admission_id','request_id','owner_epoch','generation','outcome')),'admission_identity_changed')
                require(a['request_id']=='h105e-request' and a['owner_epoch']==a['generation']==1,'native_row_identity')
                terminal=case=='state_terminal_replay_running'
                require(a['status']==('terminal' if terminal else 'started') and b['status']==('terminal' if terminal else 'unknown'),'unsafe_state_disposition')
                require(a['outcome']==('completed' if terminal else None),'outcome_changed')
                if not terminal:
                    require(last['checks']['unknown_never_claimed_again'] is True and last['checks']['old_epoch_cannot_settle'] is True,'unknown_execution_not_fenced')
        return {'result':'VERIFIED_SCOPED_NATIVE_CRASH_PROOF','cases':6,'childProcesses':len(all_pids),
            'recoveryClassifications':recovered,'launchAuthorized':False,'fullD3BAccepted':False}
    except ReceiptRejected:raise
    except (TypeError,KeyError,ValueError,IndexError,AttributeError):
        raise ReceiptRejected('malformed_receipt') from None
