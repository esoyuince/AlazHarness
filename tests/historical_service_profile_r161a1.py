"""Exact pre-R161 bytes, plus separately frozen current source identity.

Historical lookup accepts only the named parent digest. It never chooses an
archive from a live file's contents or treats an old runtime result as current
acceptance. Current source pins are a distinct source-only custody check; the
R161 tests and CI still have to execute the selected current files.
"""

import hashlib
import json
import re


BASE = '5b7eba4d97f63623c20b51f476f4bf36ba6e7d94'
FOLDER = 'evidence/p2-service-profile-r161a1'
BINDING = FOLDER + '/historical-source-bindings.json'
SOURCES = {
    'packages/claw-hermes/execution_boundary.py': {
        'path': FOLDER + '/parent-packages__claw-hermes__execution_boundary.py.txt',
        'sha256': '8497da13e09b0a1906d1767ddab0956a70f4bd650fa0dc10dae6b50729959d96',
        'size': 23681,
    },
    'packages/claw-hermes/gateway_prepared_consumer.py': {
        'path': FOLDER + '/parent-packages__claw-hermes__gateway_prepared_consumer.py.txt',
        'sha256': 'cabedadec5180b815080bdd6817c0dd03c98615566f9fb7da1814e775b47d442',
        'size': 23102,
    },
    'packages/claw-hermes/gateway_store_startup.py': {
        'path': FOLDER + '/parent-packages__claw-hermes__gateway_store_startup.py.txt',
        'sha256': 'c9958d421e9038350ab90d078d85cc6bc30cb693d919e911ea291bc6ff8750b5',
        'size': 15954,
    },
    'packages/claw-hermes/gateway_state_projection.py': {
        'path': FOLDER + '/parent-packages__claw-hermes__gateway_state_projection.py.txt',
        'sha256': 'fff5f1040860607b7c4ac76a201a99c412f758b1c5b5c573482403d042009c74',
        'size': 18991,
    },
    'tests/test_self_identity_history_r150a1.py': {
        'path': FOLDER + '/parent-tests__test_self_identity_history_r150a1.py.txt',
        'sha256': '4c38dbc07d57f1911d1c4f896b19fe2af9331f2bbe9402f3f50840ddbde54e66',
        'size': 9025,
    },
    'tests/historical_borrowed_service_r159a1.py': {
        'path': FOLDER + '/parent-tests__historical_borrowed_service_r159a1.py.txt',
        'sha256': 'ddddde0ad1fc7e5c71f8a9358eedde021d1396f5db8b5bfff46e1beac56e7eca',
        'size': 4099,
    },
}

# Fixed only after the reviewed R161 product files were frozen. These are source
# identity pins, not a substitute for executing current tests and acceptance.
CURRENT_SOURCES = {
    'packages/claw-hermes/execution_boundary.py': '3448c8912278b9368ec52b72402cc297ae75fc4d3f92541e616f1dba493c5c62',
    'packages/claw-hermes/gateway_prepared_consumer.py': 'c31cfdb0cb27e91a596d8026ac4300b060e84572e68bc2084663988f5bf3bf59',
    'packages/claw-hermes/gateway_store_startup.py': 'df19918eaa16e6ed9c1cb679971810ba7d60089b8d6bebb91460323ac6290314',
    'packages/claw-hermes/gateway_state_projection.py': '1704cd025ce82779fabbeb6b39dc5ad501e06b0c3ef3b2dc645c09e2d95ccdba',
}
CURRENT_NAMES = frozenset(CURRENT_SOURCES)


def binding_bytes():
    value = {
        'version': 1,
        'base': BASE,
        'scope': 'historical_receipt_source_identity_only',
        'currentSourceAcceptance': False,
        'nativeRerun': False,
        'sources': SOURCES,
    }
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def archived_source(root, name, expected):
    row = SOURCES.get(name)
    if row is None or expected != row['sha256']:
        return None
    # The canonical complete record binds types and all paths as well as hashes.
    # Unknown generations return above without opening even this record.
    expected_record = binding_bytes()
    with (root / BINDING).open('rb') as stream:
        raw = stream.read(len(expected_record) + 1)
    if raw != expected_record:
        raise AssertionError('unexpected pre-R161 historical source bindings')
    path = root / row['path']
    if path.is_symlink():
        raise AssertionError('pre-R161 archived source path changed')
    with path.open('rb') as stream:
        payload = stream.read(row['size'] + 1)
    if len(payload) != row['size'] or hashlib.sha256(payload).hexdigest() != row['sha256']:
        raise AssertionError('pre-R161 archived source bytes changed')
    return path


def assert_current_sources(root, names=None):
    """Compare live files to reviewed fixed pins; no historical resolution."""
    if set(CURRENT_SOURCES) != CURRENT_NAMES or not all(
        type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None
        and value != '0' * 64 for value in CURRENT_SOURCES.values()
    ):
        raise AssertionError('R161 current-source pins not frozen')
    selected = CURRENT_NAMES if names is None else tuple(names)
    if not set(selected) <= CURRENT_NAMES:
        raise AssertionError('unlisted R161 current source')
    for name in selected:
        expected = CURRENT_SOURCES[name]
        if expected == SOURCES[name]['sha256']:
            raise AssertionError('R161 source generation did not advance: ' + name)
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise AssertionError('current product bytes changed: ' + name)
