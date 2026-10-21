"""Read-only review of native P71C observations and syscall trace.

No privilege/process/file mutation. This reconciles the preserved strace
empty-array rendering mismatch; it is NOT a new native test execution.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/d3b-positive-lab-p71c'
CAPS=('CapInh','CapPrm','CapEff','CapBnd','CapAmb')
CHECK='native_trace_proves_actual_transition_and_both_peers'

def require(ok,reason):
    if not ok:raise ValueError(reason)

def review(record,trace):
    require(record['result']=='FAIL' and record['error'] is None and record['forcedCleanup'] is False,'original_outcome')
    require(record['checkCount']==20 and len(record['checks'])==20,'check_inventory')
    require({k for k,v in record['checks'].items() if v is not True}=={CHECK},'other_native_failure')
    require(record['installedSourceBefore']==record['installedSourceAfter']
            and len(record['installedSourceBefore'])==57,'source_changed')
    require(record['privateFilesBefore']==record['privateFilesAfter']
            and set(record['privateFilesBefore'])=={'/srv/alaz-p71c/private/config.json','/srv/alaz-p71c/private/budget/budget.sqlite3'},'private_changed')
    require(record['positiveUidTransitionTested'] is True and record['realModelCalls']==0
            and all(record[k] is False for k in ('realHermesGatewayTested','ipcV2MountTested','providerDispatchTested','fullD3BAccepted')),'scope_flags')
    lives=record['lifetimes'];require(len(lives)==2,'lifetime_count')
    for i,life in enumerate(lives):
        state=life['postexec'];fields=state['fields'];pid=life['ready']['pid']
        require(type(pid) is int and pid>0 and state['pid']==pid,'pid_identity')
        require(fields['Uid']==['23002']*4 and fields['Gid']==['23003']*4
                and not fields['Groups'] and fields['Threads']==['1'],'native_ids')
        require(set(CAPS)<=set(fields) and all(fields[k]==['0000000000000000'] for k in CAPS),'native_caps')
        require(fields['NoNewPrivs']==['1'] and fields['Seccomp']==['2'],'native_filter')
        require(state['uidMap']==state['gidMap']==['0','0','4294967295']
                and state['userns']==record['controllerBefore']['userns']
                and state['netns']==record['controllerBefore']['netns'],'native_namespace')
        require(state['exe']=='/usr/bin/python3.12'
                and '/opt/alazharness-broker/802fade/scripts/run_principal_broker_target.py' in state['cmdline'],'native_image')
        if i==0:require(life['launcherPid']==pid and life['traced'] is False,'untraced_pid_continuity')
        positive=life['positiveClient'];require(positive['self']['uid']==23001 and positive['self']['gid']==23003,'gateway_ids')
        require(positive['transport']['peer']=={'pid':pid,'uid':23002,'gid':23003},'client_peer')
        require(positive['transport']['actualProviderBrokerClientReady'] is True
                and positive['transport']['reply']['ok'] is True
                and positive['transport']['reply']['nonce']==positive['transport']['requestedNonce'],'authenticated_ping')
        require(life['wrongPeerClient']['self']['uid']==23002
                and life['wrongPeerClient']['transport']['reply']['error']=='broker_request_refused'
                and life['wrongPeerClient']['transport']['reply']['ok'] is False,'server_wrong_uid')
        require(life['wrongLocalClient']['transport']['localClientReason']=='broker_gateway_principal_refused','client_wrong_uid')
        expected={(p,a) for p in ('private/config.json','private/budget/budget.sqlite3') for a in ('read','write_open_only')}
        for name,denial in (('gatewayDenials',True),('brokerOwnerControls',False)):
            data=life[name]
            require(data['self']['uid']==(23001 if denial else 23002),'access_identity')
            require(len(data['accesses'])==4 and {(x['path'],x['action']) for x in data['accesses']}==expected,'access_inventory')
            for row in data['accesses']:
                require(row['opened'] is (not denial),'access_result')
                if denial:require(type(row['errno']) is int and row['errno'] in (1,13),'explicit_access_denial')
                elif row['action']=='read':
                    require(row['readSha256']==record['privateFilesBefore']['/srv/alaz-p71c/'+row['path']]['sha256'],'owner_read_control')
        close=life['shutdown']
        require(life['exitCode']==0 and close['socketRemoved'] is True and close['activeRequests']==0
                and close['pid']==pid and close['counters']['physicalAttempts']==0
                and close['counters']['pings']==2 and close['counters']['responses']==0,'clean_shutdown')
        require(close['privateBudget']['providerReservations']==0,'budget_reservation')
    require(lives[0]['ready']['brokerId']!=lives[1]['ready']['brokerId']
            and lives[0]['ready']['pid']!=lives[1]['ready']['pid']
            and lives[0]['shutdown']['privateBudget']==lives[1]['shutdown']['privateBudget'],'restart_budget')
    require(lives[1]['staleClient']['transport']['reply']['error']=='stale_broker_identity'
            and lives[1]['staleClient']['transport']['reply']['ok'] is False,'restart_stale_identity')
    life=lives[1];pid=life['ready']['pid'];prefix=r'^'+str(pid)+r'\s+'
    patterns={
        'setgroups_empty':prefix+r'setgroups\(0, (?:NULL|\[\])\)\s+= 0$',
        'setresgid':prefix+r'setresgid\(23003, 23003, 23003\)\s+= 0$',
        'setresuid':prefix+r'setresuid\(23002, 23002, 23002\)\s+= 0$',
        'target_exec':prefix+r'execve\("/usr/bin/python3.12",.*run_principal_broker_target.py.*= 0$',
        'gateway_peer':prefix+r'getsockopt\(\d+, SOL_SOCKET, SO_PEERCRED, \{pid='+str(life['positiveClient']['self']['pid'])+r', uid=23001, gid=23003\}, \[12\]\)\s+= 0$',
        'wrong_peer':prefix+r'getsockopt\(\d+, SOL_SOCKET, SO_PEERCRED, \{pid='+str(life['wrongPeerClient']['self']['pid'])+r', uid=23002, gid=23003\}, \[12\]\)\s+= 0$'}
    matches={k:re.search(p,trace,re.MULTILINE) for k,p in patterns.items()}
    require(all(matches.values()),'trace_native_syscall_or_peer_missing')
    require(matches['setgroups_empty'].start()<matches['setresgid'].start()<matches['setresuid'].start()
            <matches['target_exec'].start()<matches['gateway_peer'].start(),'trace_transition_order')
    return {'result':'PASS_REVIEWED_NATIVE_TWO_UID_BROKER','nativeChecks':20,'nativeLifetimes':2,
            'nativeSuccessfulPings':4,'privateReadWriteDenials':8,'positiveOwnerAccesses':8,
            'traceChecks':6,'originalNativeCollectorExit':1,'newNativeExecution':False,
            'realHermesGatewayTested':False,'ipcV2MountTested':False,'providerDispatchTested':False,
            'fullD3BAccepted':False,'realModelCalls':0}

def main():
    raw=(E/'native-acceptance-001.json').read_bytes();trace=(E/'native-broker2-strace.txt').read_bytes()
    result=review(json.loads(raw),trace.decode())
    result.update(nativeReceiptSha256=hashlib.sha256(raw).hexdigest(),traceSha256=hashlib.sha256(trace).hexdigest())
    print(json.dumps(result))

if __name__=='__main__':main()
