"""One caller-owned native service and its ordered, clean-only retirement.

This is the concrete consumer of BorrowedHTTPTransport and NativeStoreStartup.
It does not create another store, epoch, queue, result store, process or image
owner. A trusted launcher supplies the original startup and native plugin context.
The launcher retains this object and the image lease on every unknown outcome.
Terminal closure is returned on that retained owner channel, never inferred from
the disappearance of the HTTP listener or from a stop acknowledgement.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import re
import sqlite3
import threading

PROTOCOL = 'alaz-borrowed-service-v1'


class ServiceRuntimeRejected(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise ServiceRuntimeRejected(reason)


def _reason(exc):
    value = str(exc)
    return value if re.fullmatch('[a-z][a-z0-9_]{0,95}', value) else 'service_operation_unavailable'


class BorrowedServiceOwner:
    """One-shot service on the original thread/loop, with retained async tasks.

    Awaiter cancellation stops observation only: the original start/close task is
    shielded and remains strongly owned here. The caller must keep the owner and
    its loop alive until a terminal receipt or an explicit operator resolution.
    """
    def __init__(self, owner, *, host_policy, execution, context):
        from gateway_store_startup import NativeStoreStartup
        from host_gate import HostGatePolicy
        from execution_boundary import ExecutionBoundary
        require(type(owner) is NativeStoreStartup, 'service_native_owner_required')
        require(type(host_policy) is HostGatePolicy and type(execution) is ExecutionBoundary,
                'service_explicit_boundaries_required')
        require(execution.broker is not None and execution.adapter is None,
                'service_unbound_broker_execution_required')
        require(host_policy.allowed_models == frozenset((execution.policy.model,)),
                'service_single_model_required')
        owner._owned()
        require(owner._stage in ('NEW', 'VERIFIED') and owner._prepared_consumer is None
                and owner._response_expected is not None,
                'service_fresh_three_store_owner_required')
        require(getattr(owner, '_service_owner', None) is None, 'service_owner_already_reserved')
        self._owner = owner
        self._held = owner._held
        self._policy = host_policy
        self._execution = execution
        self._context = context
        self._actor = (os.getpid(), threading.get_ident())
        self._loop = None
        self._state = 'NEW'
        self._consumer = self._transport = self._app = None
        self._stores = self._connections = ()
        self._start_task = self._close_task = None
        self._epoch = self._instance_id = None
        self._endpoint = None
        self._last_reason = None
        self._seal_reason = None
        self._listener_started = False
        self._close = {
            'transportRetired': False, 'runtimeRetired': False,
            'apiSessionsRetired': False, 'consumerDetached': False,
            'defaultExecutorJoined': False, 'physicalStoresClosed': 0,
            'callerLeaseReleased': False, 'imageLeaseReleasedHere': False,
        }
        # A second wrapper cannot claim this owner after partial construction,
        # startup failure, listener failure or an observer losing its response.
        owner._service_owner = self

    def _actor_check(self, *, loop=False):
        require((os.getpid(), threading.get_ident()) == self._actor, 'service_other_actor')
        require(getattr(self._owner, '_service_owner', None) is self
                and self._owner._held is self._held, 'service_owner_changed')
        if loop:
            current = asyncio.get_running_loop()
            require(self._loop is current, 'service_other_loop')

    def _configure(self, app, adapter, transport):
        self._actor_check(loop=True)
        require(self._state == 'STARTING' and transport is self._transport
                and adapter is self._consumer._adapter, 'service_transport_changed')
        require(self._app is None, 'service_application_already_bound')
        self._app = app
        from hermes_cli.plugins import PluginContext
        require(type(self._context) is PluginContext, 'service_native_plugin_context_required')
        require(Path(self._context._manager.scope_key).resolve() == self._held._home
                and self._context.plugin_id == 'alaz-host-gate',
                'service_plugin_scope_changed')
        self._execution.register(self._context)
        from host_gate_plugin import bind_host_gate
        bind_host_gate(app, adapter, self._policy, execution=self._execution,
                       service_transport=transport,service_owner=self)

    def require_admission(self, *, transport, app, adapter):
        """Pure worker-safe overall readiness gate for the existing host write.

        Listener readiness alone is insufficient while execution/broker/source
        checks are still pending. This exact owner cannot be replaced by a
        caller-selected callback, descriptor label or stale ready receipt.
        """
        return self._require_binding(transport=transport,app=app,adapter=adapter,for_admission=True)

    def require_execution(self, *, transport, app, adapter):
        """External provider entry is unavailable before overall readiness.

        During draining it remains available to already admitted native workers.
        Direct startup budget initialization is not an external provider request.
        """
        return self._require_binding(transport=transport,app=app,adapter=adapter,for_admission=False)

    def _require_binding(self, *, transport, app, adapter, for_admission):
        require(os.getpid() == self._actor[0] and self._loop is not None
                and not self._loop.is_closed(), 'service_admission_actor_or_loop')
        require(self._state in (('READY',) if for_admission else ('READY','DRAINING')),
                'service_admission_not_ready')
        c, owner = self._consumer, self._owner
        require(c is not None and transport is self._transport and app is self._app
                and adapter is c._adapter and c._loop is self._loop
                and owner._service_owner is self and owner._prepared_consumer is c
                and owner._held is self._held and owner._stage == 'VERIFIED'
                and c._owner is owner and c._borrowed_service is True
                and c._admission_phase in (('ACTIVE',) if for_admission else ('ACTIVE','DRAINING'))
                and c._stage == 'ATTACHED',
                'service_admission_owner_changed')
        require(owner._expected is c._expected
                and (c._expected.epoch,c._expected.instance_id) == (self._epoch,self._instance_id)
                and len(self._stores) == len(self._connections) == len(c._stores) == len(c._connections) == 3
                and all(a is b for a,b in zip(c._stores,self._stores))
                and all(a is b for a,b in zip(c._connections,self._connections))
                and all(store._conn is connection for store,connection in zip(self._stores,self._connections)),
                'service_admission_store_generation_changed')
        authority = transport.check_binding(for_admission=for_admission,app=app,adapter=adapter)
        require(authority is c._binding._authority
                and (authority.epoch,authority.instance_id) == (self._epoch,self._instance_id),
                'service_admission_authority_changed')
        return authority

    @staticmethod
    def _retain_result(task):
        # Retrieving an exception avoids an unobserved-task traceback after a
        # disconnected observer. The same task/result remains owned and awaitable.
        if not task.cancelled():task.exception()

    async def start(self, gateway_config, api_config):
        self._actor_check()
        require(self._state == 'NEW' and self._start_task is None, 'service_already_started')
        self._loop = asyncio.get_running_loop()
        extra = getattr(api_config, 'extra', None)
        require(type(extra) is dict and extra.get('host') == '127.0.0.1'
                and type(extra.get('port')) is int and 1 <= extra['port'] <= 65535,
                'service_explicit_loopback_port_required')
        token = extra.get('key')
        require(type(token) is str and re.fullmatch('[A-Za-z0-9._~-]{32,256}', token) is not None,
                'service_explicit_api_credential_required')
        require(token != self._execution.token
                and token != self._execution.broker.link.signing_key,
                'service_separate_credentials_required')
        require(extra.get('model_name') == self._execution.policy.model,
                'service_model_configuration_mismatch')
        self._state = 'STARTING'
        self._start_task = self._loop.create_task(self._start(gateway_config, api_config))
        self._start_task.add_done_callback(self._retain_result)
        return await asyncio.shield(self._start_task)

    async def _start(self, gateway_config, api_config):
        try:
            if self._owner._stage == 'NEW':
                self._owner.start()
            self._owner._owned()
            require(self._owner._stage == 'VERIFIED', 'service_owner_not_verified')
            self._stores = (self._owner.state_store, self._owner.replay_store,
                            self._owner.response_store)
            self._connections = tuple(store._conn for store in self._stores)
            self._epoch = self._owner.expectation.epoch
            self._instance_id = self._owner.expectation.instance_id
            self._consumer = await self._owner.prepare_runtime(gateway_config, api_config,
                local_admission=True, canonical_api=True, finite_turn=True, borrowed_service=True)
            c = self._consumer
            require(all(a is b for a, b in zip(c._connections, self._connections))
                    and len(c._connections) == len(self._connections) == 3,
                    'service_original_connections_changed')
            c.publish_api_adapter()
            from gateway.platforms.api_server_borrowed_transport import BorrowedHTTPTransport
            self._transport = BorrowedHTTPTransport(c._bundle, configure_app=self._configure)
            c.activate_admission()
            receipt = await self._transport.start()
            require(receipt['state'] == 'READY' and receipt['listenerAuthorized'] is True,
                    'service_listener_start_unconfirmed')
            self._listener_started = True
            self._endpoint = receipt['endpoint']
            self._transport.check(for_admission=True, adapter=c._adapter)
            await self._execution.require_ready()
            from gateway_prepared_consumer import verify_imports
            verify_imports(c._source_proof)
            # Async readiness and source verification can outlive the selected
            # config snapshot. Recheck the original actor and profile before
            # publishing READY; the existing legacy guard remains I/O-free.
            self._actor_check(loop=True)
            self._owner._check_service_config()
            self._state = 'READY'
            return self.status()
        except BaseException as exc:
            if self._consumer is None:
                self._consumer = self._owner._prepared_consumer
            self._last_reason = _reason(exc)
            # Close the public pure readiness guard BEFORE attempting the
            # native seal. Preserve the original failure even if sealing fails.
            self._state = 'UNKNOWN'
            if self._consumer is not None and self._consumer._admission_phase in ('ACTIVE','DRAINING'):
                try:self._consumer.seal_service_admission()
                except BaseException as seal_exc:self._seal_reason = _reason(seal_exc)
            raise

    def begin_drain(self):
        self._actor_check(loop=True)
        require(self._state in ('READY', 'DRAINING'), 'service_not_ready_or_draining')
        try:
            # The consumer updates its own phase and delegates to the native
            # gate without waiting for SQL or for any physical worker.
            self._consumer.begin_drain()
            self._state = 'DRAINING'
            self._last_reason = None
            return self.status()
        except BaseException as exc:
            self._last_reason = _reason(exc)
            self._state = 'UNKNOWN'
            raise

    async def close_when_idle(self):
        self._actor_check(loop=True)
        if self._state == 'CLOSED':
            return self.status()
        if self._close_task is not None and not self._close_task.done():
            return await asyncio.shield(self._close_task)
        require(self._state in ('READY', 'DRAINING'), 'service_close_unknown_or_unstarted')
        if self._state == 'READY':
            self.begin_drain()
        self._close_task = self._loop.create_task(self._close_once())
        self._close_task.add_done_callback(self._retain_result)
        return await asyncio.shield(self._close_task)

    async def _close_once(self):
        from gateway.platforms.api_server_borrowed import BorrowedStoreRejected
        self._state = 'CLOSING'
        try:
            try:
                retired = await self._transport.retire_idle()
            except BorrowedStoreRejected as exc:
                # Only the native typed pre-effect refusal with the original
                # transport phase unchanged is re-observable. No forced close,
                # second listener, cancellation, recovery or refund follows.
                if self._transport.status()['state'] in ('READY', 'DRAINING'):
                    self._state = 'DRAINING'
                    self._last_reason = _reason(exc)
                    return self.status()
                raise
            require(retired['state'] == 'RETIRED' and retired['callerStoresClosed'] is False,
                    'service_transport_retirement_unconfirmed')
            self._close['transportRetired'] = True
            self._state = 'CLOSING'
            c = self._consumer
            result = await c.retire_idle_runtime()
            require(result['state'] == 'IDLE_RUNTIME_RETIRED', 'service_runtime_retirement_unconfirmed')
            self._close['runtimeRetired'] = True
            result = c.retire_idle_api_sessions()
            require(result['state'] == 'IDLE_API_SESSIONS_RETIRED', 'service_api_retirement_unconfirmed')
            self._close['apiSessionsRetired'] = True
            c.finish_drain()
            await c.detach()
            require(c._stage == 'DETACHED' and c._admission_phase == 'DETACHED',
                    'service_consumer_detachment_unconfirmed')
            self._close['consumerDetached'] = True
            # The dedicated owner loop retains queued to_thread obligations;
            # join its executor before physically closing the original stores.
            await self._loop.shutdown_default_executor()
            self._close['defaultExecutorJoined'] = True
            require(all(store._conn is conn for store, conn in zip(self._stores, self._connections)),
                    'service_original_connections_changed')
            self._owner.close()
            closed = 0
            for connection in self._connections:
                try:
                    connection.in_transaction
                except sqlite3.ProgrammingError:
                    closed += 1
            require(closed == 3 and self._owner.status()['callerLeaseMayBeReleased'] is True,
                    'service_physical_store_close_unconfirmed')
            self._close['physicalStoresClosed'] = closed
            self._held.check()
            self._held.finish()
            require(self._held._finished and not self._held._owner.homes,
                    'service_profile_release_unconfirmed')
            self._close['callerLeaseReleased'] = True
            self._last_reason = None
            self._state = 'CLOSED'
            return self.status()
        except BaseException as exc:
            self._last_reason = _reason(exc)
            self._state = 'UNKNOWN'
            raise

    def status(self):
        self._actor_check()
        if self._state in ('READY','DRAINING'):
            try:
                observed=self._transport.status()['state']
                expected='ACTIVE' if self._state=='READY' else 'DRAINING'
                require(observed==self._state and self._consumer._admission_phase==expected,
                        'service_runtime_phase_changed')
                self._transport.check_binding(app=self._app,adapter=self._consumer._adapter)
            except Exception as exc:
                self._last_reason=_reason(exc)
                self._state='UNKNOWN'
        return {
            'protocol': PROTOCOL, 'state': self._state,
            'pid': os.getpid(), 'epoch': self._epoch, 'instanceId': self._instance_id,
            'endpoint': self._endpoint, 'serviceStarted': self._listener_started,
            'serviceReady': self._state == 'READY', 'serviceClosed': self._state == 'CLOSED',
            'admissionOpen': self._state == 'READY', 'close': dict(self._close),
            'reason': self._last_reason, 'admissionSealReason': self._seal_reason, 'retryAllowed': False,
            'nativeStoresOwnedHere': False, 'imageLeaseOwnedHere': False,
            'fullD3BAccepted': False,
        }
