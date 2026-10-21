"""Independent F104X rule/failure audit against the preserved source snapshot.

No kernel/filesystem changes. These tests never import or alter the current
canonical guard and never claim an old native receipt applies to newer code.
"""
import ctypes
import errno
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-native-profile-q104e'
PIN=json.loads((E/'candidate-001.json').read_text())['files']['packages/claw-hermes/credential_guard.py']
SOURCE=E/PIN['snapshot']
loader=SourceFileLoader('independent_q104e_guard',str(SOURCE))
spec=importlib.util.spec_from_loader(loader.name,loader)
g=importlib.util.module_from_spec(spec);loader.exec_module(g)
P={'version':1,'enabled':True,'readonly':['/usr/bin'],'writable':['/srv/owned/work'],
   'protected':['/srv/private/canary'],'self_process_metadata':True}

class RuleFailureAudit(unittest.TestCase):
    def simulate(self,opt=False,failed=None,protected=False):
        opened={};closed=[];events=[];rules=[];nextfd=80
        def metadata(path):
            directory=path in ('/usr/bin','/srv/owned/work')
            mode=(stat.S_IFDIR|0o700) if directory else (stat.S_IFREG|0o444)
            if failed=='not_regular' and path.endswith('/mountinfo'):mode=stat.S_IFDIR|0o700
            return SimpleNamespace(st_mode=mode,st_dev=17,st_ino=sum(map(ord,path)))
        def opening(path,flags):
            nonlocal nextfd
            path=str(path);events.append(('open',path,flags))
            if path=='/srv/private/canary':raise PermissionError(errno.EACCES,'fixture')
            if path.endswith('/mountinfo') and failed=='open':raise PermissionError(errno.EACCES,'fixture')
            nextfd+=1;opened[nextfd]=path;return nextfd
        class Kernel:
            def syscall(self,call,*args):
                nr=call.value
                if nr==444:return 70
                if nr==445:
                    rule=args[2]._obj;path=opened[rule.parent_fd]
                    rules.append((path,rule.allowed_access));events.append(('rule',path,rule.allowed_access))
                    return -1 if failed=='add' and path.endswith('/mountinfo') else 0
                if nr==446:events.append(('restrict',));return -1 if failed=='restrict' else 0
                raise AssertionError(nr)
            def prctl(self,call,*args):
                events.append(('prctl',call));return 1 if call==39 else 0
        policy={k:(list(v) if isinstance(v,list) else v) for k,v in P.items()}
        if protected:policy['protected'].append('/proc/211/mountinfo')
        with (patch.object(g,'kernel',return_value=Kernel()),patch.object(g,'abi_version',return_value=3),
              patch.object(g,'_preflight',return_value=0),patch.object(g.os,'getpid',return_value=211),
              patch.object(g.os,'O_PATH',0x200000,create=True),patch.object(g.os,'O_CLOEXEC',0x80000,create=True),
              patch.object(g.os,'O_NOFOLLOW',0x20000,create=True),patch.object(g.os,'open',side_effect=opening),
              patch.object(g.os,'fstat',side_effect=lambda fd:metadata(opened[fd])),
              patch.object(g.os,'close',side_effect=closed.append),
              patch.object(Path,'stat',new=lambda path:metadata(path.as_posix()))):
            try:result=g.apply(policy,self_mount_metadata=opt);error=None
            except (g.GuardRejected,OSError) as exc:result=None;error=exc
        return result,error,opened,closed,rules,events
    def test_snapshot_hash_bound(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),PIN['sha256'])
    def test_each_metadata_rule_is_read_file_only(self):
        r,e,opened,closed,rules,events=self.simulate(True)
        self.assertIsNone(e);meta=[(n,m) for n,m in rules if n.startswith('/proc/')]
        self.assertEqual(len(meta),6);self.assertTrue(all(m==1<<2 for n,m in meta))
        self.assertEqual(meta[-1],('/proc/211/mountinfo',4))
        self.assertEqual(set(closed),set(opened)|{70});self.assertEqual(len(closed),len(set(closed)))
        self.assertIs(r['selfMountMetadata'],True)
    def test_default_has_no_mount_rule_and_preserves_digest(self):
        r,e,*rest=self.simulate()
        self.assertIsNone(e);self.assertEqual(r['metadataReadFileCount'],5)
        self.assertEqual(r['policySha256'],g.policy_digest(g.validate_policy(P)))
        self.assertIs(r['selfMountMetadata'],False)
        self.assertNotIn('/proc/211/mountinfo',[n for n,m in rest[-2]])
    def test_true_digest_is_distinct_and_explicit(self):
        r,e,*_=self.simulate(True)
        self.assertIsNone(e)
        self.assertEqual(r['policySha256'],g.policy_digest(g.validate_policy(P)|{'self_mount_metadata':True}))
        self.assertNotEqual(r['policySha256'],g.policy_digest(g.validate_policy(P)))
    def test_mount_open_failure_does_not_restrict_or_leak_descriptors(self):
        r,e,opened,closed,rules,events=self.simulate(True,'open')
        self.assertIsInstance(e,PermissionError);self.assertIsNone(r)
        self.assertNotIn(('restrict',),events);self.assertEqual(set(closed),set(opened)|{70})
    def test_directory_cannot_masquerade_as_mountinfo(self):
        r,e,opened,closed,rules,events=self.simulate(True,'not_regular')
        self.assertIsInstance(e,g.GuardRejected);self.assertEqual(str(e),'credential_guard_metadata_file')
        self.assertNotIn(('/proc/211/mountinfo',4),rules);self.assertNotIn(('restrict',),events)
        self.assertEqual(set(closed),set(opened)|{70})
    def test_rule_failure_has_no_partial_success_receipt(self):
        r,e,opened,closed,rules,events=self.simulate(True,'add')
        self.assertIsNone(r);self.assertEqual(str(e),'credential_guard_metadata_rule_failed')
        self.assertNotIn(('restrict',),events);self.assertEqual(set(closed),set(opened)|{70})
    def test_restrict_failure_is_not_enforced(self):
        r,e,opened,closed,rules,events=self.simulate(True,'restrict')
        self.assertIsNone(r);self.assertEqual(str(e),'credential_guard_enforcement_failed')
        self.assertEqual(set(closed),set(opened)|{70})
    def test_protected_metadata_conflict_not_opened(self):
        r,e,opened,closed,rules,events=self.simulate(True,protected=True)
        self.assertEqual(str(e),'credential_guard_protected_metadata');self.assertIsNone(r)
        self.assertNotIn('/proc/211/mountinfo',opened.values());self.assertNotIn(('restrict',),events)
        self.assertEqual(set(closed),set(opened)|{70})
    def test_metadata_open_has_nofollow_path_and_cloexec(self):
        r,e,opened,closed,rules,events=self.simulate(True)
        self.assertIsNone(e)
        for event in events:
            if event[0]=='open' and event[1].startswith('/proc/'):
                self.assertEqual(event[2],0x200000|0x80000|0x20000)
    def test_generic_policy_cannot_smuggle_mount_grant(self):
        for name,value in (('self_mount_metadata',True),('mountinfo','/proc/1/mountinfo'),('metadata_pid',1)):
            with self.subTest(name=name),self.assertRaises(g.GuardRejected):g.validate_policy(P|{name:value})
    def test_opt_in_without_process_metadata_refuses_before_kernel(self):
        for p in ({k:v for k,v in P.items() if k!='self_process_metadata'},P|{'self_process_metadata':False}):
            with patch.object(g,'kernel') as k,self.assertRaises(g.GuardRejected):g.apply(p,self_mount_metadata=True)
            k.assert_not_called()
if __name__=='__main__':unittest.main()
