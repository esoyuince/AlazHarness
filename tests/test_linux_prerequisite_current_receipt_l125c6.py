"""Offline evidence binding of the corrected Linux candidate; no new native run."""
import hashlib,json,unittest
from historical_layout_f126c1 import executed_source_hash as pre_f126_hash
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-linux-consumer-qa-l125c6'
class CurrentLinuxPrerequisiteReceipt(unittest.TestCase):
    def test_selected_thirty_after_five_explicit_substitutions(self):
        old=json.loads((E/'wheel-review-final.json').read_text(encoding='utf-8'))
        new=json.loads((E/'wheel-review-remediated.json').read_text(encoding='utf-8'))
        self.assertEqual((new['wheelCount'],new['recordMemberCount'],new['elfFileCount']),(30,1096,13))
        before={w['name']:w['version'] for w in old['wheels']};after={w['name']:w['version'] for w in new['wheels']}
        self.assertEqual(set(before),set(after));self.assertEqual({n for n in before if before[n]!=after[n]},{'aiohttp','certifi','multidict','urllib3','yarl'})
        self.assertEqual(new['qaSha256'],old['qaSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/l125c6_review_wheels.py').read_bytes()).hexdigest(),new['qaSha256'])
        raw=(E/'remediated-download-record.json').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),new['downloadManifestSha256'])
        self.assertEqual({w['name']:w['sha256'] for w in json.loads(raw)['files']},{w['filename']:w['sha256'] for w in new['wheels']})
        self.assertFalse(new['publisherTrustOrVulnerabilityAudited']);self.assertFalse(new['linuxLifecycleOrConfinementAccepted'])
    def test_installed_payload_and_extra_metadata_scope_preserved(self):
        r=json.loads((E/'remediated-source-review.json').read_text(encoding='utf-8'))
        self.assertEqual(r['wheelCount'],30);self.assertEqual(r['nativeSourceCount'],513);self.assertEqual(r['actualNativeImports'],499)
        self.assertFalse(r['originalRuntimeExecutedByThisReview'])
        for record in r['resultRecords']:
            self.assertEqual(record['installedFileCount'],1162);self.assertEqual(record['wheelPayloadFilesMatched'],1066)
            self.assertEqual(len(record['installerGeneratedOrRewrittenFiles']),96);self.assertEqual(record['unexplainedFiles'],[])
            self.assertFalse(record['actualDependencyImportsEnumerated'])
        self.assertTrue(r['originalLockHasUnusedWindowsMarkerMetadata']);self.assertTrue(r['noActiveRequirementUsesThoseMarkers'])
    def test_real_prepared_native_twenty_two_remain_listener_closed(self):
        r=json.loads((E/'reviewed-prepared-summary.json').read_text(encoding='utf-8'));q=r['childResult']
        self.assertEqual(r['result'],'PASS_PREPARED_PREREQUISITE_ONLY')
        self.assertEqual((q['total'],q['passed'],q['errors'],q['failures'],q['skipped']),(22,22,0,0,0))
        self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3);self.assertTrue(r['temporaryRootRemoved'])
        self.assertTrue(q['actualNativeRunnerAndAdapter']);self.assertTrue(q['sameThreeCallerConnections'])
        for name in ('nativeMethodsReplaced','epochAdvancedByAttachment','serviceAdmissionOrListenerActivated','linuxIsolationTested'):self.assertFalse(q[name])
        self.assertEqual(q['providerCalls'],0);self.assertFalse(r['namespaceConfinementTested'])
        for record in q['checks']:self.assertEqual((record['sqliteOpens'],record['rawDatabaseOpens'],record['rowChanges']),(0,0,0))
    def test_real_linux_owner_order_and_scope_not_namespace_acceptance(self):
        raw=(E/'reviewed-owner-summary.json').read_text(encoding='utf-8');r=json.loads(raw);q=r['childResult']
        verified=json.loads((E/'actual-owner-independent-review.json').read_text(encoding='utf-8'))
        self.assertEqual(r['originalOuterSha256'],verified['originalResultSha256'])
        self.assertEqual(r['result'],'PASS_OWNER_PREREQUISITE_ONLY');self.assertEqual(q['result'],'PASS_REAL_LINUX_OWNER_LIFECYCLE_NOT_CONFINEMENT')
        self.assertEqual(q['checkCount'],23);self.assertEqual(len(q['checks']),23);self.assertTrue(all(v is True for v in q['checks'].values()))
        self.assertEqual([e['phase'] for e in q['events']],['owner_started','consumer_attached','consumer_detached','stores_closed'])
        self.assertEqual(verified['actualNativeImportCount'],498);self.assertEqual(verified['nativeSourceCount'],513)
        self.assertEqual(verified['coldHelpers'],['run_store_preopen.py','run_store_preopen.py','run_response_preopen.py'])
        self.assertTrue(q['actualLinuxActorLeaseMountLayoutColdHelpersAndLiveSql'])
        for key in ('productOrNativeMethodsDoubled','namespaceConfinementTested','physicalDurabilityTested','serviceOrAdmissionActivated','rootUsed','fixtureCleanupAfterFailure'):self.assertFalse(q[key],key)
        self.assertEqual(q['providerCalls'],0);self.assertTrue(q['temporaryProfileRemoved']);self.assertTrue(r['temporaryRootRemoved'])
        self.assertFalse(verified['newNativeRunByReview']);self.assertTrue(verified['sameRemediatedDependencyPayloadAsPrepared22'])
        for name in ('packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_prepared_consumer.py'):
            self.assertEqual(pre_f126_hash(ROOT,name,verified['harnessTransportHashes'][name]),verified['harnessTransportHashes'][name])
if __name__=='__main__':unittest.main()
