"""Explicit host/target binding for one selected service profile.

The caller supplies the original supervised volume and trusted expectation.
Only the home path is remapped; config/source/store identities stay unchanged.
This data mapping neither mounts anything nor acquires a lease or authorizes a
service, model, restart or provider call. All original volume guards still run.
"""
from dataclasses import asdict, dataclass, field, replace
import json
import os
from pathlib import Path

import gateway_service_profile as profile


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _fields(volume, receipt, principal):
    from gateway_state_projection import VolumeBinding, TARGET, canonical, require
    require(type(volume) is VolumeBinding, 'service_projection_volume_type')
    volume.__post_init__()
    profile.validate_expectation(receipt)
    require(type(principal) is dict and all(type(principal.get(k)) is int
            and principal[k] > 0 for k in ('gatewayUid', 'socketGroupGid')),
            'service_projection_principal')
    source = str(canonical(volume.mountpoint) / 'profile')
    canonical(receipt.home)
    require(receipt.home in (source, TARGET), 'service_projection_receipt_home')
    device = os.makedev(7, volume.loop_number)
    require(receipt.home_identity == (device, volume.profile_inode)
            and all(pair[0] == device for pair in
                    (*receipt.database_identities, receipt.config_identity)),
            'service_projection_volume_identity')
    return source


@dataclass(frozen=True)
class ServiceProjection:
    volume: object
    receipt: profile.ServiceProfileExpectation
    principal: dict = field(repr=False)
    _principal_json: str = field(init=False, repr=False)
    _bound_values: str = field(init=False, repr=False)

    def __post_init__(self):
        _fields(self.volume, self.receipt, self.principal)
        object.__setattr__(self, '_principal_json', _json(self.principal))
        object.__setattr__(self, '_bound_values',
                           _json((asdict(self.volume), asdict(self.receipt))))


def validate(mapping, volume, principal):
    from gateway_state_projection import require
    require(type(mapping) is ServiceProjection and mapping.volume is volume,
            'service_projection_binding_changed')
    source = _fields(volume, mapping.receipt, principal)
    require(_json(principal) == mapping._principal_json
            and _json(mapping.principal) == mapping._principal_json,
            'service_projection_principal_changed')
    require(_json((asdict(volume), asdict(mapping.receipt))) == mapping._bound_values,
            'service_projection_receipt_or_volume_changed')
    return source


def inspect_view(mapping, volume, principal, *, view):
    """Recheck one explicit view without creating files or opening stores."""
    from gateway_state_projection import TARGET, require
    require(type(view) is str and view in ('host', 'target'), 'service_projection_view')
    source = validate(mapping, volume, principal)
    home = source if view == 'host' else TARGET
    receipt = replace(mapping.receipt, home=home)
    observed = profile.inspect_profile(Path(home), uid=principal['gatewayUid'],
        gid=principal['socketGroupGid'], device=receipt.home_identity[0], expectation=receipt)
    validate(mapping, volume, principal)
    require(observed['profile'][:2] == receipt.home_identity
            and tuple(observed[n][:2] for n in
                      ('state.db', 'runs_idempotency.db', 'response_store.db'))
                == receipt.database_identities
            and observed['config.yaml'][:2] == receipt.config_identity
            and observed['config.yaml'][6] == receipt.config_size,
            'service_projection_snapshot_identity')
    return observed, receipt
