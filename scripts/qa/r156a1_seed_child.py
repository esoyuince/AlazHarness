'Fixed R156 supervised seed boundary with original R155 ownership algorithm.\nOnly fixed runtime, input, state and receipt bindings are changed.\nThe original controller retains image ownership and all uncertain effects.\n'
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import sys
import threading
import time
import types

PROTOCOL = 'alaz-seed-child-r156a1-v1'
PYTHON = "/usr/bin/python3.12"
INSTALLATION = '/opt/alaz-r156a1'
INPUT_ROOT = '/opt/alaz-r156a1-accept-input'
CHILD = INPUT_ROOT + '/scripts/qa/r156a1_seed_child.py'
BOOTSTRAP = INPUT_ROOT + '/scripts/bootstrap_retained_profile_r156.py'
STATE_ROOT = '/srv/alaz-r156a1'
IMAGE = STATE_ROOT + "/images/state.ext4"
FENCE = IMAGE + ".volume-owner.json"
TARGET = STATE_ROOT + "/mount"
PROFILE = TARGET + "/profile"
CGROUP_PARENT = '/sys/fs/cgroup/alaz-r156a1'
RECEIPT_SHA = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
PYTHON_SHA = "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f"
ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC"}
HELPERS = (
    ("state_image_lease", "f57fbf1f24ea6953dd66726c6dcedb7566d66e3e12083881e78f7025c1490ddc"),
    ("state_volume_supervisor", "5088f1b0a27eb1bed83c635a3b356bd2281d3150aad1af57f1f714530a12c080"),
    ("gateway_storage_mounts", "cd468f68c6b916dada4bfce1897c3ddd9507596b48137e026ee94f06e3e5e3c1"),
)
FIELDS = {
    "protocol", "controller", "worker", "scope", "namespace", "image", "token",
    "fence", "mountpoint", "profile", "loopNumber", "principal", "installation",
    "bootstrap", "seedInstanceId",
}
IMAGE_FIELDS = {"path", "device", "inode", "size", "uid", "gid", "parent_device", "parent_inode"}
PRINCIPAL_FIELDS = {"version", "enabled", "gatewayUid", "brokerUid", "socketGroupGid", "hostUserNamespace"}
CAPS = ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")
MAX_INPUT = 16384
MAX_OUTPUT = 1024
INPUT_SECONDS = 3.0
NSFS_MAGIC = 0x6E736673
CLONE_NEWNS = 0x00020000
INITIAL_MAP = ["0", "0", "4294967295"]


class SeedRejected(RuntimeError):
    """An internal finite diagnostic, never arbitrary input or stderr."""


def require(condition, reason):
    if not condition:
        raise SeedRejected(reason)


def _object(value, keys, reason):
    require(type(value) is dict and set(value) == set(keys), reason)
    return value


def _integer(value, minimum=0, maximum=(1 << 63) - 1):
    require(type(value) is int and minimum <= value <= maximum, "integer_contract")
    return value


def _digest(value):
    require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None, "digest_contract")


def validate_contract(value):
    """Validate all fields and return a detached JSON-only contract."""
    _object(value, FIELDS, "contract_fields")
    require(value["protocol"] == PROTOCOL, "protocol_contract")
    for key in ("controller", "worker"):
        row = _object(value[key], {"pid", "startTicks"}, "process_contract")
        _integer(row["pid"], 1, (1 << 31) - 1)
        _integer(row["startTicks"], 1)
    require(value["controller"]["pid"] != value["worker"]["pid"], "process_alias")
    token = value["token"]
    require(type(token) is str and re.fullmatch(r"[a-f0-9]{32}", token) is not None, "token_contract")
    row = _object(value["scope"], {"path", "device", "inode"}, "scope_contract")
    require(row["path"] == CGROUP_PARENT + "/volume-" + token, "scope_path")
    _integer(row["device"])
    _integer(row["inode"], 1)
    row = _object(value["namespace"], {"fd", "inode"}, "namespace_contract")
    _integer(row["fd"], 3, (1 << 20) - 1)
    _integer(row["inode"], 1)
    row = _object(value["image"], IMAGE_FIELDS, "image_contract")
    require(row["path"] == IMAGE, "image_path")
    for key in IMAGE_FIELDS - {"path"}:
        _integer(row[key], 1 if key in {"inode", "parent_inode"} else 0)
    require(row["uid"] == row["gid"] == 0, "image_owner")
    require(4096 <= row["size"] <= (1 << 50) and row["size"] % 4096 == 0, "image_size")
    row = _object(value["fence"], {"path", "sha256"}, "fence_contract")
    require(row["path"] == FENCE, "fence_path")
    _digest(row["sha256"])
    require(value["mountpoint"] == TARGET and value["profile"] == PROFILE, "target_path")
    _integer(value["loopNumber"], 0, 65535)
    row = _object(value["principal"], PRINCIPAL_FIELDS, "principal_contract")
    require(type(row["version"]) is int and row["version"] == 1 and row["enabled"] is True,
            "principal_opt_in")
    for key in ("gatewayUid", "brokerUid", "socketGroupGid"):
        _integer(row[key], 1, (1 << 31) - 2)
    require(row["gatewayUid"] != row["brokerUid"], "principal_alias")
    require(type(row["hostUserNamespace"]) is str
            and re.fullmatch(r"user:\[[1-9][0-9]{0,19}\]", row["hostUserNamespace"]) is not None,
            "principal_namespace")
    row = _object(value["installation"], {"path", "receiptSha256"}, "installation_contract")
    require(row == {"path": INSTALLATION, "receiptSha256": RECEIPT_SHA}, "installation_pin")
    row = _object(value["bootstrap"], {"path", "sha256"}, "bootstrap_contract")
    require(row["path"] == BOOTSTRAP, "bootstrap_path")
    _digest(row["sha256"])
    require(type(value["seedInstanceId"]) is str
            and re.fullmatch(r"[A-Za-z0-9._-]{1,128}", value["seedInstanceId"]) is not None,
            "instance_contract")
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


def encode_contract(value):
    result = (json.dumps(validate_contract(value), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True) + "\n").encode("ascii")
    require(len(result) <= MAX_INPUT, "input_bound")
    return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _invalid_number(_text):
    raise SeedRejected("json_number_contract")


def _json(data):
    try:
        return json.loads(data, object_pairs_hook=_unique, parse_float=_invalid_number,
                          parse_constant=_invalid_number)
    except (UnicodeError, ValueError, RecursionError):
        raise SeedRejected("json_contract") from None


def decode_contract(data):
    require(type(data) is bytes and 0 < len(data) <= MAX_INPUT
            and data.endswith(b"\n") and data.count(b"\n") == 1, "input_frame")
    try:
        value = validate_contract(_json(data.decode("ascii")))
    except UnicodeError:
        raise SeedRejected("input_ascii") from None
    require(encode_contract(value) == data, "input_canonical")
    return value


def check_stdio():
    require(all(stat.S_ISFIFO(os.fstat(fd).st_mode) for fd in (0, 1, 2)), "stdio_pipes_required")


def read_contract():
    deadline = time.monotonic() + INPUT_SECONDS
    data = bytearray()
    while True:
        left = deadline - time.monotonic()
        require(left > 0 and bool(select.select([0], [], [], left)[0]), "input_timeout")
        part = os.read(0, min(4096, MAX_INPUT + 1 - len(data)))
        if not part:
            return decode_contract(bytes(data))
        data.extend(part)
        require(len(data) <= MAX_INPUT, "input_bound")


def _read_bounded(path, limit):
    with open(path, "rb", buffering=0) as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, "kernel_read_bound")
    return data


def _same_stat(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _trusted_path(path, *, directory=False):
    p = Path(path)
    require(p.is_absolute() and p == p.resolve(strict=True), "trusted_canonical_path")
    for parent in p.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not stat.S_IMODE(info.st_mode) & 0o022, "trusted_ancestor")
    info = p.lstat()
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and info.st_uid == info.st_gid == 0
            and not stat.S_IMODE(info.st_mode) & 0o6022, "trusted_object")
    return info


def trusted_bytes(path, limit, digest=None, mode=None):
    """Root-controlled no-follow read with stable descriptor and path metadata."""
    _trusted_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 0
                and before.st_nlink == 1 and not stat.S_IMODE(before.st_mode) & 0o6022
                and 0 < before.st_size <= limit, "trusted_file_metadata")
        require(mode is None or stat.S_IMODE(before.st_mode) == mode, "trusted_file_mode")
        data = bytearray()
        while len(data) <= limit:
            part = os.read(fd, min(65536, limit + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        require(_same_stat(before) == _same_stat(os.fstat(fd)) == _same_stat(os.lstat(path))
                and len(data) == before.st_size, "trusted_file_changed")
        raw = bytes(data)
        require(digest is None or hashlib.sha256(raw).hexdigest() == digest, "source_digest")
        return raw
    finally:
        os.close(fd)


def process_anchor(pid):
    """Read live kernel PID/start ticks and IDs without namespace-FD access."""
    raw = _read_bounded("/proc/" + str(pid) + "/stat", 8192).decode("ascii")
    prefix, separator, tail = raw.rpartition(") ")
    parts = tail.split()
    require(separator and prefix.startswith(str(pid) + " (") and len(parts) >= 20
            and parts[0] not in {"Z", "X", "x"}, "process_not_live")
    rows = {}
    for line in _read_bounded("/proc/" + str(pid) + "/status", 32768).decode("ascii").splitlines():
        key, _, text = line.partition(":")
        if key in {"Uid", "Gid", "Groups", "Threads", "NoNewPrivs", *CAPS}:
            require(key not in rows, "process_status_duplicate")
            rows[key] = text.split()
    require(set(rows) == {"Uid", "Gid", "Groups", "Threads", "NoNewPrivs", *CAPS}
            and len(rows["Uid"]) == len(rows["Gid"]) == 4
            and all(len(rows[k]) == 1 for k in ("Threads", "NoNewPrivs", *CAPS)), "process_status")
    return {
        "pid": pid, "parent": int(parts[1]), "startTicks": int(parts[19]),
        "uids": tuple(map(int, rows["Uid"])), "gids": tuple(map(int, rows["Gid"])),
        "groups": tuple(map(int, rows["Groups"])), "threads": int(rows["Threads"][0]),
        "nnp": int(rows["NoNewPrivs"][0]), "caps": {k: int(rows[k][0], 16) for k in CAPS},
    }


def process_identity(pid):
    root = "/proc/" + str(pid)
    return {
        **process_anchor(pid),
        "userns": os.readlink(root + "/ns/user"), "mountns": os.readlink(root + "/ns/mnt"),
        "uidMap": _read_bounded(root + "/uid_map", 4096).decode("ascii").split(),
        "gidMap": _read_bounded(root + "/gid_map", 4096).decode("ascii").split(),
    }


def check_fds(allowed):
    check_stdio()
    names = os.listdir("/proc/self/fd")
    require(len(names) <= 16 and all(name.isdecimal() for name in names), "descriptor_inventory")
    present = set()
    for name in names:
        fd = int(name)
        try:
            os.fstat(fd)
        except OSError as exc:
            # listdir's own transient enumeration descriptor is already closed.
            require(exc.errno == errno.EBADF and fd not in allowed, "descriptor_observation")
        else:
            present.add(fd)
    require(present == set(allowed), "unexpected_inherited_descriptor")


class CapHeader(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


class CapData(ctypes.Structure):
    _fields_ = [("effective", ctypes.c_uint32), ("permitted", ctypes.c_uint32),
                ("inheritable", ctypes.c_uint32)]


def reduce_identity(uid, gid):
    """The reviewed principal-launch reduction sequence, for the Gateway UID."""
    lib = ctypes.CDLL(None, use_errno=True)
    lib.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    lib.prctl.restype = ctypes.c_int
    lib.capset.argtypes = [ctypes.POINTER(CapHeader), ctypes.POINTER(CapData)]
    lib.capset.restype = ctypes.c_int

    def prctl(*args):
        require(lib.prctl(*args) == 0, "identity_prctl")

    prctl(38, 1, 0, 0, 0)  # NO_NEW_PRIVS
    prctl(8, 0, 0, 0, 0)   # no KEEP_CAPS
    prctl(47, 4, 0, 0, 0)  # clear ambient capabilities
    os.setgroups([])
    terminated = False
    for cap in range(64):
        result = lib.prctl(23, cap, 0, 0, 0)  # READ bounding set
        if result < 0:
            require(cap > 0 and ctypes.get_errno() == errno.EINVAL, "identity_capability_read")
            terminated = True
            break
        require(result in (0, 1), "identity_capability_read")
        prctl(24, cap, 0, 0, 0)  # DROP bounding set
    require(terminated, "identity_capability_range")
    os.setresgid(gid, gid, gid)
    os.setresuid(uid, uid, uid)
    header = CapHeader(0x20080522, 0)
    empty = (CapData * 2)()
    require(lib.capset(ctypes.byref(header), empty) == 0, "identity_capset")
    prctl(4, 0, 0, 0, 0)  # no dumpability (not a sandbox claim)


@dataclass(frozen=True)
class CreatedProfile:
    device: int
    inode: int


@dataclass
class Progress:
    phase: str = "input"
    effect_attempted: bool = False


def producer_command(value, profile):
    require(type(profile) is CreatedProfile, "created_profile_required")
    _integer(profile.device)
    _integer(profile.inode, 1)
    p = value["principal"]
    return [
        PYTHON, "-I", "-B", BOOTSTRAP, "--home", PROFILE,
        "--instance-id", value["seedInstanceId"],
        "--expected-profile-device", str(profile.device),
        "--expected-profile-inode", str(profile.inode),
        "--gateway-uid", str(p["gatewayUid"]),
        "--socket-group-gid", str(p["socketGroupGid"]),
        "--parent-pid", str(value["controller"]["pid"]),
    ]


class Boundary:
    """Privileged operations are never called by source-only tests."""

    def __init__(self):
        self.modules = {}
        self.before = None
        self.ns_closed = False
        self.mount_identity = None
        self.mount_record = None

    def verify_sources(self, value, *, load=False):
        _trusted_path(INSTALLATION, directory=True)
        _trusted_path(CHILD)
        require(str(Path(__file__).resolve(strict=True)) == CHILD, "fixed_child_path")
        trusted_bytes(PYTHON, 64 << 20, PYTHON_SHA)
        trusted_bytes(INSTALLATION + "/.alaz-installation.json", 4 << 20, RECEIPT_SHA)
        trusted_bytes(BOOTSTRAP, 1 << 20, value["bootstrap"]["sha256"])
        for name, digest in HELPERS:
            path = INSTALLATION + "/packages/claw-hermes/" + name + ".py"
            raw = trusted_bytes(path, 1 << 20, digest)
            if load:
                require(name not in sys.modules, "helper_already_loaded")
                module = types.ModuleType(name)
                module.__file__ = path
                sys.modules[name] = module
                exec(compile(raw, path, "exec", dont_inherit=True), module.__dict__)
                self.modules[name] = module

    @property
    def volume(self):
        return self.modules["state_volume_supervisor"]

    def authority(self, value, *, joined=False):
        controller = process_identity(value["controller"]["pid"])
        worker = process_identity(value["worker"]["pid"])
        own = process_identity(os.getpid())
        p = value["principal"]
        require(own["pid"] not in {controller["pid"], worker["pid"]}
                and os.getppid() == own["parent"] == controller["pid"], "direct_parent")
        for observed, expected in ((controller, value["controller"]), (worker, value["worker"])):
            require(observed["startTicks"] == expected["startTicks"]
                    and observed["uids"] == observed["gids"] == (0,) * 4, "original_root_process")
        require(worker["parent"] == controller["pid"] and worker["threads"] == 1, "original_worker")
        for observed in (controller, worker, own):
            require(observed["userns"] == p["hostUserNamespace"]
                    and observed["uidMap"] == observed["gidMap"] == INITIAL_MAP, "initial_namespace")
        namespace = "mnt:[" + str(value["namespace"]["inode"]) + "]"
        require(worker["mountns"] == namespace and controller["mountns"] != namespace, "worker_namespace")
        require(own["mountns"] == (namespace if joined else controller["mountns"]), "child_namespace")
        require(os.stat("/proc/" + str(worker["pid"]) + "/ns/mnt").st_ino
                == value["namespace"]["inode"], "worker_namespace_inode")
        if not joined:
            fd = value["namespace"]["fd"]
            require(os.fstat(fd).st_ino == value["namespace"]["inode"]
                    and os.readlink("/proc/self/fd/" + str(fd)) == namespace
                    and self.volume.fs_type("/proc/self/fd/" + str(fd)) == NSFS_MAGIC, "namespace_descriptor")
        return own

    def scope(self, value, expected_members):
        path = value["scope"]["path"]
        require(self.volume.trusted(path, directory=True)
                == (value["scope"]["device"], value["scope"]["inode"])
                and self.volume.fs_type(path) == self.volume.CGROUP2_MAGIC, "original_scope")
        require(not any(p.is_dir() for p in Path(path).iterdir()), "nested_scope")
        words = _read_bounded(path + "/cgroup.procs", 16384).decode("ascii").split()
        require(len(words) <= 3 and all(x.isdecimal() for x in words)
                and len(words) == len(set(words)) and set(map(int, words)) == set(expected_members),
                "scope_members")
        for pid in expected_members:
            expected = "0::/" + str(Path(path).relative_to("/sys/fs/cgroup"))
            actual = _read_bounded("/proc/" + str(pid) + "/cgroup", 16384).decode("ascii").splitlines()
            require(actual == [expected], "scope_membership")

    def image_fence(self, value):
        lease = self.modules["state_image_lease"]
        pin = lease.ImagePin(**value["image"])
        _trusted_path(IMAGE)
        lease._parent(os.lstat(str(Path(IMAGE).parent)), pin)
        lease._image(os.lstat(IMAGE), pin)
        raw = trusted_bytes(FENCE, 16384, value["fence"]["sha256"], mode=0o600)
        expected = {
            "version": 1, "token": value["token"], "controllerPid": value["controller"]["pid"],
            "image": value["image"], "scope": value["scope"]["path"], "mountpoint": TARGET,
        }
        require(_json(raw.decode("ascii")) == expected, "original_fence")
        expected_loop = {
            "device": pin.device, "inode": pin.inode, "offset": 0, "sizeLimit": 0,
            "number": value["loopNumber"], "flags": self.volume.AUTOCLEAR, "encryption": 0,
        }
        require(self.volume.attachments(pin) == [expected_loop], "original_image_attachment")

    def preflight(self, value):
        require(sys.platform == "linux" and os.uname().machine == "x86_64"
                and sys.byteorder == "little", "linux_abi")
        require(sys.executable == PYTHON and sys.version_info[:2] == (3, 12)
                and sys.flags.isolated == 1 and sys.flags.ignore_environment == 1
                and sys.flags.no_user_site == 1 and sys.flags.dont_write_bytecode == 1
                and sys.flags.optimize == 0 and sys.argv == [CHILD], "isolated_entrypoint")
        require(dict(os.environ) == ENV, "fixed_environment")
        check_fds({0, 1, 2, value["namespace"]["fd"]})
        self.verify_sources(value, load=True)
        self.volume.actor()
        own = self.authority(value)
        needed = (1 << 6) | (1 << 7) | (1 << 8) | (1 << 21)  # SETGID/SETUID/SETPCAP/SYS_ADMIN
        require(own["uids"] == own["gids"] == (0,) * 4
                and own["threads"] == 1 and threading.active_count() == 1
                and own["caps"]["CapEff"] & needed == needed, "root_actor")
        # The parent qualified these accounts; confirm the Gateway UID still resolves live.
        import pwd
        import grp
        require(pwd.getpwnam("alazgateway").pw_uid == value["principal"]["gatewayUid"],
                "gateway_account_changed")
        require(pwd.getpwuid(value["principal"]["brokerUid"]).pw_uid == value["principal"]["brokerUid"]
                and grp.getgrgid(value["principal"]["socketGroupGid"]).gr_gid
                == value["principal"]["socketGroupGid"], "principal_account_changed")
        self.scope(value, {value["worker"]["pid"]})
        self.image_fence(value)
        self.before = own

    def enroll(self, value):
        self.authority(value)
        self.scope(value, {value["worker"]["pid"]})
        path = value["scope"]["path"] + "/cgroup.procs"
        fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            raw = (str(os.getpid()) + "\n").encode("ascii")
            require(os.write(fd, raw) == len(raw), "scope_write_short")
        finally:
            os.close(fd)
        self.scope(value, {value["worker"]["pid"], os.getpid()})

    def join_namespace(self, value):
        fd = value["namespace"]["fd"]
        try:
            self.authority(value)
            lib = ctypes.CDLL(None, use_errno=True)
            lib.setns.argtypes = [ctypes.c_int, ctypes.c_int]
            lib.setns.restype = ctypes.c_int
            require(lib.setns(fd, CLONE_NEWNS) == 0, "setns_failed")
        finally:
            # Only the explicitly inherited namespace descriptor is closed.
            os.close(fd)
            self.ns_closed = True
        self.authority(value, joined=True)
        check_fds({0, 1, 2})

    def mounted(self, value):
        storage = self.modules["gateway_storage_mounts"]
        records = storage.parse_mountinfo(storage._read_mountinfo())
        record = storage.select_mount(records, TARGET)
        info = _trusted_path(TARGET, directory=True)
        require(record.mount_point == TARGET and record.root == "/" and record.filesystem == "ext4"
                and record.device == (7, value["loopNumber"])
                and {"rw", "nosuid", "nodev", "noexec"}.issubset(record.mount_options)
                and "rw" in record.super_options and "ro" not in record.mount_options
                and info.st_dev == os.makedev(7, value["loopNumber"])
                and self.volume.fs_type(TARGET) == 0xEF53
                and stat.S_IMODE(info.st_mode) & 0o001, "actual_ext4_mount")
        require(not any(r.mount_point == PROFILE or r.mount_point.startswith(PROFILE + "/")
                        for r in records), "profile_submount")
        identity = (info.st_dev, info.st_ino)
        if self.mount_identity is None:
            self.mount_identity, self.mount_record = identity, record
        require(self.mount_identity == identity and self.mount_record == record, "mount_changed")
        return identity

    def create_profile(self, value):
        self.authority(value, joined=True)
        self.scope(value, {value["worker"]["pid"], os.getpid()})
        self.mounted(value)
        target_fd = os.open(TARGET, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(target_fd)
            require((info.st_dev, info.st_ino) == self.mount_identity, "mount_descriptor_changed")
            # mkdir is exclusive, including against existing files/symlinks/directories.
            # Never adopt, remove, rename, empty or retry an existing profile.
            os.mkdir("profile", mode=0o700, dir_fd=target_fd)
            profile_fd = os.open("profile", os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=target_fd)
            try:
                before = os.fstat(profile_fd)
                require(stat.S_ISDIR(before.st_mode) and before.st_uid == before.st_gid == 0
                        and before.st_dev == info.st_dev and not os.listdir(profile_fd), "fresh_profile")
                os.fchmod(profile_fd, 0o700)
                os.fchown(profile_fd, value["principal"]["gatewayUid"], value["principal"]["socketGroupGid"])
                after = os.fstat(profile_fd)
                require((after.st_dev, after.st_ino) == (before.st_dev, before.st_ino), "profile_changed")
                result = CreatedProfile(after.st_dev, after.st_ino)
                self.verify_profile(value, result)
                os.fsync(profile_fd)
                os.fsync(target_fd)
                return result
            finally:
                os.close(profile_fd)
        finally:
            os.close(target_fd)

    def verify_profile(self, value, profile):
        require(str(Path(PROFILE).resolve(strict=True)) == PROFILE, "profile_canonical")
        info = os.lstat(PROFILE)
        require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
                and (info.st_dev, info.st_ino) == (profile.device, profile.inode)
                and info.st_uid == value["principal"]["gatewayUid"]
                and info.st_gid == value["principal"]["socketGroupGid"]
                and not any(Path(PROFILE).iterdir()), "profile_identity")

    def before_drop(self, value, profile):
        self.authority(value, joined=True)
        self.scope(value, {value["worker"]["pid"], os.getpid()})
        self.image_fence(value)
        self.mounted(value)
        self.verify_profile(value, profile)
        self.verify_sources(value)
        check_fds({0, 1, 2})

    def drop_identity(self, value):
        os.chdir("/")
        os.umask(0o077)
        reduce_identity(value["principal"]["gatewayUid"], value["principal"]["socketGroupGid"])

    def verify_target(self, value, profile):
        # Root namespace descriptors may be unreadable after UID reduction.
        # Root-side authority was revalidated immediately before that reduction;
        # now prove live anchors plus this actor\'s actual namespace and cgroup.
        own = process_identity(os.getpid())
        controller = process_anchor(value["controller"]["pid"])
        worker = process_anchor(value["worker"]["pid"])
        require(os.getppid() == own["parent"] == controller["pid"]
                and worker["parent"] == controller["pid"], "reduced_direct_parent")
        for observed, expected in ((controller, value["controller"]), (worker, value["worker"])):
            require(observed["startTicks"] == expected["startTicks"]
                    and observed["uids"] == observed["gids"] == (0,) * 4, "reduced_original_process")
        p = value["principal"]
        require(own["userns"] == self.before["userns"] == p["hostUserNamespace"]
                and own["uidMap"] == own["gidMap"] == INITIAL_MAP
                and own["mountns"] == "mnt:[" + str(value["namespace"]["inode"]) + "]",
                "reduced_namespace")
        require(own["pid"] == self.before["pid"] and own["startTicks"] == self.before["startTicks"]
                and own["uids"] == (p["gatewayUid"],) * 4 and own["gids"] == (p["socketGroupGid"],) * 4
                and own["groups"] == () and own["threads"] == 1 and own["nnp"] == 1
                and all(own["caps"][key] == 0 for key in CAPS), "identity_reduction_unproved")
        require(os.getresuid() == (p["gatewayUid"],) * 3 and os.getresgid() == (p["socketGroupGid"],) * 3
                and os.getgroups() == [], "identity_reduction_ids")
        expected_scope = "0::/" + str(Path(value["scope"]["path"]).relative_to("/sys/fs/cgroup"))
        require(_read_bounded("/proc/self/cgroup", 16384).decode("ascii").splitlines()
                == [expected_scope], "reduced_scope_membership")
        self.mounted(value)
        self.verify_profile(value, profile)
        self.verify_sources(value)
        check_fds({0, 1, 2})

    def exec_producer(self, value, profile):
        argv = producer_command(value, profile)
        os.execve(PYTHON, argv, dict(ENV))
        raise SeedRejected("exec_returned")


def run_contract(value, boundary, progress):
    """Finite order shared with owned-double tests; no recovery branch."""
    value = validate_contract(value)
    progress.phase = "preflight"
    boundary.preflight(value)
    progress.phase = "scope_enrollment"
    progress.effect_attempted = True  # before the first possible persistent effect
    boundary.enroll(value)
    progress.phase = "namespace_join"
    boundary.join_namespace(value)
    progress.phase = "fresh_profile_creation"
    profile = boundary.create_profile(value)
    require(type(profile) is CreatedProfile, "created_profile_required")
    progress.phase = "pre_drop_revalidation"
    boundary.before_drop(value, profile)
    progress.phase = "identity_reduction"
    boundary.drop_identity(value)
    progress.phase = "reduced_actor_verification"
    boundary.verify_target(value, profile)
    progress.phase = "producer_exec"
    boundary.exec_producer(value, profile)
    raise SeedRejected("exec_returned")


def failure_frame(progress, exc, pid):
    # Preserve only our finite codes. OSError or helper failures reveal no paths/data.
    reason = str(exc) if type(exc) is SeedRejected else type(exc).__name__
    if re.fullmatch(r"[A-Za-z0-9_]{1,80}", reason) is None:
        reason = "unclassified_failure"
    value = {
        "protocol": PROTOCOL, "state": "UNKNOWN" if progress.effect_attempted else "REFUSED_PRE_EFFECT",
        "phase": progress.phase, "reason": reason, "pid": pid,
        "cleanupAttempted": False, "retryPermitted": False,
    }
    frame = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    require(len(frame) <= MAX_OUTPUT, "output_bound")
    return frame


def main():
    progress = Progress()
    stdio_ok = False
    try:
        check_stdio()
        stdio_ok = True
        value = read_contract()
        run_contract(value, Boundary(), progress)
    except Exception as exc:
        if stdio_ok:
            try:
                # One bounded pipe write, no print buffering or retry.
                os.write(1, failure_frame(progress, exc, os.getpid()))
            except OSError:
                pass
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
