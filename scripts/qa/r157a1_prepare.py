"""Prepare four fixed R157 readiness sources from reviewed R155 sources.

This source-only operation revalidates the original R156 candidate, receipt and
ordinary001 proof. It retains the installed runtime, producer, ordinary driver
and all original proof bytes. The separate R157 execution binding names a fresh
seed/readiness attempt; no installation, process or native action occurs here.
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
import types

ROOT = Path(__file__).resolve().parents[2]
HELPER = 'scripts/qa/r156a1_prepare.py'
HELPER_SHA = 'cc652865855cedca4f1d06f4d8ed7d58be462d5612082d02b843b2b688130a54'
BASE_COMMIT = 'cdc974728e69f590838b82421cd244e36554a74f'
HARNESS = 'e641a5000810efb2a453ae847f689b422f7d41a7'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
MANIFEST_SHA = '7a886c32fd81d046d44715921bdaae5765a6f4e481d33182258cc7aa2bac465a'
ARCHIVE_SHA = '3c829db65670756abd531d146aa72c0dc5b3773cd750fc87d26567763f3caef8'
BINDING_SHA = '5ef09ad06075995fb7d1d82ef49b1712c66c83a7dd7b260fe70850110ba45350'
RECEIPT_SHA = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
DEPENDENCY_INVENTORY_SHA = '1e1c4d0a5a9f0d4d25c66aaabe0765c75cdca0dd84121f79883b9e3bf2b4ee18'
SOURCE_COUNT = 838
DESTINATION = '/opt/alaz-r156a1'
INSTALL_INPUT = '/opt/alaz-r156a1-install-input'
ACCEPT_INPUT = '/opt/alaz-r157a1-accept-input'
STATE_ROOT = '/srv/alaz-r157a1'
CGROUP = '/sys/fs/cgroup/alaz-r157a1'
IPC = '/tmp/alaz-ipc-r157a1'
EVIDENCE = 'evidence/m1-installed-readiness-r157a1'
ORIGINAL_PROOF = 'evidence/m1-native-finite-r156a1/ordinary001'
PRODUCER = 'scripts/bootstrap_retained_profile_r156.py'
PRODUCER_SHA = '02ac2d81d72e0ab11739081b3b95ccb05db2871581bc3494518fe2190a66a5aa'
ORDINARY_DRIVER = 'scripts/qa/r156a1_ordinary_seed.py'
ORDINARY_DRIVER_SHA = 'baa56be5f0df56a1e9679bb8efccb445aafd31c32c0fc0c4b2c22ce17fde13a7'
TEMPLATES = {
    'scripts/qa/r155a1_seed_child.py': 'fe598ba4e09e10b534d4f74de2d16246228e770eb00fd273d92c40ccf665cb12',
    'scripts/qa/r155a1_linux_accept.py': 'cc80c882fc0ada181afe86f4151e8296db13c2cd922937aa3189be9f5b71933d',
    'scripts/qa/r155a1_linux_transport.py': 'a08345f8eaa6fe179d973d28159949d5d405c4996f60ecc79bd1bc041d4119a6',
    'scripts/qa/r155a1_accept.py': '113ec74d47509cefc875a19dfa8b34b465db864ead3edd04c40b3d9d7e9fc4ef',
}
GENERATED_FILES = {
    'scripts/qa/r157a1_seed_child.py', 'scripts/qa/r157a1_linux_accept.py',
    'scripts/qa/r157a1_linux_transport.py', 'scripts/qa/r157a1_accept.py',
}
ORIGINAL_PROOF_ROWS = {
    'execution-start.json': {'sha256': '49f960fc0727a550f263be79643d2aa54de4543b674e020d8b2a52257ce13108', 'size': 363},
    'linux-runner.py': {'sha256': '3a89fb5cbd74642b67876ffe3ada4f429318a68eff9db41ecb0c11dc670642ab', 'size': 7402},
    'producer-source.py': {'sha256': PRODUCER_SHA, 'size': 35124},
    'result.json': {'sha256': 'e42a277a3371f168a08cd78f07af2253840d6004b5730c3b4dbb4de095469ae8', 'size': 11738},
    'stderr.txt': {'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0},
    'stdout.txt': {'sha256': '2851d36fb219f6b82959f30647c792a82dd969e22e7512367fea65fcc14b195c', 'size': 10142},
}
MAX_SOURCE = 4 << 20


class PreparationRejected(ValueError):
    """A bounded source-preparation diagnostic, never supplied file contents."""


def require(ok, reason):
    if not ok:
        raise PreparationRejected(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def read_file(path, maximum=MAX_SOURCE):
    """Bound and pin the helper before any code from it is loaded."""
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'r157_source_alias')
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 0 < before.st_size <= maximum, 'r157_regular_bounded_source')
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
        opened = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns)
    require(len(raw) == before.st_size and stamp(before) == stamp(opened)
            and stamp(before) == stamp(path.stat()), 'r157_source_changed')
    return raw


def reviewed_helpers(root):
    root = Path(root)
    require(root.is_absolute() and root.resolve(strict=True) == root
            and not any(p.is_symlink() for p in (root, *root.parents)) and root.is_dir(),
            'r157_repository_alias')
    raw = read_file(root / HELPER)
    require(sha(raw) == HELPER_SHA, 'r157_reviewed_helper_changed')
    helper = types.ModuleType('_r157_reviewed_source_preparation')
    helper.__file__ = str(root / HELPER)
    exec(compile(raw, helper.__file__, 'exec', dont_inherit=True), helper.__dict__)
    return helper


def original_binding(helper, binding_raw, receipt_raw):
    require(type(binding_raw) is bytes and sha(binding_raw) == BINDING_SHA,
            'r157_original_installation_binding_changed')
    binding = helper.validate_install_binding(helper.parse(binding_raw))
    require(canonical(binding) == binding_raw and binding['harnessCommit'] == HARNESS
            and binding['manifestSha256'] == MANIFEST_SHA and binding['archiveSha256'] == ARCHIVE_SHA
            and type(binding['sourceFileCount']) is int and binding['sourceFileCount'] == SOURCE_COUNT,
            'r157_original_runtime_binding')
    receipt = helper.verify_receipt(receipt_raw, RECEIPT_SHA, binding)
    require(receipt['dependencyInventorySha256'] == DEPENDENCY_INVENTORY_SHA,
            'r157_original_dependency_inventory')
    return binding, receipt


def verified_sources(helper, root, binding):
    """Use the exact R156 verifier without changing the old installation binding."""
    actual, sources = helper.verified_candidate(root, binding['candidateDirectory'],
        harness_commit=HARNESS, manifest_sha=MANIFEST_SHA, archive_sha=ARCHIVE_SHA, with_sources=True)
    require(actual == {**binding, 'repositoryRoot': str(root)}
            and str(root) != binding['repositoryRoot'], 'r157_candidate_binding_changed')
    return sources


def validate_source_bindings(helper, sources, receipt, child_template):
    require(type(sources) is dict and len(sources) == SOURCE_COUNT
            and all(type(name) is str and type(raw) is bytes and 0 <= len(raw) <= MAX_SOURCE
                    for name, raw in sources.items()), 'r157_verified_source_inventory')
    require('accepted-dependencies.json' in sources
            and sha(sources['accepted-dependencies.json']) == receipt['dependencyInventorySha256'],
            'r157_receipt_dependency_inventory')
    helpers = helper._literal_assignment(child_template, 'HELPERS')
    require(type(helpers) is tuple and len(helpers) == 3, 'r157_seed_helper_inventory')
    for name, expected in helpers:
        path = 'packages/claw-hermes/' + name + '.py'
        require(path in sources and sha(sources[path]) == expected, 'r157_seed_helper_changed')


def version_literals(helper, raw, expected_edits):
    """Change only AST literal spans in a fixed, digest-pinned readiness source."""
    retained = {
        'R155A1_TASK_FREE_RETAINED_SEED': 'R156A1_TASK_FREE_RETAINED_SEED',
        'R155A1_ORDINARY_NATIVE_SEED_PROOF': 'R156A1_ORDINARY_NATIVE_SEED_PROOF',
        '/tmp/alaz-r155a1-': '/tmp/alaz-r156a1-',
        'r155a1-': 'r156a1-',
        'scripts/qa/r155a1_ordinary_seed.py': ORDINARY_DRIVER,
    }
    tokens = (
        ('/opt/alaz-r154a1-input', INSTALL_INPUT), ('/opt/alaz-r154a1', DESTINATION),
        ('/opt/alaz-r155a1-input', ACCEPT_INPUT),
        ('bootstrap_retained_profile.py', 'bootstrap_retained_profile_r156.py'),
        ('evidence/m1-seed-readiness-r155a1', EVIDENCE),
        ('r155a1', 'r157a1'), ('R155A1', 'R157A1'), ('_r155_', '_r157_'),
        ('r155-wsl-communication', 'r157-wsl-communication'),
    )
    edits = []
    for node in ast.walk(helper._tree(raw)):
        if not isinstance(node, ast.Constant) or type(node.value) not in (str, bytes):
            continue
        value = retained.get(node.value, node.value)
        for old, new in tokens:
            value = value.replace(old.encode(), new.encode()) if type(value) is bytes else value.replace(old, new)
        if value != node.value:
            edits.append((node, repr(value).encode('utf-8')))
    require(len(edits) == expected_edits, 'r157_literal_generation_count')
    return helper._replace_nodes(raw, edits)


def function_node(helper, raw, name):
    nodes = [n for n in helper._tree(raw).body if isinstance(n, ast.FunctionDef) and n.name == name]
    require(len(nodes) == 1, 'r157_function_generation_count')
    return nodes[0]


def original_proof_guard(helper, host):
    """Keep old evidence read authority separate from fresh R157 evidence writes."""
    source = '''def original_ordinary_directory(path, *, exists):
    require(exists is True, 'runner_original_ordinary_read_only')
    path = path_without_alias(path, exists=True)
    expected = path_without_alias(ROOT / ORIGINAL_ORDINARY_DIRECTORY, exists=True)
    require(path == expected and path.is_dir(), 'runner_original_ordinary_directory')
    require({p.name for p in path.iterdir()} == PROOF_FILES, 'runner_original_ordinary_inventory')
    return path
'''
    host = helper._insert_before_class(host, 'RunnerRejected',
        'ORIGINAL_ORDINARY_DIRECTORY = ' + repr(ORIGINAL_PROOF)
        + '\nREVIEWED_ORIGINAL_PROOF = ' + repr(ORIGINAL_PROOF_ROWS)
        + '\nREVIEWED_PRODUCER_SHA = ' + repr(PRODUCER_SHA)
        + '\nREVIEWED_ORDINARY_DRIVER_SHA = ' + repr(ORDINARY_DRIVER_SHA)
        + '\n\n' + source)
    edits = []
    for name, target in (('proof_bytes', 'directory'), ('prepare', 'ordinary_directory'),
                         ('load_prepared', 'ordinary_directory')):
        function = function_node(helper, host, name)
        matches = [n for n in ast.walk(function) if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name) and n.targets[0].id == target
                   and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                   and n.value.func.id == 'owned_directory']
        require(len(matches) == 1, 'r157_original_proof_guard_count')
        call = matches[0].value
        require(len(call.args) == 1 and len(call.keywords) == 1
                and call.keywords[0].arg == 'exists' and ast.literal_eval(call.keywords[0].value) is True,
                'r157_original_proof_guard_shape')
        edits.append((call.func, b'original_ordinary_directory'))
    require(len(edits) == 3, 'r157_original_proof_generation_count')
    host = helper._replace_nodes(host, edits)
    function = function_node(helper, host, 'proof_bytes')
    returns = [n for n in function.body if isinstance(n, ast.Return)]
    require(len(returns) == 1 and isinstance(returns[0].value, ast.DictComp), 'r157_proof_return_shape')
    statement = b'files = ' + helper._node_bytes(host, returns[0].value) + b'''
    require({name: row(raw) for name, raw in files.items()} == REVIEWED_ORIGINAL_PROOF,
            'runner_original_ordinary_bytes_changed')
    return files'''
    host = helper._replace_nodes(host, [(returns[0], statement)])
    # The original three QA pins remain; also bind the unchanged R156 inputs.
    function = function_node(helper, host, 'current_inputs')
    returns = [n for n in function.body if isinstance(n, ast.Return)]
    require(len(returns) == 1, 'r157_current_inputs_return_count')
    return helper._replace_nodes(host, [(returns[0], b'''driver = read_file(ROOT / ORDINARY_DRIVER)
    require(sha(sources[SEED]) == REVIEWED_PRODUCER_SHA
            and sha(driver) == REVIEWED_ORDINARY_DRIVER_SHA, 'runner_original_r156_sources_changed')
    return sources, transport, read_file(SELF), driver''')])


def validate_original_proof(root, host, producer, driver):
    """Load only the generated host's source-only definitions; never its main."""
    namespace = {'__name__': '_r157_source_only_original_proof',
                 '__file__': str(Path(root) / 'scripts/qa/r157a1_accept.py')}
    exec(compile(host, namespace['__file__'], 'exec', dont_inherit=True), namespace)
    original = namespace['original_ordinary_directory'](Path(root) / ORIGINAL_PROOF, exists=True)
    files = namespace['proof_bytes'](original)
    namespace['validate_ordinary'](files, producer, driver)
    require(namespace['parse'](files['execution-start.json'], 8192, form='pretty')['attempt'] == 'ordinary001',
            'r157_original_ordinary_attempt')
    return files


def render_readiness(root, binding_raw, receipt_raw, sources):
    """Return exactly four sources, retaining all R155 readiness ownership logic."""
    helper = reviewed_helpers(root)
    _, receipt = original_binding(helper, binding_raw, receipt_raw)
    originals = {name: helper.pinned(Path(root) / name, expected) for name, expected in TEMPLATES.items()}
    producer = helper.pinned(Path(root) / PRODUCER, PRODUCER_SHA)
    driver = helper.pinned(Path(root) / ORDINARY_DRIVER, ORDINARY_DRIVER_SHA)
    validate_source_bindings(helper, sources, receipt, originals['scripts/qa/r155a1_seed_child.py'])
    child = version_literals(helper, originals['scripts/qa/r155a1_seed_child.py'], 8)
    child = helper._assign(child, {'RECEIPT_SHA': repr(RECEIPT_SHA)})
    child = helper._doc(child, 'Fixed R157 seed boundary for the unchanged R156 task-free producer.\n'
        'The original R155 controller ownership, namespace, identity reduction and unknown custody remain.\n'
        'Only fixed runtime, receipt, input and fresh state bindings change.\n')
    caller = version_literals(helper, originals['scripts/qa/r155a1_linux_accept.py'], 20)
    caller = helper._assign(caller, {'RECEIPT_SHA': repr(RECEIPT_SHA), 'HARNESS': repr(HARNESS)})
    caller = helper._doc(caller, 'Fixed R157 seed -> retained readiness -> original normal close.\n'
        'Uses the unchanged R156 installation and producer with original R155 ownership and budgets.\n'
        'Exactly one readiness child performs zero tasks and model calls; unknown custody is preserved.\n')
    transport = version_literals(helper, originals['scripts/qa/r155a1_linux_transport.py'], 13)
    transport = helper._doc(transport, 'Fixed R157 root staging and observation transport.\n'
        'Three sources are frozen once: unchanged R156 producer, R157 seed boundary and readiness caller.\n'
        'The original R155 bounded observation and unknown custody algorithm is retained.\n')
    host = version_literals(helper, originals['scripts/qa/r155a1_accept.py'], 25)
    host = helper._assign(host, {'BASE_COMMIT': repr(BASE_COMMIT), 'RECEIPT_SHA': repr(RECEIPT_SHA),
        'HARNESS': repr(HARNESS), 'REVIEWED_CHILD_SHA': repr(sha(child)),
        'REVIEWED_CALLER_SHA': repr(sha(caller)), 'REVIEWED_TRANSPORT_SHA': repr(sha(transport))})
    host = original_proof_guard(helper, host)
    host = helper._doc(host, 'Fixed R157 installed-runtime readiness preparation and one explicit attempt.\n'
        'Reads only the exact accepted R156 ordinary001 proof and unchanged producer/driver.\n'
        'Fresh R157 evidence and intent bind one seed/readiness/normal-close attempt; no finite work.\n'
        'Apply revalidates every original/current/frozen byte before its exclusive execution marker.\n')
    rendered = {'scripts/qa/r157a1_seed_child.py': child, 'scripts/qa/r157a1_linux_accept.py': caller,
        'scripts/qa/r157a1_linux_transport.py': transport, 'scripts/qa/r157a1_accept.py': host}
    require(set(rendered) == GENERATED_FILES and len(rendered) == 4, 'r157_generation_inventory')
    for raw in rendered.values():
        require(type(raw) is bytes and 0 < len(raw) <= 262144, 'r157_generated_source_bound')
        helper._tree(raw)
    validate_original_proof(root, host, producer, driver)
    return rendered


def publish(root, output, files):
    output = Path(output)
    base = Path(root) / 'scratch/r157-preparation'
    require(output.is_absolute() and output.parent == base
            and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,63}', output.name)
            and output.resolve(strict=False) == output
            and not any(p.is_symlink() for p in (output, *output.parents))
            and not os.path.lexists(output), 'r157_fresh_owned_output_required')
    for name, raw in files.items():
        relative = PurePosixPath(name)
        require(type(name) is str and not relative.is_absolute() and str(relative) == name
                and '\\' not in name and ':' not in name and '..' not in relative.parts
                and type(raw) is bytes and 0 < len(raw) <= MAX_SOURCE, 'r157_output_inventory')
    base.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    for name, raw in sorted(files.items()):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            require(stream.write(raw) == len(raw), 'r157_output_short_write')
            stream.flush()
            os.fsync(stream.fileno())
        require(read_file(target) == raw, 'r157_output_readback')


def prepare_sources(root, binding_path, receipt_path, output):
    root = Path(root)
    helper = reviewed_helpers(root)
    binding_raw, receipt_raw = read_file(binding_path), read_file(receipt_path)
    binding, _ = original_binding(helper, binding_raw, receipt_raw)
    sources = verified_sources(helper, root, binding)
    files = render_readiness(root, binding_raw, receipt_raw, sources)
    producer, driver = helper.pinned(root / PRODUCER, PRODUCER_SHA), helper.pinned(root / ORDINARY_DRIVER, ORDINARY_DRIVER_SHA)
    row = lambda raw: {'sha256': sha(raw), 'bytes': len(raw)}
    execution = {'schemaVersion': 1, 'kind': 'R157A1_READINESS_EXECUTION_BINDING',
        'repositoryRoot': str(root), 'baseCommit': BASE_COMMIT, 'installedHarnessCommit': HARNESS,
        'installationBindingSha256': BINDING_SHA, 'installationReceiptSha256': RECEIPT_SHA,
        'installationRoot': DESTINATION, 'installationInput': INSTALL_INPUT,
        'acceptanceInput': ACCEPT_INPUT, 'stateRoot': STATE_ROOT, 'cgroup': CGROUP, 'ipcRoot': IPC,
        'evidenceRoot': str(root / EVIDENCE), 'originalOrdinaryDirectory': str(root / ORIGINAL_PROOF),
        'originalOrdinaryFiles': ORIGINAL_PROOF_ROWS, 'sourceManifestSha256': MANIFEST_SHA,
        'archiveSha256': ARCHIVE_SHA, 'nativeFeature': NATIVE, 'sourceFileCount': SOURCE_COUNT,
        'generatedFiles': {name: row(raw) for name, raw in sorted(files.items())},
        'reusedSources': {PRODUCER: row(producer), ORDINARY_DRIVER: row(driver)},
        'stagedSources': {name: row(raw) for name, raw in sorted({PRODUCER: producer,
            **{name: raw for name, raw in files.items() if name in {
                'scripts/qa/r157a1_seed_child.py', 'scripts/qa/r157a1_linux_accept.py'}}}.items())}}
    execution_raw = canonical(execution)
    report = {'kind': 'R157A1_READINESS_SOURCE_PREPARATION', 'state': 'READINESS_SOURCES_PREPARED_NOT_RUN',
        'executionBindingSha256': sha(execution_raw), 'installationBindingSha256': BINDING_SHA,
        'installationReceiptSha256': RECEIPT_SHA, 'receiptParsedAndBound': True,
        'candidateRevalidated': True, 'installedBytesVerifiedNow': False,
        'harnessCommit': HARNESS, 'baseCommit': BASE_COMMIT, 'generatedFileCount': 4,
        'files': execution['generatedFiles'], 'reusedSources': execution['reusedSources'],
        'inputTemplates': {HELPER: HELPER_SHA, **TEMPLATES},
        'originalOrdinaryProofRevalidated': True, 'originalOrdinaryProofReexecuted': False,
        'rootRequested': False, 'nativeExecuted': False, 'finiteWorkExecuted': False,
        'executedTasks': 0, 'realModelCalls': 0, 'projectedReadinessAccepted': False,
        'sameImageReadinessAccepted': False, 'fullD3BAccepted': False,
        'automaticRetry': False, 'automaticCleanup': False}
    files.update({'installation-binding.json': binding_raw, 'installation-receipt.json': receipt_raw,
                  'execution-binding.json': execution_raw, 'preparation.json': canonical(report)})
    require(len(files) == 8, 'r157_publication_generation_count')
    publish(root, output, files)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installation-binding', type=Path, required=True)
    parser.add_argument('--installation-receipt', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = prepare_sources(ROOT, args.installation_binding, args.installation_receipt, args.output_directory)
    except (OSError, ValueError) as exc:
        report = {'kind': 'R157A1_READINESS_SOURCE_PREPARATION', 'state': 'REFUSED_NOT_RUN',
            'reason': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
            'rootRequested': False, 'nativeExecuted': False, 'finiteWorkExecuted': False,
            'projectedReadinessAccepted': False, 'realModelCalls': 0,
            'automaticRetry': False, 'automaticCleanup': False}
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
