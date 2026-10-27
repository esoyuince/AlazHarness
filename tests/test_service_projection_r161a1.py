"""Service projection contracts; mount/namespace/security syscalls are doubles.

Real profile-file admission is tested separately. These tests establish selection,
mapping and fail-closed ordering, not privileged Linux runtime acceptance.
"""
from contextlib import ExitStack
from dataclasses import asdict, replace, FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import inspect
import unittest
from unittest.mock import Mock, patch

import test_gateway_state_projection as old
import gateway_service_profile as profile
import gateway_service_projection as mapping

p = old.p
DEVICE = 1792


def receipt(home='/srv/test/volume/profile'):
    return profile.ServiceProfileExpectation(1, profile.sources.load_selection(),
        home, (DEVICE, 12), ((DEVICE, 21), (DEVICE, 22), (DEVICE, 23)),
        1, 'previous-native-owner', 'd' * 64, (DEVICE, 24), 40, 'f' * 64)


def snapshot():
    return {'profile': (DEVICE, 12, 0o40700, 23001, 23003, 2, 4096, 100, 100),
        **{name: (DEVICE, ino, 0o100600, 23001, 23003, 1, size, 100, 100)
           for name, ino, size in (('state.db', 21, 8192),
                ('runs_idempotency.db', 22, 8192), ('response_store.db', 23, 8192),
                ('config.yaml', 24, 40))}}


def posix_device(case):
    # os.makedev is absent on Windows; only loop-device arithmetic is doubled.
    case.stack.enter_context(patch.object(mapping.os, 'makedev',
        side_effect=lambda major, minor: DEVICE + minor, create=True))


class MappingContract(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close); posix_device(self)
        self.b = old.binding(); self.principal = dict(old.P); self.r = receipt()

    def bound(self):
        return mapping.ServiceProjection(self.b, self.r, self.principal)

    def test_constructing_mapping_neither_reads_nor_acquires_profile(self):
        with patch.object(profile, 'inspect_profile') as read, \
                patch.object(profile.sources, 'load_selection', side_effect=AssertionError('no I/O')):
            result = self.bound()
        read.assert_not_called(); self.assertIs(result.receipt, self.r)
        self.assertIs(result.volume, self.b)
        with self.assertRaises(FrozenInstanceError): result.volume = old.binding()

    def test_mapping_changes_only_home_and_preserves_selected_config(self):
        original = asdict(self.r); bound = self.bound()
        with patch.object(profile, 'inspect_profile', return_value=snapshot()) as read:
            observed, target = mapping.inspect_view(bound, self.b, self.principal, view='target')
        self.assertEqual(target, replace(self.r, home=p.TARGET))
        self.assertEqual(observed, snapshot()); self.assertEqual(asdict(self.r), original)
        self.assertEqual(read.call_args.args[0].as_posix(), p.TARGET)
        self.assertEqual(read.call_args.kwargs, dict(uid=23001, gid=23003,
            device=DEVICE, expectation=target))

    def test_original_target_receipt_maps_back_to_host_without_mutation(self):
        self.r = receipt(p.TARGET); bound = self.bound()
        with patch.object(profile, 'inspect_profile', return_value=snapshot()):
            _, host = mapping.inspect_view(bound, self.b, self.principal, view='host')
        self.assertEqual(host, replace(self.r, home='/srv/test/volume/profile'))
        self.assertEqual(self.r.home, p.TARGET)

    def test_foreign_home_aliases_and_wrong_volume_are_refused(self):
        for home in ('/tmp/profile', '/srv/test//volume/profile',
                     '/srv/test/volume/profile/', '/run/alaz-state/../profile'):
            with self.subTest(home=home), self.assertRaises((
                    p.StateProjectionRejected, profile.ServiceProfileRejected)):
                mapping.ServiceProjection(self.b, receipt(home), self.principal)
        for b in (replace(self.b, profile_inode=999), replace(self.b, loop_number=1)):
            with self.assertRaisesRegex(p.StateProjectionRejected, 'volume_identity'):
                mapping.ServiceProjection(b, self.r, self.principal)

    def test_equal_reconstructed_volume_cannot_replace_original(self):
        bound = self.bound()
        with self.assertRaisesRegex(p.StateProjectionRejected, 'binding_changed'):
            mapping.validate(bound, replace(self.b), self.principal)

    def test_receipt_config_or_selection_change_after_binding_is_refused(self):
        for field, value in (('config_sha256', 'e' * 64), ('config_size', 41),
                             ('config_identity', (DEVICE, 25)),
                             ('selection', replace(self.r.selection, selection_sha256='e' * 64))):
            with self.subTest(field=field):
                self.r = receipt(); bound = self.bound()
                object.__setattr__(self.r, field, value)
                with self.assertRaisesRegex(p.StateProjectionRejected, 'receipt_or_volume_changed'):
                    mapping.validate(bound, self.b, self.principal)

    def test_original_volume_mutation_cannot_hide_behind_object_identity(self):
        bound = self.bound(); object.__setattr__(self.b, 'fence_sha256', 'e' * 64)
        with self.assertRaisesRegex(p.StateProjectionRejected, 'receipt_or_volume_changed'):
            mapping.validate(bound, self.b, self.principal)

    def test_config_cannot_alias_store_or_other_device(self):
        for identity in ((DEVICE, 21), (DEVICE + 1, 24)):
            with self.assertRaises(profile.ServiceProfileRejected):
                mapping.ServiceProjection(self.b, replace(self.r, config_identity=identity), self.principal)

    def test_current_and_original_principal_are_both_pinned(self):
        bound = self.bound()
        with self.assertRaisesRegex(p.StateProjectionRejected, 'principal_changed'):
            mapping.validate(bound, self.b, dict(self.principal, hostUserNamespace='user:[2]'))
        self.principal['brokerUid'] = 999
        with self.assertRaisesRegex(p.StateProjectionRejected, 'principal_changed'):
            mapping.validate(bound, self.b, self.principal)

    def test_invalid_view_stops_before_profile_access(self):
        bound = self.bound()
        for view in ('source', 'TARGET', '/run/alaz-state/profile', True, None):
            with patch.object(profile, 'inspect_profile') as read, \
                    self.assertRaisesRegex(p.StateProjectionRejected, 'projection_view'):
                mapping.inspect_view(bound, self.b, self.principal, view=view)
            read.assert_not_called()

    def test_changed_config_identity_or_size_after_read_is_refused(self):
        bound = self.bound()
        for index, value in ((1, 999), (6, 41)):
            observed = snapshot(); info = list(observed['config.yaml']); info[index] = value
            observed['config.yaml'] = tuple(info)
            with patch.object(profile, 'inspect_profile', return_value=observed), \
                    self.assertRaisesRegex(p.StateProjectionRejected, 'snapshot_identity'):
                mapping.inspect_view(bound, self.b, self.principal, view='target')

    def test_binding_mutation_during_read_is_refused(self):
        bound = self.bound()
        def mutate(*args, **kwargs):
            self.principal['socketGroupGid'] += 1
            return snapshot()
        with patch.object(profile, 'inspect_profile', side_effect=mutate), \
                self.assertRaisesRegex(p.StateProjectionRejected, 'principal_changed'):
            mapping.inspect_view(bound, self.b, self.principal, view='host')

    def test_profile_config_refusal_propagates(self):
        bound = self.bound()
        with patch.object(profile, 'inspect_profile',
                side_effect=profile.ServiceProfileRejected('service_config_changed')), \
                self.assertRaisesRegex(profile.ServiceProfileRejected, 'service_config_changed'):
            mapping.inspect_view(bound, self.b, self.principal, view='target')


class ProjectionSequence(unittest.TestCase):
    def setUp(self):
        self.r = receipt()
        old.Sequence.setUp(self); posix_device(self)
        self.observed = snapshot(); self.meta.return_value = self.observed['profile']
        def volume(*args, **kwargs):
            self.events.append('volume'); return self.observed
        self.volume.side_effect = volume; self.target_reads = 0
        def target(bound, b, principal, *, view):
            self.assertEqual(view, 'target'); self.target_reads += 1
            self.events.append('target' + str(self.target_reads))
            mapping.validate(bound, b, principal)
            return self.observed, replace(bound.receipt, home=p.TARGET)
        self.target = self.stack.enter_context(patch.object(mapping, 'inspect_view', side_effect=target))

    def enter(self, **kwargs):
        return p.enter(old.V, old.FS, self.b, profile_layout=p.NATIVE_SERVICE_LAYOUT,
                       service_profile=self.r, **kwargs)

    def test_handoff_follows_target_check_identity_drop_filter_and_landlock(self):
        original = asdict(self.r); result = self.enter(observe_self_mount=True, observe_self_identity=True)
        self.assertEqual(self.events, ['inspect', 'volume', 'abi', 'loadfilter', 'closefds',
            'unshare', 'loopback', 'project', 'target1', 'umask', 'drop', 'verifyids',
            'filter', 'closefds', 'landlock', 'target2'])
        self.assertEqual(result['serviceProfile'], replace(self.r, home=p.TARGET))
        self.assertEqual(asdict(self.r), original); self.assertTrue(result['serviceProjectionVerified'])
        self.assertEqual(self.guard.call_args.kwargs,
            dict(self_mount_metadata=True, self_identity_metadata=True))
        self.assertIs(self.volume.call_args.kwargs['service_projection'].receipt, self.r)
        for key in ('profileOwnershipAcquired', 'nativeHermesStoresOpened', 'fullD3BAccepted'):
            self.assertIs(result[key], False)
        self.assertNotIn('retainedProfile', result)

    def test_missing_wrong_or_dual_selector_stops_before_any_probe(self):
        cases = [dict(profile_layout=p.NATIVE_SERVICE_LAYOUT),
                 dict(profile_layout=p.MINIMAL_LAYOUT, service_profile=self.r),
                 dict(profile_layout=p.NATIVE_PREPARED_LAYOUT, service_profile=self.r),
                 dict(profile_layout=p.NATIVE_RETAINED_LAYOUT, service_profile=self.r),
                 dict(profile_layout=p.NATIVE_SERVICE_LAYOUT, service_profile=self.r, retained_profile=self.r)]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(p.StateProjectionRejected):
                p.enter(old.V, old.FS, self.b, **kwargs)
        self.inspector.assert_not_called(); self.volume.assert_not_called()

    def test_invalid_profile_data_stops_before_kernel_stages(self):
        for value in ({}, False, replace(self.r, config_size=True)):
            with self.assertRaises(profile.ServiceProfileRejected):
                p.enter(old.V, old.FS, self.b, profile_layout=p.NATIVE_SERVICE_LAYOUT, service_profile=value)
        self.inspector.assert_not_called(); self.drop.assert_not_called()

    def test_wrong_home_stops_before_volume_or_unshare(self):
        self.r = replace(self.r, home='/tmp/unrelated')
        with self.assertRaisesRegex(p.StateProjectionRejected, 'receipt_home'): self.enter()
        self.volume.assert_not_called(); self.mounts.unshare.assert_not_called()

    def test_config_changed_in_first_target_view_stops_before_drop(self):
        wrong = snapshot(); wrong['config.yaml'] = (DEVICE, 999, *wrong['config.yaml'][2:])
        self.target.side_effect = lambda *a, **kw: (wrong, replace(self.r, home=p.TARGET))
        with self.assertRaisesRegex(p.StateProjectionRejected, 'service_target_changed'): self.enter()
        self.drop.assert_not_called(); self.guard.assert_not_called()

    def test_post_guard_config_change_never_returns_service_handoff(self):
        wrong = snapshot(); changed = list(wrong['config.yaml']); changed[7] += 1
        wrong['config.yaml'] = tuple(changed)
        self.target.side_effect = [(self.observed, replace(self.r, home=p.TARGET)),
                                   (wrong, replace(self.r, home=p.TARGET))]
        with self.assertRaisesRegex(p.StateProjectionRejected, 'service_target_changed'): self.enter()
        self.guard.assert_called_once(); self.assertEqual(self.target.call_count, 2)

    def test_security_filter_failure_prevents_final_profile_read(self):
        self.filterstatus.return_value = {'Seccomp': '0'}
        with self.assertRaisesRegex(p.StateProjectionRejected, 'filter_missing'): self.enter()
        self.assertEqual(self.target.call_count, 1); self.guard.assert_not_called()

    def test_landlock_failure_prevents_final_profile_read(self):
        self.guard.side_effect = p.gp.fs_guard.GuardRejected('explicit-fixture-failure')
        with self.assertRaises(p.gp.fs_guard.GuardRejected): self.enter()
        self.assertEqual(self.target.call_count, 1)

    def test_default_path_preserves_call_shape_and_omits_service_claims(self):
        result = p.enter(old.V, old.FS, self.b)
        self.target.assert_not_called(); self.assertEqual(self.volume.call_args.kwargs, {})
        self.assertNotIn('serviceProfile', result); self.assertNotIn('serviceProjectionVerified', result)
        self.assertEqual(inspect.signature(p.enter).parameters['profile_layout'].default, p.MINIMAL_LAYOUT)
        self.assertIsNone(inspect.signature(p.enter).parameters['service_profile'].default)

    def test_self_identity_observation_still_requires_mount_observation(self):
        with self.assertRaisesRegex(p.StateProjectionRejected, 'identity_requires_retained_mount'):
            self.enter(observe_self_identity=True)
        self.inspector.assert_not_called(); self.volume.assert_not_called()


class PivotBarrier(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close); posix_device(self)
        self.b = old.binding(); self.principal = dict(old.P)
        self.mapping = mapping.ServiceProjection(self.b, receipt(), self.principal)
        self.stack.enter_context(patch.object(p.gp.Mounts, '__init__', return_value=None))
        self.mounts = p._ProfileMounts(self.b, self.principal, snapshot(),
            p.NATIVE_SERVICE_LAYOUT, service_projection=self.mapping)
        self.inspector = self.stack.enter_context(patch.object(p, 'inspect_volume', return_value=snapshot()))
        self.mkdir = self.stack.enter_context(patch.object(Path, 'mkdir'))
        self.stack.enter_context(patch.object(Path, 'lstat', return_value=object()))
        self.meta = self.stack.enter_context(patch.object(p, '_metadata', return_value=snapshot()['profile']))
        self.stack.enter_context(patch.object(p.os, 'statvfs',
            return_value=SimpleNamespace(f_flag=p.SAFE_FLAGS), create=True))
        self.mounts.mount = Mock()
        self.pivot = self.stack.enter_context(patch.object(p.gp.Mounts, 'pivot'))

    def test_prebind_rechecks_original_full_volume_and_service_mapping(self):
        self.mounts.pivot(Path('/temporary-root'))
        self.assertEqual(self.inspector.call_args.kwargs, dict(joined_namespace=False,
            profile_layout=p.NATIVE_SERVICE_LAYOUT, service_projection=self.mapping))
        self.assertEqual(self.mounts.mount.call_count, 2); self.pivot.assert_called_once()
        self.assertTrue(self.mounts.projected)

    def test_config_snapshot_change_stops_before_any_mount(self):
        changed = snapshot(); info = list(changed['config.yaml']); info[8] += 1
        changed['config.yaml'] = tuple(info); self.inspector.return_value = changed
        with self.assertRaisesRegex(p.StateProjectionRejected, 'profile_changed'):
            self.mounts.pivot(Path('/temporary-root'))
        self.mkdir.assert_not_called(); self.mounts.mount.assert_not_called(); self.pivot.assert_not_called()

    def test_bound_identity_change_prevents_root_switch(self):
        self.meta.return_value = (999,) * 9
        with self.assertRaisesRegex(p.StateProjectionRejected, 'bound_identity'):
            self.mounts.pivot(Path('/temporary-root'))
        self.pivot.assert_not_called(); self.assertFalse(self.mounts.projected)

    def test_repeat_pivot_is_refused(self):
        self.mounts.projected = True
        with self.assertRaisesRegex(p.StateProjectionRejected, 'once'):
            self.mounts.pivot(Path('/temporary-root'))
        self.inspector.assert_not_called(); self.mounts.mount.assert_not_called()


if __name__ == '__main__':
    unittest.main()
