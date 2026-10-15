"""Bounded receipt validation; this checks evidence, it does not execute a lock test."""
NAMES=frozenset(('live_gateway_excludes_maintenance','stopped_gateway_allows_maintenance',
'lock_acquisition_does_not_modify_managed_db','nested_same_thread_canonical_alias',
'independent_owner_in_same_process_refused','other_maintenance_process_refused',
'maintenance_excludes_public_gateway','owned_maintenance_kill_reaped',
'process_death_releases_native_lock','lock_inode_preserved',
'managed_databases_unchanged_through_contention','same_gateway_restarts_after_lock_release','no_admissions_or_tools'))


def validate(r):
    try:
        if type(r) is not dict:return ['not_object']
        errors=[]
        if r['result']!='PASS' or r['errors']!=[] or r['code_drift']!=[] or r['fixture_errors']!=[]:errors.append('reported_failure')
        if r['source_commit']!='eb75627faf532fa6ffbdae59a0d14b0b385fc780':errors.append('source_pin')
        checks=r['checks'];names=[v['name'] for v in checks]
        if len(names)!=len(NAMES) or set(names)!=NAMES:errors.append('incomplete_or_duplicate_checks')
        if any(v['passed'] is not True for v in checks):errors.append('failed_check')
        for n in ('model_http_calls','model_inference_calls'):
            if type(r[n]) is not int or r[n]!=0:errors.append('unexpected_model_call')
        for n in ('gateway_exit','restarted_gateway_exit','blocked_gateway_exit','maintenance_kill'):
            end=r[n];pid=end.get('native_pid',end.get('pid'));chain=end['chain']
            if type(pid) is not int or type(end['launcher_pid']) is not int or not chain or chain[0]!=pid or chain[-1]!=end['launcher_pid'] or len(set(chain))!=len(chain):errors.append('process_identity')
            if end['native_reaped'] is not True or end['launcher_reaped'] is not True:errors.append('unreaped_process')
            good=n in ('gateway_exit','restarted_gateway_exit')
            if type(end['exit_code']) is not int or (end['exit_code']==0)!=good:errors.append('exit_code')
            if good:
                if end['shutdown']['native_result'] is not True or end['shutdown']['pid']!=pid or end['ready']['pid']!=pid or end['shutdown']['nonce']!=end['ready']['nonce']:errors.append('shutdown')
                if end['ready']['profile_bound'] is not True or end['ready']['runner']!='gateway.run.GatewayRunner' or end['ready']['authority']!='gateway.session_authority.SessionAuthority':errors.append('native_boundary')
        a,b=r['gateway_exit']['ready'],r['restarted_gateway_exit']['ready']
        if b['epoch']<=a['epoch'] or b['instance_id']==a['instance_id'] or b['api_port']!=a['api_port']:errors.append('restart_identity')
        db=r['snapshot']
        if db['read_only'] is not True or db['integrity']!='ok' or db['run_integrity']!='ok':errors.append('database_evidence')
        if db['admissions']!=[] or db['runs']!=[] or db['user_count']!=0 or db['tool_count']!=0:errors.append('unexpected_work')
        return errors
    except (KeyError,TypeError,ValueError,IndexError,AttributeError):return ['malformed_receipt']
