"""Bounded committed native work metadata for the single B115 policy.

Only existing caller-owned connections are used. This is NOT the complete live
collector: the caller must independently verify profile/mount identity and capture
actual live tasks plus producer revision around this read. Returned rows do not
mint storage_verified, complete, task_alive or HTTP/dispatch/release authority.
"""
from dataclasses import dataclass
import json,os,sqlite3,threading,time
from pathlib import Path
import gateway_live_store_gate as live
import gateway_work_health as policy

class WorkReadRejected(RuntimeError):pass
class WorkReadUnavailable(RuntimeError):pass

def need(ok,reason):
    if not ok:raise WorkReadRejected(reason)

def digest(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)

_ACTIVE_RUN="""CASE
 WHEN typeof(status_json)!='text' OR length(CAST(status_json AS BLOB))>65536 THEN 1
 WHEN NOT json_valid(status_json) THEN 1
 WHEN json_type(status_json)!='object' THEN 1
 WHEN EXISTS(SELECT 1 FROM json_tree(status_json) WHERE key IS NOT NULL GROUP BY parent,key HAVING COUNT(*)>1) THEN 1
 WHEN json_type(status_json,'$.status') IS NOT 'text' THEN 1
 WHEN json_extract(status_json,'$.status') NOT IN ('completed','failed','cancelled','interrupted') THEN 1
 ELSE 0 END=1"""

@dataclass(frozen=True,slots=True)
class CommittedWorkRows:
    identity: policy.RuntimeIdentity
    sample_id: int
    captured_ns: int
    admissions: tuple[policy.Admission,...]
    runs: tuple[policy.Run,...]
    responses: tuple[policy.ResponseIdentity,...]
    unresolved_workers: int
    run_bindings: tuple[tuple[str,str,str,str],...]
    response_fingerprints: tuple[tuple[str,str],...]
    # No health/permission booleans: caller must not substitute this for live task proof.

class NativeWorkReader:
    def __init__(self,state,replay,responses,expected,*,schema_hashes):
        from hermes_state import SessionDB
        from hermes_cli.sqlite_safe_read import TrackedConnection
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.platforms.api_server_response_state import BorrowedResponseState
        need(type(expected) is policy.RuntimeIdentity and expected.owner_pid==os.getpid(),'work_reader_identity')
        need(type(schema_hashes) is tuple and len(schema_hashes)==3 and all(digest(h) for h in schema_hashes),'work_reader_schema_pins')
        need(type(state) is SessionDB and type(replay) is RunIdempotencyStore and type(responses) is ResponseStore,'work_reader_native_types')
        need(state.read_only is False and state._shared_registry_owned is False and replay.durable is True,'work_reader_durable_writer')
        binding=responses._canonical_state
        need(type(binding) is BorrowedResponseState and binding._state is state and binding._connection is state._conn
             and binding._lock is state._lock,'work_reader_canonical_binding')
        self._stores=(state,replay,responses);self._connections=tuple(s._conn for s in self._stores)
        need(type(self._connections[0]) is TrackedConnection and all(type(c) is sqlite3.Connection for c in self._connections[1:])
             and len({id(c) for c in self._connections})==3,'work_reader_native_handles')
        self._locks=(state._lock,replay._lock);need(self._locks[0] is not self._locks[1],'work_reader_mutexes')
        self._binding=binding;self._actor=(os.getpid(),threading.get_ident());self._home=Path(state.db_path).parent
        self._paths=tuple(self._home/n for n in ('state.db','runs_idempotency.db','response_store.db'))
        need(self._home.is_absolute(),'work_reader_absolute_home')
        self.expected=expected;self._schemas=schema_hashes;self._sample=0;self._check()

    def _check(self):
        need((os.getpid(),threading.get_ident())==self._actor,'work_reader_other_actor')
        state,replay,response=self._stores
        need(all(s._conn is c for s,c in zip(self._stores,self._connections)) and state._lock is self._locks[0]
             and replay._lock is self._locks[1] and response._canonical_state is self._binding
             and self._binding._state is state and self._binding._connection is state._conn
             and self._binding._lock is state._lock,'work_reader_handle_changed')
        need(tuple(Path(v) for v in (state.db_path,replay._db_path,response._db_path))==self._paths,'work_reader_path_changed')
        need(state.read_only is False and state._shared_registry_owned is False and replay.durable is True,'work_reader_owner_changed')

    @staticmethod
    def _rows(conn,sql,args=()):
        rows=conn.execute(sql,args).fetchmany(policy.MAX_ROWS+1)
        if len(rows)>policy.MAX_ROWS:raise WorkReadUnavailable('work_inventory_limit')
        return rows

    @staticmethod
    def _selection(column,values):
        return (' OR '+column+' IN ('+','.join('?' for _ in values)+')',values) if values else ('',())

    def capture(self,*,live_work=()):
        """Include active records and terminal records still referenced by owner tasks.

        live_work IDs select bounded rows; they are not accepted as evidence of
        task liveness here. A complete stable task/lease collector is still needed.
        """
        acquired=[]
        try:
            self._check()
            need(type(live_work) is tuple and len(live_work)<=policy.MAX_ROWS
                 and all(type(w) is policy.LiveWork for w in live_work),'work_reader_owner_inventory')
            ids=tuple(w.admission_id for w in live_work);runs=tuple(w.run_id for w in live_work if w.run_id is not None)
            keys=tuple(w.response_key for w in live_work if w.response_key is not None)
            need(all(policy.text(v) for values in (ids,runs,keys) for v in values),'work_reader_owner_id')
            need(all(len(set(values))==len(values) for values in (ids,runs,keys)),'work_reader_duplicate_owner')
            for lock in self._locks:
                if not lock.acquire(blocking=False):raise WorkReadUnavailable('work_native_mutex_busy')
                acquired.append(lock)
            if any(c.in_transaction for c in self._connections):raise WorkReadUnavailable('work_native_transaction_active')
            state=self._stores[0]
            if state._token_writer_thread is not None and state._token_writer_thread.is_alive():raise WorkReadUnavailable('work_native_background_writer')
            seen=[live._connection(c,path,h,'delete') for c,path,h in zip(self._connections,self._paths,self._schemas)]
            sc,rc,pc=self._connections
            epoch=[tuple(r) for r in sc.execute('SELECT epoch,instance_id FROM main.runtime_epoch WHERE singleton=1').fetchmany(2)]
            store_id=live._one(sc,"SELECT value FROM main.state_meta WHERE key='store_instance_id'")
            need(epoch==[(self.expected.epoch,self.expected.instance_id)] and store_id==self.expected.store_instance_id,'work_reader_runtime_changed')
            extra,args=self._selection('a.admission_id',ids)
            admissions=tuple(policy.Admission(*tuple(r)) for r in self._rows(sc,"""SELECT a.admission_id,a.target_session_id,a.status,a.owner_epoch,
                a.generation,s.runtime_generation FROM main.session_admissions a LEFT JOIN main.sessions s ON s.id=a.target_session_id
                WHERE (a.status IS NULL OR a.status!='terminal'"""+extra+") ORDER BY a.seq LIMIT 257",args))
            workers=self._rows(sc,"SELECT execution_id FROM main.worker_executions WHERE status IS NULL OR status!='terminal' LIMIT 257")
            extra,args=self._selection('run_id',runs)
            rows=self._rows(rc,"""SELECT run_id,scope,idempotency_key,fingerprint,
                CASE WHEN typeof(status_json)='text' AND length(CAST(status_json AS BLOB))<=65536 THEN status_json ELSE NULL END,
                owner_pid,owner_started FROM main.run_idempotency WHERE ("""+_ACTIVE_RUN+extra+") ORDER BY run_id LIMIT 257",args)
            run_records=[];run_bindings=[]
            for rid,scope,key,fp,raw,pid,started in rows:
                policy._run_status(raw)  # same bounded parser as the selected pure policy
                need(all(policy.text(v) for v in (rid,scope,key)) and digest(fp),'work_reader_run_binding')
                run_records.append(policy.Run(rid,raw,pid,started));run_bindings.append((rid,scope,key,fp))
            extra,args=self._selection('k.request_key',keys)
            rows=self._rows(pc,"""SELECT k.request_key,k.fingerprint,a.admission_id,k.settled_at IS NOT NULL
                FROM main.response_keys k LEFT JOIN main.response_admissions a ON a.request_key=k.request_key
                WHERE (k.settled_at IS NULL"""+extra+") ORDER BY k.request_key LIMIT 257",args)
            responses=[];response_fingerprints=[]
            for key,fp,aid,settled in rows:
                need(policy.text(key) and digest(fp) and type(settled) is int and settled in (0,1),'work_reader_response_binding')
                responses.append(policy.ResponseIdentity(key,aid,bool(settled)));response_fingerprints.append((key,fp))
            for conn,old in zip(self._connections,seen):
                if conn.in_transaction or conn.total_changes!=old['changes'] or live._one(conn,'PRAGMA main.data_version')!=old['dataVersion']:
                    raise WorkReadUnavailable('work_snapshot_changed')
            self._check();self._sample+=1
            return CommittedWorkRows(self.expected,self._sample,time.monotonic_ns(),admissions,tuple(run_records),
                tuple(responses),len(workers),tuple(run_bindings),tuple(response_fingerprints))
        except (WorkReadRejected,WorkReadUnavailable):raise
        except (sqlite3.OperationalError,sqlite3.InterfaceError):raise WorkReadUnavailable('work_native_read_unavailable') from None
        except (sqlite3.Error,live.LiveStoreRejected,policy.InvalidEvidence,ValueError,TypeError,AttributeError,KeyError,IndexError,UnicodeError):
            raise WorkReadRejected('work_native_observation_invalid') from None
        finally:
            for lock in reversed(acquired):lock.release()
