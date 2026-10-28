"""Read-only qualification of this process's actual isolated, site-enabled startup.

The parent invokes the fixed interpreter with -I -B separately as host root and
the gateway actor. Startup has already happened when this file begins: this
probe pins the observed source/cache inputs and origins, not prior effects or
the bytecode that the interpreter executed. It never launches another process.
"""
import sys


def _name(value):
    return (getattr(value, '__module__', type(value).__module__) + '.'
            + getattr(value, '__qualname__', type(value).__qualname__))


# Capture before this probe imports its own standard-library dependencies.
_INITIAL_MODULES = {
    name: {'file': getattr(module, '__file__', None),
           'cached': getattr(module, '__cached__', None),
           'origin': getattr(getattr(module, '__spec__', None), 'origin', None),
           'loader': _name(getattr(getattr(module, '__spec__', None), 'loader', None))}
    for name, module in tuple(sys.modules.items()) if name != '__main__'
}
_INITIAL_PATH = list(sys.path)
_INITIAL_META_PATH = [_name(value) for value in sys.meta_path]
_INITIAL_PATH_HOOKS = [_name(value) for value in sys.path_hooks]
_INITIAL_CUSTOMIZER_NAMES = sorted(vars(sys.modules['sitecustomize'])) if 'sitecustomize' in sys.modules else None

import argparse
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import re
import stat


PYTHON = '/usr/bin/python3.12'
PYTHON_SHA256 = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
PYTHON_BYTES = 8020928
CUSTOMIZER = '/etc/python3.12/sitecustomize.py'
CUSTOMIZER_SHA256 = '43d81125d92376b1a69d53a71126a041cc9a18d8080e92dea0a2ae23be138b1e'
CUSTOMIZER_SOURCE = (b'# install the apport exception handler if available\n'
                     b'try:\n    import apport_python_hook\nexcept ImportError:\n'
                     b'    pass\nelse:\n    apport_python_hook.install()\n')
SYSTEM_PATH = ['/usr/lib/python312.zip', '/usr/lib/python3.12',
               '/usr/lib/python3.12/lib-dynload',
               '/usr/local/lib/python3.12/dist-packages', '/usr/lib/python3/dist-packages']
SITE_DIRECTORIES = ['/usr/lib/python3.12/site-packages',
                    '/usr/local/lib/python3.12/dist-packages',
                    '/usr/lib/python3/dist-packages', '/usr/lib/python3.12/dist-packages']
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC'}
CONTEXTS = {
    'qa': (ENVIRONMENT, '/'),
    'worker': ({'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, '/'),
    'supervised': ({'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}, '/'),
    'preopen': ({'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}, '/opt/alaz-r167a1'),
}
CONTEXT_KEYS = ('root/qa', 'gateway/qa', 'root/worker', 'root/supervised', 'gateway/preopen')
PROTOCOL = 'alaz-r168a1-os-bootstrap-contract-v2'
MAX_JSON = 131072
MAX_FILE = 16 * 1024 * 1024
MAX_FILES = 128
USER_NAMESPACE = 'user:[4026531837]'


class BootstrapRejected(ValueError):
    pass


def require(value, reason):
    if not value:
        raise BootstrapRejected(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None,
            'bootstrap_digest')
    return value


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _root_owned(info):
    return (info.st_uid, info.st_gid) == (0, 0)


def _directory(path):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and _root_owned(info)
            and not info.st_mode & 0o022, 'bootstrap_untrusted_directory')
    return _stamp(info)


def _ancestry(path):
    return {str(parent): _directory(parent) for parent in path.parents}


def read_regular(path, maximum=MAX_FILE):
    """Read one held regular inode and recheck its path and trusted ancestry."""
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'bootstrap_regular_path')
    parents = _ancestry(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and _root_owned(before)
                and before.st_nlink == 1 and not before.st_mode & 0o022
                and not before.st_mode & 0o7000 and 0 < before.st_size <= maximum,
                'bootstrap_regular_metadata')
        pieces, count = [], 0
        while count <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - count))
            if not block:
                break
            pieces.append(block)
            count += len(block)
        raw = b''.join(pieces)
        require(len(raw) == before.st_size and _stamp(before) == _stamp(os.fstat(fd))
                and _stamp(before) == _stamp(path.lstat())
                and parents == _ancestry(path), 'bootstrap_file_changed')
        return raw, {'bytes': len(raw), 'sha256': sha256(raw)}
    finally:
        os.close(fd)


def _source_path(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//')
            and str(Path(value)) == value and '..' not in Path(value).parts,
            'bootstrap_source_path')
    path = Path(value)
    require(path.is_relative_to('/usr/lib/python3.12') or value == CUSTOMIZER,
            'bootstrap_ambient_origin')
    return path


def file_observation(value, *, optional=False):
    path = _source_path(value)
    try:
        original = path.lstat()
    except FileNotFoundError:
        require(optional, 'bootstrap_source_missing')
        parent = path.parent
        while not parent.exists():
            parent = parent.parent
        stamp, parents = _directory(parent), _ancestry(parent)
        require(not os.path.lexists(path) and _directory(parent) == stamp
                and _ancestry(parent) == parents, 'bootstrap_missing_path_changed')
        return None
    parents = _ancestry(path)
    target = path.resolve(strict=True)
    link = None
    if stat.S_ISLNK(original.st_mode):
        require(value == '/usr/lib/python3.12/sitecustomize.py' and str(target) == CUSTOMIZER
                and _root_owned(original), 'bootstrap_source_alias')
        link = os.readlink(path)
    else:
        require(target == path, 'bootstrap_source_alias')
    raw, entry = read_regular(target)
    require(_stamp(path.lstat()) == _stamp(original) and path.resolve(strict=True) == target
            and parents == _ancestry(path)
            and (link is None or os.readlink(path) == link), 'bootstrap_source_changed')
    if str(target) == CUSTOMIZER:
        require(raw == CUSTOMIZER_SOURCE and len(raw) == 155
                and entry['sha256'] == CUSTOMIZER_SHA256, 'bootstrap_customizer_changed')
    return {'canonicalPath': str(target), **entry}


def site_directory_observation(value):
    path = Path(value)
    try:
        before = _directory(path)
    except FileNotFoundError:
        # An absent site directory must have a trusted, stable existing parent.
        parent = path.parent
        while not parent.exists():
            parent = parent.parent
        stamp, parents = _directory(parent), _ancestry(parent)
        require(not os.path.lexists(path) and _directory(parent) == stamp
                and _ancestry(parent) == parents,
                'bootstrap_site_directory_changed')
        return {'present': False, 'pthFiles': []}
    parents = _ancestry(path)
    pth = []
    for count, item in enumerate(path.iterdir(), 1):
        require(count <= 4096, 'bootstrap_site_directory_bound')
        if item.name.endswith('.pth'):
            pth.append(item.name)
    require(not pth, 'bootstrap_pth_not_qualified')
    require(before == _directory(path) and parents == _ancestry(path),
            'bootstrap_site_directory_changed')
    return {'present': True, 'pthFiles': []}


def initial_snapshot():
    return {'modules': _INITIAL_MODULES, 'sysPath': _INITIAL_PATH,
            'metaPath': _INITIAL_META_PATH, 'pathHooks': _INITIAL_PATH_HOOKS,
            'sitecustomizeNames': _INITIAL_CUSTOMIZER_NAMES}


def validate_snapshot(snapshot):
    require(type(snapshot) is dict and set(snapshot) == {
        'modules', 'sysPath', 'metaPath', 'pathHooks', 'sitecustomizeNames'}, 'bootstrap_snapshot_fields')
    require(snapshot['sysPath'] == SYSTEM_PATH, 'bootstrap_sys_path')
    modules = snapshot['modules']
    require(type(modules) is dict and 1 <= len(modules) <= 256
            and 'site' in modules and 'sitecustomize' in modules
            and 'apport_python_hook' not in modules and '__main__' not in modules,
            'bootstrap_startup_modules')
    for name, value in modules.items():
        require(type(name) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_.]*', name)
                and type(value) is dict and set(value) == {'file', 'cached', 'origin', 'loader'},
                'bootstrap_module_record')
        require(type(value['loader']) is str and len(value['loader']) <= 160,
                'bootstrap_module_loader')
        for field in ('file', 'cached'):
            if value[field] is not None:
                _source_path(value[field])
        origin = value['origin']
        require(origin is None or type(origin) is str, 'bootstrap_module_origin')
        if origin not in (None, 'built-in', 'frozen'):
            _source_path(origin)
        require(value['file'] is not None or origin in ('built-in', 'frozen'),
                'bootstrap_unqualified_module')
    require(modules['sitecustomize']['file'] == '/usr/lib/python3.12/sitecustomize.py',
            'bootstrap_customizer_origin')
    for key in ('metaPath', 'pathHooks', 'sitecustomizeNames'):
        values = snapshot[key]
        require(type(values) is list and 0 < len(values) <= 64
                and all(type(v) is str and 0 < len(v) <= 160 for v in values),
                'bootstrap_import_mechanism')
    return snapshot


def startup_observation(snapshot):
    validate_snapshot(snapshot)
    names = {CUSTOMIZER, '/usr/lib/python3.12/site.py'}
    optional = set()
    for value in snapshot['modules'].values():
        for field in ('file', 'origin'):
            if value[field] not in (None, 'built-in', 'frozen'):
                names.add(value[field])
        if value['cached'] is not None:
            names.add(value['cached'])
            optional.add(value['cached'])
    require(len(names) <= MAX_FILES, 'bootstrap_file_inventory_bound')
    files = {name: file_observation(name, optional=name in optional) for name in sorted(names)}
    require(sum(row['bytes'] for row in files.values() if row is not None) <= 64 * 1024 * 1024,
            'bootstrap_total_bytes_bound')
    directories = {name: site_directory_observation(name) for name in SITE_DIRECTORIES}
    require(not os.path.lexists(SYSTEM_PATH[0]), 'bootstrap_python_zip_not_qualified')
    require(importlib.machinery.PathFinder.find_spec('apport_python_hook', snapshot['sysPath']) is None,
            'bootstrap_apport_available')
    return {'startup': snapshot, 'files': files, 'siteDirectories': directories,
            'apportSpec': None, 'pythonZipPresent': False}


def context_key(label, context):
    require(type(label) is str and type(context) is str
            and label + '/' + context in CONTEXT_KEYS, 'bootstrap_actor_context')
    return label + '/' + context


def contract_observations(value):
    require(type(value) is dict and set(value) == {'protocol', 'observations'}
            and value['protocol'] == PROTOCOL, 'bootstrap_contract_fields')
    observations = value['observations']
    require(type(observations) is dict and set(observations) == set(CONTEXT_KEYS),
            'bootstrap_contract_contexts')
    return observations


def validate_observation(observation):
    require(type(observation) is dict and set(observation) == {
        'startup', 'files', 'siteDirectories', 'apportSpec', 'pythonZipPresent'},
        'bootstrap_contract_observation_fields')
    validate_snapshot(observation['startup'])
    require(type(observation['files']) is dict and 1 <= len(observation['files']) <= MAX_FILES
            and type(observation['siteDirectories']) is dict
            and set(observation['siteDirectories']) == set(SITE_DIRECTORIES)
            and observation['apportSpec'] is None and observation['pythonZipPresent'] is False,
            'bootstrap_contract_observation_scope')
    return observation


def decode_contract(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_JSON, 'bootstrap_contract_bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'bootstrap_duplicate_field')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=pairs)
        require(canonical(value) == raw, 'bootstrap_contract_not_canonical')
    except BootstrapRejected:
        raise
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        raise BootstrapRejected('bootstrap_contract_json') from None
    for observation in contract_observations(value).values():
        validate_observation(observation)
    return value


def qualify(observation, contract, label, context):
    key = context_key(label, context)
    expected = contract_observations(contract)[key]
    require(canonical(observation) == canonical(expected),
            'bootstrap_observation_changed')
    return True


def execution_context(name, environment, cwd):
    require(type(name) is str and name in CONTEXTS, 'bootstrap_context_name')
    expected_environment, expected_cwd = CONTEXTS[name]
    require(type(environment) is dict and environment == expected_environment
            and cwd == expected_cwd, 'bootstrap_fixed_environment')
    return {'name': name, 'environment': dict(environment), 'cwd': cwd}


def actor(label, context='qa'):
    require(label in ('root', 'gateway'), 'bootstrap_actor_label')
    context_key(label, context)
    uid, gid = (0, 0) if label == 'root' else (23001, 23003)
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64'
            and sys.executable == PYTHON and sys.version_info[:3] == (3, 12, 3)
            and sys.flags.isolated == 1 and sys.flags.ignore_environment == 1
            and sys.flags.no_user_site == 1 and sys.flags.no_site == 0
            and sys.flags.dont_write_bytecode == 1 and sys.flags.optimize == 0,
            'bootstrap_fixed_interpreter')
    require(os.getresuid() == (uid,) * 3 and os.getresgid() == (gid,) * 3
            and os.getgroups() == [], 'bootstrap_actor_identity')
    execution_context(context, dict(os.environ), os.getcwd())
    require(os.readlink('/proc/self/ns/user') == USER_NAMESPACE
            and Path('/proc/self/uid_map').read_text().split() == ['0', '0', '4294967295']
            and Path('/proc/self/gid_map').read_text().split() == ['0', '0', '4294967295'],
            'bootstrap_initial_namespace')
    require(Path('/etc/alaz-p71c-lab-id').read_text().strip() == 'AlazHarness-D3B-P71C'
            and not Path('/mnt/c/Windows').exists(), 'bootstrap_dedicated_lab')
    return {'label': label, 'resUid': [uid] * 3, 'resGid': [gid] * 3, 'groups': []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor', required=True, choices=('root', 'gateway'))
    parser.add_argument('--context', default='qa', choices=tuple(CONTEXTS))
    parser.add_argument('--expected-source-sha256', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--expected-contract-sha256', required=True)
    args = parser.parse_args(argv)
    result = {'kind': 'R168A1_OS_BOOTSTRAP_QUALIFICATION', 'result': 'NOT_ACCEPTED',
              'scope': 'OS_STARTUP_SOURCE_AND_ORIGIN_ONLY',
              'actor': args.actor, 'startupCodeExecutedBeforeProbe': True,
              'preStartupEffectsObserved': False, 'loadedCodeObjectsAttested': False,
              'sourceBytesVerified': False, 'productImported': False, 'serviceStarted': False,
              'kernelEffectsAttempted': False, 'realModelCalls': 0, 'automaticRetry': False}
    try:
        source_pin, contract_pin = digest(args.expected_source_sha256), digest(args.expected_contract_sha256)
        who = actor(args.actor, args.context)
        source, source_row = read_regular(Path(__file__), MAX_JSON)
        require(source_row['sha256'] == source_pin, 'bootstrap_source_pin')
        contract_raw, contract_row = read_regular(Path(args.contract), MAX_JSON)
        require(contract_row['sha256'] == contract_pin, 'bootstrap_contract_pin')
        contract = decode_contract(contract_raw)
        _, python_row = read_regular(PYTHON)
        require(python_row == {'bytes': PYTHON_BYTES, 'sha256': PYTHON_SHA256}, 'bootstrap_python_pin')
        observed = startup_observation(initial_snapshot())
        qualify(observed, contract, args.actor, args.context)
        require(startup_observation(initial_snapshot()) == observed, 'bootstrap_inputs_changed')
        require(read_regular(Path(__file__), MAX_JSON)[0] == source
                and read_regular(Path(args.contract), MAX_JSON)[0] == contract_raw
                and read_regular(PYTHON)[1] == python_row, 'bootstrap_final_readback')
        result.update(result='PASS', actor=who, sourceBytesVerified=True,
                      sourceSha256=source_pin, contractSha256=contract_pin,
                      contractProtocol=PROTOCOL, contextKey=context_key(args.actor, args.context),
                      executionContext=execution_context(args.context, dict(os.environ), os.getcwd()),
                      python={'path': PYTHON, **python_row, 'version': [3, 12, 3],
                              'isolated': 1, 'noSite': 0, 'dontWriteBytecode': 1},
                      observation=observed)
        code = 0
    except BaseException as exc:
        result['reason'] = str(exc) if type(exc) is BootstrapRejected else 'bootstrap_probe_unavailable'
        code = 2
    raw = canonical(result)
    require(len(raw) <= MAX_JSON, 'bootstrap_output_bound')
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
