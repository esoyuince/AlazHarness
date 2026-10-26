"""Actual runtime orchestration over explicit native/lease/model doubles.

Real local asyncio tasks exercise deadlines and retained UNKNOWN state. Native
API/store/model boundaries are synthetic and do not qualify installed behavior.
No native import, database, audit hook, worker thread or privileged action runs.
"""
import asyncio
from contextlib import ExitStack
import copy
import os
from pathlib import Path
import sqlite3
import sys
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_finite_runtime as runtime
from test_supervised_finite_launch import qualification_work, qualification_result


class NoncancellingWait(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_retains_pending_task_and_allows_its_original_completion(self):
        attempt = runtime._Attempt(qualification_work())
        release = asyncio.Event()

        async def operation():
            await release.wait()
            return 'original-completion'

        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'execution_unknown'):
            await attempt.wait(operation(), 0.001)
        self.assertEqual(len(attempt.tasks), 1)
        task = attempt.tasks[0]
        self.assertFalse(task.done())
        self.assertFalse(task.cancelled())
        release.set()  # Explicit fixture resolution, never product cancellation.
        self.assertEqual(await task, 'original-completion')
        self.assertIs(attempt.tasks[0], task)

    async def test_failed_task_remains_recorded_without_cancellation(self):
        attempt = runtime._Attempt(qualification_work())

        async def operation():
            raise ValueError('synthetic operation failed')

        with self.assertRaises(ValueError):
            await attempt.wait(operation(), 1)
        self.assertEqual(len(attempt.tasks), 1)
        self.assertTrue(attempt.tasks[0].done())
        self.assertFalse(attempt.tasks[0].cancelled())

    async def test_expired_total_deadline_does_not_cancel_existing_awaitable(self):
        attempt = runtime._Attempt(qualification_work())
        attempt.deadline = runtime.time.monotonic() - 1
        future = asyncio.get_running_loop().create_future()
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'execution_deadline'):
            await attempt.wait(future, 100)
        self.assertFalse(future.cancelled())
        future.set_result('fixture-completion')
        self.assertEqual(await future, 'fixture-completion')

    async def test_loop_stall_cannot_turn_late_task_completion_into_deadline_success(self):
        attempt = runtime._Attempt(qualification_work())

        async def stalled():
            time.sleep(0.02)  # Deliberate local fixture stall, no native work.
            return 'late-result'

        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'execution_deadline'):
            await attempt.wait(stalled(), 0.001)
        self.assertTrue(attempt.tasks[0].done())
        self.assertFalse(attempt.tasks[0].cancelled())
        self.assertEqual(attempt.tasks[0].result(), 'late-result')


class RuntimeLifecycle(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.events = []
        self.fault = None
        self.blockers = []
        self.loops = []
        self.work = qualification_work()
        self.record = SimpleNamespace(state=SimpleNamespace(epoch=1),
                                      response=object(), retained=object())
        self.mount = object()
        self.stack.enter_context(patch.object(runtime, '_attempt', None))
        self.stack.enter_context(patch.object(runtime, 'MAX_EXECUTION_SECONDS', 5))
        self.stack.enter_context(patch.dict(os.environ, {}, clear=True))
        self.stack.enter_context(patch.object(runtime.sys, 'addaudithook'))
        self.stack.enter_context(patch.object(runtime.sys, 'setprofile'))
        self.stack.enter_context(patch.object(runtime.sys, 'getprofile', return_value=None))
        self.stack.enter_context(patch.object(runtime.threading, 'setprofile'))
        self.stack.enter_context(patch.object(runtime.threading, 'getprofile', return_value=None))
        self.stack.enter_context(patch.object(runtime.threading, 'active_count', return_value=1))
        self.lease = SimpleNamespace(_finished=False, _owner=SimpleNamespace(homes=('fixture-home',)))
        self.lease.check = Mock(side_effect=lambda: self.events.append('lease-check'))
        self.lease.finish = Mock(side_effect=self.finish_lease)
        self.connections = [self.connection() for _ in range(3)]
        self.consumer = self.make_consumer()
        self.owner = self.make_owner()
        self.reserve = Mock(return_value=self.lease)
        self.construct = Mock(return_value=self.owner)
        config = ModuleType('gateway.config')
        config.GatewayConfig = lambda **kwargs: SimpleNamespace(**kwargs)
        config.PlatformConfig = lambda **kwargs: SimpleNamespace(**kwargs)
        gateway = ModuleType('gateway')
        gateway.__path__ = []
        api = ModuleType('gateway.session_api_turn')
        api.run_api_turn = self.api_turn
        self.registry = ModuleType('hermes_state_registry')
        self.registry.stats = Mock(return_value={'total_refcounts': 0})
        self.agent_module = ModuleType('run_agent')
        self.original_factory = object()
        self.agent_module.AIAgent = self.original_factory
        self.stack.enter_context(patch.dict(sys.modules, {
            'gateway': gateway, 'gateway.config': config, 'gateway.session_api_turn': api,
            'hermes_state_registry': self.registry, 'run_agent': self.agent_module,
            'gateway_profile_lease': SimpleNamespace(reserve_profile=self.reserve),
            'gateway_store_startup': SimpleNamespace(NativeStoreStartup=self.construct)}))
        self.stack.enter_context(patch.object(runtime, '_read_case', side_effect=self.read_case))
        self.new_loop = asyncio.new_event_loop
        self.stack.enter_context(patch.object(runtime.asyncio, 'new_event_loop', side_effect=self.create_loop))
        self.addCleanup(self.resolve_fixture_tasks)

    def connection(self):
        conn = SimpleNamespace(total_changes=0, closed=False)

        def execute(sql):
            if conn.closed:
                raise sqlite3.ProgrammingError('closed synthetic connection')
            return []

        conn.execute = Mock(side_effect=execute)
        return conn

    def finish_lease(self):
        self.events.append('lease-finish')
        self.lease._finished = True
        self.lease._owner.homes = ()

    async def block(self, label):
        self.events.append(label + '-pending')
        future = asyncio.get_running_loop().create_future()
        self.blockers.append(future)
        # A broken wait integration fails the test rather than hanging forever.
        timer = asyncio.get_running_loop().call_later(2,
            lambda: future.set_result(None) if not future.done() else None)
        try:
            await future
        finally:
            timer.cancel()

    def make_consumer(self):
        consumer = SimpleNamespace(_connections=tuple(self.connections),
            _admission_phase='PREPARED', _publication_phase='UNPUBLISHED',
            _stage='PREPARED', _adapter=object(),
            _binding=SimpleNamespace(_authority=SimpleNamespace(sessions={}, _mutation_tasks=())))

        def publish():
            self.events.append('publish')
            consumer._publication_phase = 'PUBLISHED'

        def activate():
            self.events.append('activate')
            consumer._admission_phase = 'ACTIVE'

        async def retire():
            self.events.append('retire')
            if self.fault == 'retire':
                await self.block('retire')
            for agent in runtime._attempt.agents:
                agent.closed = True

        async def detach():
            self.events.append('detach')
            consumer._stage = consumer._admission_phase = 'DETACHED'
            if self.fault == 'background-task':
                asyncio.create_task(self.block('background'))

        consumer.publish_api_adapter = Mock(side_effect=publish)
        consumer.activate_admission = Mock(side_effect=activate)
        consumer.begin_drain = Mock(side_effect=lambda: self.events.append('begin-drain'))
        consumer.retire_idle_runtime = retire
        consumer.retire_idle_api_sessions = Mock(side_effect=lambda: self.events.append('retire-sessions'))
        consumer.finish_drain = Mock(side_effect=lambda: self.events.append('finish-drain'))
        consumer.detach = detach
        return consumer

    def make_owner(self):
        owner = SimpleNamespace(_prepared_consumer=self.consumer, expectation=SimpleNamespace(epoch=2),
            state_store=SimpleNamespace(_conn=self.connections[0]),
            replay_store=SimpleNamespace(_conn=self.connections[1]),
            response_store=SimpleNamespace(_conn=self.connections[2]), closed=False)

        def start():
            self.events.append('owner-start')
            if self.fault == 'start':
                raise RuntimeError('synthetic original startup failure')
            # Synthetic trace data, never presented as executed native evidence.
            runtime._attempt.profile_counts = {name: 1 for name in runtime.protocol.PROFILE_FUNCTIONS}
            return {'completedChecks': list(runtime.protocol.COMPLETED_CHECKS)}

        async def prepare(*args, **kwargs):
            self.events.append('prepare')
            self.assertEqual(kwargs, {'local_admission': True, 'canonical_api': True, 'finite_turn': True})
            if self.fault == 'prepare':
                await self.block('prepare')
            runtime._attempt.agents.append(SimpleNamespace(closed=False))
            return self.consumer

        def close():
            self.events.append('owner-close')
            if self.fault == 'close':
                raise RuntimeError('synthetic original close failure')
            for conn in self.connections[:2 if self.fault == 'physical-close' else 3]:
                conn.closed = True
            owner.closed = True

        owner.start = Mock(side_effect=start)
        owner.prepare_runtime = prepare
        owner.close = Mock(side_effect=close)
        owner.status = Mock(side_effect=lambda: {'state': 'CLOSED' if owner.closed else 'VERIFIED',
                                                 'callerLeaseMayBeReleased': owner.closed})
        return owner

    async def api_turn(self, adapter, **kwargs):
        self.assertIs(adapter, self.consumer._adapter)
        kind = runtime.protocol.KINDS[len(runtime._attempt.cases)]
        self.events.append('api-' + kind)
        key = 'normal' if kind == 'replay' else kind
        self.assertEqual(kwargs, {'session_id': self.work['sessionId'],
            'request_id': self.work['requestIds'][key],
            'user_message': runtime.protocol.MESSAGES[key], 'conversation_history': []})
        if self.fault == 'api':
            await self.block('api')
        if kind != 'replay':
            runtime._attempt.computations.append(kind)
        return ('synthetic-result', 'synthetic-usage')

    def read_case(self, attempt, kind, result):
        self.assertEqual(result, ('synthetic-result', 'synthetic-usage'))
        index = runtime.protocol.KINDS.index(kind)
        return copy.deepcopy(qualification_result(self.work)['caseReceipts'][index])

    def create_loop(self):
        loop = self.new_loop()
        self.loops.append(loop)
        shutdown = loop.shutdown_default_executor

        async def finish_executor():
            self.events.append('executor-shutdown')
            self.assertFalse(self.lease._finished)
            self.assertFalse(self.owner.closed)
            if self.fault == 'executor':
                await self.block('executor')
            await shutdown()
            self.events.append('executor-idle')
            if self.fault == 'post-executor-task':
                asyncio.create_task(self.block('post-executor'))

        self.stack.enter_context(patch.object(loop, 'shutdown_default_executor', new=finish_executor))
        return loop

    def resolve_fixture_tasks(self):
        # Only release synthetic futures after custody assertions. No native
        # work is cancelled, no product cleanup is supplied by this fixture.
        for future in self.blockers:
            if not future.done():
                future.set_result(None)
        for loop in self.loops:
            if loop.is_closed():
                continue
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
        asyncio.set_event_loop(None)

    def invoke(self):
        if self.fault in ('prepare', 'api', 'retire', 'executor'):
            original_wait = runtime._Attempt.wait

            async def bounded_wait(attempt, awaitable, seconds):
                return await original_wait(attempt, awaitable, min(seconds, 0.05))

            with patch.object(runtime._Attempt, 'wait', new=bounded_wait):
                return runtime.execute(self.record, self.mount, 'next-owner', self.work)
        return runtime.execute(self.record, self.mount, 'next-owner', self.work)

    def assert_original_custody(self):
        attempt = runtime._attempt
        self.assertEqual(attempt.stage, 'UNKNOWN')
        self.assertIs(attempt.held, self.lease)
        self.assertIs(attempt.owner, self.owner)
        self.assertIs(self.owner._prepared_consumer, self.consumer)
        self.assertFalse(self.lease._finished)
        self.lease.finish.assert_not_called()
        self.assertTrue(all(not task.cancelled() for task in attempt.tasks))
        if attempt.loop is not None:
            self.assertFalse(attempt.loop.is_closed())
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'attempt_already_owned'):
            self.invoke()
        self.reserve.assert_called_once()
        self.construct.assert_called_once()

    def test_success_drains_native_consumer_then_idle_executor_before_original_owner_and_lease(self):
        result = self.invoke()
        self.assertEqual(runtime._attempt.stage, 'COMPLETED')
        self.assertTrue(runtime._attempt.loop.is_closed())
        self.assertEqual(result['pid'], os.getpid())
        self.assertEqual(result['close']['physicalConnectionsClosed'], 3)
        self.assertEqual([case['computationCount'] for case in result['caseReceipts']], [1, 1, 2, 3])
        expected = ['begin-drain', 'retire', 'retire-sessions', 'finish-drain', 'detach',
                    'executor-shutdown', 'executor-idle', 'owner-close', 'lease-check', 'lease-finish']
        start = self.events.index('begin-drain')
        self.assertEqual(self.events[start:], expected)
        self.assertIs(self.agent_module.AIAgent, self.original_factory)
        self.assertTrue(all(task.done() and not task.cancelled() for task in runtime._attempt.tasks))

    def test_startup_failure_keeps_original_owner_and_lease_without_cleanup(self):
        self.fault = 'start'
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.assert_original_custody()
        self.owner.close.assert_not_called()
        self.assertEqual(self.loops, [])

    def test_preparation_is_deadline_bounded_and_pending_task_retains_original_consumer(self):
        self.fault = 'prepare'
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'execution_unknown'):
            self.invoke()
        self.assert_original_custody()
        self.assertEqual(runtime._attempt.failed_stage, 'CONSUMER_PREPARE')
        self.assertEqual(len(runtime._attempt.tasks), 1)
        self.assertFalse(runtime._attempt.tasks[0].done())
        self.consumer.publish_api_adapter.assert_not_called()
        self.owner.close.assert_not_called()

    def test_api_timeout_keeps_tasks_loop_model_factory_owner_and_lease(self):
        self.fault = 'api'
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'execution_unknown'):
            self.invoke()
        self.assert_original_custody()
        self.assertEqual(runtime._attempt.failed_stage, 'NATIVE_WORK')
        self.assertIsNot(self.agent_module.AIAgent, self.original_factory)
        self.assertTrue(any(not task.done() for task in runtime._attempt.tasks))
        self.consumer.begin_drain.assert_not_called()
        self.owner.close.assert_not_called()

    def test_extra_pending_loop_task_blocks_owner_close_and_lease_release(self):
        self.fault = 'background-task'
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'loop_tasks_remain'):
            self.invoke()
        self.assert_original_custody()
        self.owner.close.assert_not_called()
        self.assertNotIn('executor-shutdown', self.events)
        self.assertTrue(asyncio.all_tasks(runtime._attempt.loop))

    def test_executor_shutdown_timeout_retains_original_open_stores_and_lease(self):
        self.fault = 'executor'
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'execution_unknown'):
            self.invoke()
        self.assert_original_custody()
        self.assertEqual(runtime._attempt.failed_stage, 'NATIVE_DRAIN')
        self.assertEqual(self.consumer._stage, 'DETACHED')
        self.assertTrue(all(not conn.closed for conn in self.connections))
        self.owner.close.assert_not_called()

    def test_second_pending_task_guard_runs_after_executor_before_owner_close(self):
        self.fault = 'post-executor-task'
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'loop_tasks_remain'):
            self.invoke()
        self.assert_original_custody()
        self.assertIn('executor-idle', self.events)
        self.owner.close.assert_not_called()

    def test_short_consumer_connection_tuple_cannot_claim_same_three_connections(self):
        self.consumer._connections = tuple(self.connections[:2])
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'original_connections_changed'):
            self.invoke()
        self.assert_original_custody()
        self.consumer.publish_api_adapter.assert_not_called()
        self.owner.close.assert_not_called()

    def test_original_close_failure_does_not_finish_caller_lease(self):
        self.fault = 'close'
        with self.assertRaisesRegex(RuntimeError, 'synthetic original close failure'):
            self.invoke()
        self.assert_original_custody()
        self.owner.close.assert_called_once()
        self.assertEqual(runtime._attempt.failed_stage, 'OWNER_CLOSE')

    def test_partial_physical_close_is_unknown_and_never_releases_caller_lease(self):
        self.fault = 'physical-close'
        with self.assertRaisesRegex(runtime.FiniteRuntimeRejected, 'connections_not_physically_closed'):
            self.invoke()
        self.assert_original_custody()
        self.assertEqual(sum(conn.closed for conn in self.connections), 2)
        self.owner.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
