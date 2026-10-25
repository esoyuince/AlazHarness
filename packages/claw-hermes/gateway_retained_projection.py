"""Fixed host/target views of one trusted retained-profile receipt.

This is not launch authority or a signature. Original VolumeBinding checks remain
in gateway_state_projection; layout checks retain exact cache/empty-registry/DB
identities. Only this helper derives a home-only view, after binding the original
receipt to the exact volume and principal. Neither original input is mutated.
"""
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
import os
from pathlib import Path
import gateway_retained_profile as retained


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _fields(volume, receipt, principal):
    from gateway_state_projection import VolumeBinding, TARGET, canonical, require
    require(type(volume) is VolumeBinding, 'retained_projection_volume_type')
    volume.__post_init__()
    retained.validate_receipt(receipt)
    require(type(principal) is dict and all(type(principal.get(k)) is int
            and principal[k] > 0 for k in ('gatewayUid', 'socketGroupGid')),
            'retained_projection_principal')
    source = str(canonical(volume.mountpoint) / 'profile')
    canonical(receipt.home)
    require(receipt.home in (source, TARGET), 'retained_projection_receipt_home')
    device = os.makedev(7, volume.loop_number)
    require(receipt.home_identity == (device, volume.profile_inode)
            and all(pair[0] == device for pair in receipt.database_identities),
            'retained_projection_volume_identity')
    return source


@dataclass(frozen=True)
class RetainedProjection:
    """Trusted per-run binding; a serialized copy is not runtime permission."""
    volume: object
    receipt: retained.RetainedProfileExpectation
    principal: dict = field(repr=False)
    _principal_json: str = field(init=False, repr=False)
    _bound_values: str = field(init=False, repr=False)

    def __post_init__(self):
        _fields(self.volume, self.receipt, self.principal)
        # Store an immutable value snapshot; do not trust mutability of a caller dict.
        object.__setattr__(self, '_principal_json', _canonical_json(self.principal))
        object.__setattr__(self, '_bound_values',
            _canonical_json((asdict(self.volume), asdict(self.receipt))))


def validate(mapping, volume, principal):
    from gateway_state_projection import require
    require(type(mapping) is RetainedProjection and mapping.volume is volume,
            'retained_projection_binding_changed')
    source = _fields(volume, mapping.receipt, principal)
    require(_canonical_json(principal) == mapping._principal_json
            and _canonical_json(mapping.principal) == mapping._principal_json,
            'retained_projection_principal_changed')
    require(_canonical_json((asdict(volume), asdict(mapping.receipt))) == mapping._bound_values,
            'retained_projection_receipt_or_volume_changed')
    return source


def inspect_view(mapping, volume, principal, *, view):
    """Read exact helper/layout metadata; never open SQLite or change files.

    Caller must already have validated live supervised-volume authority. This
    function does not claim mounting/pivot/isolation occurred. The derived receipt
    remains trusted caller data for the existing startup's mount/epoch/lease checks.
    """
    from gateway_state_projection import TARGET, require
    require(type(view) is str and view in ('host', 'target'), 'retained_projection_view')
    source = validate(mapping, volume, principal)
    home = source if view == 'host' else TARGET
    observed_receipt = replace(mapping.receipt, home=home)
    result = retained.layout.inspect_profile(Path(home), uid=principal['gatewayUid'],
        gid=principal['socketGroupGid'], device=mapping.receipt.home_identity[0],
        include_response=True, include_prepared=True, retained=observed_receipt)
    validate(mapping, volume, principal)
    # These explicit checks also guard a changed subordinate contract.
    require(result['profile'][:2] == mapping.receipt.home_identity
            and tuple(result[n][:2] for n in ('state.db','runs_idempotency.db','response_store.db'))
                == mapping.receipt.database_identities, 'retained_projection_snapshot_identity')
    return result, observed_receipt
