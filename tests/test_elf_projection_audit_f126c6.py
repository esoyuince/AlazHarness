"""Dummy ELF parsing controls and offline scope receipts, never ELF execution."""
from pathlib import Path
import hashlib,json,struct,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import f126c6_elf_dependency_audit as audit
E=ROOT/'evidence/d3b-confined-consumer-f126c6'

def fixture(needed='libc.so.6',tags=None):
    strings=b'\0'+needed.encode()+b'\0GLIBC_2.2.5\0$ORIGIN/extra\0'
    version=2+len(needed);override=version+len('GLIBC_2.2.5')+1
    dynamic=b''.join(struct.pack('<qQ',tag,value) for tag,value in (tags if tags is not None else [(1,1),(0,0)]))
    names=['','.shstrtab','.dynstr','.dynamic','.gnu.version_r','.gnu.version_d'];table=b'';indices=[]
    for name in names:indices.append(len(table));table+=name.encode()+b'\0'
    pieces=[b'',table,strings,dynamic,struct.pack('<HHIII',1,1,1,16,0)+struct.pack('<IHHII',0,0,2,version,0),struct.pack('<HHHHIII',1,0,2,1,0,20,0)+struct.pack('<II',version,0)]
    raw=bytearray(b'\0'*64);offsets=[]
    for part in pieces:offsets.append(len(raw));raw.extend(part)
    off=len(raw)
    for index,part in enumerate(pieces):raw.extend(struct.pack('<IIQQQQIIQQ',indices[index],3 if index in (1,2) else 1,0,0,offsets[index],len(part),0,0,1,0))
    ident=b'\x7fELF\x02\x01\x01'+b'\0'*9
    struct.pack_into('<16sHHIQQQIHHHHHH',raw,0,ident,3,62,1,0,0,off,0,64,0,0,64,len(pieces),1)
    return raw,off,offsets,override

class ElfParsingControls(unittest.TestCase):
    def test_valid_generated_elf_needed_and_versions(self):
        raw,_,_,_=fixture();r=audit.parse_elf(raw)
        self.assertEqual(r['needed'],['libc.so.6']);self.assertEqual(r['requiredVersions'],{'libc.so.6':['GLIBC_2.2.5']});self.assertEqual(r['providedVersions'],['GLIBC_2.2.5'])
    def test_architecture_mismatch(self):
        raw,_,_,_=fixture();struct.pack_into('<H',raw,18,183)
        with self.assertRaisesRegex(ValueError,'elf_format_or_architecture'):audit.parse_elf(raw)
    def test_section_table_out_of_bounds(self):
        raw,_,_,_=fixture();struct.pack_into('<Q',raw,40,len(raw)+1)
        with self.assertRaisesRegex(ValueError,'elf_section_table'):audit.parse_elf(raw)
    def test_payload_truncated(self):
        raw,_,_,_=fixture()
        with self.assertRaisesRegex(ValueError,'elf_section_table'):audit.parse_elf(raw[:-1])
    def test_string_offset_outside_dynstr(self):
        raw,_,_,_=fixture(tags=[(1,999999),(0,0)])
        with self.assertRaisesRegex(ValueError,'elf_string_index'):audit.parse_elf(raw)
    def test_needed_path_not_filename(self):
        raw,_,_,_=fixture(needed='../escape.so')
        with self.assertRaisesRegex(ValueError,'elf_needed_path'):audit.parse_elf(raw)
    def test_missing_dynamic_terminator(self):
        raw,_,_,_=fixture(tags=[(1,1)])
        with self.assertRaisesRegex(ValueError,'elf_dynamic_termination_or_duplicate'):audit.parse_elf(raw)
    def test_duplicate_needed_is_not_silently_deduplicated(self):
        raw,_,_,_=fixture(tags=[(1,1),(1,1),(0,0)])
        with self.assertRaisesRegex(ValueError,'elf_dynamic_termination_or_duplicate'):audit.parse_elf(raw)
    def test_search_override_is_reported(self):
        _,_,_,offset=fixture();raw,_,_,_=fixture(tags=[(1,1),(29,offset),(0,0)])
        self.assertEqual(audit.parse_elf(raw)['searchOverrides'],[{'kind':'RUNPATH','value':'$ORIGIN/extra'}])
    def test_corrupt_version_chain_is_refused(self):
        raw,_,offsets,_=fixture();struct.pack_into('<I',raw,offsets[4]+8,999999)
        with self.assertRaisesRegex(ValueError,'elf_vernaux_bounds'):audit.parse_elf(raw)

class StaticElfReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((E/'elf-linux-stdout.txt').read_bytes());cls.input=(E/'elf-input.json').read_bytes();cls.i=json.loads(cls.input);cls.c=json.loads((E/'elf-custody.json').read_text(encoding='utf-8'))
    def test_actual_linux_terminal_and_input_binding(self):
        r=self.r;self.assertEqual(r['result'],'PASS_STATIC_ELF_CLOSURE_ONLY');self.assertEqual(r['uid'],[23001]*3);self.assertEqual(r['gid'],[23003]*3)
        self.assertEqual(json.loads((E/'elf-linux-terminal.json').read_text()),{'exitCode':0})
        self.assertEqual(hashlib.sha256(self.input).hexdigest(),r['inputSha256']);self.assertEqual(self.c['inputSha256'],r['inputSha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/qa/f126c6_elf_dependency_audit.py').read_bytes()).hexdigest(),r['qaSha256'])
    def test_thirteen_binary_digests_match_accepted_target(self):
        old=json.loads((ROOT/'evidence/d3b-linux-consumer-l125p1/linux-owner-001-result.json').read_text(encoding='utf-8'))['installedFileHashes']
        self.assertEqual(self.r['binaryCandidateCount'],13);self.assertEqual(len(self.c['elfs']),13)
        for name,h in self.r['candidateDigests'].items():self.assertEqual(old[name],h);self.assertEqual(self.c['elfs'][name]['elfSha256'],h)
        self.assertEqual({n:v['sha256'] for n,v in self.i['candidates'].items()},self.r['candidateDigests'])
    def test_all_edges_resolve_in_existing_readonly_roots(self):
        r=self.r;self.assertEqual(len(r['systemLibraries']),7);self.assertEqual(r['missingLibraries'],[]);self.assertEqual(r['missingVersions'],[]);self.assertEqual(r['searchOverridesRequireReview'],[])
        for name,v in r['systemLibraries'].items():self.assertTrue(v['path'].startswith('/usr/lib/x86_64-linux-gnu/'));self.assertEqual(v['machine'],'ELF64_LSB_x86_64')
        for edge in r['dependencyEdges']:
            lib=r['systemLibraries'][edge['name']];self.assertEqual(edge['resolvedPath'],lib['path']);self.assertTrue(set(edge['requiredVersions'])<=set(lib['providedVersions']))
    def test_static_not_dynamic_or_full_confinement(self):
        for key in ('rootUsed','binaryCodeLoadedOrExecuted','projectedPolicyModified','dynamicLoaderOrFullAbiVerified','vulnerabilityAuditPerformed','fullConfinementAccepted'):self.assertIs(self.r[key],False,key)
        self.assertEqual(self.r['allowedSystemRoots'],['/usr/lib/x86_64-linux-gnu','/usr/lib64'])
if __name__=='__main__':unittest.main()
