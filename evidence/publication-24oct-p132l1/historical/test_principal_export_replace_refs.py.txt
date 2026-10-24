"""Pinned exporter must ignore real replacement refs in owned Git fixtures.

No source installation, privileged operation or candidate execution. Refs and
config are created only in TemporaryDirectory-owned repositories.
"""
import hashlib
import os
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import export_principal_source as exporter


class ExportReplacementRefs(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='alaz-export-replace-')
        self.addCleanup(temporary.cleanup)
        self.repo=Path(temporary.name).resolve()
        self.g('init','--quiet');self.g('config','core.autocrlf','false')
        for name in sorted(exporter.REQUIRED):
            p=self.repo/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(('# own original '+name+'\n').encode())
        self.name='scripts/run_principal_broker_target.py'
        self.original=(self.repo/self.name).read_bytes()
        self.g('add','--',*sorted(exporter.REQUIRED));self.commit('original')
        self.revision=self.g('rev-parse','HEAD').decode().strip()
        self.oid=self.g('rev-parse',self.revision+':'+self.name).decode().strip()
    def g(self,*args,input=None):
        return subprocess.run(['git','-C',str(self.repo),*args],input=input,
                              capture_output=True,check=True,timeout=20).stdout
    def commit(self,label):
        self.g('-c','user.name=Owned Source QA','-c','user.email=source-qa@example.invalid',
               '-c','commit.gpgsign=false','commit','--quiet','-m',label)
    def assert_original_export(self):
        out=self.repo/'scratch/principal-install/checked'
        result=exporter.build(self.repo,self.revision,out)
        self.assertEqual(result['sourceCommit'],self.revision)
        self.assertEqual(result['fileManifest'][self.name]['gitBlob'],self.oid)
        self.assertEqual(result['fileManifest'][self.name]['sha256'],
                         hashlib.sha256(self.original).hexdigest())
        with tarfile.open(out/'broker-source.tar',mode='r:') as archive:
            with archive.extractfile(exporter.PREFIX+self.name) as handle:
                self.assertEqual(handle.read(),self.original)
        self.assertIs(result['installed'],False)
        self.assertIs(result['twoHostUidAccepted'],False)
    def test_blob_replacement_cannot_change_pinned_archive_bytes(self):
        replacement=self.g('hash-object','-w','--stdin',
                           input=b'# owned replacement; never executed\n').decode().strip()
        self.g('replace',self.oid,replacement)
        self.assertEqual(self.g('for-each-ref','--format=%(refname)','refs/replace').decode().splitlines(),
                         ['refs/replace/'+self.oid])
        self.assert_original_export()
    def test_custom_replacement_namespace_does_not_change_pinned_blob(self):
        replacement=self.g('hash-object','-w','--stdin',
                           input=b'# owned custom-ref replacement; never executed\n').decode().strip()
        ref='refs/r91f-replacements/'+self.oid
        self.g('update-ref',ref,replacement)
        with patch.dict(os.environ,{'GIT_REPLACE_REF_BASE':'refs/r91f-replacements/'}):
            self.assertNotEqual(self.g('cat-file','blob',self.oid),self.original)
            self.assert_original_export()
        self.assertEqual(self.g('rev-parse',ref).decode().strip(),replacement)

    def test_empty_disable_environment_does_not_reenable_replacements(self):
        replacement=self.g('hash-object','-w','--stdin',
                           input=b'# owned replacement under empty environment flag\n').decode().strip()
        self.g('replace',self.oid,replacement)
        with patch.dict(os.environ,{'GIT_NO_REPLACE_OBJECTS':''}):
            self.assertNotEqual(self.g('cat-file','blob',self.oid),self.original)
            self.assert_original_export()
        self.assertEqual(self.g('rev-parse','refs/replace/'+self.oid).decode().strip(),replacement)

    def test_commit_replacement_cannot_change_pinned_tree(self):
        (self.repo/self.name).write_bytes(b'# second commit; never executed\n')
        self.g('add','--',self.name);self.commit('replacement commit')
        replacement=self.g('rev-parse','HEAD').decode().strip()
        self.g('replace',self.revision,replacement)
        self.assert_original_export()


if __name__=='__main__':unittest.main()
