"""Independent offline F111 full-isolation HTTP receipt consistency verifier.

This validates captured observations and their expected source manifest. It
NEVER executes native code or grants launch/dispatch authority. Expected source
hashes must come from separately verified installed/pinned sources, not blindly
from the receipt itself. Kernel proof is the original execution, not this file.
"""
from __future__ import annotations
import hashlib
import json
import re

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
REQUIRED_IMPORTS=frozenset((
 'packages/claw-hermes/gateway_http_readiness.py',
 'packages/claw-hermes/gateway_store_startup.py',
 'packages/claw-hermes/gateway_live_store_gate.py',
 'vendor-native/hermes_state.py','vendor-native/hermes_state_runtime.py',
 'vendor-native/gateway/runtime_ownership.py',
 'vendor-native/gateway/platforms/api_server_run_idempotency.py',
 'dependencies/aiohttp/web.py'))
PARENT_REQUIRED=frozenset((
 'ordinary_uid_host_positive_controls','profile_prepared_as_gateway_uid',
 'wrong_inode_refused_before_projection','wrong_loop_refused_before_projection',
 'minimal_default_refuses_native_scaffold','default_self_mount_stays_denied',
 'rows_and_inodes_survive_detach','both_duplicates_refused','broker_clean_exit',
 'exactly_two_authenticated_pings','zero_physical_provider_attempts',
 'broker_private_files_unchanged','parent_mount_table_unchanged',
 'no_remaining_loop','no_remaining_fence','no_remaining_scopes',
 'no_forced_cleanup','source_bytes_unchanged'))
CHILD_REQUIRED=frozenset((
 'native_lease_after_exec','explicit_native_layout_only','same_profile_inode',
 'actual_complete_native_layout','wrong_schema_no_bind_or_epoch',
 'refused_http_preserves_caller_lease','same_product_http_serving',
 'ready_inside_private_netns','bad_credentials_401','invalid_auth_bytes_401',
 'agent_route_closed','query_route_closed','mutation_method_closed',
 'ready_after_host_probe','product_startup_verified','clean_only_no_replay',
 'storage_not_http_authority','native_connections_are_real_disk',
 'active_transaction_blocks_product_close','refused_close_keeps_transaction_and_store',
 'no_raw_database_or_lock_open','ready_after_explicit_fixture_settlement',
 'epoch_drift_revokes_http','epoch_restore_does_not_reenable_http',
 'liveness_remains_process_only','http_closed_even_when_storage_transaction_blocks',
 'http_close_retains_native_transaction','private_http_port_closed_before_storage',
 'same_http_product_closes_native_stores','product_closes_both_connections_before_lease',
 'native_aux_inventory_survives_open_close','final_uid_gid','no_groups_or_caps',
 'nnp_seccomp_after_exec','private_namespace_preserved','self_mountinfo_exact_optin',
 'broker_ping','other_host_endpoints_denied','host_paths_private_state_hidden',
 'scratch_starts_fresh','canary_read_write_denied','inherited_fd_closed',
 'live_writer_retains_profile','native_sources_pinned'))
HTTP_SEQUENCE=(('/health/ready','GET',200),('/health/ready','GET',401),
 ('/health/ready','GET',401),('/v1/runs','POST',404),
 ('/health/ready?probe=1','GET',404),('/health/ready','POST',405),
 ('/health/ready','GET',200),('/health/ready','GET',200),
 ('/health/ready','GET',503),('/health/ready','GET',503),('/health/live','GET',200))

class ProofRejected(ValueError):pass

def need(ok,reason):
    if not ok:raise ProofRejected(reason)

def decode(value):
    need(type(value) is str and 0<len(value.encode('utf-8'))<=8*1024*1024,'json_size')
    def pairs(items):
        result={}
        for key,item in items:
            need(key not in result,'duplicate_json_key');result[key]=item
        return result
    try:
        return json.loads(value,object_pairs_hook=pairs,
            parse_constant=lambda _ : (_ for _ in ()).throw(ProofRejected('nonfinite_json')))
    except ProofRejected:raise
    except (ValueError,TypeError):raise ProofRejected('invalid_json') from None

def _checks(obj,required):
    checks=obj['checks']
    need(type(checks) is dict and required<=set(checks),'required_check_missing')
    need(all(v is True for v in checks.values()),'check_not_true')
    need(type(obj['checkCount']) is int and obj['checkCount']==len(checks),'check_count')

def _digest(sources):
    return hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def verify(outer,expected_sources):
    """Reject contradictory/tampered proof; valid proof is still NOT authority."""
    try:
        need(type(outer) is dict and type(expected_sources) is dict,'proof_type')
        need(REQUIRED_IMPORTS<=set(expected_sources),'expected_sources_incomplete')
        for name,digest in expected_sources.items():
            need(type(name) is str and not name.startswith('/') and '\\' not in name
                 and '..' not in name.split('/') and name.endswith('.py'),'source_name')
            need(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest) is not None,'source_hash')
        need(type(outer['nativeExitCode']) is int and outer['nativeExitCode']==0,'native_exit')
        need(outer['sourcesUnchanged'] is True,'source_drift')
        need(outer['sources']==expected_sources,'transport_sources')
        need(outer['nativePin']==PIN,'native_pin')
        report=decode(outer['nativeStdout'])
        need(report['result']=='PASS_SCOPED_NATIVE_STORE_LAYOUT' and report['error'] is None,'native_result')
        need(report['sourceSha256']==expected_sources,'execution_sources')
        _checks(report,PARENT_REQUIRED)
        for key in ('forcedCleanup','nativeHermesGatewayStarted','fullAdmissionGateImplemented',
                    'nativeAgentHttpAdapterStarted','legacyIpcV2Enabled','fullD3BAccepted'):
            need(report[key] is False,'scope_expansion')
        for key in ('realExt4Image','nativeProfileLease','cleanOnlyEpochStartupTested',
                    'pendingStartupRefusalTested','productStoreStartupInvoked','readinessHttpUnderFullIsolation'):
            need(report[key] is True,'native_scope_missing')
        need(type(report['paidModelCalls']) is int and report['paidModelCalls']==0,'provider_call')
        need(type(report['imageBytes']) is int and report['imageBytes']==64*1024*1024,'image_scope')
        events=report['events'];need(type(events) is list and 1<len(events)<=100,'event_limit')
        need(not any('cleanupRetained' in e for e in events),'cleanup_retained')
        negative=[e for e in events if 'negative' in e]
        need(len(negative)==4 and [e['negative'] for e in negative]==
             ['wrong_inode','wrong_loop','minimal_layout','default_metadata'],'negative_controls')
        for event,kind,reason in zip(negative[:3],
                ('StateProjectionRejected','AssertionError','StateProjectionRejected'),
                ('state_projection_profile_identity','lab_volume_device_mismatch','state_projection_profile_inventory')):
            need(type(event['exitCode']) is int and event['exitCode']==2
                 and event['diagnostic']=={'state':'REFUSED','type':kind,'reason':reason},'negative_controls')
        denied=negative[3]
        need(denied['exitCode']==0 and denied['diagnostic']['state']=='DEFAULT_REFUSED'
             and all(denied['diagnostic'][k] is True for k in
                 ('mountinfoDenied','nativeLeaseRefused','lockUnchanged')),'default_policy_weakened')
        broker=[e for e in events if 'brokerExit' in e]
        need(len(broker)==1 and type(broker[0]['brokerExit']) is int
             and broker[0]['brokerExit']==0 and broker[0]['diagnostic']=='','broker_cleanup')

        targets=[(i,e) for i,e in enumerate(events) if e.get('state')=='RESULT']
        need(len(targets)==2 and [e['mode'] for _,e in targets]==['write','read'],'two_lifetimes')
        def phase(name):
            found=[(i,e) for i,e in enumerate(events) if e.get('phase')==name]
            need(len(found)==1,'unique_phase_required');return found[0]
        pids=set();prior_close=-1;first=None;counts=[]
        for epoch,(result_index,target) in enumerate(targets,1):
            mode=target['mode'];pid=target['pid']
            need(type(pid) is int and pid>0 and pid not in pids,'distinct_target_pid');pids.add(pid)
            _checks(target,CHILD_REQUIRED);counts.append(target['checkCount'])
            need(target['result']=='PASS_CONFINED_NATIVE_STORE_LAYOUT','target_result')
            need(target['epoch']==epoch and target['recovered']==0 and target['stateStatus']=='terminal','epoch_or_replay')
            for key in ('realHermesGateway','fullAdmissionGateImplemented','fullD3BAccepted'):
                need(target[key] is False,'target_scope_expansion')
            need(target['fullIsolationReadinessHttp'] is True and target['providerSends']==0,'target_http_scope')
            rec=target['receipt'];need(rec['pid']==pid and rec['afterDrop']['pid']==pid,'pid_binding')
            need(rec['state']=='confined_state_profile' and rec['profile']=='/run/alaz-state/profile','projection_profile')
            need(rec['profileLayout']=='hermes-native-stores-cold-v1','profile_layout')
            need(rec['persistentProfileProjected'] is True and rec['stateDirectoryCount']==1
                 and rec['ambientHostDirectoriesBound']==0,'mount_scope')
            for key in ('hostUserNamespacePreserved','rootPrivilegesDropped'):need(rec[key] is True,'identity_boundary')
            need(rec['legacyIpcV2Activated'] is False and rec['fullD3BAccepted'] is False,'projection_scope')
            uid=rec['afterDrop']
            need(uid['uids']==[23001]*4 and uid['gids']==[23003]*4 and uid['groups']==[],'uid_gid_groups')
            need(uid['nnp']==1 and set(uid['caps'])=={'CapInh','CapPrm','CapEff','CapBnd','CapAmb'}
                 and all(type(v) is int and v==0 for v in uid['caps'].values()),'capabilities')
            fs=rec['filesystem'];need(fs['state']=='enforced' and fs['selfMountMetadata'] is True
                 and fs['metadataReadFileCount']==6 and fs['noNewPrivs'] is True,'landlock_scope')
            need(fs['networkConfinementVerified'] is False,'landlock_overclaim')
            a,listen=phase(mode+'-http-listening');b,probe=phase(mode+'-host-http-probe')
            c,contender=phase(mode+'-native-contender');d,released=phase(mode+'-profile-released')
            e,after=phase(mode+'-native-after-release');f,diag=phase(mode+'-native-stderr');g,closed=phase(mode+'-closed')
            need(prior_close<a<b<result_index<c<d<e<f<g,'lifecycle_order');prior_close=g
            need(listen['pid']==pid and listen['state']=='HTTP_LISTENING' and listen['localReadyStatus']==200,'positive_http_binding')
            port=listen['port'];need(type(port) is int and 0<port<65536 and probe['port']==port,'port_binding')
            need(type(probe['errno']) is int and probe['errno']==111,'host_http_reachable_or_unknown')
            http=target['httpStartup'];need(http['state']=='SERVING' and http['host']=='127.0.0.1'
                 and http['port']==port and http['listenerBindConfirmed'] is True,'http_listener')
            for key in ('agentRoutesEnabled','runtimeAdmissionAuthorized','fullHermesGatewayStarted'):
                need(http[key] is False,'http_scope')
            sequence=target['httpResults']
            need(type(sequence) is list and len(sequence)==len(HTTP_SEQUENCE),'http_observation_count')
            for seen,(path,method,status) in zip(sequence,HTTP_SEQUENCE):
                need((seen['path'],seen['method'],seen['status'])==(path,method,status),'http_sequence')
                body=seen['body'];need(type(body) is dict,'http_body')
                if status in (401,404,405):
                    need(body=={'status':{401:'unauthorized',404:'not_found',405:'method_not_allowed'}[status]},'http_error_body')
                elif path=='/health/live':
                    need(body=={'status':'alive','scope':'process_liveness_only','runtimeAdmissionAuthorized':False},'liveness_overclaim')
                else:
                    need(body=={'status':'ready' if status==200 else 'not_ready','storageReady':status==200,
                        'scope':'native_storage_readiness_only','runtimeAdmissionAuthorized':False,'agentRoutesEnabled':False},'readiness_body')
            done=target['httpClosed'];need(done['state']=='CLOSED' and done['httpCleanupPending'] is False
                 and done['readinessRevoked'] is True and done['callerLeaseMayBeReleased'] is True,'http_close')
            need(contender['exitCode']==77 and contender['proof']['reason']=='profile_already_owned'
                 and contender['proof']['lockUnchanged'] is True,'profile_exclusion')
            need(released['pid']==pid and released['state']=='PROFILE_RELEASED_PROCESS_ALIVE','profile_release_binding')
            need(after['exitCode']==0 and after['proof']['state']=='ACQUIRED_THEN_RELEASED'
                 and after['proof']['inode']==released['lockInode'],'profile_release_order')
            need(closed['state']=='CLOSED','supervisor_closed')
            for key in ('ownedUsersGone','loopAttachmentGone','fenceRemovedAfterCleanup','leaseReleasedLast'):
                need(closed[key] is True,'image_released_too_soon')
            prefix_checks={mode+'_'+suffix for suffix in ('http_listener_unreachable_from_host_netns',
                'scope_contains_confined_user','live_confined_user_blocks_stop','lease_retained',
                'released_profile_process_still_live','image_retained_after_profile_release',
                'detach_before_release','host_scratch_untouched','anchor_empty')}
            need(prefix_checks<=set(report['checks']),'supervisor_boundary_check_missing')
            errors=target['hostEndpointErrnos'];need(set(errors)=={'host_tcp','host_abstract','ambient','sibling'}
                 and all(type(v) is int and v in (1,2,13,111) for v in errors.values()),'ambient_socket_access')
            sources=target['nativeSources'];need(type(sources) is dict and REQUIRED_IMPORTS<=set(sources),'actual_imports_missing')
            need(all(expected_sources.get(n)==h for n,h in sources.items()),'actual_import_source_drift')
            need(target['sourceCount']==len(sources) and target['sourceDigest']==_digest(sources)
                 and target['sourceChunks']==(len(sources)+31)//32,'source_frame_binding')
            exp=target['nextExpectation'];need(exp['native_pin']==PIN and exp['epoch']==epoch
                 and exp['journal_mode']=='delete','expected_generation')
            need(target['journals']=={'state':'delete','replay':'delete'},'journal_mode')
            store=target['stores'];need(set(store)=={'state.db','runs_idempotency.db'},'store_pair')
            need(type(store['state.db']['inode']) is int and store['state.db']['inode']>0
                 and type(store['runs_idempotency.db']['inode']) is int and store['runs_idempotency.db']['inode']>0,'store_inode')
            need(exp['state_identity']==[rec['profileDevice'],store['state.db']['inode']]
                 and exp['replay_identity']==[rec['profileDevice'],store['runs_idempotency.db']['inode']],'store_identity')
            st=target['productStartup'];need(st['state']=='VERIFIED' and st['storageReady'] is True
                 and st['epochObserved']==epoch and st['completedChecks']==['preflight','before_epoch','after_epoch']
                 and st['recoveryPolicy']=='REFUSE_PENDING_NO_REPLAY'
                 and st['automaticRecoveryPerformed'] is False and st['runtimeAdmissionAuthorized'] is False,'startup_sequence')
            if first is None:
                first=target
                need(target['blockedStartup'] is None,'unexpected_first_pending')
                need(all(item['duplicateRefused'] is False for item in store.values()),'first_duplicate_claim')
            else:
                for name in store:
                    need(store[name]['rows']==first['stores'][name]['rows'] and len(store[name]['rows'])==1
                         and store[name]['inode']==first['stores'][name]['inode']
                         and store[name]['duplicateRefused'] is True,'persistence_or_duplicate')
                for key in ('native_pin','state_schema_sha256','replay_schema_sha256','store_instance_id',
                            'application_id','state_identity','replay_identity','journal_mode'):
                    need(exp[key]==first['nextExpectation'][key],'prepared_identity_changed')
                need(exp['instance_id']!=first['nextExpectation']['instance_id'],'instance_not_new')
                blocked=target['blockedStartup'];need(blocked['state']=='FAILED'
                    and blocked['epochMayHaveAdvanced'] is False and blocked['storageReady'] is False,'pending_not_fenced')
                need({'pending_work_blocks_product_start','failed_start_cannot_repeat',
                      'refused_start_preserves_epoch_and_started_row'}<=set(target['checks']),'pending_checks_missing')
        return {'state':'SCOPED_CONFINED_HTTP_PROOF_CONSISTENT','lifetimes':2,'httpObservations':22,
                'targetCheckCounts':counts,'parentChecks':report['checkCount'],
                'sourceCount':len(expected_sources),'newNativeExecution':False,
                'launchAuthorized':False,'fullD3BAccepted':False}
    except ProofRejected:raise
    except (KeyError,TypeError,ValueError,IndexError,AttributeError):
        raise ProofRejected('malformed_proof') from None
