"""Read-only known-constructor-repair prerequisite for pinned native state.

Use on the preopen helper's read-only connection AFTER independently pinned
schema qualification and BEFORE writable SessionDB construction. This does
not open a database or duplicate the preopen/ownership/layout gates. Known
migration/repair indicators must be resolved explicitly, never erased here.
Absence of these markers is NOT proof of zero native constructor writes or
all possible data repairs. Caller keeps the native lease and bounded SQL
execution policy; this function does not authorize HTTP/admission/retry.
"""
from __future__ import annotations
import sqlite3

NATIVE_PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
SCHEMA_VERSION=31
REQUIRED={'message_uid_backfill':'1'}
REPAIR_KEYS=frozenset(('fts_stale','fts_cjk_stale','fts_rebuild_deferral',
    'fts_rebuild_high_water','fts_optimize_available','message_uid_backfill_id'))

class ConstructorMetadataRejected(RuntimeError):
    pass


def _require(ok,reason):
    if not ok:raise ConstructorMetadataRejected(reason)


def verify_constructor_metadata(connection,*,native_pin):
    """Observe fixed main-schema metadata on an existing query-only connection.

    Finite row/field bounds. No SQL writes, raw file access, connection close,
    PRAGMA assignment, native imports, migration, epoch advance or recovery.
    Even terminal-looking marker values (0, false, empty) are not a waiver.
    """
    try:
        _require(type(native_pin) is str and native_pin==NATIVE_PIN,'constructor_metadata_pin')
        _require(type(connection) is sqlite3.Connection,'constructor_metadata_connection')
        _require(tuple(connection.execute('PRAGMA query_only').fetchone())==(1,),
                 'constructor_metadata_query_only_required')
        before=(connection.total_changes,connection.execute('PRAGMA main.data_version').fetchone())
        version=[tuple(r) for r in connection.execute('SELECT version FROM main.schema_version').fetchmany(2)]
        _require(version==[(SCHEMA_VERSION,)],'constructor_metadata_schema_version')
        keys=tuple(sorted(set(REQUIRED)|REPAIR_KEYS))
        placeholders=','.join('?' for _ in keys)
        # LIMIT caps rows before a malformed non-unique metadata table could
        # flood memory. The caller separately verifies the actual schema digest.
        rows=connection.execute('SELECT key,value FROM main.state_meta WHERE key IN ('+
            placeholders+') ORDER BY key LIMIT ?',(*keys,len(keys)+1)).fetchall()
        _require(len(rows)<=len(keys),'constructor_metadata_ambiguous')
        seen={}
        for row in rows:
            _require(len(row)==2 and type(row[0]) is str and row[0] not in seen,
                     'constructor_metadata_ambiguous')
            key,value=row
            _require(key not in REPAIR_KEYS,'constructor_metadata_repair_pending')
            _require(type(value) is str and value==REQUIRED.get(key),
                     'constructor_metadata_backfill_incomplete')
            seen[key]=value
        _require(seen==REQUIRED,'constructor_metadata_backfill_incomplete')
        _require(before==(connection.total_changes,connection.execute('PRAGMA main.data_version').fetchone()),
                 'constructor_metadata_changed')
        return {'state':'KNOWN_CONSTRUCTOR_REPAIR_MARKERS_CLEAR','nativePin':NATIVE_PIN,
                'schemaVersion':SCHEMA_VERSION,'checkedRepairKeyCount':len(REPAIR_KEYS),
                'knownBackfillComplete':True,'sqlWritesPerformed':False,
                'connectionCreated':False,'connectionClosed':False,
                'allConstructorSideEffectsExcluded':False,'nativeConstructorMayWrite':True,
                'schemaDigestVerifiedHere':False,'runtimeAdmissionAuthorized':False,
                'fullD3BAccepted':False}
    except ConstructorMetadataRejected:raise
    except (sqlite3.Error,ValueError,TypeError,IndexError,KeyError,AttributeError):
        raise ConstructorMetadataRejected('constructor_metadata_unavailable') from None
