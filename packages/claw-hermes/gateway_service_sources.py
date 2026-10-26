"""Explicit installed source selection for the opt-in borrowed HTTP service.

Historical prepared/finite/retained pins remain unchanged. The P2 candidate
must package and attest BOTH fixed configuration files below. Their digest pair
binds the selected source generation; it is not a signature, runtime grant or
permission to read a user-supplied manifest path.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[2]
SELECTION = 'config/hermes-borrowed-service-r159a1.json'
MANIFEST = 'config/borrowed-service-r159a1-sources.json'
REQUIRED = frozenset((
    'hermes_state.py', 'gateway/run_borrowed_admission.py',
    'gateway/platforms/api_server.py', 'gateway/platforms/api_server_borrowed.py',
    'gateway/platforms/api_server_prepared.py',
    'gateway/platforms/api_server_borrowed_transport.py',
    'gateway/platforms/api_server_metrics.py',
    'gateway/platforms/api_server_authority_runs.py',
    'agent/secret_sources/command.py',
))


class ServiceSourcesRejected(ValueError):
    pass


def require(value, reason):
    if not value:
        raise ServiceSourcesRejected(reason)


def _read(name, limit):
    path = ROOT / name
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            'service_source_configuration_path')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit, 'service_source_configuration_size')
    return raw


def _document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'service_source_duplicate_field')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)
    except (ValueError, UnicodeError, RecursionError):
        raise ServiceSourcesRejected('service_source_configuration_invalid') from None


@dataclass(frozen=True)
class ServiceSourceSelection:
    native_feature: str
    manifest_sha256: str
    selection_sha256: str


def load_selection():
    raw = _read(SELECTION, 16384)
    value = _document(raw)
    require(type(value) is dict and set(value) == {
        'schema', 'nativeFeature', 'sourceManifest', 'sourceManifestSha256'},
        'service_source_selection_fields')
    require(type(value['schema']) is int and value['schema'] == 1
            and value['sourceManifest'] == MANIFEST
            and type(value['nativeFeature']) is str
            and re.fullmatch('[a-f0-9]{40}', value['nativeFeature']) is not None
            and type(value['sourceManifestSha256']) is str
            and re.fullmatch('[a-f0-9]{64}', value['sourceManifestSha256']) is not None,
            'service_source_selection_invalid')
    return ServiceSourceSelection(value['nativeFeature'],
        value['sourceManifestSha256'], hashlib.sha256(raw).hexdigest())


def selected_manifest(selection):
    require(type(selection) is ServiceSourceSelection and load_selection() == selection,
            'service_source_selection_changed')
    raw = _read(MANIFEST, 1048576)
    require(hashlib.sha256(raw).hexdigest() == selection.manifest_sha256,
            'service_source_manifest_changed')
    value = _document(raw)
    require(type(value) is dict and set(value) == {'schema', 'nativeFeature', 'purpose', 'sources'}
            and type(value['schema']) is int and value['schema'] == 1
            and value['nativeFeature'] == selection.native_feature
            and type(value['purpose']) is str and 0 < len(value['purpose']) <= 1024,
            'service_source_manifest_fields')
    sources = value['sources']
    require(type(sources) is dict and REQUIRED <= set(sources) and len(sources) <= 4096,
            'service_source_manifest_closure')
    for name, digest in sources.items():
        path = PurePosixPath(name)
        require(type(name) is str and 0 < len(name) <= 1024
                and re.fullmatch('[A-Za-z0-9_./-]+',name) is not None
                and str(path) == name and not path.is_absolute()
                and '..' not in path.parts and '.' not in name.split('/')
                and path.suffix == '.py' and '\\' not in name
                and type(digest) is str and re.fullmatch('[a-f0-9]{64}', digest) is not None,
                'service_source_manifest_entry')
    return value
