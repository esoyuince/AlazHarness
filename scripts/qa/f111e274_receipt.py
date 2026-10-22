"""Offline F111E274 receipt consistency; no runtime/launch authority."""
import hashlib
import json

class InvalidReceipt(ValueError):pass

def need(ok,code):
    if not ok:raise InvalidReceipt(code)

def true_checks(value,count):
    need(type(value) is dict and len(value)==count and all(v is True for v in value.values()),'checks')

def verify(outer,manifest):
    try:
        need(outer['unitsExitCode']==outer['nativeExitCode']==0 and outer['sourcesUnchanged'] is True,'execution')
        need(outer['sources']==manifest,'manifest')
        result=json.loads(outer['nativeStdout']);true_checks(result['checks'],44)
        need(result['checkCount']==44 and result['error'] is None and result['forcedCleanup'] is False,'parent')
        need(result['result']=='PASS_SCOPED_NATIVE_STORE_LAYOUT' and result['readinessHttpUnderFullIsolation'] is True,'scope')
        for key in ('nativeHermesGatewayStarted','nativeAgentHttpAdapterStarted','fullAdmissionGateImplemented','legacyIpcV2Enabled','fullD3BAccepted'):
            need(result[key] is False,'expanded_scope')
        need(result['paidModelCalls']==0 and result['imageBytes']==64*1024*1024 and result['realExt4Image'] is True,'image')
        need(result['sourceSha256']==manifest,'sources')
        targets=[e for e in result['events'] if e.get('state')=='RESULT']
        need(len(targets)==2 and [e['mode'] for e in targets]==['write','read'],'lifetimes')
        need(targets[0]['pid']!=targets[1]['pid'],'pids')
        phases={e['phase']:e for e in result['events'] if 'phase' in e}
        for index,target in enumerate(targets):
            mode=target['mode'];need(target['result']=='PASS_CONFINED_NATIVE_STORE_LAYOUT','target')
            true_checks(target['checks'],49 if index==0 else 54)
            need(target['checkCount']==len(target['checks']),'target_count')
            proof=target['receipt'];after=proof['afterDrop']
            need(target['pid']==proof['pid']==after['pid'],'pid_binding')
            need(after['uids']==[23001]*4 and after['gids']==[23003]*4 and after['groups']==[],'identity')
            need(all(type(n) is int and n==0 for n in after['caps'].values()) and after['nnp']==1,'privileges')
            need(proof['persistentProfileProjected'] is True and proof['ambientHostDirectoriesBound']==0,'projection')
            need(proof['filesystem']['state']=='enforced' and proof['filesystem']['selfMountMetadata'] is True,'landlock')
            need(proof['profileLayout']=='hermes-native-stores-cold-v1','layout')
            need(target['epoch']==index+1 and target['recovered']==0 and target['stateStatus']=='terminal','epoch')
            startup=target['productStartup']
            need(startup['state']=='VERIFIED' and startup['completedChecks']==['preflight','before_epoch','after_epoch'],'sequence')
            need(startup['epochObserved']==index+1 and startup['automaticRecoveryPerformed'] is False,'recovery')
            need(target['fullIsolationReadinessHttp'] is True and target['realHermesGateway'] is False,'http_scope')
            need(target['providerSends']==0 and target['fullD3BAccepted'] is False,'dispatch')
            opened=target['httpStartup'];closed=target['httpClosed']
            need(opened['state']=='SERVING' and opened['host']=='127.0.0.1' and opened['listenerBindConfirmed'] is True,'listener')
            need(closed['state']=='CLOSED' and closed['readinessRevoked'] is True and closed['httpCleanupPending'] is False,'close')
            for obj in (opened,closed):
                for key in ('agentRoutesEnabled','runtimeAdmissionAuthorized','fullHermesGatewayStarted'):need(obj[key] is False,'http_authority')
            local=phases[mode+'-http-listening'];host=phases[mode+'-host-http-probe']
            need(local['pid']==target['pid'] and local['localReadyStatus']==200,'local_probe')
            need(local['port']==host['port']==opened['port']==closed['port'] and host['errno']==111,'host_probe')
            responses=target['httpResults']
            expected=[200,401,401,404,404,405,200,200,503,503,200]
            need([r['status'] for r in responses]==expected,'http_status_sequence')
            for n in (0,6,7,8,9):
                row=responses[n];body=row['body']
                need(row['path']=='/health/ready' and row['method']=='GET','ready_route')
                need(body['storageReady'] is (n<8) and body['runtimeAdmissionAuthorized'] is False and body['agentRoutesEnabled'] is False,'ready_body')
            need(responses[3]['path']=='/v1/runs' and responses[3]['method']=='POST','work_route')
            need(responses[-1]['body']['scope']=='process_liveness_only' and responses[-1]['path']=='/health/live','liveness')
            sources=target['nativeSources'];need(len(sources)==target['sourceCount'],'imports')
            need(all(manifest.get(n)==h for n,h in sources.items()),'import_hash')
            need(hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest()==target['sourceDigest'],'import_digest')
            for name in ('packages/claw-hermes/gateway_http_readiness.py','packages/claw-hermes/gateway_store_startup.py','vendor-native/hermes_state.py','vendor-native/gateway/platforms/api_server_run_idempotency.py'):
                need(name in sources,'required_import')
            finish=phases[mode+'-closed'];need(finish['leaseReleasedLast'] is True and finish['loopAttachmentGone'] is True,'detach')
        for name in ('state.db','runs_idempotency.db'):
            a,b=targets[0]['stores'][name],targets[1]['stores'][name]
            need(a['rows']==b['rows'] and a['inode']==b['inode'] and b['duplicateRefused'] is True,'persisted_identity')
        blocked=targets[1]['blockedStartup']
        need(blocked['state']=='FAILED' and blocked['epochMayHaveAdvanced'] is False and blocked['epochObserved']==2,'pending_refusal')
        return {'result':'VERIFIED_FULL_ISOLATION_READINESS_PROOF','lifetimes':2,'httpResponses':22,'fullAgentGatewayAccepted':False,'launchAuthorized':False}
    except InvalidReceipt:raise
    except (KeyError,TypeError,ValueError,IndexError):raise InvalidReceipt('malformed') from None
