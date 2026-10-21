"""Explicit composition of existing network and filesystem launch restrictions.

This is NOT a scheduler, complete sandbox, budget authority, or model-facing
permission issuer. The trusted launcher supplies the contract and command.
Both restrictions must succeed in the same fresh process; never fall back.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import credential_guard as filesystem
import linux_netns as network

FIELDS = {'version', 'enabled', 'launchId', 'network', 'filesystem', 'commandSha256'}

class CombinedGuardRejected(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise CombinedGuardRejected(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode('utf-8')).hexdigest()


def command_digest(command):
    require(type(command) is list and 1 <= len(command) <= 64, 'combined_command_count')
    require(all(type(v) is str and '\x00' not in v and len(v.encode('utf-8')) <= 4096
                for v in command), 'combined_command_arguments')
    require(sum(len(v.encode('utf-8')) for v in command) <= 16384, 'combined_command_bytes')
    require(bool(command[0]), 'combined_executable_missing')
    return digest(command)


def validate_contract(value):
    require(type(value) is dict and set(value) in (FIELDS, FIELDS | {'ipc'}), 'combined_contract_fields')
    require(type(value['version']) is int and value['version'] == 1, 'combined_contract_version')
    require(value['enabled'] is True and value['network'] == 'loopback_only',
            'combined_both_layers_required')
    require(type(value['launchId']) is str and
            re.fullmatch(r'[a-zA-Z0-9_.-]{4,80}', value['launchId']) is not None,
            'combined_launch_identity')
    require(type(value['commandSha256']) is str and
            re.fullmatch(r'[a-f0-9]{64}', value['commandSha256']) is not None,
            'combined_command_digest')
    fs=filesystem.validate_policy(value['filesystem'])
    if 'ipc' in value:
        import ipc_view
        ipc_view.validate(value['ipc'],fs)
    return {**value, 'filesystem':fs}


def enforce(contract, command):
    """Irreversible. Any exception requires immediate caller exit without exec."""
    value = validate_contract(contract)
    require(command_digest(command) == value['commandSha256'], 'combined_command_mismatch')
    # Namespace setup must precede Landlock: it needs temporary /proc writes,
    # and then irrevocably drops capabilities and installs inherited seccomp.
    net = network.enter(filesystem_view={'ipc':value['ipc'],'filesystem':value['filesystem']}) if 'ipc' in value else network.enter()
    require(net.get('mode') == 'linux_netns_loopback_only' and
            net.get('after', {}).get('pid') == os.getpid(), 'combined_network_receipt')
    if 'ipc' in value:
        mount=net.get('filesystemView',{})
        require(mount.get('state')=='projected' and mount.get('oldRootDetached') is True
                and mount.get('explicitHostSocketCount')==1,'combined_ipc_receipt')
    fs = filesystem.apply(value['filesystem'])
    require(fs.get('state') == 'enforced' and fs.get('noNewPrivs') is True and
            fs.get('protectedReadDenials') == len(value['filesystem']['protected']),
            'combined_filesystem_receipt')
    return {
        'version':1, 'state':'enforced', 'launchId':value['launchId'], 'pid':os.getpid(),
        'contractSha256':digest(value), 'commandSha256':value['commandSha256'],
        'order':['network', 'filesystem'], 'network':net, 'filesystem':fs,
        'scope':'same-process direct network and filesystem-open restrictions',
        'completeD3B':False, 'unixSocketAuthorityIsolated':False,
        'independentBrokerBudgetAuthority':False, 'separateHostUid':False,
        'targetExecutionVerified':False, 'fallback':False,
        'pathnameIpcView':net.get('filesystemView'),
        'explicitBrokerMountOnly':'ipc' in value}
