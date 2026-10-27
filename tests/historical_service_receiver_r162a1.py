"""Exact pre-R162 service runtime bytes and separate current source custody.

The nine original R159 evidence records are retained byte-exact. Selecting a
parent archive proves only historical source identity, never current execution
or installed-service acceptance. Current/unknown digests cannot use the archive.
"""
import hashlib
import json
import re

BASE = 'b56b9b321002a5bb8696fcae27edcfc92c28df1c'
FOLDER = 'evidence/p2-service-receiver-r162a1'
BINDING = FOLDER + '/historical-source-bindings.json'
RUNTIME = 'packages/claw-hermes/gateway_service_runtime.py'
PARENT = {
    'path': FOLDER + '/parent-packages__claw-hermes__gateway_service_runtime.py.txt',
    'sha256': '7936c0d964fcefcdb6d92c6c5c38ed4abcbbef421dcf731a47e8b80c69359a92',
    'size': 17305,
}
CURRENT_SHA = '109bc6eef0a8507f9149e83785e9b51f270b4689e45dd96830cf57aae2195fea'
CURRENT_SIZE = 17626
PRIOR_RECEIPTS = {
    'evidence/p2-borrowed-service-r159a1/checks/generation-repair-windows-confirmed.json':
        '18731b0f426873bcf10dea0db224bc2096e8276e4f3d0dae5acad28c8475cdee',
    'evidence/p2-borrowed-service-r159a1/checks/generation-repair-windows.json':
        'c65297780ee2f6b9cf78b0ace3ea80224395b899e8ad7dfb27024bb5a07277b8',
    'evidence/p2-borrowed-service-r159a1/checks/receipt-repair-windows.json':
        '9b30b306f737b5e4af24ebd41c04b819d9bb6a813236efa7f3225516d4b3b6e9',
    'evidence/p2-borrowed-service-r159a1/checks/windows-focused-command.json':
        '496a22c0649a389be213a4a4efdf766ab6d5fd965655f52f8ecc2fee61a93dc7',
    'evidence/p2-borrowed-service-r159a1/checks/windows-focused.json':
        '555db7ffb9d2ffc872a9562686901ae49d38c08ae959a4d85a09214613ccac47',
    'evidence/p2-borrowed-service-r159a1/ci-repair-review.json':
        '9e6aa5f579bac23aa008b9b9cc1ca792318a9614952f8abc68e23e2b9c501c35',
    'evidence/p2-borrowed-service-r159a1/final-source-docs-review.json':
        'b38396f13202a1febd5ea8a33c91bfbd45082d66526989ba950840ce7cd76520',
    'evidence/p2-borrowed-service-r159a1/host-service-tests.json':
        '672f0c61760f2903cad31722e9039516611ccf9ad3ee9109c3484ffd85893a29',
    'evidence/p2-borrowed-service-r159a1/source-custody.json':
        '9ea0fe27d590a89c2559feb6a9f41e4a34efa2574226783c18560a07f1eb9661',
}


def binding_bytes():
    value = {'version': 1, 'base': BASE,
        'scope': 'historical_receipt_source_identity_only',
        'currentSourceAcceptance': False, 'nativeRerun': False,
        'sources': {RUNTIME: PARENT}, 'priorReceiptHashes': PRIOR_RECEIPTS}
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def archived_source(root, name, expected):
    if (type(name) is not str or type(expected) is not str
            or name != RUNTIME or expected != PARENT['sha256']):
        return None
    expected_binding = binding_bytes()
    with (root / BINDING).open('rb') as stream:
        raw = stream.read(len(expected_binding) + 1)
    if raw != expected_binding:
        raise AssertionError('unexpected pre-R162 historical source binding')
    path = root / PARENT['path']
    if path.is_symlink():
        raise AssertionError('pre-R162 archive path changed')
    with path.open('rb') as stream:
        raw = stream.read(PARENT['size'] + 1)
    if len(raw) != PARENT['size'] or hashlib.sha256(raw).hexdigest() != PARENT['sha256']:
        raise AssertionError('pre-R162 archived source bytes changed')
    return path


def assert_current_source(root):
    if (type(CURRENT_SHA) is not str or re.fullmatch('[a-f0-9]{64}', CURRENT_SHA) is None
            or CURRENT_SHA in ('0' * 64, PARENT['sha256'])
            or type(CURRENT_SIZE) is not int or CURRENT_SIZE <= 0):
        raise AssertionError('R162 current source pin not frozen')
    with (root / RUNTIME).open('rb') as stream:
        raw = stream.read(CURRENT_SIZE + 1)
    if len(raw) != CURRENT_SIZE or hashlib.sha256(raw).hexdigest() != CURRENT_SHA:
        raise AssertionError('current R162 service runtime bytes changed')


def assert_prior_receipts(root):
    for name, expected in PRIOR_RECEIPTS.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise AssertionError('original R159 receipt bytes changed: ' + name)
