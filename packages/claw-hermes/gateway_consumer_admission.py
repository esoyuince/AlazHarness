"""Phase-specific operations for the original consumer, not a second owner.

Identity-only observations permit pending work but grant neither health nor close.
Draining seals the native gate without waiting for the SQL mutex. Retained queued
or unknown work is not automatically run or discarded; clean release is separate.
"""
from gateway_prepared_consumer import require,verify_imports,ADMISSION_FEATURE,CANONICAL_API_FEATURE


def _pair(c,*,quiescent=True):
    require(c._local_admission is True and c._selected_feature in (ADMISSION_FEATURE,CANONICAL_API_FEATURE),
            'consumer_local_admission_not_selected')
    require(c._stage=='ATTACHED','consumer_admission_not_attached')
    c._identity(loop=True,quiescent=quiescent)
    b,r,a=c._binding,c._runner,c._adapter
    require(b is not None and r is not None and a is not None
            and r._caller_owned_state is b and b._api_bundle is c._bundle
            and b._runner is r and c._bundle._prepared_binding is b
            and c._bundle._prepared_runner is r and c._bundle._adapter is a
            and a.gateway_runner is r and a._borrowed_api_stores is c._bundle
            and b._stage==c._admission_phase,'consumer_admission_pair_changed')
    require(c._source_proof is not None,'consumer_sources_missing')
    verify_imports(c._source_proof)
    if getattr(c,'_canonical_api',False):
        from gateway_consumer_api import check_publication
        check_publication(c)
    return b


def check(c):
    _pair(c)
    phase=c._admission_phase
    require(phase in ('PREPARED','ACTIVE','DRAINING','DRAINED'),'consumer_admission_unknown')
    idle=phase in ('PREPARED','DRAINED')
    if idle:c._work_absent()
    c._storage(require_idle=idle)
    selected=c._bundle.select(c._adapter,c._held._home)
    require(all(a is b for a,b in zip(selected,c._stores)),'consumer_native_stores_changed')
    if idle:c._work_absent()
    c._identity(loop=True)
    return c.status()


def _call_transition(c,method,expected):
    before=c._binding._stage
    try:
        receipt=method()
        require(c._binding._stage==expected and receipt['state']==expected,
                'consumer_native_transition_unconfirmed')
        c._admission_phase=expected
    except BaseException:
        # Native pre-effect rejections retain the known phase. Any changed or
        # unknown native phase must hold the original owner without retry.
        if c._binding._stage!=before:
            c._stage='ADMISSION_UNKNOWN'
            c._admission_phase='UNKNOWN'
        raise
    return c.status()


def activate(c):
    _pair(c)
    require(c._admission_phase=='PREPARED','consumer_admission_not_fresh')
    check(c)
    if getattr(c,'_canonical_api',False):
        require(c._publication_phase=='PUBLISHED','consumer_api_not_published')
    return _call_transition(c,c._bundle.activate_admission,'ACTIVE')


def begin_drain(c):
    # No storage queries or writer-quiescence precondition: an existing tracked
    # writer must not prevent withdrawal of NEW admission before its next guard.
    _pair(c,quiescent=False)
    require(c._admission_phase in ('ACTIVE','DRAINING'),'consumer_admission_not_active')
    return _call_transition(c,c._bundle.begin_drain,'DRAINING')


def finish_drain(c):
    _pair(c)
    require(c._admission_phase in ('DRAINING','DRAINED'),'consumer_drain_not_started')
    c._work_absent()
    c._storage()  # Clean-only original gates, never identity-only release.
    return _call_transition(c,c._bundle.finish_drain,'DRAINED')
