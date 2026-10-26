import base64,hashlib,json,os,pathlib,re,sqlite3,stat,subprocess,sys,time
P=pathlib.Path
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
def require(ok,reason):
    if not ok:raise RuntimeError(reason)
def put(path,raw,mode):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
report={'kind':'R155A1_ORDINARY_NATIVE_SEED_PROOF','result':'NOT_ACCEPTED','rootUsed':False,
        'projectedReadinessAccepted':False,'sameImageReadinessAccepted':False,'fullD3BAccepted':False,
        'automaticCleanup':False,'automaticRetry':False,'nativeAccepted':False,'phase':'PREFLIGHT'}
process=None
try:
    require(len(sys.argv)==4,'argument_count')
    attempt,expected,size=sys.argv[1:]
    require(re.fullmatch(r'ordinary00[1-9]',attempt) is not None,'attempt_id')
    require(expected=='2c004f6a7154d95af216517c867f1e3cafd63a05e05838f65752eca1b89c5f01','source_pin')
    require(os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
            and set(os.getgroups())<={23003},'ordinary_actor')
    require(sys.executable=='/usr/bin/python3.12' and sys.version_info[:2]==(3,12)
            and sys.flags.isolated==1 and sys.dont_write_bytecode and not sys.flags.optimize,'interpreter')
    require(sha(P(sys.executable).read_bytes())=='e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f','python_pin')
    require(os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'
            and P('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'
            and not P('/mnt/c/Windows').exists(),'dedicated_lab')
    base=P('/tmp/alaz-r155a1-'+attempt)
    require(not os.path.lexists(base),'fresh_home_required')
    raw=sys.stdin.buffer.read(262145)
    require(len(raw)==int(size)<=262144 and sha(raw)==expected,'producer_bytes')
    os.umask(0o077)
    base.mkdir(mode=0o700)
    report.update(phase='FRESH_HOME_CREATED',path=str(base),sourceSha256=expected,
                  sqliteVersion=sqlite3.sqlite_version,sqliteVersionInfo=list(sqlite3.sqlite_version_info),
                  controllerPid=os.getpid(),supplementaryGroups=os.getgroups())
    source=base/'bootstrap_retained_profile.py'
    put(source,raw,0o444)
    home=base/'profile';home.mkdir(mode=0o700);info=home.stat()
    require(source.read_bytes()==raw and home.resolve()==home,'source_or_home_changed')
    argv=['/usr/bin/python3.12','-I','-B',str(source),'--home',str(home),
          '--instance-id','r155a1-'+attempt,'--expected-profile-device',str(info.st_dev),
          '--expected-profile-inode',str(info.st_ino),'--gateway-uid','23001',
          '--socket-group-gid','23003','--parent-pid',str(os.getpid())]
    report.update(phase='PRODUCER_SPAWN_ATTEMPT',nativeProcessAttempted=True)
    started=time.monotonic()
    process=subprocess.Popen(argv,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'},
                             stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    report['producerPid']=process.pid
    try:out,err=process.communicate(timeout=45)
    except subprocess.TimeoutExpired as exc:
        report.update(phase='PRODUCER_OUTCOME_UNKNOWN',processMayBeRunning=True,
                      partialStdoutBase64=base64.b64encode((exc.output or b'')[:32768]).decode(),
                      partialStderrBase64=base64.b64encode((exc.stderr or b'')[:65536]).decode())
        raise RuntimeError('producer_timeout_unknown')
    report.update(phase='PRODUCER_TERMINAL',producerExitCode=process.returncode,
                  producerTerminalObserved=True,elapsedMillis=int((time.monotonic()-started)*1000),
                  producerStdoutSha256=sha(out),producerStderrSha256=sha(err),
                  producerStdoutBytes=len(out),producerStderrBytes=len(err))
    put(base/'producer.stdout',out,0o600);put(base/'producer.stderr',err,0o600)
    require(len(out)<=32768 and len(err)<=65536,'producer_output_bound')
    report.update(producerStdoutBase64=base64.b64encode(out).decode(),
                  producerStderrBase64=base64.b64encode(err).decode())
    require(process.returncode==0,'producer_refused_or_failed')
    require(out.endswith(b'\n') and out.count(b'\n')==1,'producer_frame')
    value=json.loads(out)
    require(canonical(value)==out,'producer_canonical_frame')
    require(value['kind']=='R155A1_TASK_FREE_RETAINED_SEED' and value['result']=='PASS'
            and value['state']=='RETAINED_SEED_CREATED' and value['phase']=='COMPLETE','producer_success')
    require(value['pid']==process.pid and value['parentPid']==os.getpid()
            and value['home']==str(home) and value['profileIdentity']==[info.st_dev,info.st_ino]
            and value['instanceId']=='r155a1-'+attempt and value['previousEpoch']==1,'producer_identity')
    require(value['resUid']==[23001]*3 and value['resGid']==[23003]*3
            and value['supplementaryGroups']==os.getgroups(),'producer_principal')
    require(value['mountNamespace']==os.readlink('/proc/self/ns/mnt')
            and value['mountNamespaceInode']==P('/proc/self/ns/mnt').stat().st_ino
            and value['mount']['filesystem']=='ext4','producer_actual_mount')
    require(value['completedChecks']==['preflight','response_preflight','before_epoch',
            'response_before_epoch','after_epoch','response_after_epoch'],'producer_six_checks')
    require(value['ownerState']=='CLOSED' and value['consumerState']=='DETACHED'
            and all(value[k] is True for k in ['allThreeConnectionsPhysicallyClosed',
                'profileLeaseReleasedNormally','retainedCapturedWhileLeaseHeld','normalLoopShutdown']),
            'producer_normal_close')
    require(all(type(value[k]) is int and value[k]==0 for k in ['outstandingAsyncTasks',
            'outstandingThreads','executedTasks','realModelCalls','listenersCreated'])
            and all(value[k] is False for k in ['apiAdmissionPublished','projectedReadinessAccepted',
                'fullD3BAccepted','automaticCleanup','automaticRetry']),'producer_scope')
    require(value['installationReceiptSha256']=='137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2'
            and value['harnessCommit']=='e03f7fd4e47fea6a58b749564ab350aeb4237a26'
            and value['nativeFeature']=='d1516731308de8e87130dc68124e69aad35d6911','producer_installed_source')
    probe=value['auxiliaryInitialization']['blockedIpv6CapabilityProbe']
    require(type(probe) is dict and set(probe)=={'count','socketClosed','bindPerformed'}
            and type(probe['count']) is int and probe['count']==1
            and probe['socketClosed'] is True and probe['bindPerformed'] is False,'producer_blocked_probe')
    report.update(phase='COMPLETE',result='PASS',nativeAccepted=True,seed=value,
                  realModelCalls=0,executedTasks=0,physicalDatabaseCloseAccepted=True)
except BaseException as exc:
    report.update(reasonType=type(exc).__name__,reason=str(exc)[:200] if type(exc) is RuntimeError else type(exc).__name__,
                  partialStatePreserved=True)
sys.stdout.buffer.write(canonical(report));sys.stdout.buffer.flush()
raise SystemExit(0 if report['result']=='PASS' else 2)
