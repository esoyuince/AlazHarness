"""Negative-only versioned IPC principal contract; no host privilege changes."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import ipc_view as ipc

FS={'version':1,'enabled':True,'readonly':['/usr'],'writable':['/dev/null'],
    'protected':['/owned/key']}
P={'version':1,'enabled':True,'gatewayUid':1000,'brokerUid':1001,
   'socketGroupGid':100,'hostUserNamespace':'user:[4026531837]'}
V={'version':2,'mode':'projected_root_principal','root':'/tmp/alaz-ipc-tests',
   'brokerSocket':'/owned/broker/egress.sock','principalContract':P}

class IPCPrincipalContractTests(unittest.TestCase):
    def test_opt_in_v2_validates_only_structural_contract(self):
        v,_=ipc.validate(V,FS)
        self.assertEqual(v,V)

    def test_v2_rejects_unknown_fields(self):
        with self.assertRaises(ipc.IPCViewRejected):
            ipc.validate(V|{'fallback':True},FS)

    def test_v2_rejects_missing_principal(self):
        with self.assertRaises(ipc.IPCViewRejected):
            ipc.validate({k:v for k,v in V.items() if k!='principalContract'},FS)

    def test_v2_rejects_equal_host_uids(self):
        with self.assertRaises(ValueError):
            ipc.validate(V|{'principalContract':P|{'brokerUid':1000}},FS)

    def test_v2_cannot_enter_unimplemented_prepare(self):
        with self.assertRaisesRegex(ipc.IPCViewRejected,'ipc_principal_runtime_not_integrated'):
            ipc.prepare(V,FS)

    def test_v2_cannot_project_without_trusted_launcher(self):
        with self.assertRaisesRegex(ipc.IPCViewRejected,'ipc_principal_runtime_not_integrated'):
            ipc.project({'ipc':V,'filesystem':FS})

    def test_principal_preflight_rejects_missing_socket(self):
        with self.assertRaisesRegex(ipc.IPCViewRejected,'ipc_principal_socket_invalid'):
            ipc.inspect_principal_socket(V,FS)

    def test_principal_preflight_rejects_legacy_contract(self):
        old={k:v for k,v in V.items() if k!='principalContract'}
        old.update(version=1,mode='projected_root')
        with self.assertRaisesRegex(ipc.IPCViewRejected,'ipc_principal_version_required'):
            ipc.inspect_principal_socket(old,FS)

    def test_verified_socket_proof_is_not_mount_permission(self):
        proof={'directory':(1,2,1001,100,0o710),
               'socket':(1,3,1001,100,0o660)}
        identity=(1,3,49152,1001,100)
        with (patch('host_principal.socket_identity',return_value=proof) as check,
              patch.object(ipc,'identity',return_value=identity)):
            result=ipc.inspect_principal_socket(V,FS)
        check.assert_called_once_with(P,V['brokerSocket'])
        self.assertEqual(result['socketPrincipal'],proof)
        self.assertEqual(result['socketIdentity'],identity)
        self.assertIs(result['mountAuthorized'],False)

    def test_mismatched_socket_owner_fails_closed(self):
        from host_principal import PrincipalRejected
        with patch('host_principal.socket_identity',
                   side_effect=PrincipalRejected('principal_path_owner_mode')):
            with self.assertRaisesRegex(ipc.IPCViewRejected,'ipc_principal_socket_invalid'):
                ipc.inspect_principal_socket(V,FS)

    def test_preflight_never_bypasses_runtime_gate(self):
        proof={'directory':(1,2,1001,100,0o710),
               'socket':(1,3,1001,100,0o660)}
        with (patch('host_principal.socket_identity',return_value=proof),
              patch.object(ipc,'identity',return_value=(1,3,49152,1001,100))):
            ipc.inspect_principal_socket(V,FS)
        with self.assertRaisesRegex(ipc.IPCViewRejected,'ipc_principal_runtime_not_integrated'):
            ipc.prepare(V,FS)

    def test_legacy_v1_remains_accepted(self):
        legacy={k:v for k,v in V.items() if k!='principalContract'}
        legacy['version']=1
        legacy['mode']='projected_root'
        self.assertEqual(ipc.validate(legacy,FS)[0],legacy)

if __name__=='__main__':
    unittest.main()
