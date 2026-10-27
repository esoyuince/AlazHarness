"""Fixed prepared API/runner consumer of the ONE NativeStoreStartup owner.

Not a second storage manager. No new DB/epoch/recovery/HTTP. Failed constructor
or awaited cleanup retains the consumer; direct original owner close is blocked.
Source trust is a fixed installed-source envelope, not an authorization capability.
Old storage pins are NOT relabelled to this native feature. Linux cold/mount and
current-source live-task/service qualification remain separate acceptance gates.
"""
from __future__ import annotations
import asyncio
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import sys

FEATURE='1e97dd617b81120255304e472ce322befcdb9ccd'
MANIFEST_SHA256='6dc037dfecb6365db67c57c8e8ef96e0c152b5b8e8aa0f96ef9b2f6e525bc215'
ADMISSION_FEATURE='1b7b31e14451baf1d56c3edbfa2cea69a8f7940c'
ADMISSION_MANIFEST_SHA256='d0a1067de53e224c43f44c04b039fe12491f10a62a843719519174a2cf8d7e35'
CANONICAL_API_FEATURE='5ff88189832c3ff71bf8fd2f6b2ff05bb8bb4979'
CANONICAL_API_MANIFEST_SHA256='f650c067e1d4a7d303c48e9be10e75273fee4d8d48dda721af320fe3ac80ae27'
FINITE_FEATURE='d1516731308de8e87130dc68124e69aad35d6911'
FINITE_MANIFEST_SHA256='30095cdda6fadecaf332b5a5dbf8c2f3e43ad550d8dfd08adfe5469f26a324f4'
RETAINED_MANIFEST_SHA256='0af0852042217675b8398e2f64c7e509935726b992d91b4bdf4080512b35f8e4'
ROOT=Path(__file__).resolve().parents[2]

class PreparedConsumerRejected(RuntimeError):pass

def require(ok,code):
    if not ok:raise PreparedConsumerRejected(code)

def qualify_sources(*,local_admission=False,canonical_api=False,finite_turn=False,retained_profile=False,service_selection=None):
    """Read fixed source files, never data files, before native consumer imports."""
    require(type(local_admission) is bool,'consumer_admission_option')
    require(type(canonical_api) is bool and (not canonical_api or local_admission),
            'consumer_canonical_api_option')
    path=('config/admission-consumer-b129d6-sources.json' if local_admission
          else 'config/prepared-consumer-s124b1-sources.json')
    expected=ADMISSION_MANIFEST_SHA256 if local_admission else MANIFEST_SHA256
    feature=ADMISSION_FEATURE if local_admission else FEATURE
    if canonical_api:
        path='config/canonical-api-consumer-i133p1-sources.json'
        expected=CANONICAL_API_MANIFEST_SHA256;feature=CANONICAL_API_FEATURE
    require(type(finite_turn) is bool and (not finite_turn or canonical_api),
            'consumer_finite_option')
    if finite_turn:
        path='config/finite-close-f135c6-sources.json'
        expected=FINITE_MANIFEST_SHA256;feature=FINITE_FEATURE
    require(type(retained_profile) is bool and (not retained_profile or finite_turn),
            'consumer_retained_source_option')
    if retained_profile:
        path='config/retained-profile-r140c6-sources.json';expected=RETAINED_MANIFEST_SHA256
    if service_selection is not None:
        require(local_admission and canonical_api and finite_turn,'consumer_service_source_option')
        from gateway_service_sources import selected_manifest
        manifest=selected_manifest(service_selection)
    else:
        raw=(ROOT/path).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==expected,'consumer_manifest_changed')
        manifest=json.loads(raw);require(manifest['nativeFeature']==feature,'consumer_feature')
    import hermes_state
    native=Path(hermes_state.__file__).resolve().parent
    require(native==Path(hermes_state.__file__).parent,'consumer_source_path')
    for name,digest in manifest['sources'].items():
        path=native/name
        require(path.is_file() and path.resolve()==path and path.suffix=='.py'
                and hashlib.sha256(path.read_bytes()).hexdigest()==digest,'consumer_source_unqualified')
    return native,manifest['sources']

def verify_imports(proof):
    """Every loaded native Python source must lie within the prevalidated set."""
    root,hashes=proof
    for mod in tuple(sys.modules.values()):
        name=getattr(mod,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(root):
                require(path.suffix=='.py' and path.relative_to(root).as_posix() in hashes,
                        'consumer_import_outside_manifest')
                require(hashlib.sha256(path.read_bytes()).hexdigest()==hashes[path.relative_to(root).as_posix()],
                        'consumer_import_source_changed')

def native_types():
    from gateway.config import GatewayConfig,PlatformConfig
    from gateway.run_borrowed_state import CallerOwnedRunnerState
    from gateway.run import GatewayRunner
    from gateway.run_runtime import initialize_gateway_runtime
    from gateway.platforms.api_server_borrowed import BorrowedAPIStores
    from gateway.platforms.api_server import APIServerAdapter
    return GatewayConfig,PlatformConfig,CallerOwnedRunnerState,GatewayRunner,initialize_gateway_runtime,BorrowedAPIStores,APIServerAdapter

def selected_feature(c):
    """The explicit service generation is separate from every historical pin."""
    if getattr(c,'_borrowed_service',False):
        from gateway_service_sources import ServiceSourceSelection
        selection=getattr(c,'_service_source',None)
        require(type(selection) is ServiceSourceSelection,'consumer_service_selection_changed')
        require(c._finite_turn and c._canonical_api and c._local_admission,
                'consumer_service_options_changed')
        return selection.native_feature
    return (FINITE_FEATURE if getattr(c,'_finite_turn',False) else
            CANONICAL_API_FEATURE if getattr(c,'_canonical_api',False) else
            ADMISSION_FEATURE if c._local_admission else FEATURE)


class PreparedRuntimeConsumer:
    def __init__(self,owner,*,local_admission=False,canonical_api=False,finite_turn=False,borrowed_service=False):
        import gateway_store_startup as startup
        require(type(local_admission) is bool,'consumer_admission_option')
        require(type(canonical_api) is bool and (not canonical_api or local_admission),
                'consumer_canonical_api_option')
        require(type(finite_turn) is bool and (not finite_turn or canonical_api),
                'consumer_finite_option')
        require(type(borrowed_service) is bool and (not borrowed_service or finite_turn),
                'consumer_service_option')
        self._borrowed_service=borrowed_service;self._service_source=None
        if borrowed_service:
            from gateway_service_sources import load_selection
            self._service_source=load_selection()
        self._finite_turn=finite_turn
        self._retained_source_receipt=getattr(owner,'_retained_profile',None)
        self._service_profile_receipt=getattr(owner,'_service_profile',None)
        require(getattr(owner,'_service_profile_binding',None) is self._service_profile_receipt,
                'consumer_service_profile_changed')
        if self._service_profile_receipt is not None:
            require(borrowed_service,'consumer_service_profile_requires_service')
            require(self._service_profile_receipt.selection==self._service_source,
                    'consumer_service_profile_selection')
        self._canonical_api=canonical_api;self._publication_phase='NEW'
        self._local_admission=local_admission
        self._selected_feature=ADMISSION_FEATURE if local_admission else FEATURE
        if canonical_api:self._selected_feature=CANONICAL_API_FEATURE
        if finite_turn:self._selected_feature=FINITE_FEATURE
        if borrowed_service:self._selected_feature=self._service_source.native_feature
        self._admission_phase='PREPARED'
        require(type(owner) is startup.NativeStoreStartup,'consumer_exact_owner_required')
        owner._owned();require(owner._stage=='VERIFIED' and owner._response_expected is not None,'consumer_verified_owner')
        self._owner=owner;self._held=owner._held;self._mount=owner._mount;self._expected=owner.expectation
        self._response_expected=owner.response_expectation
        self._stores=(owner.state_store,owner.replay_store,owner.response_store)
        self._connections=tuple(s._conn for s in self._stores)
        self._loop=asyncio.get_running_loop();self._stage='RESERVED'
        self._binding=self._runner=self._bundle=self._adapter=None
        self._source_proof=None

    def _identity(self,*,loop=False,quiescent=True):
        require(type(quiescent) is bool,'consumer_identity_policy')
        canonical=getattr(self,'_canonical_api',False)
        finite=getattr(self,'_finite_turn',False)
        require(type(finite) is bool and (not finite or canonical),'consumer_finite_option')
        require(type(getattr(self,'_borrowed_service',False)) is bool,'consumer_service_option')
        require(type(canonical) is bool and type(self._local_admission) is bool
                and (not canonical or self._local_admission)
                and self._selected_feature==selected_feature(self),
                'consumer_generation_changed')
        o=self._owner;o._owned()
        require(getattr(o,'_retained_profile',None) is getattr(self,'_retained_source_receipt',None),
                'consumer_retained_receipt_changed')
        receipt=getattr(self,'_service_profile_receipt',None)
        require(getattr(o,'_service_profile',None) is receipt
                and getattr(o,'_service_profile_binding',None) is receipt,
                'consumer_service_profile_changed')
        if receipt is not None:
            require(self._borrowed_service and self._service_source==receipt.selection,
                    'consumer_service_profile_selection')
        require(o._stage=='VERIFIED' and o._prepared_consumer is self
                and o._held is self._held and o._mount is self._mount
                and o._expected is self._expected and o._response_expected is self._response_expected,
                'consumer_owner_changed')
        require(all(a is b for a,b in zip((o._state,o._replay,o._response),self._stores)),
                'consumer_stores_changed')
        require(all(a is b for a,b in zip((o._state_conn,o._replay_conn,o._response_conn),self._connections))
                and all(s._conn is c for s,c in zip(self._stores,self._connections)),
                'consumer_connections_changed')
        if loop:require(asyncio.get_running_loop() is self._loop,'consumer_other_loop')
        if quiescent:
            require(not any(c.in_transaction for c in self._connections),'consumer_transaction_active')
            o._drained()

    def _storage(self,*,require_idle=True):
        import gateway_store_startup as startup
        self._identity()
        options={} if require_idle else {'require_idle':False}
        a=startup.live.verify_live_stores(self._held,self._mount,*self._stores[:2],self._expected,**options)
        b=startup.response_live.verify_response_connection(self._held,self._mount,
            self._stores[0],self._stores[2],self._owner._response_live_expectation(),**options)
        state='NATIVE_STORE_CONNECTIONS_VERIFIED' if require_idle else 'NATIVE_STORE_IDENTITY_OBSERVED'
        response='NATIVE_RESPONSE_CONNECTION_VERIFIED' if require_idle else 'NATIVE_RESPONSE_IDENTITY_OBSERVED'
        require(a['state']==state and b['state']==response,
                'consumer_storage_observation')
        self._identity()

    def _check_service_config(self):
        # This is an admission/readiness check, separate from ownership/storage
        # checks used while draining or closing already-known native resources.
        owner=getattr(self,'_owner',None)
        require(owner is not None,'consumer_owner_changed')
        receipt=getattr(self,'_service_profile_receipt',None)
        require(getattr(owner,'_service_profile',None) is receipt
                and getattr(owner,'_service_profile_binding',None) is receipt,
                'consumer_service_profile_changed')
        if receipt is None:return
        self._identity()
        owner._check_service_config()

    async def prepare(self,gateway_config,api_config):
        require(self._stage=='RESERVED','consumer_not_fresh')
        self._stage='QUALIFYING'
        try:
            self._check_service_config()
            self._identity(loop=True);self._storage()
            self._source_proof=(qualify_sources(local_admission=True,canonical_api=True,finite_turn=True,
                                   retained_profile=self._retained_source_receipt is not None,
                                   service_selection=self._service_source)
                                if getattr(self,'_borrowed_service',False) else
                                qualify_sources(local_admission=True,canonical_api=True,finite_turn=True,retained_profile=True)
                                if self._finite_turn and self._retained_source_receipt is not None else
                                qualify_sources(local_admission=True,canonical_api=True,finite_turn=True)
                                if self._finite_turn else
                                qualify_sources(local_admission=True,canonical_api=True)
                                if self._canonical_api else
                                qualify_sources(local_admission=True) if self._local_admission else qualify_sources())
            self._check_service_config()
            Config,Platform,Binding,Runner,initialize,Bundle,Adapter=native_types()
            verify_imports(self._source_proof)
            self._check_service_config()
            require(type(gateway_config) is Config and type(api_config) is Platform,'consumer_explicit_configs')
            self._stage='CONSTRUCTING'
            self._binding=Binding(gateway_config,self._stores[0],epoch=self._expected.epoch,instance_id=self._expected.instance_id)
            self._runner=Runner(gateway_config,caller_state=self._binding)
            await initialize(self._runner)
            self._check_service_config()
            self._identity(loop=True);self._storage()
            self._bundle=Bundle(self._held._home,*self._stores,prepared_runner=self._runner)
            self._adapter=Adapter(api_config,borrowed_stores=self._bundle)
            self._stage='ATTACHED'
            self.check()
            verify_imports(self._source_proof)
            self._check_service_config()
            return self.status()
        except BaseException:
            self._stage='FAILED_UNKNOWN'
            raise

    def _work_absent(self):
        """Read-only prepared/retired work check; never prune or finish native work.

        These fixed containers belong to the source-qualified native owners.
        This is a cooperative instantaneous observation, not proof against other
        same-process threads creating work afterward, or permission to admit it.
        Even completed/cancelled retained records require their native owner to
        settle them; task.done() is not proof that physical execution stopped.
        """
        runner,binding=self._runner,self._binding
        require(runner is not None and binding is not None
                and runner._caller_owned_state is binding,'consumer_native_objects_changed')
        require(runner._running is False and runner._executor is None
                and runner._housekeeping_executor is None
                and runner._loop_heartbeat_task is None and runner._stop_task is None,
                'consumer_runner_lifecycle_active')
        runner_fields=(('adapters',dict),('_profile_adapters',dict),('_background_tasks',set),
                       ('_sessions',dict),('_fatal_handler_tasks',set),
                       ('_completion_notification_batch_tasks',dict),
                       ('_completion_notification_batches',dict),('_completion_deliveries_inflight',set),
                       ('_completion_notification_batch_flush_tasks',set),
                       ('_session_db_handles',dict),('_startup_restore_tasks',list),
                       ('_startup_restore_queue',list),('_agent_cache',OrderedDict))
        for name,kind in runner_fields:
            value=getattr(runner,name,None)
            if name=='adapters' and getattr(self,'_canonical_api',False):
                from gateway_consumer_api import check_publication
                check_publication(self)
            else:require(type(value) is kind and not value,'consumer_runner_work_present')
        authority=binding._authority
        require(authority is not None and runner.session_authority is authority
                and authority.runner is runner and authority.db is self._stores[0],
                'consumer_work_authority_changed')
        authority_fields=(('sessions',dict),('waiters',dict),('events',dict),
                          ('native_waiters',set),('pending_results',dict),
                          ('pending_deliveries',dict),('adopted',dict),('executing',dict),
                          ('pending_stops',dict),('pending_steers',dict),
                          ('cancel_obligations',set))
        for name,kind in authority_fields:
            value=getattr(authority,name,None)
            require(type(value) is kind and not value,'consumer_authority_work_present')
        # These are lazily created by the native work producers. Do not call
        # physical_workers(): it prunes the native registry as a side effect.
        for name,kind in (('_turn_workers',dict),('_managed_workers',dict),
                          ('_mutation_tasks',set),('_bot_mailbox_operations',set),
                          ('_bot_receipt_tasks',set),
                          ('_cron_cancellations',dict)):
            value=getattr(authority,name,None)
            require(value is None or type(value) is kind and not value,
                    'consumer_authority_work_present')

    def publish_api_adapter(self):
        from gateway_consumer_api import publish
        self._check_service_config()
        value=publish(self)
        self._check_service_config()
        return value

    async def retire_idle_runtime(self):
        from gateway_consumer_api import retire_idle_runtime
        return await retire_idle_runtime(self)

    def retire_idle_api_sessions(self):
        from gateway_consumer_api import retire_idle_sessions
        return retire_idle_sessions(self)

    def activate_admission(self):
        from gateway_consumer_admission import activate
        self._check_service_config()
        value=activate(self)
        self._check_service_config()
        return value

    def begin_drain(self):
        from gateway_consumer_admission import begin_drain
        return begin_drain(self)

    def seal_service_admission(self):
        from gateway_consumer_admission import seal_service_failure
        return seal_service_failure(self)

    def finish_drain(self):
        from gateway_consumer_admission import finish_drain
        return finish_drain(self)

    def check(self):
        self._check_service_config()
        value=self._check_attached()
        self._check_service_config()
        return value

    def _check_attached(self):
        # Cleanup must still verify the original native binding and work state
        # when selected config bytes have changed and admission has been sealed.
        require(self._stage=='ATTACHED','consumer_not_attached')
        if self._local_admission:
            from gateway_consumer_admission import check
            return check(self)
        self._identity()
        self._work_absent()
        self._storage()
        require(self._runner._caller_owned_state is self._binding and self._binding._api_bundle is self._bundle
                and self._bundle._adapter is self._adapter,'consumer_native_objects_changed')
        selected=self._bundle.select(self._adapter,self._held._home)
        require(all(a is b for a,b in zip(selected,self._stores)),'consumer_native_stores_changed')
        self._work_absent()
        self._identity()
        return self.status()

    async def detach(self):
        self._identity(loop=True)
        if self._stage=='DETACHED':
            self.assert_store_closeable(self._owner);return self.status()
        require(self._stage=='ATTACHED','consumer_cleanup_unknown_or_active')
        if self._local_admission:
            require(self._admission_phase in ('PREPARED','DRAINED'),'consumer_admission_must_drain')
        # Known pre-effect refusals leave ATTACHED and may be reobserved later.
        self._check_attached()
        self._stage='DETACHING_API'
        try:
            await self._adapter.disconnect()
            if self._canonical_api:
                expected='WITHDRAWN' if self._publication_phase=='PUBLISHED' else 'NEW'
                require(self._bundle._publication_state==expected,'consumer_publication_withdrawal_unknown')
                self._publication_phase=expected
            self._identity(loop=True);self._storage()
            require(self._bundle.status()['state']=='DETACHED','consumer_api_not_detached')
            self._work_absent()
            self._stage='DETACHING_RUNNER'
            self._runner.close_all_session_db_handles()
            self._identity(loop=True);self._storage()
            require(self._binding.status()['state']=='DETACHED','consumer_runner_not_detached')
            self._stage='DETACHED'
            if self._local_admission:self._admission_phase='DETACHED'
            self.assert_store_closeable(self._owner)
            return self.status()
        except BaseException:
            self._stage='CLOSE_UNKNOWN'
            raise

    def assert_store_closeable(self,owner):
        require(owner is self._owner,'consumer_other_owner')
        require(self._stage=='DETACHED','consumer_still_attached_or_unknown')
        if self._local_admission:
            require(self._admission_phase=='DETACHED','consumer_admission_not_detached')
            verify_imports(self._source_proof)
        import gateway_store_startup as startup
        try:
            self._storage()  # New work/epoch drift after detach cannot authorize store close.
        except (startup.live.LiveStoreRejected,startup.response_live.ResponseLiveRejected):
            raise PreparedConsumerRejected('consumer_retired_storage_changed') from None
        require(self._bundle._stage=='DETACHED' and self._binding._stage=='DETACHED'
                and self._bundle._adapter is self._adapter and self._adapter._session_db_cache_closed is True
                and self._runner._caller_owned_state is self._binding and self._binding._api_bundle is self._bundle
                and self._runner.session_store._borrowed_session_state._closed is True
                and self._binding._authority.retired is True,'consumer_detachment_changed')
        from gateway.platforms.api_server_borrowed import _quiescent
        require(self._adapter._running is False and self._adapter._app is None
                and self._adapter._site is None and self._adapter._runner is None,'consumer_listener_changed')
        _quiescent(self._adapter)
        runner,binding=self._runner,self._binding
        self._work_absent()
        authority=binding._authority
        require(runner.session_authority is authority and runner.session_authorities is binding._registry
                and binding._registry.launch is authority and len(binding._registry)==1
                and binding._registry.for_home(binding.home) is authority
                and binding._registry.multiplexed is False
                and authority.db is self._stores[0] and authority.runner is runner
                and type(authority.epoch) is int and authority.epoch==self._expected.epoch
                and authority.instance_id==self._expected.instance_id
                and authority.profile_id==str(binding.home) and runner._draining is True
                and authority.retiring is True and authority.retired is True,
                'consumer_retired_authority_changed')
        descriptor=runner.session_runtime_descriptor
        require(descriptor is binding._descriptor and type(descriptor) is dict
                and type(descriptor.get('authority_epoch')) is int
                and type(descriptor.get('runtime_protocol')) is int
                and descriptor=={'instance_id':self._expected.instance_id,
                    'authority_epoch':self._expected.epoch,'runtime_protocol':1,
                    'state':'caller_detached','capabilities':[],'served_profiles':[]},
                'consumer_retired_descriptor_changed')

    def status(self):
        self._owner._owned()
        return {'state':self._stage,'nativeFeature':self._selected_feature,'storesOwnedHere':False,
            'localAdmissionSelected':self._local_admission,'nativeAdmissionState':self._admission_phase,
            'localAdmissionOpen':self._stage=='ATTACHED' and self._admission_phase=='ACTIVE',
            'canonicalApiSelected':getattr(self,'_canonical_api',False),
            'canonicalApiPublicationState':getattr(self,'_publication_phase','NEW'),
            'workHealthEvaluated':False,
            'sameAcceptedEpoch':self._expected.epoch,'serviceStarted':False,
            'runtimeAdmissionAuthorized':False,'storeReleaseAuthorized':False,
            'profileReleasedHere':False,'activeTaskObserversQualified':False,
            **({'borrowedServiceSelected':True} if getattr(self,'_borrowed_service',False) else {}),
            'fullD3BAccepted':False}
