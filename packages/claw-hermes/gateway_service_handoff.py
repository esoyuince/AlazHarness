"""Bounded service-profile data across a separately selected exec boundary.

This is not the finite retained protocol. The trusted caller supplies the home;
payload data never grants mounting, process launch, store or model authority.
The codec carries only config identity/size/digest, never config or secrets.
"""
from dataclasses import asdict, dataclass, fields
import json
import os

import gateway_retained_handoff as common
import gateway_service_profile as profile
from gateway_service_sources import ServiceSourceSelection

MAX_BYTES = 16384
PROTOCOL = 'alaz-service-startup-v1'
TARGET = common.TARGET
HandoffRejected = common.HandoffRejected
require = common.require
preopen = common.preopen
response = common.response


@dataclass(frozen=True)
class ServiceStartup:
    state: preopen.live.PreparedStoreExpectation
    response: response.PreparedResponseExpectation
    service: profile.ServiceProfileExpectation


def validate(value, *, expected_home):
    home = common._home(expected_home)
    require(type(value) is ServiceStartup, 'service_handoff_record_type')
    require(type(value.state) is preopen.live.PreparedStoreExpectation
            and type(value.response) is response.PreparedResponseExpectation
            and type(value.service) is profile.ServiceProfileExpectation,
            'service_handoff_record_members')
    value.state.__post_init__()
    value.response.__post_init__()
    profile.validate_expectation(value.service)
    response._pair(value.response, value.state)
    common._home(value.service.home)
    require(value.service.home == home, 'service_handoff_home_mismatch')
    require(value.state.journal_mode == 'delete'
            and value.service.epoch == value.state.epoch
            and value.service.instance_id == value.state.instance_id,
            'service_handoff_previous_epoch_or_instance')
    identities = (value.state.state_identity, value.state.replay_identity,
                  value.response.response_identity)
    require(value.service.database_identities == identities
            and value.service.home_identity[0] == identities[0][0],
            'service_handoff_store_or_profile_identity')
    return value


def _raw_service(value):
    common._keys(value, (f.name for f in fields(profile.ServiceProfileExpectation)))
    value = dict(value)
    selection = value['selection']
    common._keys(selection, (f.name for f in fields(ServiceSourceSelection)))
    value['selection'] = ServiceSourceSelection(**selection)
    value['home_identity'] = common._pair(value['home_identity'])
    value['config_identity'] = common._pair(value['config_identity'])
    identities = value['database_identities']
    require(type(identities) is list and len(identities) == 3,
            'service_handoff_three_identities')
    value['database_identities'] = tuple(common._pair(v) for v in identities)
    return profile.ServiceProfileExpectation(**value)


def encode(value, *, expected_home):
    try:
        validate(value, expected_home=expected_home)
        raw = json.dumps({'protocol': PROTOCOL, 'state': asdict(value.state),
                          'response': asdict(value.response), 'service': asdict(value.service)},
                         sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                         allow_nan=False).encode('utf-8')
        require(0 < len(raw) <= MAX_BYTES, 'service_handoff_size')
        return raw
    except HandoffRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, RuntimeError):
        raise HandoffRejected('service_handoff_encode_invalid') from None


def decode(raw, *, expected_home):
    try:
        common._home(expected_home)
        require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES,
                'service_handoff_size_or_type')
        wire = common._json(raw.decode('utf-8', 'strict'))
        common._keys(wire, ('protocol', 'state', 'response', 'service'))
        require(type(wire['protocol']) is str and wire['protocol'] == PROTOCOL,
                'service_handoff_protocol')
        value = ServiceStartup(preopen._expectation(wire['state']),
                               response._expected(wire['response']), _raw_service(wire['service']))
        validate(value, expected_home=expected_home)
        require(encode(value, expected_home=expected_home) == raw, 'service_handoff_noncanonical')
        return value
    except HandoffRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, RuntimeError):
        raise HandoffRejected('service_handoff_decode_invalid') from None


def encode_projected(projection, state, reply):
    """Require the caller's completed service projection, without authenticating JSON."""
    require(type(projection) is dict
            and type(projection.get('version')) is int and projection['version'] == 1
            and type(projection.get('pid')) is int and projection['pid'] == os.getpid()
            and type(projection.get('stateDirectoryCount')) is int and projection['stateDirectoryCount'] == 1
            and type(projection.get('ambientHostDirectoriesBound')) is int and projection['ambientHostDirectoriesBound'] == 0
            and projection.get('hostUserNamespacePreserved') is True
            and projection.get('legacyIpcV2Activated') is False
            and projection.get('fullD3BAccepted') is False
            and projection.get('state') == 'confined_state_profile'
            and projection.get('profile') == TARGET
            and projection.get('profileLayout') == profile.SERVICE_LAYOUT
            and projection.get('serviceProjectionVerified') is True
            and projection.get('persistentProfileProjected') is True
            and projection.get('rootPrivilegesDropped') is True
            and projection.get('profileOwnershipAcquired') is False
            and projection.get('nativeHermesStoresOpened') is False
            and 'retainedProfile' not in projection
            and projection.get('retainedProjectionVerified', False) is False,
            'service_handoff_projection_incomplete')
    value = ServiceStartup(state, reply, projection.get('serviceProfile'))
    raw = encode(value, expected_home=TARGET)
    require(type(projection.get('profileDevice')) is int
            and type(projection.get('profileInode')) is int
            and (projection['profileDevice'], projection['profileInode']) == value.service.home_identity,
            'service_handoff_projection_identity')
    return raw


def decode_projected(raw):
    return decode(raw, expected_home=TARGET)
