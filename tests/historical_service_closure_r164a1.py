"""Exact pre-R164 source/test custody; no current execution acceptance.

Original R163 receipts, logs and runner retain their original product and test
identities. R160 initial and final supervisor generations remain separate and
cannot select these archives. This standalone resolver does not alter an older
resolver, execute old code, or attest installed/kernel/native/model behavior.
"""
import hashlib
import json

BASE = '28a12e1b18a839a9489a0c463d904b8e9a46db03'
FOLDER = 'evidence/p2-service-closure-r164a1'
BINDING = FOLDER + '/historical-source-bindings.json'
R163 = 'evidence/p2-service-supervisor-r163a1/'
R160 = 'evidence/p2-service-control-r160a1/'
VOLUME = 'packages/claw-hermes/service_volume_supervisor.py'
EARLIER_R160_SHA = 'eb28de8c043aaf8105cfc54261ccd481424cf973de756ae4aea73753142f9d29'
FINAL_R160_SHA = '30fa40aa1ee1378f5136f27da04879677e457c9c56f983527833d2974bf4f8e8'
PARENT_SOURCES = {'packages/claw-hermes/gateway_supervised_service.py': {'path': 'evidence/p2-service-closure-r164a1/parent-packages__claw-hermes__gateway_supervised_service.py.txt',
                                                        'sha256': '9afadd091afd7c3dece4d3837bff75fcbb9d048ca5fbad6403c33a050111e0ed',
                                                        'size': 17161},
 'packages/claw-hermes/service_control_server.py': {'path': 'evidence/p2-service-closure-r164a1/parent-packages__claw-hermes__service_control_server.py.txt',
                                                    'sha256': '6b80555122e17561ffc1d588eab25d70445f5515c716ae31a4f3ccc8cb82ce31',
                                                    'size': 25125},
 'packages/claw-hermes/service_volume_supervisor.py': {'path': 'evidence/p2-service-closure-r164a1/parent-packages__claw-hermes__service_volume_supervisor.py.txt',
                                                       'sha256': '82d2439a3f22873267ae9f7606eef2b032f6203f2dab240c41c1c5bbd5b132df',
                                                       'size': 4504}}

PARENT_TESTS = {'tests/fixtures/service-control-server-r163a1.py': {'path': 'evidence/p2-service-closure-r164a1/parent-tests__fixtures__service-control-server-r163a1.py.txt',
                                                     'sha256': 'e7f2cb79c89f082ffdcadd5c7117571d85982c7d02b3daee9316cff365db5271',
                                                     'size': 4854},
 'tests/node/service-control-r163a1.mjs': {'path': 'evidence/p2-service-closure-r164a1/parent-tests__node__service-control-r163a1.mjs.txt',
                                           'sha256': 'e80a99f9e407d1048cff48d8b459a4e0d53e4e77b4c6b9e47d8ae5ffd8ee0b79',
                                           'size': 9791},
 'tests/service_supervisor_fixtures_r163a1.py': {'path': 'evidence/p2-service-closure-r164a1/parent-tests__service_supervisor_fixtures_r163a1.py.txt',
                                                 'sha256': 'df0fce876095274aa1139f4c404b69f60fe3d7da1012ef4e6c30176adc0e7172',
                                                 'size': 8242},
 'tests/test_service_control_cli_r163a1.py': {'path': 'evidence/p2-service-closure-r164a1/parent-tests__test_service_control_cli_r163a1.py.txt',
                                              'sha256': '1ddbd7048612761f2868adc101b500b63a8184c01405826b73c41b544f272648',
                                              'size': 5589},
 'tests/test_service_control_server_r163a1.py': {'path': 'evidence/p2-service-closure-r164a1/parent-tests__test_service_control_server_r163a1.py.txt',
                                                 'sha256': 'c25b7a03be4af031c66bcdc07677a8a4a13494a204dea1654d615a581eb42b0b',
                                                 'size': 35267},
 'tests/test_service_supervisor_r163a1.py': {'path': 'evidence/p2-service-closure-r164a1/parent-tests__test_service_supervisor_r163a1.py.txt',
                                             'sha256': '1d6f21fd64f40f65d90fc44a48f916ebd4d341d312636ff5f1da9353e752b29d',
                                             'size': 26468}}

PRESERVED_R163 = {'evidence/p2-service-supervisor-r163a1/baseline.json': {'sha256': '76e0ea0af0ea36476a3e5f5c0d7b83d5035fa89c247e56b666a809220c2ee6fb',
                                                         'size': 1281},
 'evidence/p2-service-supervisor-r163a1/focused-linux.json': {'sha256': '672e998c96847855eb7488b6cae468106c1c3c588fd704d1ad8532c2ef9eb351',
                                                              'size': 11725},
 'evidence/p2-service-supervisor-r163a1/focused-linux.log': {'sha256': 'c20794b8aedba050312000ceb9d9f795aa3a1809e43e1ca5f91e9d1df2f22e63',
                                                             'size': 119698},
 'evidence/p2-service-supervisor-r163a1/focused-runner.py': {'sha256': '0b9778344323ca9a91926abb0af3d945722010bec9bf0ad325768e9667538ecc',
                                                             'size': 10076},
 'evidence/p2-service-supervisor-r163a1/focused-windows.json': {'sha256': '5840c0933bdb6bf0b25fb1f3d627018c5077739e442590ce025fdf4415aec55c',
                                                                'size': 31766},
 'evidence/p2-service-supervisor-r163a1/focused-windows.log': {'sha256': '3ff80841b609bceed571fd1e40f4453c53902ff601b8fc6bd2f4bb4e47bbab0b',
                                                               'size': 126792},
 'evidence/p2-service-supervisor-r163a1/historical-source-bindings.json': {'sha256': 'cd13e6f35332ddc65aacef3a064f60be7f005b9ad62063266a79df3c89721dc0',
                                                                           'size': 2036},
 'evidence/p2-service-supervisor-r163a1/history-focused-linux.json': {'sha256': '233d7a75d68b8baa02ee23edd8ad27c109ddffb22a598cf5aa5a9cb0549a42b3',
                                                                      'size': 4052},
 'evidence/p2-service-supervisor-r163a1/history-focused-linux.log': {'sha256': '797fe86ed630048b4aab9cd6ae8aa6c3dc8c99a57d0dd21ca602828a40829be6',
                                                                     'size': 2075},
 'evidence/p2-service-supervisor-r163a1/parent-packages__claw-hermes__service_volume_supervisor.py.txt': {'sha256': '30fa40aa1ee1378f5136f27da04879677e457c9c56f983527833d2974bf4f8e8',
                                                                                                          'size': 3281},
 'evidence/p2-service-supervisor-r163a1/review-provenance.json': {'sha256': '874240cfeb39ad7b561a95f664d1548c8c21d6ac8b36d69f62727412acd4fe6c',
                                                                  'size': 19495},
 'evidence/p2-service-supervisor-r163a1/source-check.json': {'sha256': '2495d8dde27528be847fecf4e74a49f278eb753b17081d5ae6105ed1b46e3887',
                                                             'size': 9495},
 'evidence/p2-service-supervisor-r163a1/source-ci.json': {'sha256': '82a169dd23876ffdfe4160d841bbcecd6a7400805e897d908343ded2579e3078',
                                                          'size': 2118}}

PRESERVED_RESOLVERS = {'tests/historical_borrowed_service_r159a1.py': {'sha256': 'c46c392aa448c2ee04dfe261901cc5080635f4b29b1b8acc58fa007d60e6940c',
                                                 'size': 4432},
 'tests/historical_local_control_r158a1.py': {'sha256': '1b42d065201756a1aba705abbc498dbfa67c4d7fa88ad07577ebecfdb0bb7a5c',
                                              'size': 2304},
 'tests/historical_self_identity_r150a1.py': {'sha256': '51e79ab79981c52e23b7038e83ff4b26d4d51b06be9aed44955ea9631ef36712',
                                              'size': 2581},
 'tests/historical_service_profile_r161a1.py': {'sha256': '313374405e79a3081e9f432aa30b2a154bdd6c3911507709ed206b713c255a20',
                                                'size': 5030},
 'tests/historical_service_receiver_r162a1.py': {'sha256': '5422bad914d0d410e328f589c574df01a59c379d60204ddf7971d37aec6f7bdb',
                                                 'size': 4220},
 'tests/historical_service_supervisor_r163a1.py': {'sha256': 'ed690902e1a27585a5182455bba143964d0fe15b55703ba09ad587ae79e7d8bb',
                                                   'size': 4426},
 'tests/test_service_supervisor_history_r163a1.py': {'sha256': '5079247cca0442d7d488125f72dc15feecfb22ea19d0cdd130769907c18b9bf9',
                                                     'size': 8093}}

PRESERVED_R160 = {'evidence/p2-service-control-r160a1/focused-linux.json': {'sha256': '1f6abda42956eec4d2ffe92998c8678ec72876745a1098e65137d84e1008fda2',
                                                           'size': 2302},
 'evidence/p2-service-control-r160a1/focused-linux.log': {'sha256': '47e610216b45f4f8328254ec4a04c5556bdedda2e64411a725c6bd5a0e5df8b6',
                                                          'size': 12212},
 'evidence/p2-service-control-r160a1/focused-windows.json': {'sha256': '14e949756d282766194cf60d3b5eb4f4ad58e650cf60e39dfcb72ce8b2a17600',
                                                             'size': 2215},
 'evidence/p2-service-control-r160a1/focused-windows.log': {'sha256': 'e0339c2d6768051f4e5a13ecb35b653337c1b871b6b6c7a7ad7155602c39a4d9',
                                                            'size': 15179},
 'evidence/p2-service-control-r160a1/initial-focused-linux.json': {'sha256': '31dbf9ec183f85b03fb356209b502d9f46ed5d993d01aa15412f12bafc998ff0',
                                                                   'size': 2086},
 'evidence/p2-service-control-r160a1/initial-focused-linux.log': {'sha256': 'c904b44b006b5fbe8df8b9e3331b1d8c1337094d62a8250729413a00ae935294',
                                                                  'size': 11528}}

PARENTS = {**PARENT_SOURCES, **PARENT_TESTS}
R160_GENERATIONS = {R160 + 'initial-focused-linux.json': EARLIER_R160_SHA,
                    R160 + 'focused-linux.json': FINAL_R160_SHA,
                    R160 + 'focused-windows.json': FINAL_R160_SHA}


def binding_bytes():
    value = {'version': 1, 'base': BASE,
        'scope': 'historical_receipt_source_and_test_identity_only',
        'currentSourceAcceptance': False, 'nativeRerun': False,
        'sources': PARENT_SOURCES, 'testSources': PARENT_TESTS,
        'preservedR163Evidence': PRESERVED_R163,
        'preservedResolvers': PRESERVED_RESOLVERS,
        'preservedR160Evidence': PRESERVED_R160,
        'r160RecordSourceGenerations': R160_GENERATIONS}
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def _exact_bytes(root, name, expected):
    path = root / name
    if path.is_symlink():
        raise AssertionError('pre-R164 historical path changed')
    with path.open('rb') as stream:
        raw = stream.read(expected['size'] + 1)
    if len(raw) != expected['size'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise AssertionError('pre-R164 historical bytes changed: ' + name)
    return raw


def _binding(root):
    path = root / BINDING
    if path.is_symlink():
        raise AssertionError('pre-R164 binding path changed')
    expected = binding_bytes()
    with path.open('rb') as stream:
        raw = stream.read(len(expected) + 1)
    if raw != expected:
        raise AssertionError('unexpected pre-R164 historical source binding')


def archived_source(root, name, expected):
    """Only an exact named R163 generation selects an archive; no fallback."""
    if type(name) is not str or type(expected) is not str:
        return None
    row = PARENTS.get(name)
    if row is None or expected != row['sha256']:
        return None
    _binding(root)
    _exact_bytes(root, row['path'], row)
    return root / row['path']


def assert_preserved_evidence(root):
    """Validate prior bytes and generations without accepting current code."""
    _binding(root)
    saved = {}
    for mapping in (PRESERVED_R163, PRESERVED_RESOLVERS, PRESERVED_R160):
        for name, row in mapping.items():
            saved[name] = _exact_bytes(root, name, row)
    for platform in ('linux', 'windows'):
        name = R163 + 'focused-' + platform + '.json'
        record = json.loads(saved[name])
        for field, mapping in (('sourceHashes', PARENT_SOURCES), ('testHashes', PARENT_TESTS)):
            if any(record[field].get(source) != row['sha256'] for source, row in mapping.items()):
                raise AssertionError('R163 historical source/test generation changed')
        log = R163 + 'focused-' + platform + '.log'
        if (record['runnerSha256'] != PRESERVED_R163[R163 + 'focused-runner.py']['sha256']
                or record['logSha256'] != PRESERVED_R163[log]['sha256']
                or record['logBytes'] != PRESERVED_R163[log]['size']
                or record['testsRun'] != 721 or record['exitCode'] != 0
                or record['kernelConfinementTested'] is not False
                or record['nativeServiceStarted'] is not False
                or record['realModelCalls'] != 0 or record['realProviderCalls'] != 0):
            raise AssertionError('R163 historical receipt scope changed')
    check = json.loads(saved[R163 + 'source-check.json'])
    if check['volumeClosureIntegrated'] is not False or check['installedServiceAccepted'] is not False:
        raise AssertionError('R163 historical closure boundary changed')
    for name, generation in R160_GENERATIONS.items():
        record = json.loads(saved[name])
        if (record['sourceHashes'][VOLUME] != generation
                or record['logSha256'] != PRESERVED_R160[name[:-5] + '.log']['sha256']
                or record['exitCode'] != 0 or record['installedServiceAccepted'] is not False
                or record['realProviderCalls'] != 0):
            raise AssertionError('R160 historical generation or scope changed')
