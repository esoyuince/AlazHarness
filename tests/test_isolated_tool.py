"""Offline isolation contracts. No Docker, external network or real model runs."""
from __future__ import annotations
import copy
from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
# Standalone transfer/testing puts these files together instead.
if not (ROOT/'packages/claw-hermes/isolated_tool.py').exists():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import isolated_tool as m

P = m.ToolSandboxPolicy('sha256:'+'a'*64)
OWNER = 'b'*32
CID = 'c'*64
CAPSULE = PurePosixPath('/srv/alaz-capsules/fixture')


def inspection():
    return {'Id':CID, 'Image':P.image, 'Name':'/alaz-isolated-'+OWNER,
            'Config':{'Labels':{m.OWNER_LABEL:OWNER}, 'User':'65534:65534',
                      'WorkingDir':'/workspace', 'Entrypoint':['/usr/bin/env'],
                      'Cmd':['-i',*m.FIXED_ENV,'/usr/bin/python3','-I','-B','/workspace/program.py'],
                      'Volumes':None, 'ExposedPorts':None},
            'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,
                          'CapDrop':['ALL'],'CapAdd':None,'SecurityOpt':['no-new-privileges'],
                          'PidsLimit':32,'Memory':134217728,'MemorySwap':134217728,'NanoCpus':500000000,
                          'IpcMode':'none','PidMode':'','CgroupnsMode':'private','Init':True,
                          'RestartPolicy':{'Name':'no'},'LogConfig':{'Type':'none'},'Tmpfs':{'/tmp':m.TMPFS}},
            'Mounts':[{'Type':'bind','Source':str(CAPSULE),'Destination':'/workspace','RW':False,'Propagation':'rprivate'}],
            'NetworkSettings':{'Networks':{'none':{}}},
            'State':{'Running':False,'Status':'created','Pid':0,'ExitCode':0,'OOMKilled':False}}


class PolicyTests(unittest.TestCase):
    def test_content_pin(self): self.assertEqual(P.image, 'sha256:'+'a'*64)
    def test_tag_refused(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy('node:latest')
    def test_registry_url_refused(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy('https://provider.invalid/x')
    def test_bool_limit_not_integer(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy(P.image, timeout_seconds=True)
    def test_zero_timeout_refused(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy(P.image, timeout_seconds=0)
    def test_long_timeout_refused(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy(P.image, timeout_seconds=31)
    def test_unbounded_memory_refused(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy(P.image, memory_bytes=0)
    def test_unbounded_output_refused(self):
        with self.assertRaises(m.IsolationError):m.ToolSandboxPolicy(P.image, output_limit_bytes=10**10)
    def test_mutation_refused(self):
        with self.assertRaises(FrozenInstanceError):P.image='other'
    def test_shell_not_used(self):
        args=m.create_arguments(P,CAPSULE,OWNER)
        self.assertNotIn('sh',args);self.assertNotIn('/bin/sh',args);self.assertNotIn('--privileged',args)
    def test_no_inherited_credentials(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'dummy-private', 'DOCKER_HOST':'tcp://bad:123'}):
            args=m.create_arguments(P,CAPSULE,OWNER)
        self.assertNotIn('dummy-private',' '.join(args));self.assertNotIn('tcp://bad',' '.join(args))
        self.assertFalse(any(x.startswith('--env') for x in args))
    def test_image_no_pull(self):self.assertIn('--pull=never',m.create_arguments(P,CAPSULE,OWNER))
    def test_only_readonly_capsule(self):
        mounts=[x for x in m.create_arguments(P,CAPSULE,OWNER) if x.startswith('--mount=')]
        self.assertEqual(len(mounts),1);self.assertIn(',readonly,',mounts[0])
    def test_comma_mount_injection_refused(self):
        with self.assertRaises(m.IsolationError):m.create_arguments(P,PurePosixPath('/tmp/a,source=/'),OWNER)
    def test_owner_injection_refused(self):
        with self.assertRaises(m.IsolationError):m.create_arguments(P,CAPSULE,'--privileged')


class InspectTests(unittest.TestCase):
    def read(self, raw):return m.validate_container(raw,policy=P,capsule=CAPSULE,owner=OWNER,container_id=CID)
    def bad(self, section, key, value):
        obj=inspection();obj[section][key]=value
        with self.assertRaises(m.IsolationError):self.read(obj)
    def test_complete_exact_inspection(self):self.assertTrue(self.read(inspection())['onlyCapsuleMounted'])
    def test_host_network(self):self.bad('HostConfig','NetworkMode','host')
    def test_bridge_network(self):self.bad('HostConfig','NetworkMode','bridge')
    def test_writable_root(self):self.bad('HostConfig','ReadonlyRootfs',False)
    def test_privileged(self):self.bad('HostConfig','Privileged',True)
    def test_root_user(self):self.bad('Config','User','0')
    def test_added_capability(self):self.bad('HostConfig','CapAdd',['NET_ADMIN'])
    def test_missing_capdrop(self):self.bad('HostConfig','CapDrop',[])
    def test_unconfined_seccomp(self):self.bad('HostConfig','SecurityOpt',['seccomp=unconfined'])
    def test_host_pid_namespace(self):self.bad('HostConfig','PidMode','host')
    def test_host_ipc_namespace(self):self.bad('HostConfig','IpcMode','host')
    def test_host_cgroup_namespace(self):self.bad('HostConfig','CgroupnsMode','host')
    def test_no_resource_limit(self):self.bad('HostConfig','Memory',0)
    def test_extra_bind(self):self.bad('HostConfig','Binds',['/:/host'])
    def test_device_passthrough(self):self.bad('HostConfig','Devices',[{'PathOnHost':'/dev/sda'}])
    def test_published_port(self):self.bad('HostConfig','PublishAllPorts',True)
    def test_image_volume(self):self.bad('Config','Volumes',{'/data':{}})
    def test_changed_entrypoint(self):self.bad('Config','Entrypoint',['/bin/sh'])
    def test_changed_cmd(self):self.bad('Config','Cmd',['sh','-c','x'])
    def test_wrong_label(self):self.bad('Config','Labels',{m.OWNER_LABEL:'e'*32})
    def test_jsonfile_logging(self):self.bad('HostConfig','LogConfig',{'Type':'json-file'})
    def test_missing_keys(self):
        with self.assertRaises(m.IsolationError):self.read({})
    def test_wrong_image(self):
        obj=inspection();obj['Image']='sha256:'+'d'*64
        with self.assertRaises(m.IsolationError):self.read(obj)
    def test_wrong_cid(self):
        obj=inspection();obj['Id']='d'*64
        with self.assertRaises(m.IsolationError):self.read(obj)
    def test_writable_mount(self):
        obj=inspection();obj['Mounts'][0]['RW']=True
        with self.assertRaises(m.IsolationError):self.read(obj)
    def test_additional_network(self):
        obj=inspection();obj['NetworkSettings']['Networks']['bridge']={}
        with self.assertRaises(m.IsolationError):self.read(obj)
    def test_multiple_mounts(self):
        obj=inspection();obj['Mounts']*=2
        with self.assertRaises(m.IsolationError):self.read(obj)


class CapsuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.cap=self.root/'capsule';self.cap.mkdir()
        (self.cap/'program.py').write_text('print(42)\n')
    def test_plain_capsule(self):self.assertEqual(m.checked_capsule(self.root,self.cap)[0],self.cap)
    def test_changed_content_changes_digest(self):
        before=m.checked_capsule(self.root,self.cap)[1];(self.cap/'program.py').write_text('print(43)\n')
        self.assertNotEqual(before,m.checked_capsule(self.root,self.cap)[1])
    def test_root_mount_refused(self):
        with self.assertRaises(m.IsolationError):m.checked_capsule(self.root,self.root)
    def test_missing_program(self):
        (self.cap/'program.py').unlink()
        with self.assertRaises(m.IsolationError):m.checked_capsule(self.root,self.cap)
    def test_parent_escape(self):
        with self.assertRaises(m.IsolationError):m.checked_capsule(self.root,self.root.parent)
    def test_too_many_files(self):
        for n in range(32):(self.cap/f'{n}.txt').write_text('x')
        with self.assertRaises(m.IsolationError):m.checked_capsule(self.root,self.cap)
    def test_oversized_file(self):
        (self.cap/'large').write_bytes(b'x'*1048577)
        with self.assertRaises(m.IsolationError):m.checked_capsule(self.root,self.cap)
    def test_existing_receipt_refused(self):
        with self.assertRaises(m.IsolationError):m.IsolatedToolRunner(root=self.root,capsule=self.cap,receipt_dir=self.cap,policy=P)
    def test_receipt_inside_capsule_refused(self):
        with self.assertRaises(m.IsolationError):m.IsolatedToolRunner(root=self.root,capsule=self.cap,receipt_dir=self.cap/'out',policy=P)
    def test_no_automatic_second_execution(self):
        runner=m.IsolatedToolRunner(root=self.root,capsule=self.cap,receipt_dir=self.root/'out',policy=P)
        runner.used=True
        with self.assertRaisesRegex(m.IsolationError,'runner_already_used'):runner.run()
    def test_nonlinux_does_not_fallback(self):
        runner=m.IsolatedToolRunner(root=self.root,capsule=self.cap,receipt_dir=self.root/'out',policy=P)
        with patch.object(m.os,'name','nt'):
            with self.assertRaisesRegex(m.IsolationError,'linux_backend_required'):runner.run()
        self.assertFalse((self.root/'out').exists())


if __name__=='__main__':unittest.main()
