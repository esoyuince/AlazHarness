"""Reviewed R156-only finite behavior inserted into exact pinned R155 templates.

These are source templates, never native execution or acceptance records. The
preparer supplies actual installation pins and preserves the other template
bytes. The shared assertion suffix extends the candidate's exact pure protocol.
"""

FINITE_ASSERTION_SUFFIX = '''

WORK = {'protocol': 'alaz-finite-qualification-v1', 'sessionId': 'r156a1-session',
        'requestIds': {'normal': 'r156a1-normal', 'new': 'r156a1-new', 'error': 'r156a1-error'}}


def validate_supervised(value):
    require(type(value) is dict and set(value) == {
        'state', 'pid', 'childStartTicks', 'owner', 'inputSha256', 'stdoutSha256',
        'stderrSha256', 'stderrBytes', 'observedAfterUnknown', 'childExited',
        'volumeMayClose', 'finiteWorkExecuted', 'fullD3BAccepted'}, 'accept_finite_supervisor_fields')
    require(value['state'] == 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED'
            and value['childExited'] is True and value['volumeMayClose'] is True
            and value['finiteWorkExecuted'] is True and value['fullD3BAccepted'] is False
            and value['observedAfterUnknown'] is False, 'accept_finite_supervisor_close')
    require(type(value['pid']) is int and value['pid'] > 0
            and type(value['childStartTicks']) is int and value['childStartTicks'] > 0
            and type(value['stderrBytes']) is int and 0 <= value['stderrBytes'] <= 65536
            and all(_sha(value[name]) for name in ('inputSha256', 'stdoutSha256', 'stderrSha256')),
            'accept_finite_supervisor_identity')
    owner = validate_result(value['owner'], work=WORK, pid=value['pid'], previous_epoch=1)
    require(hashlib.sha256(canonical(owner) + b'\\n').hexdigest() == value['stdoutSha256'],
            'accept_finite_owner_output_binding')
    return copy.deepcopy(value)


def validate_caller(value, manifest_sha):
    require(type(value) is dict and value.get('kind') == 'R156A1_SAME_IMAGE_SEED_FINITE'
            and value.get('result') == 'PASS' and value.get('state') == 'SAME_IMAGE_SEED_FINITE_CLOSED'
            and value.get('manifestSha256') == manifest_sha and _sha(manifest_sha),
            'accept_finite_caller_identity')
    require(all(value.get(name) is True for name in (
        'projectedFiniteAccepted', 'sameImageSeedAndFinite', 'sameOriginalSupervisor',
        'allOwnedChildrenTerminal', 'hostMountNamespaceUnchanged', 'hostMountTableUnchanged',
        'brokerMetadataFixtureOnly', 'finiteWorkExecuted')), 'accept_finite_caller_close')
    require(all(value.get(name) is False for name in (
        'realBrokerExchangeAccepted', 'serviceStarted', 'runtimeAdmissionAuthorized',
        'fullD3BAccepted', 'm1Accepted', 'productionReady', 'automaticCleanup', 'automaticRetry')),
        'accept_finite_caller_excluded_scope')
    require(all(type(value.get(name)) is int and value[name] == count for name, count in (
        ('executedTasks', 3), ('scriptedModelInvocations', 3), ('realModelCalls', 0),
        ('realProviderCalls', 0))), 'accept_finite_caller_work_scope')
    seed = value.get('seedResult')
    installed = value.get('installation')
    require(type(seed) is dict and seed.get('installationReceiptSha256') == INSTALLATION_RECEIPT_SHA
            and seed.get('harnessCommit') == HARNESS_COMMIT and seed.get('previousEpoch') == 1
            and type(installed) is dict and installed.get('receiptSha256') == INSTALLATION_RECEIPT_SHA
            and installed.get('harnessCommit') == HARNESS_COMMIT
            and installed.get('destination') == '/opt/alaz-r156a1'
            and installed.get('verifiedInstalledBytesNow') is True,
            'accept_finite_installed_binding')
    finite = validate_supervised(value.get('finite'))
    observations = value.get('observations')
    child = observations.get('retained') if type(observations) is dict else None
    require(type(child) is dict and child.get('phase') == 'COMPLETED'
            and child.get('pid') == finite['pid'] and child.get('startTicks') == finite['childStartTicks']
            and type(child.get('exitCode')) is int and child['exitCode'] == 0
            and child.get('complete') is True and child.get('overflowed') is False
            and type(child.get('inputWritten')) is int and 0 < child['inputWritten'] <= 65536
            and child.get('payloadSha256') == finite['inputSha256'],
            'accept_finite_original_child_observation')
    import base64
    for name in ('stdout', 'stderr'):
        row = child.get(name)
        require(type(row) is dict and set(row) == {'bytes', 'sha256', 'base64'}
                and type(row['bytes']) is int and 0 <= row['bytes'] <= 65536
                and type(row['base64']) is str and len(row['base64']) <= 87384,
                'accept_finite_observed_output_fields')
        try:
            raw = base64.b64decode(row['base64'], validate=True)
        except (ValueError, UnicodeError):
            raise FiniteProtocolRejected('accept_finite_observed_output_encoding') from None
        require(base64.b64encode(raw).decode('ascii') == row['base64']
                and len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
                and row['sha256'] == finite[name + 'Sha256'], 'accept_finite_observed_output_binding')
        if name == 'stdout':
            require(raw == canonical(finite['owner']) + b'\\n', 'accept_finite_original_owner_frame')
        else:
            require(len(raw) == finite['stderrBytes'], 'accept_finite_stderr_count')
    closure = value.get('closure')
    finish = closure.get('finish') if type(closure) is dict else None
    require(type(finish) is dict and finish.get('state') == 'CLOSED'
            and all(finish.get(name) is True for name in (
                'ownedUsersGone', 'loopAttachmentGone', 'fenceRemovedAfterCleanup', 'leaseReleasedLast')),
            'accept_finite_original_volume_close')
    return copy.deepcopy(value)
'''


CALLER_RUN_FINITE = '''def run_finite(self, view, filesystem, record):
        require(self.seed is not None and self.seed['phase'] == 'COMPLETED'
                and self.finite is None, 'caller_finite_requires_seed')
        self.event('PROJECTED_FINITE_ATTEMPT')
        self.finite = self.volume.run_finite(view, filesystem, record, self.modules.finite.WORK,
            scratch=str(SCRATCH), instance_id=FINITE_INSTANCE, timeout=FINITE_SECONDS)
        self.modules.finite.validate_supervised(self.finite)
        require(self.volume.observe_finite() == self.finite, 'caller_finite_observation_changed')
        self.event('PROJECTED_FINITE_COMPLETED')'''


CALLER_EXECUTE = '''def execute(controller, manifest_sha):
    actor()
    manifest, sources = verify_inputs(manifest_sha)
    seed = load_source('_r156_reviewed_seed', INPUT / SEED_ENTRY, sources[SEED_ENTRY])
    installed = seed.verify_installation()
    require(installed['receiptSha256'] == RECEIPT_SHA, 'caller_installation_changed')
    require(digest(trusted_read('/usr/sbin/mke2fs', 4 * 1024 * 1024)) == FORMATTER_SHA,
            'caller_formatter_changed')
    child = load_source('_r156_reviewed_child', INPUT / CHILD_ENTRY, sources[CHILD_ENTRY])
    finite = load_source('_r156_reviewed_finite_assertion', INPUT / FINITE_ENTRY, sources[FINITE_ENTRY])
    sys.path.insert(0, str(INSTALLATION / 'packages/claw-hermes'))
    import gateway_supervised_launch as supervised
    import gateway_retained_handoff as handoff
    import gateway_state_projection as projection
    import gateway_projection as gateway_projection
    import state_volume_supervisor as volume
    import state_image_lease as image
    import supervised_pipe_capture as capture
    import host_principal as principal
    controller.modules = types.SimpleNamespace(supervised=supervised, handoff=handoff, projection=projection,
        volume=volume, image=image, capture=capture, principal=principal, finite=finite)
    volume.actor()
    view, filesystem = projection_contract()
    gateway_projection.validate(view, filesystem)
    host_namespace = os.readlink('/proc/self/ns/mnt')
    host_mounts = Path('/proc/self/mountinfo').read_bytes()
    pin = controller.provision()
    controller.start_broker(manifest_sha)
    export_preflight = gateway_projection.inspect(view, filesystem)
    controller.event('BEGIN_ORIGINAL_SUPERVISOR')
    controller.volume = supervised.RetainedVolumeSupervisor.begin(pin, CGROUP, MOUNT)
    v = controller.volume
    controller.event('ATTACH_ORIGINAL_SUPERVISOR')
    loop = v.attach()
    controller.event('START_ORIGINAL_WORKER')
    mounted = v.start()
    record = controller.run_seed(manifest, child)
    controller.run_finite(view, filesystem, record)
    closure = controller.close_volume()
    controller.stop_broker()
    controller.event('VERIFY_NORMAL_CLOSE')
    require(os.readlink('/proc/self/ns/mnt') == host_namespace
            and Path('/proc/self/mountinfo').read_bytes() == host_mounts
            and not os.path.ismount(MOUNT) and not any(MOUNT.iterdir())
            and not os.path.lexists(v.fence) and not os.path.lexists(v.scope)
            and not volume.attachments(pin) and not (CGROUP / 'cgroup.procs').read_text().strip()
            and not volume.populated((CGROUP / 'cgroup.events').read_text()), 'caller_close_postconditions')
    current, parent = IMAGE.stat(), IMAGE.parent.stat()
    require(asdict(pin) == asdict(image.ImagePin(str(IMAGE), current.st_dev, current.st_ino, current.st_size,
        current.st_uid, current.st_gid, parent.st_dev, parent.st_ino)), 'caller_final_image_identity')
    controller.event('COMPLETE')
    result = {'kind': 'R156A1_SAME_IMAGE_SEED_FINITE', 'result': 'PASS',
        'state': 'SAME_IMAGE_SEED_FINITE_CLOSED', 'manifestSha256': manifest_sha,
        'installation': installed, 'image': asdict(pin), 'loopPath': loop, 'workerMounted': mounted,
        'seedResult': controller.seed_result, 'finite': controller.finite, 'closure': closure,
        'observations': controller.snapshot(), 'exportEntriesScanned': export_preflight['scanned'],
        'hostMountNamespaceUnchanged': True, 'hostMountTableUnchanged': True,
        'allOwnedChildrenTerminal': True, 'sameOriginalSupervisor': True,
        'sameImageSeedAndFinite': True, 'projectedFiniteAccepted': True,
        'brokerMetadataFixtureOnly': True, 'realBrokerExchangeAccepted': False,
        'executedTasks': 3, 'scriptedModelInvocations': 3, 'realModelCalls': 0, 'realProviderCalls': 0,
        'serviceStarted': False, 'runtimeAdmissionAuthorized': False, 'finiteWorkExecuted': True,
        'fullD3BAccepted': False, 'm1Accepted': False, 'productionReady': False,
        'automaticCleanup': False, 'automaticRetry': False}
    return finite.validate_caller(result, manifest_sha)'''


TRANSPORT_CLASSIFY = '''def classify(process, identity, out, err, finite, manifest_sha):
    if out:
        require(not err, 'transport_mixed_caller_frames')
        result = parse(out, MAX_OUTPUT)
        finite['validate_caller'](result, manifest_sha)
        require(process.wait(timeout=5) == 0, 'transport_caller_exit')
        return {'result': 'PASS', 'state': 'CALLER_TERMINAL_ACCEPTED', 'callerTerminalObserved': True,
                'callerExitCode': 0, 'caller': result}
    result = parse(err, MAX_OUTPUT)
    require(result.get('kind') == 'R156A1_SAME_IMAGE_SEED_FINITE'
            and result.get('result') == 'NOT_ACCEPTED', 'transport_negative_result')
    custody = result.get('custody')
    if custody is not None:
        require(type(custody) is dict and set(custody) == {'state', 'pid', 'startTicks'}
                and custody['state'] == 'RETAINED_CONTROLLER'
                and type(custody['pid']) is int and custody['pid'] == process.pid
                and type(custody['startTicks']) is int and custody['startTicks'] == identity['startTicks']
                and process.poll() is None and process_identity(process.pid) == identity,
                'transport_custody_not_live_unknown')
        return {'result': 'NOT_ACCEPTED', 'state': 'CALLER_RETAINED_OUTCOME_UNKNOWN',
                'callerTerminalObserved': False, 'verifiedLiveCustody': True, 'custody': custody,
                'caller': result}
    require(result.get('state') == 'REFUSED' and process.wait(timeout=5) == 2,
            'transport_unclassified_caller_unknown')
    return {'result': 'NOT_ACCEPTED', 'state': 'CALLER_TERMINAL_REFUSED',
            'callerTerminalObserved': True, 'callerExitCode': 2, 'caller': result}'''


HOST_CURRENT_INPUTS = '''def current_inputs():
    sources = {name: read_file(ROOT / name) for name in sorted(SOURCES)}
    transport = read_file(ROOT / TRANSPORT)
    require(sha(transport) == REVIEWED_TRANSPORT_SHA and sha(sources[CALLER]) == REVIEWED_CALLER_SHA
            and sha(sources[CHILD]) == REVIEWED_CHILD_SHA
            and sha(sources[FINITE]) == REVIEWED_FINITE_SHA, 'runner_reviewed_sources_changed')
    return sources, transport, read_file(SELF), read_file(ROOT / ORDINARY_DRIVER)'''


HOST_FINITE_LOADER = '''def load_finite_assertion():
    raw = read_file(ROOT / FINITE)
    require(sha(raw) == REVIEWED_FINITE_SHA, 'runner_finite_assertion_changed')
    namespace = {'__name__': '_r156_verified_finite_assertion', '__file__': str(ROOT / FINITE)}
    exec(compile(raw, str(ROOT / FINITE), 'exec'), namespace)
    return namespace'''


HOST_TRANSPORT_RESULT = '''def transport_result(out, err, exit_code, intent):
    require(not err, 'runner_transport_stderr')
    report = parse(out, MAX_OUTPUT)
    require(type(report) is dict and report.get('kind') == 'R156A1_ROOT_TRANSPORT'
            and report.get('rootUsed') is True and report.get('automaticRetry') is False
            and report.get('automaticCleanup') is False, 'runner_transport_identity')
    if report.get('result') != 'PASS':
        observation = {'result': 'UNKNOWN', 'state': 'ROOT_OUTCOME_UNKNOWN', 'transport': report,
                       'continuingLiveCustodyVerified': False}
        if report.get('state') == 'CALLER_RETAINED_OUTCOME_UNKNOWN':
            require(exit_code == 2 and report.get('intentSha256') == sha(canonical(intent))
                    and report.get('manifestSha256') == intent['manifestSha256']
                    and report.get('verifiedLiveCustody') is True
                    and report.get('callerTerminalObserved') is False
                    and report.get('pipesComplete') is True, 'runner_retained_observation')
            custody = exact(report.get('custody'), {'state', 'pid', 'startTicks'}, 'runner_retained_fields')
            require(custody['state'] == 'RETAINED_CONTROLLER'
                    and number(custody['pid'], 1) == number(report.get('callerPid'), 1)
                    and number(custody['startTicks'], 1) == number(report.get('callerStartTicks'), 1),
                    'runner_retained_identity')
            caller = parse(output_row(report.get('stderr'), 524288), 524288)
            require(not output_row(report.get('stdout'), 524288) and caller == report.get('caller')
                    and caller.get('kind') == 'R156A1_SAME_IMAGE_SEED_FINITE'
                    and caller.get('result') == 'NOT_ACCEPTED'
                    and caller.get('state') == 'OUTCOME_UNKNOWN' and caller.get('custody') == custody,
                    'runner_retained_diagnostic')
            observation.update(custodyObservedBeforeTransportExit=custody)
        return observation
    require(type(exit_code) is int and exit_code == 0 and report.get('phase') == 'OBSERVED'
            and report.get('state') == 'CALLER_TERMINAL_ACCEPTED'
            and report.get('intentSha256') == sha(canonical(intent))
            and report.get('manifestSha256') == intent['manifestSha256']
            and report.get('pipesComplete') is True and report.get('callerTerminalObserved') is True
            and type(report.get('callerExitCode')) is int and report['callerExitCode'] == 0,
            'runner_transport_acceptance')
    number(report.get('callerPid'), 1)
    number(report.get('callerStartTicks'), 1)
    caller = parse(output_row(report.get('stdout'), 524288), 524288)
    require(not output_row(report.get('stderr'), 524288) and caller == report.get('caller'),
            'runner_caller_output_binding')
    load_finite_assertion()['validate_caller'](caller, intent['manifestSha256'])
    validate_seed(caller.get('seedResult'), home='/srv/alaz-r156a1/mount/profile', instance='r156a1-seed')
    return {'result': 'PASS', 'state': 'SAME_IMAGE_SEED_FINITE_ACCEPTED', 'transport': report,
            'projectedFiniteAccepted': True, 'finiteWorkExecuted': True, 'realProviderCalls': 0,
            'continuingLiveCustodyVerified': False}'''
