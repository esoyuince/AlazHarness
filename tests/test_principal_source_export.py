"""Source-export checks only; never install, elevate or execute packaged code."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import export_principal_source as exp
SHA='a'*40
FILES={'LICENSE':b'owned license fixture\n',
       'scripts/run_principal_broker.py':b'print("not executed")\n'}
EXPECTED={n:{'mode':0o644,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
          for n,b in FILES.items()}


def archive(entries=None,sha=SHA):
    target=io.BytesIO()
    if entries is None:entries=[(exp.PREFIX+n,b,tarfile.REGTYPE,0o644,'') for n,b in FILES.items()]
    with tarfile.open(fileobj=target,mode='w',format=tarfile.PAX_FORMAT,
                      pax_headers={'comment':sha}) as out:
        for name,data,kind,mode,link in entries:
            info=tarfile.TarInfo(name);info.type=kind;info.mode=mode;info.linkname=link
            info.size=len(data) if kind==tarfile.REGTYPE else 0
            out.addfile(info,io.BytesIO(data) if kind==tarfile.REGTYPE else None)
    return target.getvalue()


class ArchiveContracts(unittest.TestCase):
    def check(self,raw):return exp.verify_archive(raw,EXPECTED,SHA)
    def test_exact_owned_archive_passes_without_extracting(self):
        with patch.object(tarfile.TarFile,'extractall',side_effect=AssertionError('no extraction')):
            result=self.check(archive())
        self.assertEqual(result['files'],2)
        self.assertEqual(result['sourceBytes'],sum(map(len,FILES.values())))
        self.assertEqual(result['archiveSha256'],hashlib.sha256(archive()).hexdigest())
    def test_changed_bytes_rejected(self):
        entries=[(exp.PREFIX+n,b,tarfile.REGTYPE,0o644,'') for n,b in FILES.items()]
        n,b,k,m,l=entries[0];entries[0]=(n,b.replace(b'owned',b'other'),k,m,l)
        with self.assertRaisesRegex(exp.ExportRejected,'digest'):self.check(archive(entries))
    def test_missing_file_rejected(self):
        with self.assertRaisesRegex(exp.ExportRejected,'incomplete'):
            self.check(archive([(exp.PREFIX+'LICENSE',FILES['LICENSE'],tarfile.REGTYPE,0o644,'')]))
    def test_duplicate_and_case_collision_rejected(self):
        for name in (exp.PREFIX+'LICENSE',exp.PREFIX+'license'):
            entries=[(exp.PREFIX+n,b,tarfile.REGTYPE,0o644,'') for n,b in FILES.items()]
            entries.append((name,FILES['LICENSE'],tarfile.REGTYPE,0o644,''))
            with self.subTest(name=name),self.assertRaises(exp.ExportRejected):self.check(archive(entries))
    def test_unexpected_file_rejected(self):
        entries=[(exp.PREFIX+n,b,tarfile.REGTYPE,0o644,'') for n,b in FILES.items()]
        entries.append((exp.PREFIX+'private.json',b'fixture',tarfile.REGTYPE,0o644,''))
        with self.assertRaises(exp.ExportRejected):self.check(archive(entries))
    def test_symlink_hardlink_fifo_and_device_rejected(self):
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE,tarfile.CHRTYPE):
            with self.subTest(kind=kind),self.assertRaises(exp.ExportRejected):
                self.check(archive([(exp.PREFIX+'LICENSE',b'',kind,0o644,'/tmp/not-followed')]))
    def test_absolute_dotdot_backslash_and_alias_rejected(self):
        for name in ('/LICENSE',exp.PREFIX+'../LICENSE',exp.PREFIX+'./LICENSE',
                     exp.PREFIX+'scripts//x.py',exp.PREFIX+'scripts'+chr(92)+'x.py',
                     exp.PREFIX+'LICENSE/'):
            with self.subTest(name=name),self.assertRaises(exp.ExportRejected):
                self.check(archive([(name,FILES['LICENSE'],tarfile.REGTYPE,0o644,'')]))
    def test_changed_commit_rejected(self):
        with self.assertRaisesRegex(exp.ExportRejected,'commit'):self.check(archive(sha='b'*40))
    def test_writeable_or_setuid_archive_mode_rejected(self):
        for mode in (0o666,0o777,0o4644):
            with self.subTest(mode=mode),self.assertRaises(exp.ExportRejected):
                self.check(archive([(exp.PREFIX+'LICENSE',FILES['LICENSE'],tarfile.REGTYPE,mode,'')]))
    def test_extra_trailing_payload_rejected(self):
        with self.assertRaisesRegex(exp.ExportRejected,'trailing'):self.check(archive()+b'not-in-git')
    def test_empty_and_non_tar_rejected(self):
        for raw in (b'',b'not a tar'):
            with self.subTest(raw=raw),self.assertRaises(exp.ExportRejected):self.check(raw)
    def test_only_canonical_ancestor_directories_accepted(self):
        entries=[(exp.PREFIX,b'',tarfile.DIRTYPE,0o755,''),
                 (exp.PREFIX+'scripts/',b'',tarfile.DIRTYPE,0o755,'')]
        entries += [(exp.PREFIX+n,b,tarfile.REGTYPE,0o644,'') for n,b in FILES.items()]
        self.assertEqual(self.check(archive(entries))['files'],2)
        entries.append((exp.PREFIX+'foreign/',b'',tarfile.DIRTYPE,0o755,''))
        with self.assertRaises(exp.ExportRejected):self.check(archive(entries))


class PublicationContracts(unittest.TestCase):
    def test_branch_or_short_revision_never_reaches_git(self):
        with patch.object(exp,'git') as call:
            for revision in ('HEAD','main','802fade','A'*40,'-bad'):
                with self.subTest(revision=revision),self.assertRaises(exp.ExportRejected):
                    exp.source_inventory(ROOT,revision)
        call.assert_not_called()
    def test_outside_scratch_cannot_be_written(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exp,'source_inventory') as read:
            root=Path(tmp).resolve();outside=root/'not-scratch'
            with self.assertRaisesRegex(exp.ExportRejected,'scratch'):
                exp.build(root,SHA,outside)
            self.assertFalse(outside.exists());read.assert_not_called()
    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(exp,'source_inventory') as read:
            root=Path(tmp).resolve();out=root/'scratch/principal-install/test';out.mkdir(parents=True)
            sentinel=out/'keep';sentinel.write_bytes(b'owned')
            with self.assertRaisesRegex(exp.ExportRejected,'absent'):exp.build(root,SHA,out)
            self.assertEqual(sentinel.read_bytes(),b'owned');read.assert_not_called()
    def test_real_git_export_ignores_autocrlf_and_untracked_private_files(self):
        with tempfile.TemporaryDirectory(prefix='alaz-export-git-') as tmp:
            root=Path(tmp).resolve()
            exp.git(root,'init','--quiet')
            exp.git(root,'config','core.autocrlf','false')
            for name in exp.REQUIRED:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(b'owned fixture line one\nline two\n')
            exp.git(root,'add','--all')
            exp.git(root,'-c','user.name=Owned Export Test',
                    '-c','user.email=export-test@example.invalid',
                    '-c','commit.gpgsign=false','commit','--quiet','-m','owned fixture')
            revision=exp.git(root,'rev-parse','HEAD').decode().strip()
            exp.git(root,'config','core.autocrlf','true')
            private=root/'.env';private.write_bytes(b'owned untracked fixture')
            a=root/'scratch/principal-install/a';b=root/'scratch/principal-install/b'
            first=exp.build(root,revision,a);second=exp.build(root,revision,b)
            self.assertEqual(first,second)
            self.assertEqual((a/'broker-source.tar').read_bytes(),(b/'broker-source.tar').read_bytes())
            self.assertEqual((a/'manifest.json').read_bytes(),(b/'manifest.json').read_bytes())
            self.assertNotIn('.env',first['fileManifest'])
            self.assertIs(first['installed'],False)
            self.assertIs(first['twoHostUidAccepted'],False)
            self.assertEqual(private.read_bytes(),b'owned untracked fixture')
            with tarfile.open(a/'broker-source.tar',mode='r:') as archive_file:
                self.assertEqual(archive_file.extractfile(exp.PREFIX+'LICENSE').read(),
                                 b'owned fixture line one\nline two\n')

    def test_only_selected_runtime_paths(self):
        for name in ('runtime/state.db','.env','vendor/hermes-agent/secret','status.md','tests/a.py'):
            self.assertFalse(exp.selected(name),name)
        self.assertTrue(exp.selected('packages/upstream/hermes-agent/LICENSE'))
        self.assertTrue(exp.selected('scripts/run_principal_broker_target.py'))


if __name__=='__main__':unittest.main()
