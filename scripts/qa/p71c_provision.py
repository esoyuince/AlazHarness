"""One-shot provisioning for the explicitly approved disposable P71C distro only.

Never run on existing Ubuntu/production. Exact marker, paths, IDs, source digest.
No network, service, elevation helper or general command delegation is provided.
"""
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import grp
import stat
import subprocess
import sys
import tarfile

DISTRO='AlazHarness-D3B-P71C'
INSTALL=Path('/opt/alazharness-broker/802fade')
STATE=Path('/srv/alaz-p71c')
GATEWAY,BROKER,GROUP=23001,23002,23003
ARCHIVE_SHA='8c0bbad498ccc877edbce85af535dd0fcd68b2dbf21b72858487577942424451'
SOURCE='802fade74d5b08b26f975738d4aa8d7546dc9cac'

def require(ok, reason):
    if not ok:raise RuntimeError(reason)

def guard():
    require(sys.platform=='linux' and os.getuid()==os.geteuid()==0,'lab_root_required')
    require(Path('/etc/alaz-p71c-lab-id').read_text().strip()==DISTRO,'wrong_lab_marker')
    require(os.environ.get('WSL_DISTRO_NAME')==DISTRO,'wrong_distro')
    require(not Path('/mnt/c/Windows').exists(),'windows_drive_exposed')
    require(Path('/proc/self/uid_map').read_text().split()==['0','0','4294967295'],'not_initial_host_map')
    require(Path('/proc/self/gid_map').read_text().split()==['0','0','4294967295'],'not_initial_group_map')

def create_dir(path,uid=0,gid=0,mode=0o755):
    path.mkdir(mode=mode)
    os.chown(path,uid,gid);os.chmod(path,mode)

def save(path,data,uid=0,gid=0,mode=0o600):
    with path.open('xb') as stream:stream.write(data)
    os.chown(path,uid,gid);os.chmod(path,mode)

def main():
    guard()
    require(not INSTALL.parent.exists() and not STATE.exists(),'fresh_lab_paths_required')
    for uid in (GATEWAY,BROKER):
        try:pwd.getpwuid(uid)
        except KeyError:pass
        else:raise RuntimeError('test_uid_already_used')
    for name in ('alazgateway','alazbroker'):
        try:pwd.getpwnam(name)
        except KeyError:pass
        else:raise RuntimeError('test_name_already_used')
    for key in (GROUP,'alazipc'):
        try:grp.getgrgid(key) if isinstance(key,int) else grp.getgrnam(key)
        except KeyError:pass
        else:raise RuntimeError('test_group_already_used')
    raw=Path('/root/p71c-input/broker-source.tar').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA,'archive_digest')
    manifest=json.loads(Path('/root/p71c-input/manifest.json').read_text())
    require(manifest['sourceCommit']==SOURCE and manifest['archiveSha256']==ARCHIVE_SHA
            and len(manifest['fileManifest'])==57,'manifest_scope')
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
        for member in archive:
            if member.isdir():continue
            require(member.type==tarfile.REGTYPE and not member.linkname and not member.sparse,'regular_only')
            require(member.name.startswith('alazharness-broker/'),'archive_prefix')
            name=member.name.removeprefix('alazharness-broker/')
            p=PurePosixPath(name)
            require(str(p)==name and not p.is_absolute() and '..' not in p.parts
                    and name not in files and name in manifest['fileManifest'],'archive_path')
            wanted=manifest['fileManifest'][name]
            require(member.size==wanted['bytes'] and member.size<2097152,'archive_size')
            with archive.extractfile(member) as handle:data=handle.read(2097153)
            require(hashlib.sha256(data).hexdigest()==wanted['sha256'],'archive_file_digest')
            files[name]=data
    require(set(files)==set(manifest['fileManifest']),'archive_inventory')
    create_dir(INSTALL.parent);create_dir(INSTALL)
    for name,data in files.items():
        dest=INSTALL/name
        missing=[];parent=dest.parent
        while not parent.exists():missing.append(parent);parent=parent.parent
        for directory in reversed(missing):create_dir(directory)
        save(dest,data,mode=0o644)
    for args in (['/usr/sbin/groupadd','--gid',str(GROUP),'alazipc'],
                 ['/usr/sbin/useradd','--uid',str(GATEWAY),'--gid',str(GROUP),'--no-create-home','--no-log-init','--shell','/usr/sbin/nologin','alazgateway'],
                 ['/usr/sbin/useradd','--uid',str(BROKER),'--gid',str(GROUP),'--no-create-home','--no-log-init','--shell','/usr/sbin/nologin','alazbroker']):
        subprocess.run(args,check=True,stdin=subprocess.DEVNULL,capture_output=True,timeout=15)
    create_dir(STATE);create_dir(STATE/'control',mode=0o700)
    create_dir(STATE/'private',BROKER,GROUP,0o700)
    create_dir(STATE/'gateway',GATEWAY,GROUP,0o700)
    for name in ('sock1','sock2'):create_dir(STATE/name,BROKER,GROUP,0o710)
    sys.path.insert(0,str(INSTALL/'packages/claw-hermes'))
    from execution_budget import ExecutionPolicy
    from provider_egress import BrokerConfig
    import principal_launch as launch
    p={'version':1,'enabled':True,'gatewayUid':GATEWAY,'brokerUid':BROKER,
       'socketGroupGid':GROUP,'hostUserNamespace':os.readlink('/proc/self/ns/user')}
    policy=ExecutionPolicy('owned-p71c-no-inference',0,0,64,16,0,0,0,0)
    cfg={'upstream_base_url':'http://127.0.0.1:1/v1','model':policy.model,
         'upstream_bearer':'p'*48,'signing_key':'b'*64,
         'state_db':str(STATE/'gateway/state.db'),'scope':'c'*64,'binding':'d'*64,
         'policy_fingerprint':policy.fingerprint,
         'budget_authority':{'version':1,'enabled':True,'directory':str(STATE/'private/budget'),
                             'budget_id':'a'*32,'policy':asdict(policy)},'principal_contract':p}
    BrokerConfig(**cfg)
    config_data=(json.dumps(cfg,sort_keys=True)+'\n').encode()
    save(STATE/'private/config.json',config_data,BROKER,GROUP)
    py=str(Path(sys.executable).resolve())
    initialize="import sys,json;sys.path.insert(0,'/opt/alazharness-broker/802fade/packages/claw-hermes');from provider_egress import BrokerConfig;from broker_budget import initialize;print(json.dumps(initialize(BrokerConfig(**json.load(open('/srv/alaz-p71c/private/config.json'))))))"
    result=subprocess.run([py,'-I','-B','-c',initialize],user=BROKER,group=GROUP,extra_groups=[],
        stdin=subprocess.DEVNULL,capture_output=True,timeout=15,cwd='/',
        env={'PATH':'/usr/bin:/bin','HOME':'/','LANG':'C.UTF-8'})
    require(result.returncode==0,'explicit_budget_initialization_failed')
    initial=json.loads(result.stdout)
    contracts={}
    for name in ('sock1','sock2'):
        value={'version':1,'enabled':True,'role':'broker','principalContract':p,
               'python':py,'config':str(STATE/'private/config.json'),
               'configSha256':hashlib.sha256(config_data).hexdigest(),'output':str(STATE/name),
               'commandSha256':''}
        value['commandSha256']=launch.command_digest(launch.command(value))
        launch.validate(value);launch.trusted_install(value);launch.deployment(value)
        dest=STATE/'control'/(name+'-contract.json')
        save(dest,(json.dumps(value,sort_keys=True)+'\n').encode())
        contracts[name]={'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    require(all(hashlib.sha256((INSTALL/n).read_bytes()).hexdigest()==v['sha256']
                for n,v in manifest['fileManifest'].items()),'installed_source_drift')
    result={'result':'PROVISIONED_TEST_ONLY','distro':DISTRO,'sourceCommit':SOURCE,
        'archiveSha256':ARCHIVE_SHA,'installedFiles':57,'installPath':str(INSTALL),
        'python':py,'pythonSha256':hashlib.sha256(Path(py).read_bytes()).hexdigest(),
        'principal':p,'contracts':contracts,'initialBudget':initial,
        'controller':launch.observation(),'provisionedUids':[GATEWAY,BROKER],'provisionedGid':GROUP,
        'brokerLaunched':False,'providerCallsAllowed':0}
    save(STATE/'control/provision.json',(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result))

if __name__=='__main__':main()
