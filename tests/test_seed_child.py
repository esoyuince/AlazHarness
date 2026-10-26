"""Owned boundary doubles only: no WSL, setns, UID change, mount or native import."""
from __future__ import annotations

from copy import deepcopy
import ctypes
import errno
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "qa" / "r155a1_seed_child.py"
SPEC = importlib.util.spec_from_file_location("_r155_seed_child_owned_test", SOURCE)
child = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = child
SPEC.loader.exec_module(child)


def contract():
    """Synthetic values exclusively for source-only tests, never an acceptance receipt."""
    return {
        "protocol": child.PROTOCOL,
        "controller": {"pid": 101, "startTicks": 10001},
        "worker": {"pid": 102, "startTicks": 10002},
        "scope": {"path": child.CGROUP_PARENT + "/volume-" + "a" * 32, "device": 25, "inode": 300},
        "namespace": {"fd": 7, "inode": 400},
        "image": {"path": child.IMAGE, "device": 2096, "inode": 500, "size": 64 << 20,
                  "uid": 0, "gid": 0, "parent_device": 2096, "parent_inode": 499},
        "token": "a" * 32,
        "fence": {"path": child.FENCE, "sha256": "b" * 64},
        "mountpoint": child.TARGET,
        "profile": child.PROFILE,
        "loopNumber": 8,
        "principal": {"version": 1, "enabled": True, "gatewayUid": 23001, "brokerUid": 23002,
                      "socketGroupGid": 23003, "hostUserNamespace": "user:[4026531837]"},
        "installation": {"path": child.INSTALLATION, "receiptSha256": child.RECEIPT_SHA},
        "bootstrap": {"path": child.BOOTSTRAP, "sha256": "c" * 64},
        "seedInstanceId": "seed-r155a1-unit",
    }


class Replaced(BaseException):
    pass


class OwnedBoundary:
    ORDER = ("preflight", "enroll", "join_namespace", "create_profile", "before_drop",
             "drop_identity", "verify_target", "exec_producer")

    def __init__(self, fail=None, created=None):
        self.events = []
        self.fail = fail
        self.created = created if created is not None else child.CreatedProfile(1800, 1234)
        self.argv = None

    def __getattr__(self, name):
        if name not in self.ORDER:
            raise AssertionError("unexpected boundary operation: " + name)

        def operation(value, *args):
            self.events.append(name)
            if name == self.fail:
                raise child.SeedRejected("owned_failure")
            if name == "create_profile":
                return self.created
            if name == "exec_producer":
                self.argv = child.producer_command(value, args[0])
                raise Replaced()

        return operation


class ProtocolTests(unittest.TestCase):
    def test_roundtrip_and_detached_copy(self):
        value = contract()
        result = child.decode_contract(child.encode_contract(value))
        self.assertEqual(value, result)
        result["controller"]["pid"] = 999
        self.assertEqual(value["controller"]["pid"], 101)

    def test_all_top_level_fields_required(self):
        for field in child.FIELDS:
            with self.subTest(field=field):
                value = contract()
                del value[field]
                with self.assertRaises(child.SeedRejected):
                    child.validate_contract(value)

    def test_no_command_environment_or_profile_inode_input(self):
        for key in ("command", "env", "profile_inode", "cleanup", "retry"):
            with self.subTest(key=key):
                value = contract()
                value[key] = "untrusted"
                with self.assertRaises(child.SeedRejected):
                    child.validate_contract(value)

    def test_fixed_paths_and_pins(self):
        mutations = (
            ("mountpoint", None, "/tmp/mount"),
            ("profile", None, child.TARGET + "/profile/.."),
            ("image", "path", "/tmp/image"),
            ("fence", "path", "/tmp/fence"),
            ("scope", "path", child.CGROUP_PARENT + "/volume-" + "d" * 32),
            ("bootstrap", "path", "/bin/sh"),
            ("installation", "receiptSha256", "d" * 64),
        )
        for outer, inner, value in mutations:
            with self.subTest(outer=outer, inner=inner):
                candidate = contract()
                if inner is None:
                    candidate[outer] = value
                else:
                    candidate[outer][inner] = value
                with self.assertRaises(child.SeedRejected):
                    child.validate_contract(candidate)

    def test_integer_booleans_bounds_and_principal_alias_rejected(self):
        mutations = (
            ("controller", "pid", True), ("worker", "startTicks", 0),
            ("namespace", "fd", 2), ("scope", "inode", 0),
            ("image", "size", 4097), ("image", "uid", 1),
            ("principal", "gatewayUid", 0), ("principal", "brokerUid", 23001),
            ("principal", "socketGroupGid", 1 << 31),
            ("principal", "version", True), ("principal", "enabled", 1),
        )
        for outer, inner, value in mutations:
            with self.subTest(outer=outer, inner=inner):
                candidate = contract()
                candidate[outer][inner] = value
                with self.assertRaises(child.SeedRejected):
                    child.validate_contract(candidate)

    def test_digest_and_instance_are_bounded(self):
        for bad in ("A" * 64, "a" * 63, "../x", ""):
            candidate = contract()
            candidate["bootstrap"]["sha256"] = bad
            with self.assertRaises(child.SeedRejected):
                child.validate_contract(candidate)
        for bad in ("a" * 129, "x y", "x\n", "/tmp/x"):
            candidate = contract()
            candidate["seedInstanceId"] = bad
            with self.assertRaises(child.SeedRejected):
                child.validate_contract(candidate)

    def test_duplicate_keys_noncanonical_and_multiple_frames_rejected(self):
        good = child.encode_contract(contract())
        duplicate = b'{"protocol":"wrong",' + good[1:]
        cases = (duplicate, good + good, good[:-1], good + b" ", b"\xff\n",
                 json.dumps(contract(), indent=2).encode() + b"\n",
                 b" " + good, b'{"x":NaN}\n', b'{"x":1.5}\n',
                 b"x" * (child.MAX_INPUT + 1))
        for data in cases:
            with self.subTest(data=data[:30]):
                with self.assertRaises(child.SeedRejected):
                    child.decode_contract(data)

    def test_fixed_exec_has_actual_created_identity_and_no_environment_passthrough(self):
        argv = child.producer_command(contract(), child.CreatedProfile(1800, 1234))
        self.assertEqual(argv[:6], [child.PYTHON, "-I", "-B", child.BOOTSTRAP, "--home", child.PROFILE])
        self.assertEqual(argv[argv.index("--expected-profile-device") + 1], "1800")
        self.assertEqual(argv[argv.index("--expected-profile-inode") + 1], "1234")
        self.assertEqual(argv[argv.index("--parent-pid") + 1], "101")
        self.assertEqual(child.ENV, {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC"})
        self.assertNotIn("HOME", child.ENV)
        with self.assertRaises(child.SeedRejected):
            child.producer_command(contract(), {"device": 1800, "inode": 1234})

    def test_inherited_home_is_refused_before_any_other_boundary(self):
        fake_sys = SimpleNamespace(platform="linux", byteorder="little", executable=child.PYTHON,
                                   version_info=(3, 12, 3), argv=[child.CHILD],
                                   flags=SimpleNamespace(isolated=1, ignore_environment=1,
                                                         no_user_site=1, dont_write_bytecode=1, optimize=0))
        fake_os = SimpleNamespace(uname=lambda: SimpleNamespace(machine="x86_64"),
                                  environ={**child.ENV, "HOME": "/unexpected"})
        with patch.object(child, "sys", fake_sys), patch.object(child, "os", fake_os), \
                patch.object(child, "check_fds") as fd_check:
            with self.assertRaisesRegex(child.SeedRejected, "fixed_environment"):
                child.Boundary().preflight(contract())
            fd_check.assert_not_called()


class StateMachineTests(unittest.TestCase):
    def test_complete_order_and_only_created_identity_reaches_exec(self):
        owned = OwnedBoundary()
        progress = child.Progress()
        with self.assertRaises(Replaced):
            child.run_contract(contract(), owned, progress)
        self.assertEqual(owned.events, list(OwnedBoundary.ORDER))
        self.assertEqual(progress.phase, "producer_exec")
        self.assertTrue(progress.effect_attempted)
        self.assertIn("1234", owned.argv)

    def test_every_effect_phase_failure_is_unknown_and_never_retried(self):
        phases = (
            ("preflight", "preflight", False),
            ("enroll", "scope_enrollment", True),
            ("join_namespace", "namespace_join", True),
            ("create_profile", "fresh_profile_creation", True),
            ("before_drop", "pre_drop_revalidation", True),
            ("drop_identity", "identity_reduction", True),
            ("verify_target", "reduced_actor_verification", True),
            ("exec_producer", "producer_exec", True),
        )
        for failing, phase, effect in phases:
            with self.subTest(failing=failing):
                owned = OwnedBoundary(fail=failing)
                progress = child.Progress()
                with self.assertRaises(child.SeedRejected) as caught:
                    child.run_contract(contract(), owned, progress)
                self.assertEqual(progress.phase, phase)
                self.assertEqual(progress.effect_attempted, effect)
                self.assertEqual(owned.events, list(OwnedBoundary.ORDER[:OwnedBoundary.ORDER.index(failing) + 1]))
                record = json.loads(child.failure_frame(progress, caught.exception, 103))
                self.assertEqual(record["state"], "UNKNOWN" if effect else "REFUSED_PRE_EFFECT")
                self.assertFalse(record["cleanupAttempted"])
                self.assertFalse(record["retryPermitted"])
                self.assertLessEqual(len(child.failure_frame(progress, caught.exception, 103)), child.MAX_OUTPUT)

    def test_invalid_input_never_reaches_boundary(self):
        owned = OwnedBoundary()
        value = contract()
        value["controller"]["startTicks"] = False
        progress = child.Progress()
        with self.assertRaises(child.SeedRejected):
            child.run_contract(value, owned, progress)
        self.assertEqual(owned.events, [])
        self.assertFalse(progress.effect_attempted)

    def test_missing_real_created_identity_prevents_drop(self):
        owned = OwnedBoundary(created={"device": 1800, "inode": 1234})
        progress = child.Progress()
        with self.assertRaisesRegex(child.SeedRejected, "created_profile_required"):
            child.run_contract(contract(), owned, progress)
        self.assertEqual(owned.events[-1], "create_profile")
        self.assertTrue(progress.effect_attempted)

    def test_diagnostic_does_not_disclose_exception_text(self):
        frame = child.failure_frame(child.Progress("producer_exec", True),
                                    OSError("secret data or arbitrary pathname"), 103)
        self.assertNotIn(b"secret", frame)
        self.assertEqual(json.loads(frame)["reason"], "OSError")
        self.assertEqual(json.loads(child.failure_frame(child.Progress(),
                                                       child.SeedRejected("bad\nframe"), 103))["reason"],
                         "unclassified_failure")


class DescriptorTests(unittest.TestCase):
    def test_extra_live_fd_is_refused_without_closing_any_fd(self):
        fake = SimpleNamespace(listdir=lambda _: ["0", "1", "2", "7", "8"],
                               fstat=lambda _: object())
        with patch.object(child, "os", fake), patch.object(child, "check_stdio"):
            with self.assertRaisesRegex(child.SeedRejected, "unexpected_inherited_descriptor"):
                child.check_fds({0, 1, 2, 7})

    def test_only_closed_enumeration_fd_is_ignored(self):
        def fstat(fd):
            if fd == 9:
                raise OSError(errno.EBADF, "owned transient descriptor")
            return object()

        fake = SimpleNamespace(listdir=lambda _: ["0", "1", "2", "7", "9"], fstat=fstat)
        with patch.object(child, "os", fake), patch.object(child, "check_stdio"):
            child.check_fds({0, 1, 2, 7})
            with self.assertRaises(child.SeedRejected):
                child.check_fds({0, 1, 2, 7, 9})

    def test_namespace_descriptor_closed_once_on_success_and_failure(self):
        for result in (0, -1):
            with self.subTest(result=result):
                called = []
                syscall = Mock(return_value=result)
                fake_lib = SimpleNamespace(setns=syscall)
                fake_ctypes = SimpleNamespace(CDLL=lambda *a, **kw: fake_lib, c_int=ctypes.c_int)
                fake_os = SimpleNamespace(close=lambda fd: called.append(fd))
                boundary = child.Boundary()
                boundary.authority = Mock()
                with patch.object(child, "ctypes", fake_ctypes), patch.object(child, "os", fake_os), \
                        patch.object(child, "check_fds") as checked:
                    if result:
                        with self.assertRaisesRegex(child.SeedRejected, "setns_failed"):
                            boundary.join_namespace(contract())
                        checked.assert_not_called()
                    else:
                        boundary.join_namespace(contract())
                        checked.assert_called_once_with({0, 1, 2})
                self.assertEqual(called, [7])
                self.assertTrue(boundary.ns_closed)
                syscall.assert_called_once_with(7, child.CLONE_NEWNS)


def info(device=1800, inode=1234, uid=0, gid=0, mode=stat.S_IFDIR | 0o700, size=0):
    return SimpleNamespace(st_dev=device, st_ino=inode, st_uid=uid, st_gid=gid, st_mode=mode,
                           st_nlink=1, st_size=size, st_mtime_ns=100, st_ctime_ns=100)


class ProfileOS:
    O_RDONLY = 0
    O_CLOEXEC = 1
    O_DIRECTORY = 2
    O_NOFOLLOW = 4

    def __init__(self, fail=None):
        self.events = []
        self.fail = fail
        self.target = info(inode=2, mode=stat.S_IFDIR | 0o755)
        self.profile = info()
        self.next_fd = 10

    def getpid(self):
        return 103

    def open(self, path, flags, **kwargs):
        self.events.append(("open", str(path), kwargs))
        result = self.next_fd
        self.next_fd += 1
        return result

    def fstat(self, fd):
        return self.target if fd == 10 else self.profile

    def mkdir(self, name, **kwargs):
        self.events.append(("mkdir", name, kwargs))
        if self.fail in ("existing_file", "existing_symlink", "existing_directory"):
            raise FileExistsError(self.fail)

    def listdir(self, _fd):
        return []

    def fchmod(self, fd, mode):
        self.events.append(("fchmod", fd, mode))
        self.profile.st_mode = stat.S_IFDIR | mode

    def fchown(self, fd, uid, gid):
        self.events.append(("fchown", fd, uid, gid))
        if self.fail == "chown":
            raise PermissionError("owned chown failure")
        self.profile.st_uid, self.profile.st_gid = uid, gid

    def fsync(self, fd):
        self.events.append(("fsync", fd))

    def close(self, fd):
        self.events.append(("close", fd))


class ProfileCreationTests(unittest.TestCase):
    def boundary(self):
        boundary = child.Boundary()
        boundary.authority = Mock()
        boundary.scope = Mock()
        boundary.mounted = Mock()
        boundary.verify_profile = Mock()
        boundary.mount_identity = (1800, 2)
        return boundary

    def test_exclusive_creation_then_mode_owner_and_actual_inode(self):
        fake = ProfileOS()
        boundary = self.boundary()
        with patch.object(child, "os", fake):
            created = boundary.create_profile(contract())
        self.assertEqual(created, child.CreatedProfile(1800, 1234))
        self.assertEqual([e[0] for e in fake.events],
                         ["open", "mkdir", "open", "fchmod", "fchown", "fsync", "fsync", "close", "close"])
        self.assertEqual(fake.events[1], ("mkdir", "profile", {"mode": 0o700, "dir_fd": 10}))
        self.assertEqual(fake.events[4], ("fchown", 11, 23001, 23003))
        boundary.verify_profile.assert_called_once_with(contract(), created)

    def test_existing_file_symlink_or_directory_never_adopted_or_overwritten(self):
        for kind in ("existing_file", "existing_symlink", "existing_directory"):
            with self.subTest(kind=kind):
                fake = ProfileOS(kind)
                boundary = self.boundary()
                with patch.object(child, "os", fake):
                    with self.assertRaises(FileExistsError):
                        boundary.create_profile(contract())
                self.assertEqual([e[0] for e in fake.events], ["open", "mkdir", "close"])
                boundary.verify_profile.assert_not_called()

    def test_failure_after_creation_preserves_profile_and_only_closes_owned_fds(self):
        fake = ProfileOS("chown")
        boundary = self.boundary()
        with patch.object(child, "os", fake):
            with self.assertRaises(PermissionError):
                boundary.create_profile(contract())
        self.assertEqual([e for e in fake.events if e[0] == "close"], [("close", 11), ("close", 10)])
        self.assertEqual([e[0] for e in fake.events].count("mkdir"), 1)
        self.assertNotIn("fsync", [e[0] for e in fake.events])


class SourceAndProcessTests(unittest.TestCase):
    def test_trusted_bytes_digest_change_and_metadata_change_refused(self):
        raw = b"abc"
        expected = hashlib.sha256(raw).hexdigest()
        for mode in ("correct", "digest", "metadata", "fifo"):
            with self.subTest(mode=mode):
                file_info = info(mode=(stat.S_IFIFO if mode == "fifo" else stat.S_IFREG) | 0o444, size=3)
                later_info = deepcopy(file_info)
                if mode == "metadata":
                    later_info.st_ino += 1
                reads = iter((raw, b""))
                closed = []
                fake = SimpleNamespace(O_RDONLY=0, O_CLOEXEC=1, O_NOFOLLOW=2, O_NONBLOCK=4,
                                       open=lambda *a: 11, fstat=lambda _: file_info,
                                       lstat=lambda _: later_info, read=lambda *a: next(reads),
                                       close=lambda fd: closed.append(fd))
                digest = "0" * 64 if mode == "digest" else expected
                with patch.object(child, "os", fake), patch.object(child, "_trusted_path"):
                    if mode == "correct":
                        self.assertEqual(child.trusted_bytes("/owned/fixture", 10, digest), raw)
                    else:
                        with self.assertRaises(child.SeedRejected):
                            child.trusted_bytes("/owned/fixture", 10, digest)
                self.assertEqual(closed, [11])

    def test_kernel_start_ticks_parser_handles_parentheses_and_rejects_zombie(self):
        status = (
            "Uid:\t0 0 0 0\nGid:\t0 0 0 0\nGroups:\t\nThreads:\t1\nNoNewPrivs:\t0\n"
            + "".join(key + ":\t00000000\n" for key in child.CAPS)
        ).encode()
        for state in ("S", "Z"):
            suffix = [state, "101"] + ["0"] * 17 + ["10002"] + ["0"] * 5
            raw_stat = ("102 (worker ) embedded) " + " ".join(suffix) + "\n").encode()
            with patch.object(child, "_read_bounded",
                              side_effect=lambda path, limit: status if path.endswith("/status") else raw_stat):
                if state == "Z":
                    with self.assertRaisesRegex(child.SeedRejected, "process_not_live"):
                        child.process_anchor(102)
                else:
                    observed = child.process_anchor(102)
                    self.assertEqual((observed["pid"], observed["parent"], observed["startTicks"]),
                                     (102, 101, 10002))

    def test_input_requires_eof_and_bounded_wait(self):
        raw = child.encode_contract(contract())
        chunks = iter((raw[:30], raw[30:], b""))
        fake_os = SimpleNamespace(read=lambda *a: next(chunks))
        fake_select = SimpleNamespace(select=lambda *a: ([0], [], []))
        fake_time = SimpleNamespace(monotonic=lambda: 0)
        with patch.object(child, "os", fake_os), patch.object(child, "select", fake_select), \
                patch.object(child, "time", fake_time):
            self.assertEqual(child.read_contract(), contract())
        with patch.object(child, "select", SimpleNamespace(select=lambda *a: ([], [], []))), \
                patch.object(child, "time", fake_time):
            with self.assertRaisesRegex(child.SeedRejected, "input_timeout"):
                child.read_contract()


class IdentityReductionTests(unittest.TestCase):
    def test_privilege_reduction_order_and_no_root_syscall(self):
        events = []

        def prctl(operation, arg, *_rest):
            events.append(("prctl", operation, arg))
            return -1 if operation == 23 and arg == 1 else (1 if operation == 23 else 0)

        lib = SimpleNamespace(prctl=Mock(side_effect=prctl),
                              capset=Mock(side_effect=lambda *a: events.append(("capset",)) or 0))
        fake_ctypes = SimpleNamespace(
            CDLL=lambda *a, **kw: lib, c_int=ctypes.c_int, c_ulong=ctypes.c_ulong,
            POINTER=ctypes.POINTER, byref=ctypes.byref, get_errno=lambda: errno.EINVAL,
        )
        fake_os = SimpleNamespace(
            setgroups=lambda groups: events.append(("setgroups", groups)),
            setresgid=lambda *ids: events.append(("setresgid", ids)),
            setresuid=lambda *ids: events.append(("setresuid", ids)),
        )
        with patch.object(child, "os", fake_os), patch.object(child, "ctypes", fake_ctypes):
            child.reduce_identity(23001, 23003)
        self.assertEqual(events[:4], [("prctl", 38, 1), ("prctl", 8, 0), ("prctl", 47, 4),
                                      ("setgroups", [])])
        self.assertLess(events.index(("setresgid", (23003,) * 3)), events.index(("setresuid", (23001,) * 3)))
        self.assertLess(events.index(("setresuid", (23001,) * 3)), events.index(("capset",)))
        self.assertEqual(events[-1], ("prctl", 4, 0))


def kernel_process(pid, parent, start, *, namespace="mnt:[400]", uid=0, gid=0):
    return {
        "pid": pid, "parent": parent, "startTicks": start,
        "uids": (uid,) * 4, "gids": (gid,) * 4, "groups": (), "threads": 1,
        "nnp": 1, "caps": {key: 0 for key in child.CAPS},
        "userns": "user:[4026531837]", "mountns": namespace,
        "uidMap": list(child.INITIAL_MAP), "gidMap": list(child.INITIAL_MAP),
    }


class KernelBindingTests(unittest.TestCase):
    def actors(self):
        return {
            101: kernel_process(101, 1, 10001, namespace="mnt:[399]"),
            102: kernel_process(102, 101, 10002),
            103: kernel_process(103, 101, 10003, namespace="mnt:[399]"),
        }

    def test_root_authority_is_bound_to_original_processes_and_fd(self):
        cases = (
            (None, None, None),
            (101, "startTicks", 999),
            (101, "uids", (1,) * 4),
            (102, "parent", 999),
            (102, "mountns", "mnt:[401]"),
            (102, "threads", 2),
            (102, "uidMap", ["0", "1", "65536"]),
            (103, "parent", 999),
            (103, "userns", "user:[1]"),
            (103, "mountns", "mnt:[400]"),
        )
        for pid, key, value in cases:
            with self.subTest(pid=pid, key=key):
                actors = self.actors()
                if pid is not None:
                    actors[pid][key] = value
                boundary = child.Boundary()
                boundary.modules["state_volume_supervisor"] = SimpleNamespace(fs_type=lambda _: child.NSFS_MAGIC)
                fake_os = SimpleNamespace(
                    getpid=lambda: 103, getppid=lambda: 101,
                    stat=lambda _: SimpleNamespace(st_ino=400),
                    fstat=lambda _: SimpleNamespace(st_ino=400),
                    readlink=lambda _: "mnt:[400]",
                )
                with patch.object(child, "process_identity", side_effect=lambda n: deepcopy(actors[n])), \
                        patch.object(child, "os", fake_os):
                    if pid is None:
                        self.assertEqual(boundary.authority(contract())["pid"], 103)
                    else:
                        with self.assertRaises(child.SeedRejected):
                            boundary.authority(contract())

    def test_mismatched_namespace_fd_refused(self):
        actors = self.actors()
        boundary = child.Boundary()
        boundary.modules["state_volume_supervisor"] = SimpleNamespace(fs_type=lambda _: child.NSFS_MAGIC)
        fake_os = SimpleNamespace(getpid=lambda: 103, getppid=lambda: 101,
                                  stat=lambda _: SimpleNamespace(st_ino=400),
                                  fstat=lambda _: SimpleNamespace(st_ino=999),
                                  readlink=lambda _: "mnt:[400]")
        with patch.object(child, "process_identity", side_effect=lambda n: actors[n]), \
                patch.object(child, "os", fake_os):
            with self.assertRaisesRegex(child.SeedRejected, "namespace_descriptor"):
                boundary.authority(contract())

    def test_scope_refuses_foreign_member_or_replaced_identity(self):
        class OwnedPath:
            def __init__(self, value):
                self.value = value

            def iterdir(self):
                return iter(())

            def relative_to(self, base):
                return self.value[len(base) + 1:]

        for member_text, identity in (("102\n", (25, 300)), ("102\n999\n", (25, 300)),
                                      ("102\n", (25, 999))):
            boundary = child.Boundary()
            boundary.modules["state_volume_supervisor"] = SimpleNamespace(
                trusted=lambda *a, **kw: identity, fs_type=lambda _: 99, CGROUP2_MAGIC=99,
            )
            expected_cgroup = "0::/alaz-r155a1/volume-" + "a" * 32 + "\n"
            with patch.object(child, "Path", OwnedPath), patch.object(
                child, "_read_bounded",
                side_effect=lambda path, limit: (member_text if path.endswith("/cgroup.procs")
                                                else expected_cgroup).encode(),
            ):
                if member_text == "102\n" and identity == (25, 300):
                    boundary.scope(contract(), {102})
                else:
                    with self.assertRaises(child.SeedRejected):
                        boundary.scope(contract(), {102})

    def test_mount_requires_exact_ext4_loop_and_options_without_profile_submount(self):
        for fault in (None, "device", "filesystem", "root", "mount_point", "readonly", "submount"):
            with self.subTest(fault=fault):
                record = SimpleNamespace(
                    mount_point=child.TARGET, root="/", filesystem="ext4", device=(7, 8),
                    mount_options=frozenset({"rw", "nosuid", "nodev", "noexec"}),
                    super_options=frozenset({"rw"}),
                )
                records = [record]
                if fault in ("device", "filesystem", "root", "mount_point"):
                    setattr(record, fault, (7, 9) if fault == "device" else "wrong")
                elif fault == "readonly":
                    record.mount_options = frozenset({"ro", "nosuid", "nodev", "noexec"})
                elif fault == "submount":
                    records.append(SimpleNamespace(mount_point=child.PROFILE))
                boundary = child.Boundary()
                boundary.modules["gateway_storage_mounts"] = SimpleNamespace(
                    _read_mountinfo=lambda: b"owned fixture",
                    parse_mountinfo=lambda raw: records,
                    select_mount=lambda observed, path: observed[0],
                )
                boundary.modules["state_volume_supervisor"] = SimpleNamespace(fs_type=lambda _: 0xEF53)
                fake_os = SimpleNamespace(makedev=lambda major, minor: 1800)
                with patch.object(child, "os", fake_os), \
                        patch.object(child, "_trusted_path", return_value=info(inode=2, mode=stat.S_IFDIR | 0o755)):
                    if fault is None:
                        self.assertEqual(boundary.mounted(contract()), (1800, 2))
                    else:
                        with self.assertRaises(child.SeedRejected):
                            boundary.mounted(contract())

    def test_reduced_actor_uses_own_namespace_and_root_process_anchors(self):
        value = contract()
        own = kernel_process(103, 101, 10003, uid=23001, gid=23003)
        actors = self.actors()
        boundary = child.Boundary()
        boundary.before = kernel_process(103, 101, 10003, namespace="mnt:[399]")
        boundary.mounted = Mock()
        boundary.verify_profile = Mock()
        boundary.verify_sources = Mock()
        fake_os = SimpleNamespace(getpid=lambda: 103, getppid=lambda: 101,
                                  getresuid=lambda: (23001,) * 3, getresgid=lambda: (23003,) * 3,
                                  getgroups=lambda: [])
        expected = "0::/" + str(child.Path(value["scope"]["path"]).relative_to("/sys/fs/cgroup"))
        with patch.object(child, "os", fake_os), \
                patch.object(child, "process_identity", return_value=own) as identity, \
                patch.object(child, "process_anchor", side_effect=lambda n: actors[n]) as anchor, \
                patch.object(child, "_read_bounded", return_value=(expected + "\n").encode()), \
                patch.object(child, "check_fds"):
            boundary.verify_target(value, child.CreatedProfile(1800, 1234))
            identity.assert_called_once_with(103)
            self.assertEqual([call.args[0] for call in anchor.call_args_list], [101, 102])
            own["caps"]["CapEff"] = 1
            with self.assertRaisesRegex(child.SeedRejected, "identity_reduction_unproved"):
                boundary.verify_target(value, child.CreatedProfile(1800, 1234))

if __name__ == "__main__":
    unittest.main()
