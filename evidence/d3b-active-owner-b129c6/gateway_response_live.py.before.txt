"""Read-only observation of the third, caller-owned native response connection.

A separate cold preflight must precede ResponseStore construction. This verifier
opens NO database descriptor/connection, owns NO handle/lease and never closes,
settles, repairs or advances anything. Trusted expectations come from prepared
state, never from the candidate. Success is a cooperative startup snapshot, not
HTTP/work permission or cross-store recovery. Only pinned DELETE startup here.
"""
from __future__ import annotations
from dataclasses import dataclass
import os
import hashlib
import sys
from pathlib import Path
import re
import sqlite3
import threading

import gateway_live_store_gate as live

FEATURE_COMMIT='cc16c10b16a0ca8d80b23fd9be3f0e59ee605075'
RESPONSE_NAME='response_store.db'

class ResponseLiveRejected(RuntimeError):
    pass


def require(ok,code):
    if not ok:raise ResponseLiveRejected(code)


@dataclass(frozen=True)
class ResponseConnectionExpectation:
    feature_commit: str
    schema_sha256: str
    identity: tuple[int,int]
    max_size: int = 100
    max_identities: int = 1000

    def __post_init__(self):
        require(self.feature_commit==FEATURE_COMMIT,'response_live_feature_pin')
        require(type(self.schema_sha256) is str and re.fullmatch('[0-9a-f]{64}',self.schema_sha256) is not None,
                'response_live_schema_expectation')
        require(type(self.identity) is tuple and len(self.identity)==2
                and all(type(n) is int and 0<n<2**64 for n in self.identity),'response_live_file_expectation')
        require(type(self.max_size) is int and 1<=self.max_size<=100
                and type(self.max_identities) is int and 1<=self.max_identities<=1000,
                'response_live_retention_expectation')


SOURCE_HASHES={
    'gateway.platforms.api_server_response_store':'9d787af0433af6d99c0518ba7bcabfbea06b73bd3f8da48e47e63464e1e0f3ad',
    'gateway.platforms.api_server_response_state':'8bca7e8c5a7d7e42545b811ecaa34cbe982bfcab363f0a9f4a295f735cf50b83'}


def qualified_response_type():
    # Trusted deployment imports only; never dynamically apply/choose a patch.
    State,Response,Binding=_native_types()
    for name,want in SOURCE_HASHES.items():
        path=Path(sys.modules[name].__file__)
        require(path.suffix=='.py' and hashlib.sha256(path.read_bytes()).hexdigest()==want,
                'response_live_source_mismatch')
    return Response


def _native_types():
    from hermes_state import SessionDB
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.platforms.api_server_response_state import BorrowedResponseState
    return SessionDB,ResponseStore,BorrowedResponseState


def _observe(home,expected_mount,expected,actor):
    proof=live.mounts.observe_profile_mounts(home,expected_mount)
    raw=live.mounts._read_mountinfo()
    require(hashlib.sha256(raw).hexdigest()==proof['mountTableSha256'],'response_live_mount_changed')
    records=live.mounts.parse_mountinfo(raw)
    path=home/RESPONSE_NAME
    live.mounts._check_mount(live.mounts.select_mount(records,path.as_posix()),expected_mount)
    identity=live._file_identity(path,actor,expected.identity)
    for suffix in ('-journal','-wal','-shm'):
        require(not os.path.lexists(home/(RESPONSE_NAME+suffix)), 'response_live_sidecar_recovery_required')
    require(live.mounts._read_mountinfo()==raw,'response_live_mount_changed')
    return proof,identity


def verify_response_connection(held,expected_mount,state,response,expected,*,constructor=False):
    """No raw DB/sidecar open; only native handle queries and metadata.

    constructor=True verifies zero response-row modifications by the JUST
    completed constructor. It is not appropriate after legitimate client writes.
    ResponseStore has no native mutex; require final main thread and externally
    drained writers. Malicious same-process writers/ABA are outside this model.
    """
    try:
        require(type(expected) is ResponseConnectionExpectation,'response_live_trusted_expectation')
        require(type(constructor) is bool,'response_live_constructor_flag')
        require(type(held) is live.profiles.ProfileLease,'response_live_native_lease')
        require(type(expected_mount) is live.mounts.ExpectedMount,'response_live_expected_mount')
        held.check();actor=live.profiles._actor();home=held._home
        require(actor==held._actor and threading.current_thread() is threading.main_thread(),
                'response_live_other_actor')
        State,Response,Binding=_native_types()
        require(type(state) is State and type(response) is Response,'response_live_native_types')
        require(type(response._conn) is sqlite3.Connection,'response_live_connection_type')
        require(response._db_path is not None and Path(response._db_path)==home/RESPONSE_NAME,
                'response_live_disk_path')
        require(response._max_size==expected.max_size and response._identity_bound()==expected.max_identities,
                'response_live_retention_mismatch')
        binding=response._canonical_state
        require(type(binding) is Binding and binding._state is state
                and binding._connection is state._conn and binding._lock is state._lock,
                'response_live_canonical_binding')
        require(expected.identity!=state._db_file_identity
                and expected.identity[0]==state._db_file_identity[0], 'response_live_distinct_database')
        conn=response._conn
        require(not conn.in_transaction,'response_live_transaction_active')
        if constructor:require(conn.total_changes==0,'response_live_constructor_changed_rows')
        before=_observe(home,expected_mount,expected,actor)
        with binding.read():
            seen=live._connection(conn,home/RESPONSE_NAME,expected.schema_sha256,'delete')
            require(live._one(conn,'PRAGMA main.application_id')==0
                    and live._one(conn,'PRAGMA main.user_version')==0,'response_live_unexpected_header_version')
            # Startup is quiescent; unresolved response identities are NOT replay authority.
            require(conn.execute('SELECT 1 FROM main.response_keys WHERE settled_at IS NULL LIMIT 1').fetchone() is None,
                    'response_live_unsettled_identity')
            bodies=live._one(conn,'SELECT COUNT(*) FROM main.responses')
            identities=live._one(conn,'SELECT COUNT(*) FROM main.response_keys')
            require(type(bodies) is int and bodies<=expected.max_size
                    and type(identities) is int and identities<=expected.max_identities,
                    'response_live_retention_overflow')
            require(conn.total_changes==seen['changes'] and not conn.in_transaction
                    and live._one(conn,'PRAGMA main.data_version')==seen['dataVersion'],
                    'response_live_changed')
        require(response._conn is conn and response._canonical_state is binding,'response_live_handle_changed')
        require(_observe(home,expected_mount,expected,actor)==before,'response_live_mount_changed')
        held.check();require(live.profiles._actor()==actor,'response_live_other_actor')
        return {'state':'NATIVE_RESPONSE_CONNECTION_VERIFIED','featureCommit':expected.feature_commit,
            'constructorRowsUnchanged':True if constructor else None,
            'bodyCount':bodies,'identityCount':identities,'normalSqliteConnection':True,
            'sameCanonicalConnectionBorrowed':True,'newDatabaseConnectionsOpened':False,
            'rawDatabaseDescriptorsOpened':False,'sqlWritesPerformed':False,'connectionsClosed':False,
            'preConstructorVerificationPerformed':False,'pairedRecoveryVerified':False,
            'sqliteHandleInodeProven':False,'runtimeAdmissionAuthorized':False,'fullD3BAccepted':False}
    except ResponseLiveRejected:raise
    except Exception as exc:
        # Native binding errors must be bounded too, without private SQL/path contents.
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):raise
        raise ResponseLiveRejected('response_live_observation_unavailable') from None
