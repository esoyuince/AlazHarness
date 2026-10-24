"""One fixed native-store startup sequence under a caller-held ProfileLease.

Call after final exec/confinement. Finite layout -> isolated read-only preflight
-> pinned native constructors -> live gate -> clean-only native epoch -> live
gate. No listener, provider, arbitrary callback or automatic work recovery.
The caller owns the profile/image lease and MUST retain it until close succeeds.
If a constructor/close has unknown effects, exit the dedicated process rather
than retrying or releasing ownership. No destructor/context-manager cleanup.
"""
from __future__ import annotations
from dataclasses import replace
import re
import sqlite3
import threading
import gateway_live_store_gate as live
import gateway_native_layout as layout
import gateway_store_preopen as preopen
import gateway_response_preopen as response_preopen
import gateway_response_live as response_live


class StoreStartupRejected(RuntimeError):
    pass


def require(ok,reason):
    if not ok:raise StoreStartupRejected(reason)


def _native():
    # Only normal imports from the trusted pinned installation, after preflight.
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    import hermes_state_runtime
    return SessionDB,RunIdempotencyStore,hermes_state_runtime


class NativeStoreStartup:
    """Process/thread-bound one-shot object; failed starts are never replayed.

    No user-selectable factory or dynamic opening policy. Only reject-pending
    recovery policy is supported. Success is storage readiness, not a grant to
    expose HTTP or redispatch a partial pair. Even terminal pairs have not been
    reconciled here. Public native handles are available ONLY after verification.
    """
    def __init__(self,held,expected_mount,expected,*,instance_id,response_expected=None,prepared_layout=False):
        require(type(held) is live.profiles.ProfileLease,'startup_native_lease_required')
        require(type(expected_mount) is live.mounts.ExpectedMount,'startup_mount_expectation')
        require(type(expected) is live.PreparedStoreExpectation and expected.journal_mode=='delete',
                'startup_trusted_cold_expectation')
        require(type(instance_id) is str and re.fullmatch('[A-Za-z0-9._-]{1,128}',instance_id) is not None,
                'startup_instance_id')
        require(instance_id!=expected.instance_id,'startup_new_instance_required')
        require(type(prepared_layout) is bool,'startup_prepared_layout_option')
        require(not prepared_layout or response_expected is not None,'startup_prepared_layout_requires_response')
        self._prepared_layout=prepared_layout
        if response_expected is not None:
            response_preopen._pair(response_expected,expected)
        self._response_expected=response_expected
        self._response=None;self._response_conn=None
        held.check()
        self._actor=live.profiles._actor()
        require(self._actor==held._actor,'startup_other_actor')
        self._held,self._mount,self._expected=held,expected_mount,expected
        self._instance_id=instance_id
        self._state=self._replay=None
        self._state_conn=self._replay_conn=None
        self._unknown_constructor=False
        self._epoch_attempted=False
        self._stage='NEW';self._receipts=[]
        self._prepared_consumer=None

    def _owned(self):
        require(live.profiles._actor()==self._actor,'startup_other_actor')
        self._held.check()

    def _drained(self):
        # Extra cooperative guard only, not inventory of hostile same-UID code.
        owner=self._held._owner
        with owner._mutex:
            require(not any(t.is_alive() for t in owner._writers),'startup_writers_active')
        if self._state is not None:
            writer=self._state._token_writer_thread
            require(writer is None or not writer.is_alive(),'startup_writers_active')

    def start(self):
        self._owned()
        require(self._stage=='NEW','startup_not_fresh')
        # Set before any filesystem/import/constructor/epoch effect.
        self._stage='STARTING'
        try:
            self._drained()
            home=self._held._home
            self._stage='LAYOUT'
            options={'include_response':True} if self._response_expected is not None else {}
            if self._prepared_layout:options['include_prepared']=True
            snapshot=layout.inspect_profile(home,uid=self._actor[1],gid=self._actor[2],
                                            device=self._expected.state_identity[0],**options)
            if self._response_expected is not None:
                require(snapshot['response_store.db'][:2]==self._response_expected.response_identity,
                        'startup_response_layout_identity')
            require(snapshot['state.db'][:2]==self._expected.state_identity
                    and snapshot['runs_idempotency.db'][:2]==self._expected.replay_identity,
                    'startup_layout_identity')
            self._stage='PREFLIGHT'
            proof=preopen.verify_preopen(self._held,self._mount,self._expected)
            require(proof['state']=='COLD_STORES_PREFLIGHT_VERIFIED','startup_preflight_result')
            self._receipts.append(('preflight',proof))
            if self._response_expected is not None:
                self._stage='RESPONSE_PREFLIGHT'
                proof=response_preopen.verify_response_preopen(self._held,self._mount,self._response_expected,self._expected)
                require(proof['state']=='COLD_RESPONSE_PREFLIGHT_VERIFIED','startup_response_preflight_result')
                self._receipts.append(('response_preflight',proof))
            self._owned();self._drained()
            State,Replay,runtime=_native()
            self._stage='STATE_CONSTRUCTOR';self._unknown_constructor=True
            self._state=State(home/'state.db')
            self._state_conn=self._state._conn
            self._unknown_constructor=False
            self._stage='REPLAY_CONSTRUCTOR';self._unknown_constructor=True
            self._replay=Replay(str(home/'runs_idempotency.db'))
            self._replay_conn=self._replay._conn
            self._unknown_constructor=False
            self._stage='LIVE_BEFORE_EPOCH'
            proof=live.verify_live_stores(self._held,self._mount,self._state,self._replay,self._expected)
            require(proof['state']=='NATIVE_STORE_CONNECTIONS_VERIFIED','startup_live_result')
            self._receipts.append(('before_epoch',proof))
            if self._response_expected is not None:
                Response=response_live.qualified_response_type()
                want=self._response_expected
                self._stage='RESPONSE_CONSTRUCTOR';self._unknown_constructor=True
                self._response=Response(db_path=str(home/'response_store.db'),canonical_state=self._state,
                                        max_size=want.max_size,max_identities=want.max_identities)
                self._response_conn=self._response._conn;self._unknown_constructor=False
                self._stage='RESPONSE_LIVE_BEFORE_EPOCH'
                proof=response_live.verify_response_connection(self._held,self._mount,self._state,
                    self._response,self._response_live_expectation(),constructor=True)
                require(proof['state']=='NATIVE_RESPONSE_CONNECTION_VERIFIED','startup_response_live_result')
                self._receipts.append(('response_before_epoch',proof))
            self._owned();self._drained()
            # No recover_session_inputs, queue mutation, provider or task dispatch.
            # An exception/interrupt after this flag is never treated as no effect.
            self._stage='EPOCH_COMMITTING';self._epoch_attempted=True
            epoch=runtime.begin_runtime_epoch(self._state,instance_id=self._instance_id)
            require(type(epoch) is int and epoch==self._expected.epoch+1,'startup_epoch_result')
            self._expected=replace(self._expected,epoch=epoch,instance_id=self._instance_id)
            self._stage='LIVE_AFTER_EPOCH'
            proof=live.verify_live_stores(self._held,self._mount,self._state,self._replay,self._expected)
            require(proof['state']=='NATIVE_STORE_CONNECTIONS_VERIFIED','startup_live_result')
            self._receipts.append(('after_epoch',proof))
            if self._response_expected is not None:
                self._stage='RESPONSE_LIVE_AFTER_EPOCH'
                proof=response_live.verify_response_connection(self._held,self._mount,self._state,
                    self._response,self._response_live_expectation(),constructor=True)
                require(proof['state']=='NATIVE_RESPONSE_CONNECTION_VERIFIED','startup_response_live_result')
                self._receipts.append(('response_after_epoch',proof))
            self._owned();self._drained()
            self._stage='VERIFIED'
            return self.status()
        except BaseException as exc:
            self._stage='FAILED'
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):raise
            if isinstance(exc,StoreStartupRejected):raise
            # Bound diagnostics; original exception retains details only locally.
            raise StoreStartupRejected('startup_sequence_rejected') from exc

    async def prepare_runtime(self, gateway_config, api_config, *, local_admission=False, canonical_api=False, finite_turn=False):
        """Attach the fixed prepared consumer; no new store owner or service."""
        self._owned()
        require(type(local_admission) is bool,'startup_admission_option')
        require(type(canonical_api) is bool and (not canonical_api or local_admission),
                'startup_canonical_api_option')
        require(self._stage=='VERIFIED' and self._response_expected is not None,
                'startup_verified_three_stores_required')
        require(self._prepared_consumer is None,'startup_consumer_already_reserved')
        from gateway_prepared_consumer import PreparedRuntimeConsumer
        require(type(finite_turn) is bool and (not finite_turn or canonical_api),
                'startup_finite_option')
        consumer=(PreparedRuntimeConsumer(self,local_admission=True,canonical_api=True,finite_turn=True) if finite_turn
                  else PreparedRuntimeConsumer(self,local_admission=True,canonical_api=True) if canonical_api
                  else PreparedRuntimeConsumer(self,local_admission=True) if local_admission
                  else PreparedRuntimeConsumer(self))
        # Reserve BEFORE imports/native constructors/awaits can have effects.
        self._prepared_consumer=consumer
        await consumer.prepare(gateway_config,api_config)
        return consumer

    def _response_live_expectation(self):
        want=self._response_expected
        return response_live.ResponseConnectionExpectation(want.native_feature,want.schema_sha256,
            want.response_identity,want.max_size,want.max_identities)

    @property
    def response_store(self):
        self._owned();require(self._stage=='VERIFIED','startup_not_verified')
        require(self._response_expected is not None,'startup_response_not_configured')
        return self._response

    @property
    def response_expectation(self):
        self._owned();require(self._stage=='VERIFIED','startup_not_verified')
        require(self._response_expected is not None,'startup_response_not_configured')
        return self._response_expected

    @property
    def state_store(self):
        self._owned();require(self._stage=='VERIFIED','startup_not_verified');return self._state

    @property
    def replay_store(self):
        self._owned();require(self._stage=='VERIFIED','startup_not_verified');return self._replay

    @property
    def expectation(self):
        self._owned();require(self._stage=='VERIFIED','startup_not_verified');return self._expected

    def status(self):
        require(live.profiles._actor()==self._actor,'startup_other_actor')
        return {'state':self._stage,'nativePin':live.NATIVE_PIN,
            'responseConfigured':self._response_expected is not None,
            'epochObserved':self._expected.epoch,'epochMayHaveAdvanced':self._epoch_attempted,
            'unknownConstructorEffects':self._unknown_constructor,
            'completedChecks':[label for label,_ in self._receipts],
            'storageReady':self._stage=='VERIFIED','callerLeaseMayBeReleased':self._stage=='CLOSED',
            'recoveryPolicy':'REFUSE_PENDING_NO_REPLAY','automaticRecoveryPerformed':False,
            'runtimeAdmissionAuthorized':False,'pairedRecoveryVerified':False,'fullD3BAccepted':False}

    def close(self):
        require(live.profiles._actor()==self._actor,'startup_other_actor')
        if self._stage=='CLOSED':return
        self._owned()
        require(self._stage in ('NEW','FAILED','VERIFIED'),'startup_close_unknown_or_active')
        require(not self._unknown_constructor,'startup_constructor_effects_unknown')
        if self._prepared_consumer is not None:
            from gateway_prepared_consumer import PreparedRuntimeConsumer
            require(type(self._prepared_consumer) is PreparedRuntimeConsumer,'startup_consumer_identity')
            self._prepared_consumer.assert_store_closeable(self)
        self._drained()
        # Never implicitly discard a caller's uncommitted transaction.
        # The caller must explicitly settle it before asking for shutdown.
        if self._response_expected is not None:
            for store,connection in ((self._state,self._state_conn),(self._replay,self._replay_conn),
                                     (self._response,self._response_conn)):
                require(store is None or store._conn is connection,'startup_connection_replaced')
        for connection in (self._response_conn,self._state_conn,self._replay_conn):
            if connection is not None:
                require(not connection.in_transaction,'startup_transaction_active')
        self._stage='CLOSING'
        try:
            # Close only returned/owned handles; never release caller's lease here.
            for store,connection in ((self._response,self._response_conn),(self._replay,self._replay_conn),(self._state,self._state_conn)):
                if store is None:continue
                store.close()
                try:connection.in_transaction
                except sqlite3.ProgrammingError:pass
                else:raise StoreStartupRejected('startup_connection_not_closed')
            self._held.check()
            self._stage='CLOSED'
        except BaseException as exc:
            self._stage='CLOSE_UNKNOWN'
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):raise
            if isinstance(exc,StoreStartupRejected):raise
            raise StoreStartupRejected('startup_close_unconfirmed') from exc
