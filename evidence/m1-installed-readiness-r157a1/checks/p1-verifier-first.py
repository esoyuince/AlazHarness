"""Read-only joint P1 evidence and unchanged packaged-source verification.

This does not execute the runtime, install, call a provider, or repeat either
native attempt. It prints a separate acceptance record; original evidence and
the source-only installation receipt remain immutable.
"""
from pathlib import Path
import base64
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
R156 = 'evidence/m1-native-finite-r156a1/image001'
R157 = 'evidence/m1-installed-readiness-r157a1/image001'
INSTALLATION = 'evidence/m1-finite-product-r156a1/installation'
HARNESS = 'e641a5000810efb2a453ae847f689b422f7d41a7'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
QA_BASE = 'cdc974728e69f590838b82421cd244e36554a74f'
RECEIPT = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
CHECKS = ['preflight', 'response_preflight', 'before_epoch',
          'response_before_epoch', 'after_epoch', 'response_after_epoch']
PINS = {
    R156 + '/result.json': '6a67c078680fa4cb41ae29547c3c9e6e7048f7aeb49327384c37822ea0e88931',
    R156 + '/intent.json': '45b5db7c1057ab2f181b14a6d9481e077f87597b666a2a31c2064b6a58848959',
    R156 + '/ordinary-proof.json': 'c44c6e0806b6cd60bd33f4d410268bcdbd4e06bfe4333b6e77502989e10dfa71',
    R157 + '/result.json': '5bd9879c71d3c2ee2e45762899892f51195068937cf1d30108d5c32127f33426',
    R157 + '/intent.json': '995225a4262b807450226ed252ed4bdc5a9e9cb8f40313ef6acd37aa26bbd72a',
    R157 + '/ordinary-proof.json': 'e93e48abd121f78fbcc0163bf523eb8ebc820ac8b23230c9b39e335649fdfcf8',
    INSTALLATION + '/installation-receipt.json': RECEIPT,
    INSTALLATION + '/installation-binding.json': '5ef09ad06075995fb7d1d82ef49b1712c66c83a7dd7b260fe70850110ba45350',
    INSTALLATION + '/candidate-manifest.json': '7a886c32fd81d046d44715921bdaae5765a6f4e481d33182258cc7aa2bac465a',
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    path = ROOT / name
    require(path.resolve(strict=True) == path and path.is_file(), 'evidence_path')
    return path.read_bytes()


def capture(row):
    raw = base64.b64decode(row['base64'], validate=True)
    require(type(row['bytes']) is int and len(raw) == row['bytes']
            and sha(raw) == row['sha256'], 'capture_digest')
    return raw


def verify_attempt(folder, expected_state, child_name):
    value = json.loads(read(folder + '/result.json'))
    require(value['result'] == 'PASS' and value['state'] == expected_state
            and value['transportTerminalObserved'] is True and value['transportExitCode'] == 0
            and value['communicationCompletedWithinDeadline'] is True, 'host_acceptance')
    require(value['intentSha256'] == PINS[folder + '/intent.json']
            and value['ordinaryProofSha256'] == PINS[folder + '/ordinary-proof.json'], 'host_binding')
    for filename, key in (('stdout.txt', 'stdoutSha256'), ('stderr.txt', 'stderrSha256'),
                          ('execution-start.json', 'executionStartSha256')):
        require(sha(read(folder + '/' + filename)) == value[key], 'host_capture_digest')
    require(read(folder + '/stderr.txt') == b'', 'outer_stderr')
    transport = json.loads(read(folder + '/stdout.txt'))
    require(transport == value['transport'] and transport['result'] == 'PASS'
            and transport['callerTerminalObserved'] is True and transport['callerExitCode'] == 0
            and transport['pipesComplete'] is True, 'transport_acceptance')
    caller = json.loads(capture(transport['stdout']))
    require(caller == transport['caller'] and capture(transport['stderr']) == b'', 'caller_capture')
    require(caller['result'] == 'PASS' and caller['sameOriginalSupervisor'] is True
            and caller['allOwnedChildrenTerminal'] is True
            and caller['hostMountNamespaceUnchanged'] is True
            and caller['hostMountTableUnchanged'] is True, 'caller_closure')
    for key in ('automaticRetry', 'automaticCleanup', 'fullD3BAccepted', 'm1Accepted',
                'productionReady', 'serviceStarted', 'runtimeAdmissionAuthorized',
                'realBrokerExchangeAccepted'):
        require(caller[key] is False, 'caller_scope')
    require(caller['realModelCalls'] == 0 and caller['brokerMetadataFixtureOnly'] is True, 'model_scope')
    seed, child, obs = caller['seedResult'], caller[child_name], caller['observations']
    require(seed['kind'] == 'R156A1_TASK_FREE_RETAINED_SEED' and seed['previousEpoch'] == 1
            and seed['completedChecks'] == CHECKS and seed['ownerState'] == 'CLOSED'
            and seed['consumerState'] == 'DETACHED'
            and seed['allThreeConnectionsPhysicallyClosed'] is True
            and seed['profileLeaseReleasedNormally'] is True
            and seed['retainedCapturedWhileLeaseHeld'] is True
            and seed['normalLoopShutdown'] is True, 'seed_closure')
    for key in ('executedTasks', 'realModelCalls', 'listenersCreated',
                'outstandingAsyncTasks', 'outstandingThreads'):
        require(type(seed[key]) is int and seed[key] == 0, 'seed_work')
    require(seed['parentPid'] == transport['callerPid']
            and seed['pid'] == obs['seed']['pid']
            and seed['startTicks'] == obs['seed']['startTicks'], 'seed_process_identity')
    require(child['childExited'] is True and child['volumeMayClose'] is True
            and child['observedAfterUnknown'] is False and child['owner']['epoch'] == 2
            and child['owner']['completedChecks'] == CHECKS
            and child['pid'] == child['owner']['pid'] == obs['retained']['pid']
            and child['childStartTicks'] == obs['retained']['startTicks']
            and child['inputSha256'] == obs['retained']['payloadSha256'], 'child_identity')
    require(obs['phase'] == 'COMPLETE' and obs['volumeStage'] == 'CLOSED'
            and obs['originalRetainedVolumes'] == [], 'owned_custody_closed')
    for name in ('seed', 'retained', 'brokerFixture', 'formatter'):
        item = obs[name]
        require(item['phase'] == 'COMPLETED' and item['complete'] is True
                and type(item['exitCode']) is int and item['exitCode'] == 0
                and item.get('overflowed', False) is False, 'owned_process_terminal')
        capture(item['stdout'])
        capture(item['stderr'])
    require(json.loads(capture(obs['seed']['stdout'])) == seed
            and json.loads(capture(obs['retained']['stdout'])) == child['owner']
            and sha(capture(obs['retained']['stdout'])) == child['stdoutSha256']
            and sha(capture(obs['retained']['stderr'])) == child['stderrSha256'], 'owned_raw_frames')
    close = caller['closure']
    require(close['stop']['state'] == 'UNMOUNTED' and close['finish']['state'] == 'CLOSED', 'normal_close')
    for key in ('ownedUsersGone', 'loopAttachmentGone', 'fenceRemovedAfterCleanup', 'leaseReleasedLast'):
        require(close['finish'][key] is True, 'normal_close_postconditions')
    require(obs['events'][-5:] == ['NORMAL_STOP', 'NORMAL_FINISH', 'VOLUME_CLOSED',
                                  'VERIFY_NORMAL_CLOSE', 'COMPLETE'], 'normal_close_order')
    return value, caller


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def blobs(commit, paths):
    found = {}
    for record in git('ls-tree', '-r', '-z', commit, '--', *paths).split(b'\0'):
        if not record:
            continue
        header, path = record.split(b'\t', 1)
        mode, kind, blob = header.decode().split()
        require(kind == 'blob' and mode == '100644', 'packaged_git_object')
        found[path.decode('utf-8')] = blob
    require(set(found) == set(paths), 'packaged_git_inventory')
    return found


def main():
    require(not sys.flags.optimize, 'verification_assertions_enabled')
    for name, expected in PINS.items():
        require(sha(read(name)) == expected, 'pinned_evidence_changed:' + name)
    finite, f = verify_attempt(R156, 'SAME_IMAGE_SEED_FINITE_ACCEPTED', 'finite')
    ready, r = verify_attempt(R157, 'SAME_IMAGE_SEED_READINESS_ACCEPTED', 'readiness')
    installation = r['installation']
    require(installation == f['installation'] and installation['harnessCommit'] == HARNESS
            and installation['nativeFeature'] == NATIVE and installation['receiptSha256'] == RECEIPT
            and installation['sourceFileCount'] == 838 and installation['dependencyFileCount'] == 1162
            and installation['rootDevice'] == 2096 and installation['rootInode'] == 29702
            and installation['verifiedInstalledBytesNow'] is True
            and installation['sourceAndDependenciesReadBack'] is True, 'same_current_installation')
    for key in ('executionAuthorized', 'projectedReadinessAccepted', 'finiteWorkExecuted'):
        require(installation[key] is False, 'original_source_receipt_unchanged')
    require(f['image']['path'] != r['image']['path'] and f['image']['inode'] != r['image']['inode']
            and f['image']['size'] == r['image']['size'] == 64 * 1024 * 1024
            and f['closure']['stop']['token'] != r['closure']['stop']['token'], 'separate_fresh_lifecycles')
    require(r['executedTasks'] == 0 and r['finiteWorkExecuted'] is False
            and r['projectedReadinessAccepted'] is True
            and r['readiness']['state'] == 'SUPERVISED_PROJECTED_OWNER_CLOSED', 'readiness_only')
    owner = f['finite']['owner']
    cases = owner['caseReceipts']
    require([x['kind'] for x in cases] == ['normal', 'replay', 'new', 'error']
            and [x['computationCount'] for x in cases] == [1, 1, 2, 3]
            and cases[-1]['outcome'] == 'failed', 'finite_cases')
    for key in ('admissionId', 'apiResultSha256', 'storedResultSha256', 'requestId'):
        require(cases[0][key] == cases[1][key], 'original_replay_identity')
    require(cases[2]['admissionId'] != cases[0]['admissionId']
            and owner['model']['kind'] == 'scripted-factory-fixture'
            and owner['model']['realProviderCalls'] == 0
            and owner['close']['physicalConnectionsClosed'] == 3
            and owner['close']['sameThreeConnections'] is True
            and owner['close']['callerLeaseReleased'] is True, 'finite_original_closure')
    manifest = json.loads(read(INSTALLATION + '/candidate-manifest.json'))
    sources = {path: row for path, row in manifest['fileManifest'].items()
               if row['repository'] == 'harness'}
    require(len(sources) == 81 and manifest['sourceFileCount'] == 838
            and manifest['nativeSourceFileCount'] == 756, 'source_counts')
    head = git('rev-parse', 'HEAD').decode().strip()
    prior, current = blobs(HARNESS, list(sources)), blobs(head, list(sources))
    for path, row in sources.items():
        raw = read(path)
        require(sha(raw) == row['sha256'] and len(raw) == row['bytes']
                and prior[path] == current[path] == row['gitBlob'], 'packaged_source_changed:' + path)
    require(git('rev-parse', 'HEAD').decode().strip() == head, 'head_changed_during_verification')
    print(json.dumps({'kind': 'R157A1_JOINT_P1_ACCEPTANCE', 'result': 'PASS', 'p1Complete': True,
        'atUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'qaBaseCommit': QA_BASE,
        'verifiedHead': head, 'installedHarnessCommit': HARNESS, 'nativeFeature': NATIVE,
        'installation': installation, 'evidenceSha256': PINS, 'packagedHarnessFileCount': len(sources),
        'packagedHarnessSourcesUnchanged': True, 'packagedHarnessFiles': sources,
        'separateFreshImageLifecycles': True, 'finiteCases': cases,
        'readiness': {'seedEpoch': 1, 'readinessEpoch': 2, 'completedChecks': CHECKS,
                      'executedTasks': 0, 'realModelCalls': 0, 'normalClose': True},
        'runtimeChanged': False, 'runtimeReinstalled': False, 'finiteAttemptRepeated': False,
        'modelFactoryFixtureOnly': True, 'realBrokerExchangeAccepted': False,
        'serviceStarted': False, 'runtimeAdmissionAuthorized': False,
        'restartReplayAccepted': False, 'p2Complete': False, 'p3Complete': False,
        'p4Complete': False, 'p5Complete': False, 'fullD3BAccepted': False,
        'm1Accepted': False, 'productionReady': False, 'newNativeExecutionInVerifier': False,
        'publicationCiRecordedSeparately': True}, sort_keys=True, indent=2) + '\n', end='')


if __name__ == '__main__':
    main()
