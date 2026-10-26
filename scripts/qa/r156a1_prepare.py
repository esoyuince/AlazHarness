"""Freeze real R156 inputs and render fixed reviewed operators; never run them.

The original R154/R155 sources remain unchanged. Rendered operators are ordinary
source files with explicit fixed bindings, not modules whose globals are patched
at runtime. Installation preparation requires a complete, verified candidate.
Native acceptance preparation additionally requires an actual installation
receipt; no placeholder commit, digest or successful acceptance is generated.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
INSTALL_TEMPLATE = 'scripts/qa/r154a1_install_candidate.py'
INSTALL_TEMPLATE_SHA = '06755f6d866a30b208c80ce23dab30e99326077d0b632211b42d9f6dcac18a14'
BUILDER_SHA = '7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b'
INSTALLER_SHA = 'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
DESTINATION = '/opt/alaz-r156a1'
INSTALL_INPUT = '/opt/alaz-r156a1-install-input'
ACCEPT_INPUT = '/opt/alaz-r156a1-accept-input'
DEPENDENCIES = '/opt/alaz-f126c1a6/dependencies'
MAX_SOURCE = 4 * 1024 * 1024
MAX_ARCHIVE = 64 * 1024 * 1024
ACCEPT_TEMPLATES = 'scripts/qa/r156a1_acceptance_templates.py'
ACCEPT_TEMPLATES_SHA = 'e2aa6b659e2926222be552dfa47835b6ef67aaa1c0296104b6c1a994c9d794f0'
SEED_TEMPLATES = {
    'scripts/bootstrap_retained_profile.py': '2c004f6a7154d95af216517c867f1e3cafd63a05e05838f65752eca1b89c5f01',
    'scripts/qa/r155a1_ordinary_seed.py': 'b06ffe888e75406721da111c6e8d58941a2b01004bf0b544981195a364769e6f',
    'scripts/qa/r155a1_seed_child.py': 'fe598ba4e09e10b534d4f74de2d16246228e770eb00fd273d92c40ccf665cb12',
    'scripts/qa/r155a1_linux_accept.py': 'cc80c882fc0ada181afe86f4151e8296db13c2cd922937aa3189be9f5b71933d',
    'scripts/qa/r155a1_linux_transport.py': 'a08345f8eaa6fe179d973d28159949d5d405c4996f60ecc79bd1bc041d4119a6',
    'scripts/qa/r155a1_accept.py': '113ec74d47509cefc875a19dfa8b34b465db864ead3edd04c40b3d9d7e9fc4ef',
}
FINITE_ENTRY = 'scripts/qa/r156a1_finite_assert.py'


class PreparationRejected(ValueError):
    """Bounded diagnostic; no file contents or supplied payload are exposed."""


def require(ok, reason):
    if not ok:
        raise PreparationRejected(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def digest(value, length=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value),
            'preparation_exact_digest_required')
    return value


def path_text(value):
    require(type(value) is str and 0 < len(value) <= 4096
            and not any(c in value for c in '\x00\r\n'), 'preparation_path_text')
    return value


def read_file(path, maximum=MAX_SOURCE):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)),
            'preparation_source_alias')
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 0 < before.st_size <= maximum, 'preparation_regular_bounded_source')
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink,
                       s.st_size, s.st_mtime_ns)
    require(len(raw) == before.st_size and stamp(before) == stamp(after)
            and stamp(before) == stamp(path.stat()), 'preparation_source_changed')
    return raw


def pinned(path, expected, maximum=MAX_SOURCE):
    raw = read_file(path, maximum)
    require(sha(raw) == digest(expected), 'preparation_template_changed')
    return raw


def parse(raw):
    def unique(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'preparation_duplicate_json_key')
            result[key] = value
        return result
    def no_constant(_):
        raise PreparationRejected('preparation_nonfinite_json')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=no_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise PreparationRejected('preparation_invalid_json') from None


def _tree(raw):
    try:
        return ast.parse(raw.decode('utf-8'))
    except (ValueError, SyntaxError, UnicodeError):
        raise PreparationRejected('preparation_template_syntax') from None


def _replace_nodes(raw, edits):
    """Replace reviewed AST node spans while preserving every other source byte."""
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    ranges = []
    for node, replacement in edits:
        require(type(replacement) is bytes and hasattr(node, 'end_lineno'),
                'preparation_edit_span')
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        ranges.append((start, end, replacement))
    ranges.sort()
    require(all(left[1] <= right[0] for left, right in zip(ranges, ranges[1:])),
            'preparation_overlapping_edits')
    for start, end, replacement in reversed(ranges):
        raw = raw[:start] + replacement + raw[end:]
    _tree(raw)
    return raw


def _assign(raw, replacements):
    found = {}
    for node in _tree(raw).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in replacements):
            name = node.targets[0].id
            require(name not in found, 'preparation_duplicate_assignment')
            found[name] = node.value
    require(set(found) == set(replacements), 'preparation_assignment_missing')
    return _replace_nodes(raw, [(found[name], value.encode('utf-8'))
                               for name, value in replacements.items()])


def _literals(raw, replacements):
    edits = []
    counts = {key: 0 for key in replacements}
    for node in ast.walk(_tree(raw)):
        if not isinstance(node, ast.Constant):
            continue
        key = (type(node.value), node.value)
        if key in replacements:
            edits.append((node, repr(replacements[key]).encode('utf-8')))
            counts[key] += 1
    require(all(counts.values()), 'preparation_literal_missing')
    return _replace_nodes(raw, edits)


def _function(raw, name, replacement):
    nodes = [node for node in _tree(raw).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    require(len(nodes) == 1, 'preparation_function_missing')
    return _replace_nodes(raw, [(nodes[0], replacement.encode('utf-8'))])


def _literal_assignment(raw, name):
    nodes = [node.value for node in _tree(raw).body if isinstance(node, ast.Assign)
             and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
             and node.targets[0].id == name]
    require(len(nodes) == 1, 'preparation_literal_assignment_missing')
    try:
        return ast.literal_eval(nodes[0])
    except (ValueError, TypeError):
        raise PreparationRejected('preparation_literal_assignment_required') from None


def validate_install_binding(value):
    require(type(value) is dict and set(value) == {
        'schemaVersion', 'kind', 'repositoryRoot', 'candidateDirectory', 'harnessCommit',
        'manifestSha256', 'archiveSha256', 'sourceFileCount', 'builderSha256',
        'installerSha256', 'nativeFeature', 'pythonSha256', 'destination',
        'installationInput', 'acceptanceInput', 'dependencyRoot'}, 'preparation_binding_fields')
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1
            and value['kind'] == 'R156A1_INSTALL_BINDING', 'preparation_binding_schema')
    for name in ('repositoryRoot', 'candidateDirectory'):
        path_text(value[name])
    digest(value['harnessCommit'], 40)
    for name in ('manifestSha256', 'archiveSha256'):
        digest(value[name])
    require(type(value['sourceFileCount']) is int and 756 < value['sourceFileCount'] <= 1600,
            'preparation_source_count')
    require({name: value[name] for name in ('builderSha256', 'installerSha256', 'nativeFeature',
        'pythonSha256', 'destination', 'installationInput', 'acceptanceInput', 'dependencyRoot')}
        == {'builderSha256': BUILDER_SHA, 'installerSha256': INSTALLER_SHA, 'nativeFeature': NATIVE,
            'pythonSha256': PYTHON_SHA, 'destination': DESTINATION, 'installationInput': INSTALL_INPUT,
            'acceptanceInput': ACCEPT_INPUT, 'dependencyRoot': DEPENDENCIES},
        'preparation_fixed_runtime_binding')
    return value


def render_install_operator(template, binding):
    """Render a fixed new operator, retaining the original installation lifecycle."""
    require(type(template) is bytes and sha(template) == INSTALL_TEMPLATE_SHA,
            'preparation_install_template_changed')
    validate_install_binding(binding)
    transport = _literal_assignment(template, 'LINUX_TRANSPORT').encode('utf-8')
    transport = _literals(transport, {
        (str, '/opt/alaz-r154a1-input'): INSTALL_INPUT,
        (str, '/opt/alaz-r154a1'): DESTINATION,
        (str, 'R154A1_SOURCE_INSTALL_OPERATION'): 'R156A1_SOURCE_INSTALL_OPERATION',
        (str, 'R154A1_SOURCE_INSTALL_INTENT'): 'R156A1_SOURCE_INSTALL_INTENT',
        (str, 'e03f7fd4e47fea6a58b749564ab350aeb4237a26'): binding['harnessCommit'],
        (str, '182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9'): binding['manifestSha256'],
        (str, 'e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b'): binding['archiveSha256'],
        (str, '97be4be2a0aec7a045fd099b1f56b12c58501e312777e1ad67fee45cbe601cc7'): BUILDER_SHA,
        (int, 834): binding['sourceFileCount'],
    })
    rendered = _assign(template, {
        'ROOT': 'Path(' + repr(binding['repositoryRoot']) + ')',
        'SOURCE': repr(binding['harnessCommit']), 'ARCHIVE_SHA': repr(binding['archiveSha256']),
        'MANIFEST_SHA': repr(binding['manifestSha256']), 'BUILDER_SHA': repr(BUILDER_SHA),
        'INPUT': repr(INSTALL_INPUT), 'DESTINATION': repr(DESTINATION),
        'LINUX_TRANSPORT': repr(transport.decode('utf-8')),
    })
    rendered = _literals(rendered, {
        (str, 'R154A1_SOURCE_INSTALL_OPERATION'): 'R156A1_SOURCE_INSTALL_OPERATION',
        (str, 'R154A1_SOURCE_INSTALL_INTENT'): 'R156A1_SOURCE_INSTALL_INTENT',
    })
    rendered = _function(rendered, 'candidate',
        'def candidate():\n    return Path(' + repr(binding['candidateDirectory']) + ')')
    old_doc = _tree(rendered).body[0].value
    rendered = _replace_nodes(rendered, [(old_doc, repr(
        'One fixed R156 source installation in the dedicated P71C laboratory.\n\n'
        'Generated from the exact reviewed R154 operator by literal binding changes.\n'
        'Preparation and apply remain explicit, one-shot and source-only. No native,\n'
        'mount, model, service, retry or cleanup action is added.\n').encode('utf-8'))])
    return rendered


def verified_candidate(root, candidate, *, harness_commit, manifest_sha, archive_sha, with_sources=False):
    root, candidate = Path(root).resolve(strict=True), Path(candidate).resolve(strict=True)
    builder = pinned(root / 'scripts/build_projected_candidate.py', BUILDER_SHA)
    installer = pinned(root / 'scripts/install_projected_candidate.py', INSTALLER_SHA)
    manifest = pinned(candidate / 'manifest.json', manifest_sha, 2 * 1024 * 1024)
    archive = pinned(candidate / 'projected-source.tar', archive_sha, MAX_ARCHIVE)
    name = '_alaz_r156_source_only_installer'
    require(name not in sys.modules, 'preparation_verifier_already_loaded')
    module = types.ModuleType(name)
    module.__file__ = str(root / 'scripts/install_projected_candidate.py')
    sys.modules[name] = module
    try:
        exec(compile(installer, module.__file__, 'exec'), module.__dict__)
        prepared = module.prepare_bytes(manifest, archive,
            expected_manifest_sha256=manifest_sha, expected_archive_sha256=archive_sha,
            expected_harness_commit=digest(harness_commit, 40))
    finally:
        sys.modules.pop(name, None)
    require(prepared.native_feature == NATIVE and len(prepared.dependencies) == 1162,
            'preparation_native_or_dependencies_changed')
    binding = validate_install_binding({
        'schemaVersion': 1, 'kind': 'R156A1_INSTALL_BINDING', 'repositoryRoot': str(root),
        'candidateDirectory': str(candidate), 'harnessCommit': harness_commit,
        'manifestSha256': sha(manifest), 'archiveSha256': sha(archive),
        'sourceFileCount': len(prepared.source), 'builderSha256': sha(builder),
        'installerSha256': sha(installer), 'nativeFeature': NATIVE, 'pythonSha256': PYTHON_SHA,
        'destination': DESTINATION, 'installationInput': INSTALL_INPUT,
        'acceptanceInput': ACCEPT_INPUT, 'dependencyRoot': DEPENDENCIES})
    return (binding, dict(prepared.source)) if with_sources else binding


def publish(root, output, files):
    root, output = Path(root).resolve(strict=True), Path(output)
    require(output.is_absolute() and output.resolve(strict=False) == output
            and not any(p.is_symlink() for p in (output, *output.parents)),
            'preparation_output_alias')
    base = root / 'scratch/r156-preparation'
    require(output.is_relative_to(base) and output != base and not os.path.lexists(output),
            'preparation_fresh_owned_output_required')
    for name, raw in sorted(files.items()):
        require(type(name) is str and re.fullmatch('[a-zA-Z0-9_./-]+', name)
                and not PurePosixPath(name).is_absolute() and str(PurePosixPath(name)) == name
                and not set(name.split('/')) & {'', '.', '..'} and type(raw) is bytes,
                'preparation_output_entry')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in sorted(files.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(path.read_bytes() == raw, 'preparation_output_readback')


def prepare_install(root, candidate, output, *, harness_commit, manifest_sha, archive_sha):
    root = Path(root).resolve(strict=True)
    binding = verified_candidate(root, candidate, harness_commit=harness_commit,
                                 manifest_sha=manifest_sha, archive_sha=archive_sha)
    template = pinned(root / INSTALL_TEMPLATE, INSTALL_TEMPLATE_SHA)
    operator = render_install_operator(template, binding)
    transport = _literal_assignment(operator, 'LINUX_TRANSPORT').encode('utf-8')
    binding_raw = canonical(binding)
    report = {'kind': 'R156A1_INSTALL_PREPARATION', 'state': 'INSTALL_OPERATOR_PREPARED_NOT_RUN',
        'bindingSha256': sha(binding_raw), 'operatorSha256': sha(operator),
        'transportSha256': sha(transport),
        'operatorFile': 'r156a1_install_candidate.py', 'templateSha256': INSTALL_TEMPLATE_SHA,
        'candidateVerifiedSourceOnly': True, 'sourceFileCount': binding['sourceFileCount'],
        'installed': False, 'rootRequested': False, 'nativeExecuted': False,
        'finiteWorkExecuted': False, 'realProviderCalls': 0, 'acceptancePrepared': False,
        'installationReceiptSha256': None, 'automaticRetry': False, 'automaticCleanup': False}
    publish(root, output, {'installation-binding.json': binding_raw,
                          report['operatorFile']: operator, 'linux-transport.py': transport,
                          'preparation.json': canonical(report)})
    return report


def _node_bytes(raw, node):
    lines = raw.splitlines(keepends=True)
    first = sum(map(len, lines[:node.lineno - 1])) + node.col_offset
    last = sum(map(len, lines[:node.end_lineno - 1])) + node.end_col_offset
    return raw[first:last]


def _method(raw, class_name, name, replacement):
    classes = [node for node in _tree(raw).body if isinstance(node, ast.ClassDef)
               and node.name == class_name]
    require(len(classes) == 1, 'preparation_class_missing')
    methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(methods) == 1, 'preparation_method_missing')
    return _replace_nodes(raw, [(methods[0], replacement.encode('utf-8'))])


def _doc(raw, text):
    tree = _tree(raw)
    require(isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)
            and type(tree.body[0].value.value) is str, 'preparation_docstring_missing')
    return _replace_nodes(raw, [(tree.body[0].value, repr(text).encode('utf-8'))])


def _insert_before_class(raw, name, source):
    nodes = [node for node in _tree(raw).body if isinstance(node, ast.ClassDef) and node.name == name]
    require(len(nodes) == 1, 'preparation_class_missing')
    return _replace_nodes(raw, [(nodes[0], source.encode('utf-8') + b'\n\n' + _node_bytes(raw, nodes[0]))])


def _insert_before_assignment(raw, name, source):
    nodes = [node for node in _tree(raw).body if isinstance(node, ast.Assign)
             and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
             and node.targets[0].id == name]
    require(len(nodes) == 1, 'preparation_assignment_missing')
    return _replace_nodes(raw, [(nodes[0], source.encode('utf-8') + b'\n' + _node_bytes(raw, nodes[0]))])


def _version_literals(raw):
    """Only explicit lab/version tokens inside literals; no source-code replace."""
    tokens = (
        ('/opt/alaz-r154a1-input', INSTALL_INPUT), ('/opt/alaz-r154a1', DESTINATION),
        ('/opt/alaz-r155a1-input', ACCEPT_INPUT),
        ('bootstrap_retained_profile.py', 'bootstrap_retained_profile_r156.py'),
        ('r155a1', 'r156a1'), ('R155A1', 'R156A1'), ('_r155_', '_r156_'),
        ('r155-wsl-communication', 'r156-wsl-communication'),
        ('m1-seed-readiness-r156a1', 'm1-native-finite-r156a1'),
        ('SAME_IMAGE_SEED_READINESS', 'SAME_IMAGE_SEED_FINITE'),
        ('r156a1-ready', 'r156a1-finite'),
    )
    edits = []
    for node in ast.walk(_tree(raw)):
        if not isinstance(node, ast.Constant) or type(node.value) not in (str, bytes):
            continue
        value = node.value
        for old, new in tokens:
            value = value.replace(old.encode(), new.encode()) if type(value) is bytes else value.replace(old, new)
        if value != node.value:
            edits.append((node, repr(value).encode('utf-8')))
    return _replace_nodes(raw, edits)


def _rename_caller_identifiers(raw):
    names = {'READY_INSTANCE': 'FINITE_INSTANCE', 'READY_SECONDS': 'FINITE_SECONDS',
             'readiness': 'finite', 'run_readiness': 'run_finite'}
    edits = []
    for node in ast.walk(_tree(raw)):
        if isinstance(node, ast.Name) and node.id in names:
            edits.append((node, names[node.id].encode()))
        elif isinstance(node, ast.Attribute) and node.attr in names:
            span = types.SimpleNamespace(lineno=node.end_lineno, end_lineno=node.end_lineno,
                col_offset=node.end_col_offset - len(node.attr), end_col_offset=node.end_col_offset)
            edits.append((span, names[node.attr].encode()))
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            span = types.SimpleNamespace(lineno=node.lineno, end_lineno=node.lineno,
                col_offset=node.col_offset + 4, end_col_offset=node.col_offset + 4 + len(node.name))
            edits.append((span, names[node.name].encode()))
    return _replace_nodes(raw, edits)


def _function_literals(raw, name, replacements):
    node = next((n for n in _tree(raw).body if isinstance(n, ast.FunctionDef) and n.name == name), None)
    require(node is not None, 'preparation_function_missing')
    function = _literals(_node_bytes(raw, node), replacements)
    keywords = []
    for item in ast.walk(_tree(function)):
        if isinstance(item, ast.keyword) and (str, item.arg) in replacements:
            span = types.SimpleNamespace(lineno=item.lineno, end_lineno=item.lineno,
                col_offset=item.col_offset, end_col_offset=item.col_offset + len(item.arg))
            keywords.append((span, replacements[(str, item.arg)].encode('utf-8')))
    return _replace_nodes(raw, [(node, _replace_nodes(function, keywords))])


def verify_receipt(raw, expected_sha, binding):
    """Bind supplied original receipt bytes; the later producer re-verifies Linux."""
    validate_install_binding(binding)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SOURCE and sha(raw) == digest(expected_sha),
            'preparation_actual_receipt_digest_required')
    receipt = parse(raw)
    require(type(receipt) is dict and canonical(receipt) == raw and set(receipt) == {
        'schemaVersion', 'kind', 'destination', 'sourceManifestSha256', 'archiveSha256',
        'harnessCommit', 'nativeFeature', 'sourceFileCount', 'dependencyFileCount',
        'dependencyInventorySha256', 'python', 'rootDevice', 'rootInode',
        'sourceAndDependenciesReadBack', 'rootControlledAncestryVerified', 'installed',
        'executionAuthorized', 'projectedReadinessAccepted', 'finiteWorkExecuted', 'realModelCalls'},
        'preparation_original_receipt_schema')
    expected = {'schemaVersion': 1, 'kind': 'VERIFIED_PROJECTED_INSTALLATION',
        'destination': DESTINATION, 'sourceManifestSha256': binding['manifestSha256'],
        'archiveSha256': binding['archiveSha256'], 'harnessCommit': binding['harnessCommit'],
        'nativeFeature': NATIVE, 'sourceFileCount': binding['sourceFileCount'], 'dependencyFileCount': 1162,
        'sourceAndDependenciesReadBack': True, 'rootControlledAncestryVerified': True, 'installed': True,
        'executionAuthorized': False, 'projectedReadinessAccepted': False,
        'finiteWorkExecuted': False, 'realModelCalls': 0}
    require(all(type(receipt[name]) is type(value) and receipt[name] == value
                for name, value in expected.items()), 'preparation_receipt_binding')
    digest(receipt['dependencyInventorySha256'])
    for name in ('rootDevice', 'rootInode'):
        require(type(receipt[name]) is int and 0 < receipt[name] < 2**64, 'preparation_receipt_identity')
    python = receipt['python']
    require(type(python) is dict and set(python) == {'path', 'sha256', 'device', 'inode', 'uid', 'gid', 'mode'}
            and python['path'] == '/usr/bin/python3.12' and python['sha256'] == PYTHON_SHA
            and all(type(python[name]) is int for name in ('device', 'inode', 'uid', 'gid', 'mode'))
            and 0 < python['device'] < 2**64 and 0 < python['inode'] < 2**64
            and python['uid'] == python['gid'] == 0 and python['mode'] == 0o755,
            'preparation_receipt_python')
    return receipt


def _acceptance_templates(root):
    raw = pinned(Path(root) / ACCEPT_TEMPLATES, ACCEPT_TEMPLATES_SHA)
    namespace = {'__name__': '_r156_reviewed_acceptance_templates'}
    exec(compile(raw, ACCEPT_TEMPLATES, 'exec'), namespace)
    return namespace


def render_acceptance(root, binding, receipt_raw, receipt_sha, sources, *, base_commit):
    """Generate new fixed sources only after candidate and original receipt binding."""
    root = Path(root)
    receipt = verify_receipt(receipt_raw, receipt_sha, binding)
    digest(base_commit, 40)
    originals = {name: pinned(root / name, expected) for name, expected in SEED_TEMPLATES.items()}
    templates = _acceptance_templates(root)
    protocol_path = 'packages/claw-hermes/gateway_finite_protocol.py'
    require(protocol_path in sources, 'preparation_finite_protocol_missing')
    protocol = sources[protocol_path]
    _tree(protocol)
    require(sha(sources['accepted-dependencies.json']) == receipt['dependencyInventorySha256'],
            'preparation_receipt_dependency_inventory')
    # The seed boundary's original helpers remain exact source-qualified bytes.
    helpers = _literal_assignment(originals['scripts/qa/r155a1_seed_child.py'], 'HELPERS')
    for name, expected in helpers:
        require(sha(sources['packages/claw-hermes/' + name + '.py']) == expected,
                'preparation_seed_helper_changed')
    producer = _version_literals(originals['scripts/bootstrap_retained_profile.py'])
    producer = _assign(producer, {'INSTALLER_SHA256': repr(INSTALLER_SHA), 'RECEIPT_SHA256': repr(receipt_sha),
        'PINS': repr({'expected_manifest_sha256': binding['manifestSha256'],
                      'expected_archive_sha256': binding['archiveSha256'],
                      'expected_harness_commit': binding['harnessCommit'],
                      'expected_python_sha256': PYTHON_SHA})})
    producer = _literals(producer, {(int, 834): binding['sourceFileCount']})
    producer = _doc(producer, 'Fixed R156 task-free producer; original R155 native bootstrap algorithm.\n'
        'Only the explicit verified runtime binding and version labels are changed.\n'
        'No API admission, work, provider, mount, retry or cleanup action is added.\n')
    child = _version_literals(originals['scripts/qa/r155a1_seed_child.py'])
    child = _assign(child, {'RECEIPT_SHA': repr(receipt_sha)})
    child = _doc(child, 'Fixed R156 supervised seed boundary with original R155 ownership algorithm.\n'
        'Only fixed runtime, input, state and receipt bindings are changed.\n'
        'The original controller retains image ownership and all uncertain effects.\n')
    ordinary = _version_literals(originals['scripts/qa/r155a1_ordinary_seed.py'])
    linux_node = next(n.value for n in _tree(ordinary).body if isinstance(n, ast.Assign)
        and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'LINUX')
    require(isinstance(linux_node, ast.Call) and isinstance(linux_node.func, ast.Attribute)
            and linux_node.func.attr == 'lstrip', 'preparation_ordinary_literal')
    linux = ast.literal_eval(linux_node.func.value).lstrip().encode('utf-8')
    linux = _literals(linux, {
        (str, SEED_TEMPLATES['scripts/bootstrap_retained_profile.py']): sha(producer),
        (str, '137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2'): receipt_sha,
        (str, 'e03f7fd4e47fea6a58b749564ab350aeb4237a26'): binding['harnessCommit'],
    })
    ordinary = _assign(ordinary, {'PRODUCER_SHA': repr(sha(producer)), 'LINUX': repr(linux.decode('utf-8'))})
    assertion = protocol.rstrip() + b'\n\n' + (
        'INSTALLATION_RECEIPT_SHA = ' + repr(receipt_sha) + '\nHARNESS_COMMIT = '
        + repr(binding['harnessCommit']) + '\n').encode('ascii') + templates['FINITE_ASSERTION_SUFFIX'].encode('utf-8')
    _tree(assertion)
    caller = _rename_caller_identifiers(_version_literals(originals['scripts/qa/r155a1_linux_accept.py']))
    caller = _insert_before_assignment(caller, 'INPUT_FILES', 'FINITE_ENTRY = ' + repr(FINITE_ENTRY))
    caller = _assign(caller, {'RECEIPT_SHA': repr(receipt_sha), 'HARNESS': repr(binding['harnessCommit']),
        'INPUT_FILES': '{SEED_ENTRY, CHILD_ENTRY, CALLER_ENTRY, FINITE_ENTRY}'})
    caller = _literals(caller, {(str, 'SUPERVISED_PROJECTED_OWNER_CLOSED'): 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED'})
    caller = _method(caller, 'Controller', 'run_finite', templates['CALLER_RUN_FINITE'])
    caller = _function(caller, 'execute', templates['CALLER_EXECUTE'])
    caller = _function_literals(caller, 'main', {(str, 'projectedReadinessAccepted'): 'projectedFiniteAccepted'})
    caller = _doc(caller, 'One fixed R156 seed -> scripted native finite qualification -> normal close.\n'
        'The original R155 provisioning, seed ownership, capture and unknown custody remain.\n'
        'Exactly one finite child uses original API/runner/authority/store/drain/close.\n'
        'Model factory/computation/close is an explicit fixture; external provider calls remain zero.\n')
    transport = _version_literals(originals['scripts/qa/r155a1_linux_transport.py'])
    transport = _insert_before_assignment(transport, 'FILES', 'FINITE = ' + repr(FINITE_ENTRY))
    transport = _assign(transport, {'FILES': "{SEED, CALLER, 'scripts/qa/r156a1_seed_child.py', FINITE}"})
    transport = _function(transport, 'classify', templates['TRANSPORT_CLASSIFY'])
    transport_tree = _tree(transport)
    main_node = next(n for n in transport_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    stage_nodes = [n for n in ast.walk(main_node) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                   and isinstance(n.value.func, ast.Name) and n.value.func.id == 'stage']
    classify_nodes = [n for n in ast.walk(main_node) if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Name) and n.func.id == 'classify']
    require(len(stage_nodes) == len(classify_nodes) == 1, 'preparation_transport_hooks')
    transport = _replace_nodes(transport, [(stage_nodes[0],
        b"stage(data)\n        finite = {'__name__': '_r156_verified_finite_assertion'}\n"
        b"        exec(compile(data[FINITE], str(INPUT / FINITE), 'exec'), finite)"),
        (classify_nodes[0], b"classify(process, identity, out, err, finite, intent['manifestSha256'])")])
    transport = _doc(transport, 'Fixed R156 root staging and observation transport.\n'
        'Stages four frozen sources once; validates finite results directly and preserves unknown custody.\n'
        'No retry, signalling, image action or automatic cleanup is added.\n')
    host = _version_literals(originals['scripts/qa/r155a1_accept.py'])
    host = _insert_before_assignment(host, 'SOURCES', 'FINITE = ' + repr(FINITE_ENTRY))
    host = _insert_before_class(host, 'RunnerRejected', 'REVIEWED_FINITE_SHA = ' + repr(sha(assertion))
        + '\n\n' + templates['HOST_FINITE_LOADER'])
    host = _assign(host, {'BASE_COMMIT': repr(base_commit), 'RECEIPT_SHA': repr(receipt_sha),
        'HARNESS': repr(binding['harnessCommit']), 'REVIEWED_CALLER_SHA': repr(sha(caller)),
        'REVIEWED_CHILD_SHA': repr(sha(child)), 'REVIEWED_TRANSPORT_SHA': repr(sha(transport)),
        'SOURCES': '{SEED, CALLER, CHILD, FINITE}'})
    host = _function(host, 'current_inputs', templates['HOST_CURRENT_INPUTS'])
    host = _function(host, 'transport_result', templates['HOST_TRANSPORT_RESULT'])
    host = _function_literals(host, 'apply', {(str, 'projectedReadinessAccepted'): 'projectedFiniteAccepted'})
    # ROOT remains the actual repository after generated sources are installed there.
    rendered = {'scripts/bootstrap_retained_profile_r156.py': producer,
        'scripts/qa/r156a1_ordinary_seed.py': ordinary, 'scripts/qa/r156a1_seed_child.py': child,
        'scripts/qa/r156a1_linux_accept.py': caller, 'scripts/qa/r156a1_linux_transport.py': transport,
        'scripts/qa/r156a1_accept.py': host, FINITE_ENTRY: assertion}
    for raw in rendered.values():
        require(len(raw) <= 262144, 'preparation_rendered_source_limit')
        _tree(raw)
    return rendered


def prepare_acceptance(root, binding_path, receipt_path, output, *, receipt_sha, base_commit):
    root = Path(root).resolve(strict=True)
    binding_raw = read_file(Path(binding_path))
    binding = validate_install_binding(parse(binding_raw))
    require(canonical(binding) == binding_raw and binding['repositoryRoot'] == str(root),
            'preparation_original_install_binding')
    actual, sources = verified_candidate(root, binding['candidateDirectory'],
        harness_commit=binding['harnessCommit'], manifest_sha=binding['manifestSha256'],
        archive_sha=binding['archiveSha256'], with_sources=True)
    require(actual == binding, 'preparation_candidate_binding_changed')
    receipt_raw = read_file(Path(receipt_path))
    files = render_acceptance(root, binding, receipt_raw, receipt_sha, sources, base_commit=base_commit)
    report = {'kind': 'R156A1_ACCEPTANCE_SOURCE_PREPARATION', 'state': 'ACCEPTANCE_SOURCES_PREPARED_NOT_RUN',
        'installationBindingSha256': sha(binding_raw), 'installationReceiptSha256': receipt_sha,
        'receiptParsedAndBound': True, 'installedBytesVerifiedNow': False,
        'harnessCommit': binding['harnessCommit'], 'baseCommit': base_commit,
        'files': {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in sorted(files.items())},
        'ordinaryProofRequired': True, 'ordinaryProofAccepted': False,
        'rootRequested': False, 'nativeExecuted': False, 'finiteWorkExecuted': False,
        'realProviderCalls': 0, 'sameImageFiniteAccepted': False, 'fullD3BAccepted': False,
        'automaticRetry': False, 'automaticCleanup': False}
    files.update({'installation-binding.json': binding_raw, 'installation-receipt.json': receipt_raw,
                  'preparation.json': canonical(report)})
    publish(root, output, files)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acceptance-sources', action='store_true')
    parser.add_argument('--candidate-directory', type=Path)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--expected-harness-commit')
    parser.add_argument('--expected-manifest-sha256')
    parser.add_argument('--expected-archive-sha256')
    parser.add_argument('--installation-binding', type=Path)
    parser.add_argument('--installation-receipt', type=Path)
    parser.add_argument('--expected-receipt-sha256')
    parser.add_argument('--base-commit')
    args = parser.parse_args(argv)
    try:
        install = (args.candidate_directory, args.expected_harness_commit,
                   args.expected_manifest_sha256, args.expected_archive_sha256)
        acceptance = (args.installation_binding, args.installation_receipt,
                      args.expected_receipt_sha256, args.base_commit)
        require((all(value is None for value in install) and all(value is not None for value in acceptance))
                if args.acceptance_sources else
                (all(value is not None for value in install) and all(value is None for value in acceptance)),
                'preparation_complete_exclusive_arguments_required')
        if args.acceptance_sources:
            result = prepare_acceptance(ROOT, args.installation_binding, args.installation_receipt,
                args.output_directory, receipt_sha=args.expected_receipt_sha256, base_commit=args.base_commit)
        else:
            result = prepare_install(ROOT, args.candidate_directory, args.output_directory,
                harness_commit=args.expected_harness_commit,
                manifest_sha=args.expected_manifest_sha256, archive_sha=args.expected_archive_sha256)
    except (PreparationRejected, OSError, ValueError) as exc:
        result = {'kind': 'R156A1_INSTALL_PREPARATION', 'state': 'REFUSED_NOT_RUN',
            'reason': str(exc) if isinstance(exc, PreparationRejected) else type(exc).__name__,
            'installed': False, 'rootRequested': False, 'nativeExecuted': False,
            'finiteWorkExecuted': False, 'realProviderCalls': 0,
            'automaticRetry': False, 'automaticCleanup': False}
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
