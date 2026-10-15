"""Synthetic SQLite fixture. Native maintenance is explicitly substituted ONLY here."""
from contextlib import closing,contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from operator_resolution import OperatorResolution,ResolutionError
from recovery_inspector import LocalRecoveryContext,LocalRecoveryInspector,request_fingerprint,_json

class ResolutionFixture:
    def __init__(self,home):
        self.home=Path(home);self.now=100000.0;self.run_id='run_'+'a'*32;self.key='test-request';self.command='c'*32
        self.body={'input':'local test ışık 😀'};self.observed={'run_id':self.run_id,'status':'interrupted'}
        self.context=LocalRecoveryContext(self.home,'local-fake-bearer',2,'second-instance')
        self.live_owner=False;self.maintenance_entries=0
        with closing(sqlite3.connect(self.home/'state.db')) as c:
            c.executescript('CREATE TABLE runtime_epoch(singleton INTEGER PRIMARY KEY,epoch INTEGER,instance_id TEXT);\nCREATE TABLE state_meta(key TEXT PRIMARY KEY,value TEXT);\nCREATE TABLE session_admissions(admission_id TEXT,request_id TEXT,principal_id TEXT,target_session_id TEXT);\nCREATE TABLE sessions(id TEXT);CREATE TABLE messages(session_id TEXT);\nCREATE TABLE worker_executions(session_id TEXT);')
            c.execute('INSERT INTO runtime_epoch VALUES(1,2,?)',('second-instance',));c.commit()
        with closing(sqlite3.connect(self.home/'runs_idempotency.db')) as c:
            c.execute('CREATE TABLE run_idempotency(scope TEXT,idempotency_key TEXT,fingerprint TEXT,run_id TEXT,status_json TEXT,owner_pid INTEGER,owner_started INTEGER,retention_until REAL,acknowledged_at REAL,created_at REAL,updated_at REAL)')
            c.execute('INSERT INTO run_idempotency VALUES(?,?,?,?,?,999999,1,0,NULL,?,?)',
                      (self.context.scope,self.key,request_fingerprint(self.body),self.run_id,_json(self.observed),self.now,self.now));c.commit()
        self.service=OperatorResolution(self.context,source_root=self.home/'not-native',clock=lambda:self.now)
        self.service._source=lambda:self.home/'not-native'
        @contextmanager
        def fake_maintenance():
            self.maintenance_entries+=1
            yield SimpleNamespace(_pid_exists=lambda pid:self.live_owner)
        self.service._maintenance=fake_maintenance
    def prepare(self,**overrides):
        return self.service.prepare(**({'body':self.body,'idempotency_key':self.key,'observed':self.observed,'command_id':self.command}|overrides))
    def apply(self,plan,**overrides):
        return self.service.apply(**({'plan':plan,'confirmation':plan['confirmationDigest'],'body':self.body,'idempotency_key':self.key,'observed':self.observed}|overrides))
    def sql(self,sql,args=(),replay=False):
        with closing(sqlite3.connect(self.home/('runs_idempotency.db' if replay else 'state.db'))) as c:c.execute(sql,args);c.commit()
    def audit(self):
        with closing(sqlite3.connect(self.home/'state.db')) as c:return c.execute('SELECT key,value FROM state_meta ORDER BY key').fetchall()
    def hashes(self):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.home.glob('*.db')}
    def inspect(self):return LocalRecoveryInspector(self.context,clock=lambda:self.now).inspect(body=self.body,idempotency_key=self.key,observed=self.observed)
