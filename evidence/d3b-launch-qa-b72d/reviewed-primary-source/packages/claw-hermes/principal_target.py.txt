"""Post-exec broker admission. No authority comes from command-line claims.

All identity/privilege predicates use the current kernel state. This is not
proof of a prior root transition or two-process transport. The interpreter,
imports and runtime must already belong to the trusted installation.
"""
from __future__ import annotations
import ctypes
import hashlib
from pathlib import PurePosixPath
import threading

import host_principal as hp
import principal_launch as launch
from credential_guard import unique_json
import linux_netns as net


class TargetRejected(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise TargetRejected(reason)


def seccomp_mode():
    lib = ctypes.CDLL(None, use_errno=True)
    lib.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                         ctypes.c_ulong, ctypes.c_ulong]
    lib.prctl.restype = ctypes.c_int
    mode = lib.prctl(21, 0, 0, 0, 0)  # PR_GET_SECCOMP, no mutation
    require(mode >= 0, 'target_filter_state_unavailable')
    return mode


def restricted_kernel(principal):
    p = hp.policy(principal)
    state = launch.observation()
    require(type(state) is dict, 'target_kernel_state')
    require(type(state.get('pid')) is int and state['pid'] > 0
            and type(state.get('uids')) is tuple and len(state['uids']) == 4
            and all(type(n) is int and n == p['brokerUid'] for n in state['uids'])
            and type(state.get('gids')) is tuple and len(state['gids']) == 4
            and all(type(n) is int and n == p['socketGroupGid'] for n in state['gids']),
            'target_wrong_identity')
    require(state.get('userns') == p['hostUserNamespace']
            and state.get('uidMap') == ['0', '0', '4294967295']
            and state.get('gidMap') == ['0', '0', '4294967295'],
            'target_not_host_namespace')
    caps = state.get('caps')
    require(type(caps) is dict and set(caps) == set(launch.CAPS)
            and all(type(v) is int and v == 0 for v in caps.values()),
            'target_capabilities_remain')
    require(type(state.get('groups')) is tuple and not state['groups']
            and type(state.get('nnp')) is int and state['nnp'] == 1
            and type(state.get('threads')) is int and state['threads'] == 1
            and threading.active_count() == 1, 'target_process_not_restricted')
    mode = seccomp_mode()
    require(type(mode) is int and mode == 2, 'target_inherited_filter_missing')
    return state


def prepare(principal, config_path, config_sha256, output):
    """Admit this broker image before event-loop/socket/private-budget activity.

    The argv pins carry expectations, never permission. A bare Seccomp=2 only
    means some filter is installed: install our exact deny rules again before
    reading the private config. The broker's provider network remains allowed.
    """
    p = hp.policy(principal)
    hp.canonical(config_path); hp.canonical(output)
    require(type(config_sha256) is str and len(config_sha256) == 64
            and all(c in '0123456789abcdef' for c in config_sha256), 'target_config_digest')
    require(len((output + '/egress.sock').encode()) <= 100, 'target_socket_path')
    cfg_path, out_path = PurePosixPath(config_path), PurePosixPath(output)
    require(not cfg_path.is_relative_to(out_path) and not out_path.is_relative_to(cfg_path),
            'target_config_output_overlap')
    before = restricted_kernel(p)
    library = net._load_seccomp()
    launch.close_ambient_fds()
    net._filter(library)
    require(restricted_kernel(p) == before, 'target_kernel_changed')
    raw = launch.file_bytes(config_path, p['brokerUid'], 0o600, 32768)
    require(hashlib.sha256(raw).hexdigest() == config_sha256, 'target_config_changed')
    data = unique_json(raw.decode('utf-8'))
    require(type(data) is dict and data.get('principal_contract') == p,
            'target_config_principal_mismatch')
    from provider_egress import BrokerConfig
    config = BrokerConfig(**data)
    # Reuse actual launcher deployment gates; no new directories or budgets.
    launch.deployment({'principalContract': p, 'config': config_path,
                       'configSha256': config_sha256, 'output': output})
    require(restricted_kernel(p) == before, 'target_kernel_changed')
    return config
