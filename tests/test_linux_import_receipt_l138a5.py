"""Offline receipts for Linux import-only scope, not a lifecycle rerun."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-linux-finite-preflight-l138a5'
def read(name):return json.loads((E/name).read_text(encoding='utf-8'))
class LinuxImportEvidence(unittest.TestCase):
    def test_actual_unprivileged_import_and_cleanup(self):
        r=read('import-001-result.json');self.assertEqual(r['result'],'PASS_LINUX_SYNTAX_AND_IMPORT_ONLY');self.assertEqual(r['commandExitCode'],0)
        self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3);self.assertTrue(r['temporaryRootRemoved']);self.assertTrue(r['inputBytesUnchanged'])
        for key in ('constructorInstancesCreated','nativeStoresOpened','finiteWorkExecuted','rootUsed','confinementTested','httpOrModelStarted','systemPackagesInstalled'):self.assertFalse(r[key],key)
    def test_all_import_and_compilation_bytes_bound(self):
        r=read('import-001-result.json');m=read('import-001-transport-manifest.json');i=read('import-001-intent.json')
        self.assertEqual(r['bundleSha256'],i['bundleSha256']);self.assertEqual(r['compiledSourceCount'],806)
        self.assertEqual(set(r['compiledSources']),{n for n in m['files'] if n.endswith('.py')})
        self.assertEqual(len(r['nativeImports']),444);self.assertEqual(len(r['dependencyImports']),304)
        native=json.loads((ROOT/'config/finite-close-f135c6-sources.json').read_text(encoding='utf-8'))['sources']
        deps=json.loads((ROOT/'evidence/d3b-linux-consumer-l125p1/linux-prepared-001-result.json').read_text(encoding='utf-8'))['installedFileHashes']
        for name,h in r['nativeImports'].items():self.assertEqual(h,native[name]);self.assertEqual(h,m['files']['native/'+name])
        for name,h in r['dependencyImports'].items():self.assertEqual(h,deps[name])
        self.assertFalse(r['unqualifiedSystemPackages']);self.assertEqual(r['dependencyFileCount'],1162)
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/l138a5_linux_import_probe.py').read_bytes()).hexdigest(),r['probeSha256'])
    def test_import_side_effects_not_hidden_or_called_kernel_acceptance(self):
        r=read('import-001-result.json');self.assertEqual(r['deniedEvents'],['socket.bind']);self.assertEqual(r['fixtureFilesCreated'],['home/SOUL.md'])
        self.assertFalse(r['confinementTested']);self.assertFalse(r['httpOrModelStarted']);self.assertFalse(r['finiteWorkExecuted'])
        # A caught offline bind attempt and owned profile scaffolding are not no-effects proof.
if __name__=='__main__':unittest.main()
