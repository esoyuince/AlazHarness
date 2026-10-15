"""Fail-closed validator for an OBSERVATION, never a product-recovery approval."""
from __future__ import annotations
import json
import re

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'


def validate_gap(r: dict) -> list[str]:
    errors=[]
    try:
        if not isinstance(r,dict):return ['not an object']
        if r.get('source_commit')!=PIN:errors.append('wrong native source')
        if r.get('errors')!=[] or r.get('fixture_errors')!=[]:errors.append('reported failure')
        if r.get('source_or_program_drift') is not False:errors.append('unproven source stability')
        if r.get('profile_config_unchanged') is not True:errors.append('profile changed')
        if r.get('product_recovery_accepted') is not False:errors.append('unsupported product acceptance')
        if r.get('observation')!='reservation_replayed_without_canonical_admission':errors.append('wrong observation')
        for name in ('model_requests','model_inference_calls','paid_calls','client_exit'):
            if type(r[name]) is not int or r[name]!=0:errors.append('invalid '+name)
        first,second=r['first_ready'],r['second_ready']
        for stage in (first,second):
            for name in ('pid','epoch','api_port'):
                if type(stage[name]) is not int or stage[name]<=0:errors.append('invalid native '+name)
            if stage.get('profile_bound') is not True or stage.get('state')!='ready' or stage.get('api_host')!='127.0.0.1':errors.append('unqualified native readiness')
            if stage.get('aiohttp_version')!='3.14.3':errors.append('unqualified HTTP dependency')
            if (stage.get('runner'),stage.get('authority'),stage.get('adapter'))!=('gateway.run.GatewayRunner','gateway.session_authority.SessionAuthority','gateway.platforms.api_server.APIServerAdapter'):errors.append('not native classes')
            if not isinstance(stage.get('nonce'),str) or not re.fullmatch('[a-f0-9]{32}',stage['nonce']):errors.append('invalid nonce')
            if not isinstance(stage.get('instance_id'),str) or not stage['instance_id']:errors.append('no runtime instance')
        if second['epoch']<=first['epoch'] or second['instance_id']==first['instance_id'] or second['nonce']==first['nonce']:errors.append('no new owner generation')
        if second['api_port']!=first['api_port']:errors.append('changed API endpoint')
        for name,ready,killed in [('first_exit',first,True),('second_exit',second,False)]:
            end=r[name];chain=end['ownership_chain']
            if type(end['native_pid']) is not int or end['native_pid']!=ready['pid'] or end['nonce']!=ready['nonce']:errors.append('native lifetime mismatch')
            if type(end['launcher_pid']) is not int or not chain or chain[0]!=ready['pid'] or chain[-1]!=end['launcher_pid'] or len(set(chain))!=len(chain) or any(type(n) is not int or n<=0 for n in chain):errors.append('unowned process chain')
            if end['native_reaped'] is not True or end['launcher_reaped'] is not True:errors.append('writer not reaped')
            if end['kill_requested'] is not killed or end['forced'] is not killed:errors.append('wrong termination mode')
            if type(end['exit_code']) is not int or (end['exit_code']==0)==killed:errors.append('wrong process exit')
            if killed:
                if end['shutdown'] is not None:errors.append('graceful first shutdown is not a crash')
            else:
                close=end['shutdown']
                if close['native_result'] is not True or close['lifecycle_completed'] is not True or close['pid']!=ready['pid'] or close['nonce']!=ready['nonce']:errors.append('no native shutdown')
                if type(close['nonloopback_attempts_blocked']) is not int or close['nonloopback_attempts_blocked']!=0:errors.append('unexpected network attempt')
        request=r['first_request']
        if 'http_status' in request or not isinstance(request.get('error_type'),str) or not request['error_type']:errors.append('first request not demonstrably unacknowledged')
        ids=[];fingerprints=[]
        for name in ('barrier','after_crash','after_recovery'):
            db=r[name]
            if db['read_only'] is not True or db['integrity']!='ok' or db['reservation_integrity']!='ok':errors.append('unproven independent database')
            if db['admissions']!=[] or type(db['messages']) is not int or db['messages']!=0:errors.append('unexpected canonical execution')
            if len(db['reservations'])!=1:return errors+['missing/duplicate reservation']
            row=db['reservations'][0];ids.append(row['run_id']);fingerprints.append(row['fingerprint'])
            if not re.fullmatch(r'run_[a-f0-9]{32}',row['run_id']) or not re.fullmatch('[a-f0-9]{64}',row['fingerprint']):errors.append('invalid reservation identity')
            if type(row['owner_pid']) is not int or row['owner_pid']!=first['pid']:errors.append('wrong original reservation owner')
            saved=json.loads(row['status_json'])
            expected='interrupted' if name=='after_recovery' else 'queued'
            if saved.get('status')!=expected or saved.get('run_id')!=row['run_id']:errors.append('wrong persisted status')
        if len(set(ids))!=1 or len(set(fingerprints))!=1:errors.append('reservation changed')
        client=r['client'];rid=ids[0]
        if client['nonce']!=second['nonce']:errors.append('wrong client generation')
        for name in ('status','replay'):
            if client[name]['run_id']!=rid or client[name]['status']!='interrupted':errors.append('wrong native HTTP projection')
        if client['replay']['replayed'] is not True or client['conflict']!='http_409':errors.append('replay/conflict not confirmed')
        observed=client['observed']
        if observed['run']['run_id']!=rid or observed['run']['status']!='interrupted':errors.append('wrong observed run')
        # Characterize this gap; these transport flags are NOT canonical admission proof.
        if observed['backendConfirmed'] is not True or observed['requiresOperator'] is not False:errors.append('transport observation changed')
        return errors
    except (KeyError,IndexError,TypeError,ValueError,AttributeError):return errors+['malformed observation']
