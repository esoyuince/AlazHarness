"""Ordinary-user M96Q native metadata qualification in the approved P71C lab.

Only owned temporary SQLite fixtures are created/removed. The observer never
opens their contents. No mount/namespace/UID/config change, Hermes, or broker.
No WAL is enabled. This does NOT certify persistent Gateway or power-loss safety.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_storage_mounts as m


def identity():
    return {'uid':os.getuid(),'euid':os.geteuid(),'gid':os.getgid(),
            'groups':os.getgroups(),'mnt':os.readlink('/proc/self/ns/mnt'),
            'user':os.readlink('/proc/self/ns/user')}


def inventory(home):
    return {p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                    'inode':p.stat().st_ino,'device':p.stat().st_dev,
                    'mode':p.stat().st_mode,'uid':p.stat().st_uid,
                    'mtimeNs':p.stat().st_mtime_ns,'nlink':p.stat().st_nlink}
            for p in sorted(home.iterdir()) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected',required=True)
    args=parser.parse_args()
    if sys.platform!='linux' or os.getuid()!=23001 or os.getgid()!=23003:
        raise ValueError('designated_unprivileged_lab_user_required')
    cfg=json.loads(args.expected);cfg['device']=tuple(cfg['device'])
    expected=m.ExpectedMount(**cfg)
    before=identity();raw=Path('/proc/self/mountinfo').read_bytes()
    source_names=('packages/claw-hermes/gateway_storage_mounts.py',
                  'tests/test_gateway_storage_mounts.py',
                  'scripts/qa/n97k_storage_mount_probe.py')
    hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names}
    checks={};details={};roots=[];active=False;attempted=[];opens=[]
    def audit(event,values):
        if not active:return
        if event=='open':
            path=values[0];mode=values[1];flags=values[2]
            if path!='/proc/self/mountinfo' or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
                attempted.append(event);raise AssertionError('observer_content_or_write_open')
            opens.append(path)
        if event in ('os.remove','os.rename','os.mkdir','os.chmod','os.chown',
                     'os.link','os.symlink','subprocess.Popen','socket.__new__'):
            attempted.append(event);raise AssertionError('observer_mutation_or_execution')
    sys.addaudithook(audit)
    def observe(home,contract=expected):
        nonlocal active
        active=True
        try:return m.observe_profile_mounts(home,contract)
        finally:active=False
    def refused(home,reason,contract=expected):
        try:observe(home,contract)
        except m.StorageMountRejected as exc:return str(exc)==reason
        return False
    with tempfile.TemporaryDirectory(prefix='alaz-n97k-profile-',dir='/tmp') as tmp:
        home=Path(tmp).resolve();roots.append(home)
        for name in m.DATABASE_NAMES:
            with closing(sqlite3.connect(home/name)) as conn:
                assert conn.execute('PRAGMA journal_mode=PERSIST').fetchone()==('persist',)
                conn.execute('PRAGMA synchronous=FULL')
                conn.execute('CREATE TABLE owned_fixture (marker TEXT)')
                conn.execute("INSERT INTO owned_fixture VALUES ('n97k-dummy-only')")
                conn.commit()
        checks['real_two_sqlite_databases_and_journals']=all((home/n).is_file()
            for n in m.DATABASE_NAMES+tuple(n+'-journal' for n in m.DATABASE_NAMES))
        find=subprocess.run(['/usr/bin/findmnt','--json','--target',str(home),
            '--output','ID,MAJ:MIN,FSROOT,TARGET,FSTYPE'],capture_output=True,text=True,timeout=5,check=True)
        independent=json.loads(find.stdout)['filesystems'];assert len(independent)==1
        f=independent[0];details['independentFindmnt']=f
        checks['independent_findmnt_matches_expected']=(int(f['id']),tuple(map(int,f['maj:min'].split(':'))),
            f['fsroot'],f['target'],f['fstype'])==(expected.mount_id,expected.device,
                                                expected.root,expected.mount_point,expected.filesystem)
        original=inventory(home);positive=observe(home);details['observation']=positive
        checks['actual_ext4_profile_observed']=positive['state']=='CONFIGURED_MOUNT_OBSERVED' and positive['filesystem']=='ext4'
        checks['actual_present_journals_observed']=positive['presentFiles']==4 and positive['sidecarsObserved']==2
        checks['observer_did_not_mutate_present_files']=inventory(home)==original
        checks['wrong_expected_mount_rejected']=refused(home,'storage_mount_binding_mismatch',
                                                         replace(expected,mount_id=expected.mount_id+100000))
        checks['wrong_expected_device_rejected']=refused(home,'storage_mount_binding_mismatch',
                                                         replace(expected,device=(expected.device[0],expected.device[1]+1)))
        checks['wrong_expected_root_rejected']=refused(home,'storage_mount_binding_mismatch',
                                                       replace(expected,root='/unrelated-subvolume'))
        missing=home/'missing-profile';missing.mkdir()
        (missing/'state.db').write_bytes(b'owned missing pair fixture')
        checks['missing_replay_refused_without_creation']=refused(missing,'storage_required_database_missing') and not (missing/'runs_idempotency.db').exists()
        alias=home/'fixture-hardlink';os.link(home/'state.db',alias)
        checks['real_hardlink_refused']=refused(home,'storage_regular_single_file_required');alias.unlink()
        linked=home/'linked-profile';linked.symlink_to(home,target_is_directory=True)
        try:
            observe(linked);checks['real_symlink_refused']=False
        except m.StorageMountRejected as exc:
            checks['real_symlink_refused']=str(exc) in ('storage_profile_not_canonical','storage_profile_linked')
        linked.unlink()
        saved=home/'saved-journal';(home/'state.db-journal').rename(saved)
        (home/'state.db-journal').mkdir()
        checks['sidecar_directory_refused']=refused(home,'storage_regular_single_file_required')
        (home/'state.db-journal').rmdir();saved.rename(home/'state.db-journal')
        checks['second_observation_succeeds_after_fixture_cleanup']=observe(home)['state']=='CONFIGURED_MOUNT_OBSERVED'
        # Renaming fixtures can change directory/ctime; original file bytes and inodes must remain.
        final=inventory(home)
        checks['all_original_bytes_and_inodes_preserved']=all(final[n]['sha256']==v['sha256']
            and final[n]['inode']==v['inode'] and final[n]['device']==v['device']
            for n,v in original.items())
        details['filesBefore']=original;details['filesAfter']=final
        with tempfile.TemporaryDirectory(prefix='alaz-n97k-tmpfs-',dir='/dev/shm') as volatile:
            vhome=Path(volatile).resolve();roots.append(vhome)
            for name in m.DATABASE_NAMES:(vhome/name).write_bytes(b'owned volatile file')
            record=m.select_mount(m.parse_mountinfo(Path('/proc/self/mountinfo').read_bytes()),str(vhome))
            checks['actual_tmpfs_refused']=record.filesystem=='tmpfs' and refused(vhome,'storage_volatile_filesystem')
            details['volatileFilesystem']=record.filesystem
        checks['no_durability_or_launch_claim']=all(positive[k] is False for k in (
            'databaseContentsOpened','writesPerformed','sqliteOpenInodeVerified',
            'physicalMediumDurabilityVerified','exclusiveWriterVerified',
            'pairedStoreConsistencyVerified','fullGatewayPersistenceAccepted','launchAuthorized'))
    checks['all_owned_fixtures_removed']=all(not p.exists() for p in roots)
    checks['observer_only_opened_mountinfo']=bool(opens) and not attempted
    checks['identity_and_namespaces_unchanged']=identity()==before
    checks['mount_table_unchanged']=Path('/proc/self/mountinfo').read_bytes()==raw
    checks['sources_unchanged']=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    record={'result':'PASS_SCOPED_NATIVE_MOUNT_OBSERVER' if all(checks.values()) else 'FAIL',
            'checks':checks,'checkCount':len(checks),'details':details,'identity':before,
            'expected':asdict(expected),'mountinfoBeforeSha256':hashlib.sha256(raw).hexdigest(),
            'sourceSha256':hashes,'sqliteVersion':sqlite3.sqlite_version,
            'observerOpenEvents':len(opens),'observerForbiddenEvents':attempted,
            'scope':'ordinary-user existing ext4/tmpfs mounts; owned synthetic SQLite schema, not Hermes',
            'rootCommand':False,'mountsChanged':False,'uidChanged':False,
            'gatewayStarted':False,'brokerStarted':False,'powerLossTested':False,
            'persistentGatewayQualified':False,'fullD3BAccepted':False,'modelCalls':0}
    print(json.dumps(record,sort_keys=True))
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
