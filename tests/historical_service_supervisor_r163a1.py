"""One exact pre-R163 supervisor generation and unchanged tracked R160 evidence.

The final R160 focused records name this parent generation. The earlier R160
record names a different generation and must never select this archive. This
standalone helper does not change an older resolver or attest current service
execution, installed sources, kernel state, or model/provider behavior.
"""
import hashlib
import json


BASE = 'dc1ccb5ecf4e9741f6fd828a03e8ebed7f9497b7'
FOLDER = 'evidence/p2-service-supervisor-r163a1'
BINDING = FOLDER + '/historical-source-bindings.json'
SOURCE = 'packages/claw-hermes/service_volume_supervisor.py'
PARENT = {
    'path': FOLDER + '/parent-packages__claw-hermes__service_volume_supervisor.py.txt',
    'sha256': '30fa40aa1ee1378f5136f27da04879677e457c9c56f983527833d2974bf4f8e8',
    'size': 3281,
}
EARLIER_SHA = 'eb28de8c043aaf8105cfc54261ccd481424cf973de756ae4aea73753142f9d29'
R160 = 'evidence/p2-service-control-r160a1/'
RECORDS = {
    R160 + 'focused-linux.json': {
        'sha256': '1f6abda42956eec4d2ffe92998c8678ec72876745a1098e65137d84e1008fda2',
        'size': 2302,
    },
    R160 + 'focused-windows.json': {
        'sha256': '14e949756d282766194cf60d3b5eb4f4ad58e650cf60e39dfcb72ce8b2a17600',
        'size': 2215,
    },
    R160 + 'initial-focused-linux.json': {
        'sha256': '31dbf9ec183f85b03fb356209b502d9f46ed5d993d01aa15412f12bafc998ff0',
        'size': 2086,
    },
}
LOGS = {
    R160 + 'focused-linux.log': {
        'sha256': '47e610216b45f4f8328254ec4a04c5556bdedda2e64411a725c6bd5a0e5df8b6',
        'size': 12212,
    },
    R160 + 'focused-windows.log': {
        'sha256': 'e0339c2d6768051f4e5a13ecb35b653337c1b871b6b6c7a7ad7155602c39a4d9',
        'size': 15179,
    },
    R160 + 'initial-focused-linux.log': {
        'sha256': 'c904b44b006b5fbe8df8b9e3331b1d8c1337094d62a8250729413a00ae935294',
        'size': 11528,
    },
}
RECORD_GENERATIONS = {
    R160 + 'focused-linux.json': PARENT['sha256'],
    R160 + 'focused-windows.json': PARENT['sha256'],
    R160 + 'initial-focused-linux.json': EARLIER_SHA,
}


def binding_bytes():
    value = {
        'version': 1,
        'base': BASE,
        'scope': 'historical_receipt_source_identity_only',
        'currentSourceAcceptance': False,
        'nativeRerun': False,
        'sources': {SOURCE: PARENT},
        'preservedRecords': RECORDS,
        'preservedLogs': LOGS,
        'recordSourceGenerations': RECORD_GENERATIONS,
    }
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def _binding(root):
    expected = binding_bytes()
    path = root / BINDING
    if path.is_symlink():
        raise AssertionError('pre-R163 binding path changed')
    with path.open('rb') as stream:
        raw = stream.read(len(expected) + 1)
    if raw != expected:
        raise AssertionError('unexpected pre-R163 historical source binding')


def _exact_bytes(root, name, expected):
    path = root / name
    if path.is_symlink():
        raise AssertionError('pre-R163 historical path changed')
    with path.open('rb') as stream:
        raw = stream.read(expected['size'] + 1)
    if len(raw) != expected['size'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise AssertionError('pre-R163 historical bytes changed: ' + name)
    return raw


def archived_source(root, name, expected):
    # Current/unknown/earlier generations do not require the new archive files.
    if (type(name) is not str or type(expected) is not str
            or name != SOURCE or expected != PARENT['sha256']):
        return None
    _binding(root)
    _exact_bytes(root, PARENT['path'], PARENT)
    return root / PARENT['path']


def assert_preserved_evidence(root):
    """Check the six tracked R160 files without rebasing their source identities."""
    _binding(root)
    records = {name: json.loads(_exact_bytes(root, name, row)) for name, row in RECORDS.items()}
    for name, row in LOGS.items():
        _exact_bytes(root, name, row)
    for name, record in records.items():
        if (record['sourceHashes'][SOURCE] != RECORD_GENERATIONS[name]
                or record['logSha256'] != LOGS[name[:-5] + '.log']['sha256']
                or record['exitCode'] != 0 or record['installedServiceAccepted'] is not False
                or record['realProviderCalls'] != 0):
            raise AssertionError('R160 historical receipt generation or scope changed')
