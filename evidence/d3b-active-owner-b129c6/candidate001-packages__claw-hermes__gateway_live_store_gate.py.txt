"""Read-only startup gate for already-open PINNED native Hermes stores.

Call under the final ProfileLease BEFORE admission/epoch mutation. Prepared
schema/identity expectations are trusted local configuration, not data learned
from a candidate and not remote launch authority. This gate does NOT validate
before constructors, create/repair/close stores, advance epochs or authorize a
listener. The separate prepared-layout/pre-constructor gate remains mandatory.
No raw database open/close: preserve native SQLite POSIX locks and tracking.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading
import uuid

import gateway_profile_lease as profiles
import gateway_storage_mounts as mounts

NATIVE_PIN = 'eb75627faf532fa6ffbdae59a0d14b0b385fc780'
SCHEMA_VERSION = 31
MAX_SCHEMA_ROWS = 2048
MAX_SCHEMA_BYTES = 1024 * 1024


class LiveStoreRejected(RuntimeError):
    """Only bounded codes; no SQL, rows, credentials or paths in the message."""


def require(ok, reason):
    if not ok:
        raise LiveStoreRejected(reason)


@dataclass(frozen=True)
class PreparedStoreExpectation:
    native_pin: str
    state_schema_sha256: str
    replay_schema_sha256: str
    store_instance_id: str
    application_id: int
    state_identity: tuple[int,int]
    replay_identity: tuple[int,int]
    epoch: int
    instance_id: str | None
    journal_mode: str = 'delete'

    def __post_init__(self):
        require(self.native_pin == NATIVE_PIN, 'live_store_source_pin')
        for value in (self.state_schema_sha256,self.replay_schema_sha256):
            require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None,
                    'live_store_schema_expectation')
        try:
            valid_uuid = type(self.store_instance_id) is str and str(uuid.UUID(self.store_instance_id)) == self.store_instance_id
        except (ValueError,TypeError,AttributeError):
            valid_uuid = False
        require(valid_uuid, 'live_store_instance_expectation')
        for pair in (self.state_identity,self.replay_identity):
            require(type(pair) is tuple and len(pair)==2
                    and all(type(n) is int and 0<n<2**64 for n in pair), 'live_store_file_expectation')
        require(self.state_identity != self.replay_identity
                and self.state_identity[0] == self.replay_identity[0], 'live_store_distinct_pair')
        require(type(self.application_id) is int and 0 < self.application_id < 2**31,
                'live_store_application_expectation')
        require(type(self.epoch) is int and 0 <= self.epoch < 2**63, 'live_store_epoch_expectation')
        require((self.epoch == 0 and self.instance_id is None) or
                (self.epoch > 0 and type(self.instance_id) is str
                 and 0 < len(self.instance_id) <= 1024), 'live_store_epoch_instance_expectation')
        require(self.journal_mode in ('delete','truncate','persist','wal'), 'live_store_journal_expectation')


def _native_types():
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from hermes_cli.sqlite_safe_read import TrackedConnection
    return SessionDB, RunIdempotencyStore, TrackedConnection


def _one(connection, sql, args=()):
    rows=connection.execute(sql,args).fetchmany(2)
    require(len(rows)==1 and len(rows[0])==1, 'live_store_single_value')
    return rows[0][0]


def schema_digest(connection):
    """Provisioning helper on an independently prepared SQLite connection.

    Using its result as the expected value of that SAME untrusted candidate
    would defeat verification. The caller must supply separate trusted pins.
    """
    rows=connection.execute('SELECT type,name,tbl_name,sql FROM main.sqlite_schema ORDER BY type,name,tbl_name,sql').fetchmany(MAX_SCHEMA_ROWS+1)
    require(0 < len(rows) <= MAX_SCHEMA_ROWS, 'live_store_schema_limit')
    data=json.dumps([list(r) for r in rows],ensure_ascii=True,separators=(',',':')).encode()
    require(len(data)<=MAX_SCHEMA_BYTES, 'live_store_schema_limit')
    return hashlib.sha256(data).hexdigest()


def _file_identity(path,actor,wanted):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1
            and stat.S_IMODE(info.st_mode)==0o600
            and (info.st_uid,info.st_gid)==actor[1:3]
            and (info.st_dev,info.st_ino)==wanted, 'live_store_file_identity')
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink)


def _connection(connection,path,schema,journal):
    require(not connection.in_transaction, 'live_store_transaction_active')
    attached=[tuple(r) for r in connection.execute('PRAGMA database_list').fetchall()]
    main=[r for r in attached if r[1]=='main']
    require(len(main)==1 and bool(main[0][2]) and Path(main[0][2])==path
            and all(r[1]=='main' or (r[1]=='temp' and r[2]=='') for r in attached),
            'live_store_connection_path')
    require(_one(connection,'PRAGMA query_only')==0, 'live_store_query_only_connection')
    require(_one(connection,'PRAGMA main.journal_mode')==journal, 'live_store_journal_mode')
    sync=_one(connection,'PRAGMA main.synchronous')
    require(type(sync) is int and 2<=sync<=3, 'live_store_synchronous')
    require(schema_digest(connection)==schema, 'live_store_schema_mismatch')
    # No arbitrary SQL, pragmas with assignments, transaction or connection reset.
    # Deep integrity is a separate bounded maintenance/preflight responsibility.
    return {'changes':connection.total_changes,
            'dataVersion':_one(connection,'PRAGMA main.data_version')}


def verify_live_stores(held,expected_mount,state,replay,expected,*,require_idle=True):
    """Validate live connections without taking ownership of their lifecycle.

    Caller remains responsible for all unregistered writers. Both native mutexes
    are acquired without waiting. Observed drift fails closed. Path/identity
    checks are cooperative snapshots, not a SQLite-VFS handle-to-inode proof.
    Every rejection leaves connections, transactions and native profile intact.
    require_idle=False observes identity only; pending work is not health/readiness.
    Startup/constructor/close callers retain the default clean-only policy.
    """
    acquired=[]
    try:
        require(type(require_idle) is bool, 'live_store_idle_policy')
        require(type(held) is profiles.ProfileLease, 'live_store_profile_lease_required')
        require(type(expected) is PreparedStoreExpectation, 'live_store_trusted_expectation')
        require(type(expected_mount) is mounts.ExpectedMount, 'live_store_mount_expectation')
        held.check()
        actor=profiles._actor();home=held._home
        require(actor==held._actor and threading.current_thread() is threading.main_thread(),
                'live_store_other_actor')
        state_type,replay_type,connection_type=_native_types()
        require(type(state) is state_type and type(replay) is replay_type,
                'live_store_native_types')
        require(state.read_only is False and state._shared_registry_owned is False,
                'live_store_dedicated_writer_required')
        require(replay.durable is True, 'live_store_volatile_replay')
        require(type(state._conn) is connection_type and type(replay._conn) is sqlite3.Connection,
                'live_store_native_connections')
        require(Path(state.db_path)==home/'state.db' and replay._db_path==str(home/'runs_idempotency.db'),
                'live_store_declared_paths')
        require(state._lock is not replay._lock, 'live_store_distinct_mutexes')
        for lock in (state._lock,replay._lock):
            require(lock.acquire(blocking=False), 'live_store_busy')
            acquired.append(lock)
        require(state._token_writer_thread is None or not state._token_writer_thread.is_alive(),
                'live_store_background_writer')
        handles=(state._conn,replay._conn)
        require(handles[0] is not handles[1], 'live_store_distinct_connections')
        paths=(home/'state.db',home/'runs_idempotency.db')
        ids=(expected.state_identity,expected.replay_identity)
        first=tuple(_file_identity(p,actor,i) for p,i in zip(paths,ids))
        require(state._db_file_identity==expected.state_identity
                and state._db_file_application_id==expected.application_id,
                'live_store_native_state_identity')
        observation=mounts.observe_profile_mounts(home,expected_mount)
        before=[_connection(c,p,h,expected.journal_mode) for c,p,h in zip(handles,paths,
                 (expected.state_schema_sha256,expected.replay_schema_sha256))]
        require(_one(state._conn,'PRAGMA main.application_id')==expected.application_id,
                'live_store_application_id')
        require(_one(state._conn,'PRAGMA foreign_keys')==1, 'live_store_foreign_keys')
        require(_one(state._conn,'SELECT version FROM main.schema_version')==SCHEMA_VERSION,
                'live_store_native_schema_version')
        require(_one(state._conn,"SELECT value FROM main.state_meta WHERE key='store_instance_id'")==expected.store_instance_id,
                'live_store_instance_mismatch')
        epochs=[tuple(r) for r in state._conn.execute('SELECT epoch,instance_id FROM main.runtime_epoch WHERE singleton=1').fetchmany(2)]
        require(epochs==([] if expected.epoch==0 else [(expected.epoch,expected.instance_id)]),
                'live_store_epoch_mismatch')
        if require_idle:
            # Startup will not decide whether queued/unknown/cross-store work may run.
            require(state._conn.execute("SELECT 1 FROM main.session_admissions WHERE status IS NULL OR status != 'terminal' LIMIT 1").fetchone() is None,
                    'live_store_unresolved_admissions')
            require(state._conn.execute("SELECT 1 FROM main.worker_executions WHERE status IS NULL OR status != 'terminal' LIMIT 1").fetchone() is None,
                    'live_store_unresolved_workers')
            # CASE short-circuits malformed/oversized JSON before tree traversal.
            # Duplicate keys are ambiguous across SQLite and native json.loads;
            # never choose one spelling of a supposedly terminal state.
            require(replay._conn.execute("""SELECT 1 FROM main.run_idempotency WHERE CASE
                WHEN typeof(status_json) != 'text' OR length(CAST(status_json AS BLOB)) > 2097152 THEN 1
                WHEN NOT json_valid(status_json) THEN 1
                WHEN json_type(status_json) != 'object' THEN 1
                WHEN EXISTS (SELECT 1 FROM json_tree(status_json) WHERE key IS NOT NULL
                             GROUP BY parent,key HAVING COUNT(*) > 1) THEN 1
                WHEN json_type(status_json,'$.status') IS NOT 'text' THEN 1
                WHEN json_extract(status_json,'$.status') NOT IN
                     ('completed','failed','cancelled','interrupted') THEN 1
                ELSE 0 END = 1 LIMIT 1""").fetchone() is None,
                    'live_store_unresolved_replay')
        for connection,seen in zip(handles,before):
            require(connection.total_changes==seen['changes'] and not connection.in_transaction
                    and _one(connection,'PRAGMA main.data_version')==seen['dataVersion'],
                    'live_store_observation_changed')
        require(tuple(_file_identity(p,actor,i) for p,i in zip(paths,ids))==first,
                'live_store_observation_changed')
        final_mount=mounts.observe_profile_mounts(home,expected_mount)
        require(final_mount['mountTableSha256']==observation['mountTableSha256'],
                'live_store_mount_changed')
        held.check()
        require(profiles._actor()==actor, 'live_store_other_actor')
        return {'version':1,'state':('NATIVE_STORE_CONNECTIONS_VERIFIED' if require_idle else 'NATIVE_STORE_IDENTITY_OBSERVED'),
                'idleRequired':require_idle,'workHealthEvaluated':False,
                'nativePin':NATIVE_PIN,'schemaVersion':SCHEMA_VERSION,
                'epochObserved':expected.epoch,'volatileReplayRejected':True,
                'connectionPathsMatchPreparedFiles':True,'nativeStateIdentityMatches':True,
                'cooperativePathSnapshotsStable':True,'sqlWritesPerformed':False,
                'rawDatabaseFilesOpened':False,'connectionsClosed':False,
                'sqliteHandleInodeProven':False,'writeCapabilityProven':False,'snapshotOnly':True,
                'preConstructorValidationPerformed':False,'pairedRecoveryVerified':False,
                'runtimeAdmissionAuthorized':False,'fullD3BAccepted':False}
    except LiveStoreRejected:
        raise
    except (OSError,sqlite3.Error,ValueError,TypeError,AttributeError,IndexError,KeyError,
            profiles.ProfileLeaseRejected,mounts.StorageMountRejected):
        raise LiveStoreRejected('live_store_observation_unavailable') from None
    finally:
        for lock in reversed(acquired):
            lock.release()
