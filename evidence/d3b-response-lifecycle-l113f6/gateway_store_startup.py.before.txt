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
    def __init__(self,held,expected_mount,expected,*,instance_id):
        require(type(held) is live.profiles.ProfileLease,'startup_native_lease_required')
        require(type(expected_mount) is live.mounts.ExpectedMount,'startup_mount_expectation')
        require(type(expected) is live.PreparedStoreExpectation and expected.journal_mode=='delete',
                'startup_trusted_cold_expectation')
        require(type(instance_id) is str and re.fullmatch('[A-Za-z0-9._-]{1,128}',instance_id) is not None,
                'startup_instance_id')
        require(instance_id!=expected.instance_id,'startup_new_instance_required')
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
            snapshot=layout.inspect_profile(home,uid=self._actor[1],gid=self._actor[2],
                                            device=self._expected.state_identity[0])
            require(snapshot['state.db'][:2]==self._expected.state_identity
                    and snapshot['runs_idempotency.db'][:2]==self._expected.replay_identity,
                    'startup_layout_identity')
            self._stage='PREFLIGHT'
            proof=preopen.verify_preopen(self._held,self._mount,self._expected)
            require(proof['state']=='COLD_STORES_PREFLIGHT_VERIFIED','startup_preflight_result')
            self._receipts.append(('preflight',proof))
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
            self._owned();self._drained()
            self._stage='VERIFIED'
            return self.status()
        except BaseException as exc:
            self._stage='FAILED'
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):raise
            if isinstance(exc,StoreStartupRejected):raise
            # Bound diagnostics; original exception retains details only locally.
            raise StoreStartupRejected('startup_sequence_rejected') from exc

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
        self._drained()
        # Never implicitly discard a caller's uncommitted transaction.
        # The caller must explicitly settle it before asking for shutdown.
        for connection in (self._state_conn,self._replay_conn):
            if connection is not None:
                require(not connection.in_transaction,'startup_transaction_active')
        self._stage='CLOSING'
        try:
            # Close only returned/owned handles; never release caller's lease here.
            for store,connection in ((self._replay,self._replay_conn),(self._state,self._state_conn)):
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
