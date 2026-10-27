"""Final READY recheck on the real BorrowedServiceOwner with real config bytes.

Native startup/preparation/HTTP and execution readiness are explicit fixture
ports. The real service start/failure-seal code and original startup config
guard run; real local files, identities and SQLite close probes are exercised.
This does not qualify a native listener, confinement, provider or model.
"""
import asyncio
from dataclasses import replace
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'tests')]

import gateway_service_profile as profile
import gateway_service_runtime as runtime
import gateway_store_startup as startup
import service_profile_fixtures_r161a1 as profiles
import test_borrowed_service_host_r159a1 as lifecycle


def attach_selected_profile(case):
    profiles.set_up_profile(case)
    owner = case.s._owner
    owner._actor = (os.getpid(), case.uid, case.gid, threading.get_ident())
    owner._held._home = case.home
    owner._service_profile = owner._service_profile_binding = case.expectation
    # Establish that the selected real file is valid before the async gap.
    owner._check_service_config()
    return owner


class ServiceReadyConfigTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await lifecycle.ServiceStartupGuards.asyncSetUp(self)
        self.original_owner = attach_selected_profile(self)
        self.original_held = self.s._held

    async def in_last_readiness_wait(self, mutation):
        entered, release = asyncio.Event(), asyncio.Event()

        async def last_readiness_wait():
            entered.set()
            await release.wait()

        self.s._execution.require_ready.side_effect = last_readiness_wait
        observer = asyncio.create_task(self.s.start(object(), self.config))
        await entered.wait()
        self.assertEqual(self.s._state, 'STARTING')
        self.assertEqual(self.trace, ['publish', 'activate', 'listener'])
        try:
            mutation()
        finally:
            release.set()
        return await observer

    def assert_unknown_retained(self):
        self.assertIs(type(self.s), runtime.BorrowedServiceOwner)
        self.assertIs(type(self.original_owner), startup.NativeStoreStartup)
        self.assertIs(self.s._owner, self.original_owner)
        self.assertIs(self.s._held, self.original_held)
        self.assertIs(self.original_owner._prepared_consumer, self.s._consumer)
        state = self.s.status()
        self.assertEqual(state['state'], 'UNKNOWN')
        self.assertFalse(state['serviceReady'] or state['admissionOpen'])
        self.assertFalse(state['close']['callerLeaseReleased'])
        self.assertFalse(self.original_held._finished)
        self.assertEqual(self.s._consumer._binding._stage, 'DRAINING')
        self.assertEqual(self.trace.count('native_failure_seal'), 1)
        self.assertEqual(self.trace.count('listener'), 1)
        for connection in self.connections:
            self.assertEqual(connection.execute('SELECT 1').fetchone(), (1,))

    async def test_config_drift_during_final_readiness_wait_cannot_publish_ready(self):
        with self.assertRaises(profile.ServiceProfileRejected):
            await self.in_last_readiness_wait(
                lambda: (self.home / profile.CONFIG_NAME).write_bytes(b'{}'))
        self.assert_unknown_retained()
        original_start = self.s._start_task
        with self.assertRaisesRegex(runtime.ServiceRuntimeRejected, 'already_started'):
            await self.s.start(object(), self.config)
        self.assertIs(self.s._start_task, original_start)

    async def test_unchanged_selected_profile_reaches_ready_on_original_owner(self):
        result = await self.in_last_readiness_wait(lambda: None)
        self.assertEqual(result['state'], 'READY')
        self.assertTrue(result['serviceReady'] and result['admissionOpen'])
        self.assertIs(self.s._owner, self.original_owner)
        self.assertIs(self.original_owner._service_profile, self.expectation)
        self.assertEqual(len(self.s._connections), 3)
        self.assertTrue(all(a is b for a, b in zip(self.s._connections, self.connections)))
        self.assertFalse(self.original_held._finished)
        self.verify.assert_called_once_with(self.s._consumer._source_proof)

    async def test_receipt_removal_during_final_wait_is_not_a_legacy_downgrade(self):
        with self.assertRaisesRegex(startup.StoreStartupRejected, 'service_profile_changed'):
            await self.in_last_readiness_wait(
                lambda: setattr(self.original_owner, '_service_profile', None))
        self.assert_unknown_retained()

    async def test_source_selection_change_during_final_wait_cannot_publish_ready(self):
        changed = replace(self.selection, selection_sha256='e' * 64)
        with patch.object(profile.sources, 'load_selection', return_value=changed):
            with self.assertRaises(profile.ServiceProfileRejected):
                await self.in_last_readiness_wait(lambda: None)
        self.assert_unknown_retained()

    async def test_source_recheck_cannot_hide_config_change_before_ready(self):
        self.verify.side_effect = lambda _: (
            self.home / profile.CONFIG_NAME).write_bytes(b'{}')
        with self.assertRaises(profile.ServiceProfileRejected):
            await self.s.start(object(), self.config)
        self.assert_unknown_retained()

    async def test_legacy_owner_does_not_require_a_service_profile_or_config_file(self):
        del self.original_owner._service_profile
        del self.original_owner._service_profile_binding
        (self.home / profile.CONFIG_NAME).unlink()
        with patch.object(profile, 'check_config', side_effect=AssertionError(
                'legacy owner must not inspect service config')) as inspect:
            result = await self.s.start(object(), self.config)
        self.assertEqual(result['state'], 'READY')
        inspect.assert_not_called()


class KnownCleanupAfterConfigDriftTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await lifecycle.ServiceClosureTests.asyncSetUp(self)
        self.original_owner = attach_selected_profile(self)

    async def test_known_close_after_config_drift_keeps_original_cleanup_order(self):
        (self.home / profile.CONFIG_NAME).write_bytes(b'{}')
        with patch.object(profile, 'check_config', side_effect=AssertionError(
                'cleanup must not read or re-admit config')) as inspect:
            result = await self.s.close_when_idle()
        inspect.assert_not_called()
        self.assertEqual(result['state'], 'CLOSED')
        self.assertEqual(self.trace, ['drain', 'transport', 'runtime', 'api',
            'finish_drain', 'detach', 'executor', 'stores', 'lease'])
        self.assertEqual(result['close']['physicalStoresClosed'], 3)
        self.assertTrue(result['close']['callerLeaseReleased'])
        self.assertFalse(result['close']['imageLeaseReleasedHere'])


if __name__ == '__main__':
    unittest.main()
