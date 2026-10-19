"""Fail-closed D3B budget+IPC acceptance contracts; no provider is started."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
spec=importlib.util.spec_from_file_location('native_ext4',ROOT/'scripts/qa/native_budget_ext4.py')
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)

def good():
    return {'result':'PASS','nativeCombinedResult':'PASS',
            'actualHermesGatewayWithDualGuard':True,
            'actualBrokerPersistentBudget':True,
            'ipcProjectionVerified':True,'pathnameSocketProjection':True,
            'explicitSelectedBrokerSocketOnly':True,
            'brokerBudgetIndependentFromGateway':True,
            'projectedRootProof':{'state':'projected',
                                  'explicitHostSocketCount':1,'oldRootDetached':True},
            'privateBudget':{'gatewayDatabaseIsBudgetAuthority':False,
                             'noAutomaticRefunds':True,'measuredInvoiceVerified':False},
            'realModelCalls':0,'completeD3B':False}

class IntegrationEvidenceGate(unittest.TestCase):
    def test_positive(self):
        self.assertTrue(qa.accepted_scope(0,good(),True,True,True))
    def test_bad_code_or_source(self):
        for exitcode,source,copy in [(1,True,True),(0,False,True),(0,True,False)]:
            self.assertFalse(qa.accepted_scope(exitcode,good(),source,copy,True))
    def test_missing_or_wrong_ipc(self):
        for key,value in [('ipcProjectionVerified',False),
                          ('pathnameSocketProjection',False),
                          ('explicitSelectedBrokerSocketOnly',False)]:
            a=good();a[key]=value
            with self.subTest(key=key):self.assertFalse(qa.accepted_scope(0,a,True,True,True))
        for key,value in [('state','failed'),('explicitHostSocketCount',2),
                          ('oldRootDetached',False)]:
            a=good();a['projectedRootProof'][key]=value
            self.assertFalse(qa.accepted_scope(0,a,True,True,True))
        a=good();del a['projectedRootProof']
        self.assertFalse(qa.accepted_scope(0,a,True,True,True))
    def test_private_authority_mandatory(self):
        for key,value in [('actualBrokerPersistentBudget',False),
                          ('brokerBudgetIndependentFromGateway',False),
                          ('actualHermesGatewayWithDualGuard',False),
                          ('nativeCombinedResult','FAIL')]:
            a=good();a[key]=value
            self.assertFalse(qa.accepted_scope(0,a,True,True,True))
        for key,value in [('gatewayDatabaseIsBudgetAuthority',True),
                          ('noAutomaticRefunds',False),
                          ('measuredInvoiceVerified',True)]:
            a=good();a['privateBudget'][key]=value
            self.assertFalse(qa.accepted_scope(0,a,True,True,True))
    def test_model_paid_or_full_d3b_not_claimed(self):
        for key,value in [('realModelCalls',1),('completeD3B',True),('result','FAIL')]:
            a=good();a[key]=value
            self.assertFalse(qa.accepted_scope(0,a,True,True,True))
    def test_initial_false_positive_preserved_but_refused(self):
        old=json.loads((ROOT/'evidence/d3b-integration-19oct/gateway-int19-normal1.json').read_text())
        self.assertEqual(old['result'],'PASS')
        self.assertIs(old['ipcProjectionVerified'],False)
        self.assertFalse(qa.accepted_scope(0,old['gatewayPrivateBudgetAcceptance'],True,True,True))
    def test_legacy_non_ipc_compatibility(self):
        self.assertTrue(qa.accepted_scope(0,{'result':'PASS'},True,True,False))
        self.assertFalse(qa.accepted_scope(0,{'result':'PASS'},True,True,True))

if __name__=='__main__':unittest.main()
