"""Broker post-exec command binding; no privileged operation."""
from pathlib import Path
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import principal_launch as launch

def fixture():
    value={'version':1,'enabled':True,'role':'broker',
        'principalContract':{'version':1,'enabled':True,'gatewayUid':1000,
            'brokerUid':1101,'socketGroupGid':1102,'hostUserNamespace':'user:[4026531837]'},
        'python':'/usr/bin/python3.14','config':'/srv/alaz/private/broker.json',
        'configSha256':'a'*64,'output':'/srv/alaz/socket','commandSha256':''}
    value['commandSha256']=launch.command_digest(launch.command(value))
    return value

class PostexecBinding(unittest.TestCase):
    def test_fixed_target_is_postexec_gate_not_legacy_cli(self):
        argv=launch.command(fixture())
        self.assertEqual(Path(argv[3]).name,'run_principal_broker_target.py')
        self.assertEqual(argv[1:3],['-I','-B'])

    def test_expected_config_digest_reaches_new_image(self):
        v=fixture();argv=launch.command(v)
        self.assertIn('--config-sha256',argv)
        self.assertEqual(argv[argv.index('--config-sha256')+1],v['configSha256'])

    def test_exact_principal_reaches_new_image(self):
        v=fixture();argv=launch.command(v)
        self.assertIn('--principal',argv)
        self.assertEqual(json.loads(argv[argv.index('--principal')+1]),v['principalContract'])

    def test_changing_digest_without_rebinding_command_is_refused(self):
        with self.assertRaisesRegex(launch.LaunchRejected,'command_mismatch'):
            launch.validate(fixture()|{'configSha256':'f'*64})

    def test_changing_principal_without_rebinding_command_is_refused(self):
        v=fixture();v['principalContract']['brokerUid']=1201
        with self.assertRaisesRegex(launch.LaunchRejected,'command_mismatch'):
            launch.validate(v)

    def test_equivalent_principal_key_order_has_stable_command(self):
        v=fixture();other=dict(v)
        other['principalContract']=dict(reversed(list(v['principalContract'].items())))
        self.assertEqual(launch.command(v),launch.command(other))

if __name__=='__main__':unittest.main()
