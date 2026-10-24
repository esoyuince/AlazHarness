"""Canonical API registration on the existing consumer; never a second owner.

Explicit source selection does not enable a listener, recover a queue, execute a
model, or authorize worker health. All registry effects use native owner methods.
"""
import asyncio
from gateway_prepared_consumer import require,verify_imports,CANONICAL_API_FEATURE,FINITE_FEATURE


def check_publication(c):
    require(c._canonical_api is True and c._selected_feature==(FINITE_FEATURE if getattr(c,'_finite_turn',False) else CANONICAL_API_FEATURE),
            'consumer_canonical_api_not_selected')
    bundle,runner,adapter,binding=c._bundle,c._runner,c._adapter,c._binding
    phase=c._publication_phase
    require(phase in ('NEW','PUBLISHED','WITHDRAWN') and bundle._publication_state==phase,
            'consumer_publication_pair_changed')
    if phase!='WITHDRAWN' or binding._stage!='DETACHED':
        from gateway.run_borrowed_publication import check_publication as native_check
        native_check(bundle)
        return
    # Native check intentionally permits only pre-runner-detach phases. Here the
    # existing owner checks the final withdrawn identity, never republishes it.
    require(c._stage=='DETACHED' and bundle._stage=='DETACHED'
            and type(runner.adapters) is dict and not runner.adapters
            and runner.adapters is bundle._publication_registry
            and type(runner._profile_adapters) is dict and not runner._profile_adapters
            and runner._profile_adapters is bundle._publication_profiles
            and bundle._publication_loop is c._loop and not c._loop.is_closed()
            and (binding._admission_loop is None or binding._admission_loop is c._loop)
            and adapter.config is bundle._publication_config
            and adapter._owner_profile is None and adapter._shared_listener_profile is None,
            'consumer_retired_publication_changed')
    from gateway.config import Platform
    require(adapter.platform is Platform.API_SERVER,'consumer_retired_publication_changed')


def publish(c):
    from gateway_consumer_admission import _pair,check
    _pair(c)
    require(c._canonical_api is True and c._publication_phase=='NEW'
            and c._admission_phase=='PREPARED','consumer_publication_not_fresh')
    check(c)
    try:
        receipt=c._bundle.publish_api_adapter()
        require(receipt['state']=='CANONICAL_API_PUBLISHED'
                and c._bundle._publication_state=='PUBLISHED',
                'consumer_publication_unconfirmed')
        c._publication_phase='PUBLISHED'
        check(c)
    except BaseException:
        if c._bundle._publication_state!='NEW':
            c._stage='PUBLICATION_UNKNOWN';c._publication_phase='UNKNOWN'
        raise
    return c.status()


def retire_idle_sessions(c):
    from gateway_consumer_admission import _pair
    _pair(c)
    require(c._canonical_api is True and c._admission_phase=='DRAINING'
            and c._publication_phase=='PUBLISHED','consumer_retirement_not_sealed')
    c._storage()  # SQL obligations must already be terminal; memory may remain.
    from gateway.platforms.api_server_borrowed import BorrowedStoreRejected
    before=c._binding._stage;returned=False
    try:
        receipt=c._bundle.retire_idle_api_sessions()
        returned=True
        require(receipt['state']=='IDLE_API_SESSIONS_RETIRED'
                and c._binding._stage==before,'consumer_retirement_unconfirmed')
        verify_imports(c._source_proof);c._storage();check_publication(c)
    except BaseException as exc:
        # A completed retirement returns to DRAINING, so an unchanged phase
        # alone cannot prove a failure had no effects. Only the native typed
        # pre-effect refusal may retain a known phase without a receipt.
        if returned or c._binding._stage!=before or not isinstance(exc,BorrowedStoreRejected):
            c._stage='ADMISSION_UNKNOWN';c._admission_phase='UNKNOWN'
        raise
    return receipt


async def retire_idle_runtime(c):
    from gateway_consumer_admission import _pair
    from gateway.platforms.api_server_borrowed import BorrowedStoreRejected
    _pair(c)
    require(c._finite_turn is True and c._admission_phase=='DRAINING'
            and c._publication_phase=='PUBLISHED','consumer_runtime_retirement_not_sealed')
    c._storage()
    before=c._binding._stage;returned=False
    try:
        receipt=await c._bundle.retire_idle_runtime()
        returned=True
        require(receipt['state']=='IDLE_RUNTIME_RETIRED' and c._binding._stage==before,
                'consumer_runtime_retirement_unconfirmed')
        verify_imports(c._source_proof);c._storage();check_publication(c)
    except BaseException as exc:
        if returned or c._binding._stage!=before or not isinstance(exc,BorrowedStoreRejected):
            c._stage='ADMISSION_UNKNOWN';c._admission_phase='UNKNOWN'
        raise
    return receipt
