"""Versioned operator audit records. A stored receipt never grants execution rights."""
import hashlib
import json
import re

ACTION='abandon_unadmitted'
PREFIX='alaz.operator_resolution.v1.'
INDEX='alaz.operator_resolution.run.v1.'
HEX=re.compile(r'[a-f0-9]{32}\Z')
HASH=re.compile(r'[a-f0-9]{64}\Z')


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def key_digest(value):return hashlib.sha256(value.encode()).hexdigest()


def run_index(scope,run_id):return INDEX+digest({'scope':scope,'runId':run_id})


def validate_record(record,*,context,reservation,run_id):
    """Verify exact bindings, not authenticity against a hostile DB administrator."""
    if type(record) is not dict:raise ValueError('malformed_resolution')
    expected={'receiptVersion','commandId','action','profileBinding','scopeHash','runId',
              'keyHash','requestFingerprint','epoch','instanceId','snapshotDigest',
              'planDigest','recordedAtMs','recordDigest'}
    if set(record)!=expected:raise ValueError('malformed_resolution')
    if type(record['receiptVersion']) is not int or record['receiptVersion']!=1 or record['action']!=ACTION:
        raise ValueError('unsupported_resolution')
    if not isinstance(record['commandId'],str) or not HEX.fullmatch(record['commandId']):raise ValueError('malformed_resolution')
    for name in ('profileBinding','scopeHash','keyHash','requestFingerprint','snapshotDigest','planDigest','recordDigest'):
        if not isinstance(record[name],str) or not HASH.fullmatch(record[name]):raise ValueError('malformed_resolution')
    if record['recordDigest']!=digest({k:v for k,v in record.items() if k!='recordDigest'}):raise ValueError('resolution_digest_mismatch')
    if (record['profileBinding'],record['scopeHash'],record['runId'],record['keyHash'],record['requestFingerprint']) != (
          context.binding,context.scope,run_id,key_digest(reservation['idempotency_key']),reservation['fingerprint']):
        raise ValueError('resolution_identity_mismatch')
    if type(record['epoch']) is not int or not 0<record['epoch']<=context.epoch:raise ValueError('resolution_epoch_mismatch')
    if not isinstance(record['instanceId'],str) or not record['instanceId']:raise ValueError('malformed_resolution')
    if record['epoch']==context.epoch and record['instanceId']!=context.instance_id:raise ValueError('resolution_epoch_mismatch')
    if type(record['recordedAtMs']) is not int or record['recordedAtMs']<=0:raise ValueError('malformed_resolution')
    return record


def read_resolution(conn,*,context,reservation,run_id,decode):
    index=conn.execute('SELECT value FROM state_meta WHERE key=?',(run_index(context.scope,run_id),)).fetchone()
    if index is None:return None
    command_id=decode(index[0])
    if not isinstance(command_id,str) or not HEX.fullmatch(command_id):raise ValueError('malformed_resolution_index')
    row=conn.execute('SELECT value FROM state_meta WHERE key=?',(PREFIX+command_id,)).fetchone()
    if row is None:raise ValueError('missing_resolution_record')
    record=validate_record(decode(row[0]),context=context,reservation=reservation,run_id=run_id)
    if record['commandId']!=command_id:raise ValueError('resolution_index_mismatch')
    return record


def assert_no_recorded_work(conn, run_id, decode):
    """An incomplete terminal index cannot establish the absence of historical work.

    Bounded conservative scan: malformed archives or an excessive scan refuse
    maintenance rather than guessing. This is only on an explicit operator path.
    """
    if conn.execute('SELECT 1 FROM session_admissions WHERE request_id=? OR target_session_id=? LIMIT 1',(run_id,run_id)).fetchone():
        raise ValueError('canonical_work_exists')
    for table,column in (('sessions','id'),('messages','session_id'),('worker_executions','session_id')):
        if conn.execute(f'SELECT 1 FROM {table} WHERE {column}=? LIMIT 1',(run_id,)).fetchone():
            raise ValueError('related_work_exists')
    size=0
    cursor=conn.execute("SELECT value FROM state_meta WHERE key GLOB ? LIMIT 10001",('gateway.terminal_admission.v1.*',))
    for count,(encoded,) in enumerate(cursor,1):
        if count>10000 or not isinstance(encoded,str):raise ValueError('archive_scan_unverified')
        size+=len(encoded.encode('utf-8'))
        if size>8_388_608:raise ValueError('archive_scan_unverified')
        archived=decode(encoded)
        if type(archived) is not dict or any(not isinstance(archived.get(k),str) or not archived[k] for k in ('request_id','target_session_id','admission_id')):
            raise ValueError('archive_scan_unverified')
        if archived['request_id']==run_id or archived['target_session_id']==run_id:
            raise ValueError('retired_work_exists')
