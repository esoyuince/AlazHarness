"""Fail-closed checks for native process recovery evidence; adoption is separate."""
from __future__ import annotations
import hashlib
import re

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
SCENARIOS={'completed','before-model','after-tool','before-reserve','after-reserve'}


def validate(r: dict) -> list[str]:
    try:
        errors=[];case=r['scenario'];before=r['before_restart'];after=r['after_restart']
        if case not in SCENARIOS:return ['unknown scenario']
        if r.get('errors') or r.get('fixture_errors'):errors.append('execution or fixture errors')
        if r.get('source_commit')!=PIN:errors.append('unqualified native source')
        if r.get('program_drift') is not False or r.get('profile_config_unchanged') is not True:errors.append('source/config drift')
        for key in ('model_inference_calls','paid_calls'):
            if type(r.get(key)) is not int or r[key]!=0:errors.append('unexpected inference')
        if r.get('os_sandbox_claimed') is not False:errors.append('unsupported isolation claim')
        if not re.fullmatch(r'[0-9a-f]{32}',r['nonce']) or not re.fullmatch(r'run_[0-9a-f]{32}',r['run_id']):errors.append('invalid request identity')
        first=r['first_exit'];second=r['second_exit'];a=r['first_ready'];b=r['second_ready']
        if first.get('hard_kill') is not True or type(first.get('exit_code')) is not int or first['exit_code']==0:errors.append('no real crash')
        if second.get('hard_kill') is not False or type(second.get('exit_code')) is not int or second['exit_code']!=0:errors.append('unclean replacement shutdown')
        for exit,ready in ((first,a),(second,b)):
            if exit.get('native_reaped') is not True or exit.get('launcher_reaped') is not True:errors.append('unreaped native process')
            if type(exit.get('pid')) is not int or exit['pid']<=0 or type(exit.get('launcher_pid')) is not int:errors.append('invalid OS identity')
            chain=exit['chain']
            if not chain or any(type(pid) is not int or pid<=0 for pid in chain) or len(set(chain))!=len(chain) or chain[0]!=ready['pid'] or chain[-1]!=exit['launcher_pid']:errors.append('invalid held-handle ownership chain')
            if exit.get('ready')!=ready or exit.get('nonce')!=ready['nonce'] or ready.get('profile_bound') is not True:errors.append('readiness identity mismatch')
            if ready.get('runner')!='gateway.run.GatewayRunner' or ready.get('adapter')!='gateway.platforms.api_server.APIServerAdapter' or ready.get('authority')!='gateway.session_authority.SessionAuthority':errors.append('not native Gateway')
            if ready.get('state')!='ready' or ready.get('api_host')!='127.0.0.1':errors.append('unqualified listener')
        if a['nonce']!=r['nonce'] or a['nonce']==b['nonce']:errors.append('reused incarnation nonce')
        if type(a.get('epoch')) is not int or type(b.get('epoch')) is not int or not 0<a['epoch']<b['epoch'] or a['instance_id']==b['instance_id']:errors.append('no new runtime epoch')
        if a['api_port']!=b['api_port']:errors.append('listener changed')
        shut=second['shutdown']
        if shut.get('nonce')!=b['nonce'] or shut.get('pid')!=b['pid'] or shut.get('native_result') is not True or shut.get('lifecycle_completed') is not True:errors.append('no native final shutdown')
        for db in (before,after):
            if db.get('read_only') is not True or db.get('integrity')!='ok' or db.get('run_integrity')!='ok':errors.append('no read-only integrity proof')
            for key in ('user_count','tool_count','read_count'):
                if type(db.get(key)) is not int or db[key]<0:errors.append('invalid database count')
            if db.get('marker_in_user') is not False:errors.append('tool marker leaked into input')
        if r['conflict'].get('ok') is not False or r['conflict'].get('code')!='http_409' or r['conflict'].get('mayHaveBeenAccepted') is not False:errors.append('payload conflict missing')
        calls=r['model_calls'];call_count=len(calls)
        if type(r['model_calls_before_restart']) is not int or any(c.get('forbidden') is not False or c.get('stream') is not False for c in calls):errors.append('unexpected provider path')
        if r['trace_checkpoint'] is not (case in ('before-reserve','after-reserve')):errors.append('fault mode mismatch')
        if r['trace_checkpoint']:
            point=r['checkpoint'];lost=r['lost_response']
            if point.get('phase')!=case or point.get('pid')!=a['pid'] or point.get('nonce')!=r['nonce'] or point.get('run_id')!=r['run_id']:errors.append('unowned timing checkpoint')
            if type(point.get('line')) is not int or point['line']<=0 or not re.fullmatch(r'[a-f0-9]{64}',point['source_sha256']):errors.append('unpinned checkpoint')
            if lost.get('code')!='write_outcome_unknown' or lost.get('mayHaveBeenAccepted') is not True:errors.append('unknown ACK not retained')
        offer=r['reoffered']
        if offer.get('ok') is not True:return errors+['native keyed reoffer failed']
        if case=='before-reserve':
            if before['admissions'] or before['runs'] or before['user_count'] or before['tool_count']:errors.append('unexpected pre-reservation effect')
            if r['recovered_status'].get('code')!='http_404' or r['recovered_status'].get('ok') is not False:errors.append('unreserved ID was created')
            if offer['value'].get('replayed') is not False or offer['value']['run_id']==r['run_id']:errors.append('unreserved request not newly admitted')
            if r['new_final'].get('ok') is not True or r['new_final']['value']['run']['status']!='completed':errors.append('explicit new request not completed')
            if len(after['admissions'])!=1 or len(after['runs'])!=1 or after['tool_count']!=1 or after['read_count']!=1 or after['tool_marker'] is not True or after['user_count']!=1:errors.append('new native effect mismatch')
            if after['admissions'][0]['request_id']!=r['new_run_id'] or after['runs'][0]['run_id']!=r['new_run_id']:errors.append('new native ID mismatch')
            if call_count!=2 or r['model_calls_before_restart']!=0:errors.append('unexpected explicit execution count')
            return errors
        if offer['value'].get('replayed') is not True or offer['value']['run_id']!=r['run_id']:errors.append('duplicate not bound to original run')
        if len(before['runs'])!=1 or len(after['runs'])!=1 or before['runs'][0]['run_id']!=r['run_id'] or after['runs'][0]['run_id']!=r['run_id'] or before['runs'][0]['fingerprint']!=after['runs'][0]['fingerprint']:errors.append('reservation identity changed')
        if call_count!=r['model_calls_before_restart']:errors.append('model replay after recovery')
        status=r['recovered_status'];resume=r['resumed']
        if status.get('ok') is not True or resume.get('ok') is not True:return errors+['recovery lookup failed']
        if status['value']['run_id']!=r['run_id'] or resume['value']['run']['run_id']!=r['run_id']:errors.append('lookup changed run')
        if case=='after-reserve':
            if before['admissions'] or after['admissions'] or before['tool_count'] or after['tool_count'] or call_count:errors.append('reservation-only gap unexpected execution')
            if status['value']['status']!='interrupted' or offer['value']['status']!='interrupted':errors.append('reservation gap not closed as interrupted')
            # This passes a CHARACTERIZATION contract only: no canonical job existed.
            return errors
        if len(before['admissions'])!=1 or len(after['admissions'])!=1:return errors+['canonical admission duplicated or absent']
        row0,row1=before['admissions'][0],after['admissions'][0]
        for key in ('admission_id','request_id','target_session_id','payload_digest','generation'):
            if row0[key]!=row1[key]:errors.append('canonical identity changed '+key)
        if row1['request_id']!=r['run_id'] or status['value']['admission_id']!=row1['admission_id'] or status['value']['session_id']!=row1['target_session_id']:errors.append('HTTP/canonical identity mismatch')
        if before['user_count']!=1 or after['user_count']!=1:errors.append('user message duplicated')
        expected_tools=0 if case=='before-model' else 1
        if before['tool_count']!=expected_tools or after['tool_count']!=expected_tools or after['read_count']!=expected_tools:errors.append('unexpected real tool replay')
        if expected_tools and (before['tool_marker'] is not True or after['tool_marker'] is not True):errors.append('missing native read marker')
        if call_count!=(1 if case=='before-model' else 2):errors.append('unexpected original model count')
        if case=='completed':
            original=r['first_final']['value']['run']
            for key in ('run_id','session_id','admission_id','execution_generation','output','usage'):
                if original[key]!=status['value'][key] or original[key]!=resume['value']['run'][key]:errors.append('completed result changed '+key)
            digest=hashlib.sha256(original['output'].encode()).hexdigest()
            if before['final_digests']!=[digest] or after['final_digests']!=[digest]:errors.append('saved final result mismatch')
            if row1['status']!='terminal' or row1['outcome']!='completed' or status['value']['status']!='completed':errors.append('completion not retained')
        else:
            if row0['status']!='started' or row1['status']!='unknown' or status['value']['status']!='unknown' or resume['value']['run']['status']!='unknown':errors.append('started work not quarantined as unknown')
            if resume['value'].get('backendConfirmed') is not False or resume['value'].get('requiresOperator') is not True or resume['value'].get('stopRequested') is not False:errors.append('unsafe unknown classification')
        return errors
    except (KeyError,TypeError,IndexError,AttributeError,ValueError):return ['malformed recovery evidence']
