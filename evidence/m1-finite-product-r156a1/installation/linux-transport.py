
import hashlib,io,json,os,pathlib,re,stat,subprocess,sys,zipfile
LAB='AlazHarness-D3B-P71C'
PYTHON='/usr/bin/python3.12'
INPUT=pathlib.Path('/opt/alaz-r156a1-install-input')
DEST=pathlib.Path('/opt/alaz-r156a1')
DEPS='/opt/alaz-f126c1a6/dependencies'
MAX=24*1024*1024
FILES=('candidate/manifest.json','candidate/projected-source.tar',
       'scripts/build_projected_candidate.py','scripts/install_projected_candidate.py')
report={'kind':'R156A1_SOURCE_INSTALL_OPERATION','phase':'PREFLIGHT','installed':False,
        'executionAuthorized':False,'projectedReadinessAccepted':False,
        'finiteWorkExecuted':False,'realModelCalls':0,'mountsChanged':False,
        'servicesChanged':False,'dependencyDownloads':0,'automaticCleanup':False}
created=False
def sha(data):return hashlib.sha256(data).hexdigest()
def trusted(path,directory):
    assert path.is_absolute() and path.resolve(strict=True)==path,'noncanonical_input_ancestry'
    for p in (path,*path.parents):
        s=p.lstat()
        assert s.st_uid==s.st_gid==0 and not s.st_mode&0o022 and not stat.S_ISLNK(s.st_mode),'untrusted_input_ancestry'
    assert path.is_dir() if directory else path.is_file()
def put(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fchmod(stream.fileno(),0o644);os.fsync(stream.fileno())
    assert path.read_bytes()==data,'provisioning_readback_mismatch'
def new_directory(path):
    path.mkdir(mode=0o700)
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:os.fchmod(fd,0o755);os.fsync(fd)
    finally:os.close(fd)
try:
    assert len(sys.argv)==2,'transport_argument_count'
    intent=json.loads(sys.argv[1])
    assert intent['kind']=='R156A1_SOURCE_INSTALL_INTENT'
    assert intent['lab']==LAB and intent['inputDirectory']==str(INPUT) and intent['destination']==str(DEST)
    assert intent['dependencyRoot']==DEPS and intent['nativeFeature']=='d1516731308de8e87130dc68124e69aad35d6911'
    assert intent['harnessCommit']=='e641a5000810efb2a453ae847f689b422f7d41a7'
    assert intent['manifestSha256']=='7a886c32fd81d046d44715921bdaae5765a6f4e481d33182258cc7aa2bac465a'
    assert intent['archiveSha256']=='3c829db65670756abd531d146aa72c0dc5b3773cd750fc87d26567763f3caef8'
    assert intent['pythonSha256']=='e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
    assert os.environ.get('WSL_DISTRO_NAME')==LAB
    assert pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()==LAB
    assert not pathlib.Path('/mnt/c/Windows').exists(),'windows_mount_present'
    assert sys.platform=='linux' and os.uname().machine=='x86_64'
    assert sys.executable==PYTHON and sys.flags.isolated==1 and sys.dont_write_bytecode and not sys.flags.optimize
    assert os.getresuid()==os.getresgid()==(0,0,0),'host_root_required'
    for name in ('uid_map','gid_map'):
        assert pathlib.Path('/proc/self',name).read_text().split()==['0','0','4294967295'],'initial_userns_required'
    trusted(pathlib.Path(PYTHON),False)
    assert sha(pathlib.Path(PYTHON).read_bytes())==intent['pythonSha256'],'interpreter_changed'
    trusted(INPUT.parent,True)
    assert not os.path.lexists(INPUT) and not os.path.lexists(DEST),'fresh_paths_required'
    raw=sys.stdin.buffer.read(MAX+1)
    assert len(raw)==intent['bundleBytes']<=MAX and sha(raw)==intent['bundleSha256'],'bundle_identity'
    assert set(intent['members'])==set(FILES),'member_inventory'
    data={}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist()
        assert len(infos)==len(FILES) and {i.filename for i in infos}==set(FILES),'bundle_members'
        for info in infos:
            assert info.compress_type==zipfile.ZIP_STORED and not info.is_dir(),'bundle_encoding'
            expected=intent['members'][info.filename]
            assert info.file_size==info.compress_size==expected['bytes'] and 0<info.file_size<=MAX,'member_bound'
            value=archive.read(info)
            assert len(value)==expected['bytes'] and sha(value)==expected['sha256'],'member_identity'
            data[info.filename]=value
    assert sha(data['candidate/manifest.json'])==intent['manifestSha256']
    assert sha(data['candidate/projected-source.tar'])==intent['archiveSha256']
    assert sha(data['scripts/build_projected_candidate.py'])=='7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b'
    assert sha(data['scripts/install_projected_candidate.py'])==intent['installerSha256']
    report['phase']='STAGING_REVIEWED_INPUTS'
    new_directory(INPUT);created=True
    for folder in ('candidate','scripts'):
        new_directory(INPUT/folder)
    put(INPUT/'operator-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode())
    for name in FILES:put(INPUT/name,data[name])
    report['phase']='INSTALLER_INVOKED'
    command=[PYTHON,'-I','-B',str(INPUT/'scripts/install_projected_candidate.py'),
        '--candidate-directory',str(INPUT/'candidate'),'--destination',str(DEST),
        '--dependencies',DEPS,'--expected-manifest-sha256',intent['manifestSha256'],
        '--expected-archive-sha256',intent['archiveSha256'],
        '--expected-harness-commit',intent['harnessCommit'],
        '--expected-python-sha256',intent['pythonSha256']]
    report['installerSpawnAttempted']=True
    process=subprocess.Popen(command,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'},
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    report['installerPid']=process.pid
    try:
        out,err=process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        report.update(phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True)
        raise RuntimeError('installer_timeout_unknown')
    report['installerTerminalObserved']=True
    assert len(out)<=1024*1024 and len(err)<=65536,'installer_output_bound'
    report.update(installerExitCode=process.returncode,installerStdout=out.decode('utf-8'),installerStderr=err.decode('utf-8'))
    assert process.returncode==0,'installer_refused_or_failed'
    result=json.loads(out)
    assert type(result) is dict and result.get('result')=='PASS' and result.get('kind')=='VERIFIED_PROJECTED_INSTALLATION','installer_success_receipt_missing'
    assert result.get('installed') is True and result.get('destination')==str(DEST),'installer_destination_receipt'
    assert result.get('harnessCommit')==intent['harnessCommit'] and result.get('nativeFeature')==intent['nativeFeature'],'installer_source_receipt'
    assert result.get('sourceManifestSha256')==intent['manifestSha256'] and result.get('archiveSha256')==intent['archiveSha256'],'installer_candidate_receipt'
    assert type(result.get('sourceFileCount')) is int and result['sourceFileCount']==838 and type(result.get('dependencyFileCount')) is int and result['dependencyFileCount']==1162,'installer_inventory_receipt'
    assert all(result.get(k) is False for k in ('executionAuthorized','projectedReadinessAccepted','finiteWorkExecuted')),'installer_execution_claim'
    assert type(result.get('realModelCalls')) is int and result['realModelCalls']==0,'installer_model_claim'
    assert result.get('sourceAndDependenciesReadBack') is True and result.get('rootControlledAncestryVerified') is True,'installer_readback_receipt'
    assert type(result.get('receiptSha256')) is str and re.fullmatch('[0-9a-f]{64}',result['receiptSha256']),'installer_receipt_digest'
    python=result.get('python')
    assert type(python) is dict and python.get('path')==PYTHON and python.get('sha256')==intent['pythonSha256'] and python.get('uid')==python.get('gid')==0 and python.get('mode')==0o755,'installer_python_receipt'
    report.update(phase='INSTALLED_SOURCE_ONLY',installed=True,installerResult=result,
                  inputDirectory=str(INPUT),destination=str(DEST),pythonSha256=intent['pythonSha256'],
                  bundleSha256=intent['bundleSha256'])
except BaseException as exc:
    report.update(errorType=type(exc).__name__,errorCode=str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else 'local_io_or_parse_failed')
    if report.get('installerSpawnAttempted') and not report.get('installerTerminalObserved'):
        report.update(failurePhase=report['phase'],phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True)
report['inputDirectoryCreated']=created
report['destinationExists']=os.path.lexists(DEST)
if created:
    try:put(INPUT/'operator-result.json',(json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
    except BaseException as exc:report['operatorResultWriteError']=type(exc).__name__;report['installed']=False
print(json.dumps(report,sort_keys=True),flush=True)
raise SystemExit(0 if report['installed'] and report['phase']=='INSTALLED_SOURCE_ONLY' else 2)
