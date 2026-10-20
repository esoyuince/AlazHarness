"""Offline trusted-launch contract/order tests; no UID transition is executed."""
from contextlib import ExitStack
import copy
import errno
import hashlib
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import principal_launch as launch


def fixture():
    p = {'version': 1, 'enabled': True, 'gatewayUid': 1000, 'brokerUid': 1101,
         'socketGroupGid': 1102, 'hostUserNamespace': 'user:[4026531837]'}
    value = {'version': 1, 'enabled': True, 'role': 'broker', 'principalContract': p,
             'python': '/usr/bin/python3.14', 'config': '/srv/alaz/private/broker.json',
             'configSha256': 'a' * 64, 'output': '/srv/alaz/socket', 'commandSha256': ''}
    value['commandSha256'] = launch.command_digest(launch.command(value))
    return value


def root_state():
    return {'pid': 314, 'uids': (0,) * 4, 'gids': (0,) * 4, 'groups': (0,),
            'threads': 1, 'nnp': 0, 'caps': {k: 0xffff for k in launch.CAPS},
            'userns': fixture()['principalContract']['hostUserNamespace'],
            'uidMap': ['0', '0', '4294967295'], 'gidMap': ['0', '0', '4294967295']}


def target_state():
    s = root_state()
    s.update(uids=(1101,) * 4, gids=(1102,) * 4, groups=(), nnp=1,
             caps={k: 0 for k in launch.CAPS})
    return s


class Contract(unittest.TestCase):
    def test_valid_contract_is_detached(self):
        v = fixture(); approved = launch.validate(v)
        v['principalContract']['brokerUid'] = 1200
        self.assertEqual(approved['principalContract']['brokerUid'], 1101)

    def test_only_explicit_broker_role(self):
        for role in ('gateway', 'shell', None):
            with self.subTest(role=role), self.assertRaises(launch.LaunchRejected):
                launch.validate(fixture() | {'role': role})

    def test_fields_are_closed(self):
        v = fixture()
        for value in (v | {'fallback': True}, {k: x for k, x in v.items() if k != 'enabled'}):
            with self.assertRaises(launch.LaunchRejected): launch.validate(value)

    def test_version_and_optin_strict(self):
        for fields in ({'version': True}, {'version': 2}, {'enabled': 1}, {'enabled': False}):
            with self.subTest(fields=fields), self.assertRaises(launch.LaunchRejected):
                launch.validate(fixture() | fields)

    def test_same_uid_rejected(self):
        v = fixture(); v['principalContract']['brokerUid'] = 1000
        with self.assertRaises(ValueError): launch.validate(v)

    def test_changed_command_refused(self):
        for field, value in (('python', '/usr/bin/other'), ('config', '/srv/new.json'),
                             ('output', '/srv/new')):
            with self.subTest(field=field), self.assertRaisesRegex(launch.LaunchRejected, 'command_mismatch'):
                launch.validate(fixture() | {field: value})

    def test_noncanonical_paths_refused(self):
        for path in ('relative', '//srv/alaz', '/srv/../other', '/srv/x\x00'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                launch.validate(fixture() | {'config': path})

    def test_config_not_inside_socket_directory(self):
        v = fixture(); v['config'] = v['output'] + '/secret.json'
        with self.assertRaisesRegex(launch.LaunchRejected, 'overlap'): launch.validate(v)

    def test_invalid_digest_and_long_socket_refused(self):
        for v in (fixture() | {'configSha256': 'A' * 64}, fixture() | {'output': '/' + 'a' * 100}):
            with self.assertRaises(launch.LaunchRejected): launch.validate(v)

    def test_command_is_fixed_isolated_python_broker(self):
        argv = launch.command(fixture())
        self.assertEqual(argv[1:3], ['-I', '-B'])
        self.assertTrue(argv[3].endswith('run_provider_broker.py'))
        self.assertEqual(argv[4::2], ['--config', '--output'])


class ControllerAdmission(unittest.TestCase):
    def test_root_with_initial_map_can_reach_preflight_only(self):
        with patch.object(launch, 'observation', return_value=root_state()):
            self.assertEqual(launch.controller(fixture())['pid'], 314)

    def test_nonroot_or_saved_root_mix_refused(self):
        for key in ('uids', 'gids'):
            for position in range(4):
                s = root_state(); v = list(s[key]); v[position] = 1000; s[key] = tuple(v)
                with self.subTest(key=key, position=position), patch.object(launch, 'observation', return_value=s):
                    with self.assertRaisesRegex(launch.LaunchRejected, 'host_root_required'):
                        launch.controller(fixture())

    def test_remapped_root_is_not_host_root(self):
        for field, value in (('userns', 'user:[99]'), ('uidMap', ['0', '1000', '1']),
                             ('gidMap', ['0', '1000', '1'])):
            with self.subTest(field=field), patch.object(launch, 'observation', return_value=root_state() | {field: value}):
                with self.assertRaisesRegex(launch.LaunchRejected, 'initial_user_namespace'):
                    launch.controller(fixture())

    def test_threads_or_missing_capabilities_refused(self):
        for s in (root_state() | {'threads': 2}, root_state() | {'caps': {'CapEff': 0}}):
            with patch.object(launch, 'observation', return_value=s), self.assertRaises(launch.LaunchRejected):
                launch.controller(fixture())

    def test_nonroot_cli_does_not_read_contract(self):
        with (patch.object(launch.sys, 'platform', 'linux'),
              patch.object(launch.os, 'getuid', create=True, return_value=1000),
              patch.object(launch.os, 'geteuid', create=True, return_value=1000),
              patch.object(launch, 'file_bytes') as read):
            with self.assertRaisesRegex(launch.LaunchRejected, 'host_root_required'):
                launch.load_contract('/private/not-to-read')
        read.assert_not_called()


class KernelTransition(unittest.TestCase):
    def run_drop(self, failure=None):
        events = []
        lib = Mock()
        def prctl(op, *args):
            events.append(('prctl', op, *args))
            if failure == ('prctl', op): return -1
            if op == 23 and args[0] >= 41:
                launch.ctypes.set_errno(errno.EINVAL); return -1
            return 1 if op == 23 else 0
        def record(name):
            def call(*args):
                events.append((name, *args))
                if failure == name: raise PermissionError('injected')
            return call
        lib.prctl.side_effect = prctl
        lib.capset.side_effect = lambda *a: events.append(('capset',)) or (-1 if failure == 'capset' else 0)
        with (patch.object(launch.ctypes, 'CDLL', return_value=lib),
              patch.object(launch.os, 'setgroups', create=True, side_effect=record('groups')),
              patch.object(launch.os, 'setresgid', create=True, side_effect=record('gid')),
              patch.object(launch.os, 'setresuid', create=True, side_effect=record('uid'))):
            try: launch.drop_identity(fixture()['principalContract'])
            except (OSError, launch.LaunchRejected):
                return events, False
        return events, True

    def test_no_new_privs_groups_bounding_gid_uid_capset_order(self):
        events, ok = self.run_drop(); self.assertTrue(ok)
        self.assertEqual(events[0], ('prctl', 38, 1, 0, 0, 0))
        groups = events.index(('groups', [])); gid = events.index(('gid', 1102, 1102, 1102))
        uid = events.index(('uid', 1101, 1101, 1101))
        drops = [i for i, e in enumerate(events) if e[:2] == ('prctl', 24)]
        self.assertEqual(len(drops), 41)
        self.assertLess(groups, min(drops)); self.assertLess(max(drops), gid)
        self.assertLess(gid, uid); self.assertGreater(events.index(('capset',)), uid)
        self.assertIn(('prctl', 8, 0, 0, 0, 0), events)
        self.assertIn(('prctl', 47, 4, 0, 0, 0), events)

    def test_failed_critical_steps_never_continue_transition(self):
        for failure in (('prctl', 38), ('prctl', 8), ('prctl', 47), 'groups',
                        ('prctl', 24), 'gid', 'uid', 'capset'):
            with self.subTest(failure=failure):
                events, ok = self.run_drop(failure); self.assertFalse(ok)
                self.assertNotIn(('prctl', 4, 0, 0, 0, 0), events)

    def test_post_drop_requires_all_saved_and_filesystem_ids(self):
        for field in ('uids', 'gids'):
            for index in range(4):
                s = target_state(); values = list(s[field]); values[index] = 0; s[field] = tuple(values)
                with (self.subTest(field=field, index=index), patch.object(launch.hp, 'broker_identity'),
                      patch.object(launch, 'observation', return_value=s), self.assertRaises(launch.LaunchRejected)):
                    launch.verify_target(fixture(), root_state())

    def test_post_drop_requires_every_capability_set_zero(self):
        for key in launch.CAPS:
            s = target_state(); s['caps'][key] = 1
            with (self.subTest(key=key), patch.object(launch.hp, 'broker_identity'),
                  patch.object(launch, 'observation', return_value=s), self.assertRaises(launch.LaunchRejected)):
                launch.verify_target(fixture(), root_state())

    def test_post_drop_requires_namespace_pid_nnp_groups_and_threads(self):
        for key, value in (('userns', 'user:[99]'), ('pid', 315), ('groups', (0,)),
                           ('nnp', 0), ('threads', 2), ('uidMap', ['0', '1000', '1'])):
            with (self.subTest(key=key), patch.object(launch.hp, 'broker_identity'),
                  patch.object(launch, 'observation', return_value=target_state() | {key: value}),
                  self.assertRaises(launch.LaunchRejected)):
                launch.verify_target(fixture(), root_state())

    def test_exact_post_drop_identity_passes_without_exec(self):
        with (patch.object(launch.hp, 'broker_identity') as identity,
              patch.object(launch, 'observation', return_value=target_state())):
            launch.verify_target(fixture(), root_state())
        identity.assert_called_once_with(fixture()['principalContract'])


class EndToEndOrdering(unittest.TestCase):
    def run_launch(self, fail=None, mutate=False):
        events = []; stack = ExitStack(); self.addCleanup(stack.close)
        original = fixture(); checked_uids = []
        def step(name, result=None):
            def call(*args):
                events.append(name)
                if name == 'drop_identity': checked_uids.append(args[0]['brokerUid'])
                if name == 'trusted_install' and mutate: original['principalContract']['brokerUid'] = 2200
                if name == fail: raise launch.LaunchRejected('injected_' + name)
                return result
            return call
        for name, result in (('controller', root_state()), ('trusted_install', None),
                             ('deployment', {'same': True}), ('close_ambient_fds', None),
                             ('drop_identity', None), ('verify_target', None)):
            stack.enter_context(patch.object(launch, name, side_effect=step(name, result)))
        stack.enter_context(patch.object(launch.net, '_load_seccomp', side_effect=step('loadseccomp', object())))
        stack.enter_context(patch.object(launch.net, '_filter', side_effect=step('filter')))
        stack.enter_context(patch.object(launch.os, 'chdir', side_effect=step('chdir')))
        stack.enter_context(patch.object(launch.os, 'umask', side_effect=step('umask')))
        exec_call = stack.enter_context(patch.object(launch.os, 'execve', side_effect=step('exec')))
        with self.assertRaises(launch.LaunchRejected): launch.launch(original)
        return events, exec_call, checked_uids

    def test_exec_occurs_only_after_postdrop_revalidation_and_filter(self):
        events, call, _ = self.run_launch()
        self.assertEqual(events, ['controller', 'trusted_install', 'deployment', 'loadseccomp',
            'close_ambient_fds', 'chdir', 'umask', 'drop_identity', 'verify_target', 'deployment', 'filter', 'exec'])
        argv0, argv, env = call.call_args.args
        self.assertEqual(argv0, fixture()['python']); self.assertEqual(argv, launch.command(fixture()))
        self.assertEqual(set(env), {'PATH', 'LANG', 'HOME', 'PYTHONNOUSERSITE', 'PYTHONDONTWRITEBYTECODE'})

    def test_every_admission_or_enforcement_failure_blocks_exec(self):
        for step in ('controller', 'trusted_install', 'deployment', 'loadseccomp',
                     'close_ambient_fds', 'drop_identity', 'verify_target', 'filter'):
            with self.subTest(step=step):
                events, call, _ = self.run_launch(step)
                call.assert_not_called(); self.assertEqual(events[-1], step)

    def test_caller_mutation_does_not_change_selected_uid(self):
        _, _, checked = self.run_launch(mutate=True); self.assertEqual(checked, [1101])

    def test_gateway_never_reaches_controller(self):
        with patch.object(launch, 'controller') as controller:
            with self.assertRaises(launch.LaunchRejected): launch.launch(fixture() | {'role': 'gateway'})
        controller.assert_not_called()


class FileCustody(unittest.TestCase):
    def info(self, **change):
        d = dict(st_dev=1, st_ino=2, st_uid=0, st_gid=0, st_mode=stat.S_IFREG | 0o600,
                 st_nlink=1, st_size=2, st_mtime_ns=5, st_ctime_ns=6)
        return SimpleNamespace(**(d | change))

    def read(self, info=None, after=None, path_info=None):
        s = info or self.info(); data = b'{}'; p = Mock(); p.lstat.return_value = path_info or s
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(launch, 'trusted_ancestors', return_value=p))
        for n in ('O_CLOEXEC', 'O_NOFOLLOW', 'O_NONBLOCK'):
            if not hasattr(launch.os, n): stack.enter_context(patch.object(launch.os, n, {'O_CLOEXEC': 0x80000, 'O_NOFOLLOW': 0x20000, 'O_NONBLOCK': 0x800}[n], create=True))
        opened = stack.enter_context(patch.object(launch.os, 'open', return_value=99))
        stack.enter_context(patch.object(launch.os, 'fstat', side_effect=[s, after or s]))
        read = stack.enter_context(patch.object(launch.os, 'read', side_effect=[data, b'']))
        close = stack.enter_context(patch.object(launch.os, 'close'))
        return lambda: launch.file_bytes('/owned/contract', 0, 0o600, 32768), read, close, opened

    def test_read_pins_fd_and_path_and_closes(self):
        run, _, close, opened = self.read(); self.assertEqual(run(), b'{}'); close.assert_called_once_with(99)
        flags = opened.call_args.args[1]
        required = launch.os.O_CLOEXEC | launch.os.O_NOFOLLOW | launch.os.O_NONBLOCK
        self.assertEqual(flags & required, required)

    def test_file_type_owner_mode_link_count_and_size_are_required_before_read(self):
        for fields in ({'st_uid': 1000}, {'st_mode': stat.S_IFIFO | 0o600},
                       {'st_mode': stat.S_IFREG | 0o644}, {'st_nlink': 2},
                       {'st_size': 32769}, {'st_size': 0}):
            with self.subTest(fields=fields):
                run, read, close, _ = self.read(self.info(**fields))
                with self.assertRaises(launch.LaunchRejected): run()
                read.assert_not_called(); close.assert_called_once_with(99)

    def test_changed_fd_or_rebound_path_rejected(self):
        for args in ({'after': self.info(st_mtime_ns=9)}, {'path_info': self.info(st_ino=9)}):
            with self.subTest(args=args):
                run, _, close, _ = self.read(**args)
                with self.assertRaisesRegex(launch.LaunchRejected, 'changed'): run()
                close.assert_called_once_with(99)



class Deployment(unittest.TestCase):
    def setUp(self):
        import json
        self.value = fixture()
        self.cfg = {'principal_contract': copy.deepcopy(self.value['principalContract'])}
        self.raw = json.dumps(self.cfg).encode()
        self.value['configSha256'] = hashlib.sha256(self.raw).hexdigest()
        self.authority = {'enabled': True, 'directory': '/srv/alaz/private-budget'}
        self.out = Path('/srv/alaz/socket')
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.entries = self.stack.enter_context(patch.object(launch.Path, 'iterdir', return_value=iter(())))
        self.stack.enter_context(patch.object(launch, 'file_bytes', return_value=self.raw))
        self.stack.enter_context(patch.object(launch, 'trusted_ancestors', return_value=self.out))
        self.budget = self.stack.enter_context(patch.object(launch.hp, 'budget_identity', return_value={'private': True}))
        self.directory = self.stack.enter_context(patch.object(launch.hp, 'regular', return_value=(1, 2, 1101, 1102, 0o710)))
        self.config = self.stack.enter_context(patch('provider_egress.BrokerConfig', return_value=SimpleNamespace(budget_authority=self.authority)))

    def test_prepared_deployment_uses_existing_exact_owner_checks(self):
        result = launch.deployment(self.value)
        self.assertEqual(result['configSha256'], self.value['configSha256'])
        self.directory.assert_called_once_with(str(self.out), 'dir', 1101, 1102, 0o710)
        self.budget.assert_called_once_with(self.value['principalContract'], '/srv/alaz/private-budget')

    def test_changed_config_bytes_are_not_parsed_or_adopted(self):
        with self.assertRaisesRegex(launch.LaunchRejected, 'config_changed'):
            launch.deployment(self.value | {'configSha256': '0' * 64})
        self.config.assert_not_called()

    def test_different_principal_refused(self):
        self.value['principalContract']['brokerUid'] = 2200
        with self.assertRaisesRegex(launch.LaunchRejected, 'principal_mismatch'):
            launch.deployment(self.value)
        self.config.assert_not_called()

    def test_independent_private_budget_is_required(self):
        self.config.return_value = SimpleNamespace(budget_authority=None)
        with self.assertRaisesRegex(launch.LaunchRejected, 'private_budget_required'):
            launch.deployment(self.value)
        self.directory.assert_not_called()

    def test_old_socket_or_receipt_directory_never_adopted(self):
        self.entries.return_value = iter([Path('/srv/alaz/socket/ready.json')])
        with self.assertRaisesRegex(launch.LaunchRejected, 'not_empty'):
            launch.deployment(self.value)

    def test_budget_cannot_live_under_exported_socket_directory(self):
        self.authority['directory'] = '/srv/alaz/socket/private-budget'
        with self.assertRaisesRegex(launch.LaunchRejected, 'budget_socket_overlap'):
            launch.deployment(self.value)

    def test_wrong_budget_or_socket_owner_is_fatal(self):
        for checker in (self.budget, self.directory):
            checker.side_effect = launch.hp.PrincipalRejected('invalid_owner')
            with self.assertRaises(launch.hp.PrincipalRejected): launch.deployment(self.value)
            checker.side_effect = None


class AdditionalOrdering(unittest.TestCase):
    def test_second_deployment_change_blocks_exec(self):
        with ExitStack() as stack:
            for name, value in (('controller', root_state()), ('trusted_install', None),
                                ('close_ambient_fds', None), ('drop_identity', None), ('verify_target', None)):
                stack.enter_context(patch.object(launch, name, return_value=value))
            stack.enter_context(patch.object(launch.net, '_load_seccomp'))
            filtered = stack.enter_context(patch.object(launch.net, '_filter'))
            stack.enter_context(patch.object(launch.os, 'chdir'))
            stack.enter_context(patch.object(launch.os, 'umask'))
            stack.enter_context(patch.object(launch, 'deployment', side_effect=[{'inode': 1}, {'inode': 2}]))
            executed = stack.enter_context(patch.object(launch.os, 'execve'))
            with self.assertRaisesRegex(launch.LaunchRejected, 'deployment_changed'): launch.launch(fixture())
            filtered.assert_not_called(); executed.assert_not_called()

    def test_non_linux_observation_fails_without_proc_access(self):
        with patch.object(launch.sys, 'platform', 'win32'), patch.object(launch.Path, 'read_text') as read:
            with self.assertRaisesRegex(launch.LaunchRejected, 'linux_x86_64'): launch.observation()
        read.assert_not_called()

    def test_untrusted_ancestor_rejected(self):
        for change in ({'st_mode': stat.S_IFDIR | 0o777, 'st_uid': 0},
                       {'st_mode': stat.S_IFDIR | 0o755, 'st_uid': 1000},
                       {'st_mode': stat.S_IFLNK | 0o777, 'st_uid': 0}):
            with self.subTest(change=change), patch.object(launch.Path, 'lstat', return_value=SimpleNamespace(**change)):
                with self.assertRaisesRegex(launch.LaunchRejected, 'untrusted_parent'):
                    launch.trusted_ancestors('/srv/alaz/contract.json', {0})

    def test_root_owned_nonwritable_ancestors_accepted(self):
        s = SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0)
        with patch.object(launch.Path, 'lstat', return_value=s):
            self.assertEqual(launch.trusted_ancestors('/srv/alaz/contract.json', {0}), Path('/srv/alaz/contract.json'))

if __name__ == '__main__': unittest.main(verbosity=2)
