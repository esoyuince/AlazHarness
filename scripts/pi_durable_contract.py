"""Pure evidence checks; a passed characterization does not accept a production dependency."""
from __future__ import annotations
SCENARIOS=('admission','cancel-wait','abort-work','storage-before','storage-after','crash-pending','crash-unsafe','crash-safe','crash-committed')


def integer(value) -> bool:
    return type(value) is int and value >= 0


def check_barrier(value: dict, scenario: str) -> list[str]:
    errors=[]
    if not isinstance(value,dict):return ['missing barrier']
    if value.get('scenario')!=scenario or value.get('phase')!='before':errors.append('wrong barrier identity')
    kinds=value.get('entries',[])
    tasks=value.get('taskStates',[])
    if not isinstance(kinds,list) or not isinstance(tasks,list):return errors+['invalid barrier state']
    if scenario in ('crash-safe','crash-unsafe'):
        if value.get('cut')!='effect_complete_result_uncommitted':errors.append('wrong effect cut')
        if value.get('effects')!=1 or value.get('attempts')!=1 or 'pi.tool-result' in kinds:errors.append('wrong pre-crash effects/results')
        policy='safe' if scenario=='crash-safe' else 'unsafe'
        if not any(t.get('kind')=='pi.tool' and t.get('state',{}).get('status')=='running'
                   and t['state'].get('checkpoint',{}).get('phase')=='execute'
                   and t['state']['checkpoint'].get('replay')==policy for t in tasks):errors.append('missing durable executing intent')
    elif scenario=='crash-pending':
        if value.get('cut')!='request_pending_no_response' or kinds!=['pi.user']:errors.append('wrong pending-request cut')
        if not any(t.get('kind')=='pi.generation' and t.get('state',{}).get('checkpoint',{}).get('phase')=='request' for t in tasks):errors.append('request not checkpointed')
    elif scenario=='crash-committed':
        if value.get('cut')!='settled_commit_before_close' or value.get('settlement',{}).get('status')!='done':errors.append('result not committed before crash')
        if not tasks or any(t.get('state',{}).get('status')!='terminal' for t in tasks):errors.append('not all tasks committed terminal')
    else:errors.append('not a crash scenario')
    return errors


def evaluate_case(case: dict) -> list[str]:
    try:return _evaluate(case)
    except (AttributeError,KeyError,TypeError,IndexError,ValueError):return ['malformed evidence']


def _evaluate(case: dict) -> list[str]:
    errors=[];scenario=case.get('scenario');o=case.get('observation',{});runs=case.get('processes',[])
    if scenario not in SCENARIOS:return ['unknown scenario']
    if case.get('characterization')!='PASS' or o.get('characterization')!='PASS':errors.append('native characterization failed')
    if o.get('scenario')!=scenario or o.get('schema')!=1:errors.append('wrong native identity/schema')
    if o.get('modelInferenceCalls')!=0 or o.get('paidCalls')!=0:errors.append('unexpected real model use')
    for field in ('powerLossTested','osSandboxClaimed','productionIntegrated'):
        if o.get(field) is not False:errors.append('unsupported claim '+field)
    if not integer(o.get('modelCalls')) or not integer(o.get('toolExecutions')):errors.append('invalid native counters')
    if not runs:return errors+['missing execution evidence']
    for p in runs:
        if p.get('child_reaped') is not True or p.get('timed_out') is not False:errors.append('unreaped or timed-out process')
        if not integer(p.get('pid')):errors.append('missing process identity')
    if runs[-1].get('exit_code')!=0 or o.get('processCleanClose') is not True:errors.append('native exit/close failed')
    if scenario.startswith('crash-'):
        if len(runs)!=2:return errors+['crash needs two separate process stages']
        before,after=runs
        if before.get('phase')!='before' or after.get('phase')!='after':errors.append('wrong crash/recovery phases')
        if before.get('killed_at_barrier') is not True or before.get('ready_received') is not True:errors.append('no proven forced crash')
        if type(before.get('exit_code')) is not int or before['exit_code']==0:errors.append('crash exited normally')
        if before.get('finished_monotonic',float('inf'))>after.get('started_monotonic',0):errors.append('overlapping storage owners')
        barrier=before.get('barrier',{});errors.extend(check_barrier(barrier,scenario))
        db=case.get('database_after_crash',{})
        if db.get('integrity')!='ok' or db.get('read_only') is not True:errors.append('no independent persisted-state proof')
        if db.get('entry_kinds')!=barrier.get('entries'):errors.append('barrier disagrees with persisted entries')
        task_states=[{'id':t['id'],'kind':t['kind'],'state':t['state']} for t in db.get('tasks',[])]
        if task_states!=barrier.get('taskStates'):errors.append('barrier disagrees with persisted checkpoints')
        if not any(s.get('id')==barrier.get('submissionId') and s.get('conversationId')==barrier.get('rootId') for s in db.get('submissions',[])):errors.append('admission not found after crash')
        for field in ('rootIdentityPreserved','submissionIdentityPreserved','providerIdentityPreserved','idle'):
            if o.get(field) is not True:errors.append('lost '+field)
        independent=case.get('independent_effect_counts',{})
        expected_attempts=2 if scenario=='crash-safe' else (0 if scenario=='crash-pending' else 1)
        expected_effects=0 if scenario=='crash-pending' else 1
        for field,n in [('attempts',expected_attempts),('effects',expected_effects)]:
            if not integer(o.get(field)) or o.get(field)!=n or independent.get(field)!=n:errors.append('unexpected '+field)
        if scenario=='crash-unsafe':
            if o.get('taskCompleted') is not False or o.get('uncertainEffect') is not True or o.get('toolErrors')!=1:errors.append('unsafe outcome misreported')
        elif o.get('taskCompleted') is not True or o.get('toolErrors')!=0:errors.append('unexpected recovered outcome')
        if o.get('modelCalls')!=(0 if scenario=='crash-committed' else 1):errors.append('unexpected replayed provider requests')
    else:
        if len(runs)!=1 or runs[0].get('phase')!='single':errors.append('wrong single-process shape')
        if scenario=='admission':
            if any(o.get(f) is not True for f in ('sameKeySameId','changedPayloadSameId','originalPayloadPreserved','typeMismatchRejected','conversationScopeSeparated','reopenIdentityPreserved','inputChangedPayloadSameId','inputOriginalPayloadPreserved','inputDuplicateAfterReopenSameId')):errors.append('admission contract changed')
            if o.get('strictPayloadConflict') is not False or not o.get('adoptionBlockers'):errors.append('payload conflict gap concealed')
        elif scenario=='cancel-wait':
            if o.get('waitCancelled') is not True or o.get('workContinued') is not True or o.get('taskCompleted') is not True:errors.append('wait cancellation affected work')
            if o.get('abortObservedImmediatelyAfterWait') is not False:errors.append('wait cancellation signal ambiguity')
        elif scenario=='abort-work':
            if o.get('workAborted') is not True or o.get('taskCompleted') is not False or o.get('settlement',{}).get('reason')!='aborted':errors.append('work abort not proven')
        else:
            for f in ('originalErrorPreserved','sessionFailed','reopened'):
                if o.get(f) is not True:errors.append('storage fault missing '+f)
            if o.get('injectionCount')!=1 or o.get('persistedBeforeRetry')!=(1 if scenario=='storage-after' else 0) or o.get('recordsAfterRetry')!=1:errors.append('wrong commit/ack recovery')
    return errors
