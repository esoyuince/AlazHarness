"""Independent prepared-owner drift tests; only own inert native fixture objects.
All thirty cases include original24 plus six prepared-identity boundaries.
No native method replacement and no admission or service activation.
"""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import r122q6_native_runner_checks as q

class PreparedIdentityChecks(q.RunnerOwnershipTests):
    def test_prepared_authority_identity_rechecked_on_selection(self):
        b,r=self.make();a=self.prepare(r)
        for name,value in (('epoch',self.epoch+1),('instance_id','other'),('profile_id',str(self.home/'foreign')),('runner',object())):
            old=getattr(a,name);setattr(a,name,value)
            try:
                with self.subTest(name=name),self.observe(),self.assertRaises(q.Rejected):r._session_db
            finally:setattr(a,name,old)
        self.assertIs(r._session_db._db,self.state)
    def test_prepared_descriptor_identity_blocks_detach(self):
        b,r=self.make();self.prepare(r);old=r.session_runtime_descriptor;r.session_runtime_descriptor=dict(old)
        try:
            with self.observe(),self.assertRaises(q.Rejected):r.close_all_session_db_handles()
            self.assertEqual(b.status()['state'],'PREPARED');self.assertTrue(q.Ownership.owns(self.home))
        finally:r.session_runtime_descriptor=old
    def test_prepared_descriptor_values_cannot_claim_readiness(self):
        b,r=self.make();self.prepare(r);d=r.session_runtime_descriptor
        for key,value in (('state','ready'),('authority_epoch',self.epoch+1),('instance_id','other'),('capabilities',['fixture-not-authorized']),('served_profiles',[{'fixture':'not-served'}])):
            old=d[key];d[key]=value
            try:
                with self.subTest(key=key),self.observe(),self.assertRaises(q.Rejected):r._session_db
            finally:d[key]=old
        self.assertEqual(d['state'],'caller_prepared')
    def test_prepared_registry_extra_slot_cannot_be_ignored_on_detach(self):
        b,r=self.make();self.prepare(r);registry=r.session_authorities;old=registry.multiplexed;home=self.home/'foreign'
        registry.add(home,object())
        try:
            with self.observe(),self.assertRaises(q.Rejected):r.close_all_session_db_handles()
            self.assertEqual(b.status()['state'],'PREPARED')
        finally:registry.remove(home);registry.multiplexed=old
        self.assertFalse(home.exists())
    def test_prepared_runner_flags_must_stay_not_running_and_draining(self):
        b,r=self.make();self.prepare(r)
        for name,value in (('_draining',False),('_running',True)):
            old=getattr(r,name);setattr(r,name,value)
            try:
                with self.subTest(name=name),self.observe(),self.assertRaises(q.Rejected):r._session_db
            finally:setattr(r,name,old)
    def test_prepared_authority_flags_cannot_become_active(self):
        b,r=self.make();a=self.prepare(r)
        for name,value in (('retiring',False),('retired',True)):
            old=getattr(a,name);setattr(a,name,value)
            try:
                with self.subTest(name=name),self.observe(),self.assertRaises(q.Rejected):r._session_db
            finally:setattr(a,name,old)
        self.assertTrue(a.retiring);self.assertFalse(a.retired)

def main():
    q.RunnerOwnershipTests=PreparedIdentityChecks
    code=q.main();out=Path(sys.argv[sys.argv.index('--output')+1]);r=json.loads((out/'result.json').read_text(encoding='utf-8'))
    r.update(driverSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='actual real runner native24 plus six prepared-owner identity cases; not activation')
    (out/'extended-result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    return code
if __name__=='__main__':raise SystemExit(main())
