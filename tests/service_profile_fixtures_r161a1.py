"""Service layout fixtures: real files/FDs, fake DB bytes, no native runtime.

The old fixture doubles only owner IDs under root CI and POSIX metadata under
Windows. Its pinned SOUL/cache content and ordinary Linux file checks remain.
"""
import hashlib
import json

import test_gateway_native_layout as original
import gateway_service_profile as service


DEFAULT_CONFIG = {'model': {'default': 'fixture-model'}, 'plugins': {'enabled': False}}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def set_up_profile(case, *, config=None):
    original.LayoutFixtures.setUp(case)
    (case.home / 'response_store.db').write_bytes(b'r' * 512)
    for name in ('platforms', 'platforms/pairing', 'runtime', 'cache/documents'):
        (case.home / name).mkdir(mode=0o700)
    for name in ('auth.lock', 'runtime/active_sessions.lock'):
        (case.home / name).write_bytes(b'')
    (case.home / 'runtime/active_sessions.json').write_bytes(b'{"entries":[]}')
    case.discovery = {'/trusted-fixture/tools/file_tools.py': [123, 456, True]}
    discovery = canonical(case.discovery)
    (case.home / 'cache/tool_discovery_cache.json').write_bytes(discovery)
    case.config_bytes = canonical(DEFAULT_CONFIG if config is None else config)
    (case.home / service.CONFIG_NAME).write_bytes(case.config_bytes)
    for path in case.home.rglob('*'):
        if path.is_file():
            path.chmod(0o600)
    identity = lambda path: (path.stat().st_dev, path.stat().st_ino)
    case.selection = service.sources.load_selection()
    case.expectation = service.ServiceProfileExpectation(
        schema=1, selection=case.selection, home=str(case.home),
        home_identity=identity(case.home),
        database_identities=tuple(identity(case.home / name) for name in service._DATABASES),
        epoch=1, instance_id='service-fixture-previous',
        discovery_sha256=hashlib.sha256(discovery).hexdigest(),
        config_identity=identity(case.home / service.CONFIG_NAME),
        config_size=len(case.config_bytes),
        config_sha256=hashlib.sha256(case.config_bytes).hexdigest())


def arguments(case, expectation=None):
    return {'uid': case.uid, 'gid': case.gid, 'device': case.device,
            'expectation': case.expectation if expectation is None else expectation}
