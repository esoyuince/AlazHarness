"""Trusted receipt for reopening one cleanly closed finite profile.

The receipt is captured only after the original owner confirms closure, while its
caller still holds the real lease. It is data supplied by that trusted caller,
like PreparedStoreExpectation, not a signature or hostile same-process sandbox.
No generated file is deleted, repaired or used to discover new executable paths.
Old cold layouts remain unchanged unless this exact receipt is selected.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
import gateway_native_layout as layout

FEATURE='d1516731308de8e87130dc68124e69aad35d6911'
DIRECTORIES=frozenset(('runtime','cache/documents'))
FILES=frozenset(('auth.lock','cache/tool_discovery_cache.json',
                 'runtime/active_sessions.json','runtime/active_sessions.lock'))
PATHS=DIRECTORIES|FILES
MAX_DISCOVERY_BYTES=262144
MAX_ACTIVE_BYTES=4096
MAX_DISCOVERY_ENTRIES=1024

@dataclass(frozen=True)
class RetainedProfileExpectation:
    native_feature: str
    home: str
    home_identity: tuple
    database_identities: tuple
    epoch: int
    instance_id: str
    discovery_sha256: str


def _json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            layout.require(key not in result,'retained_duplicate_key');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
                      parse_constant=lambda _ : (_ for _ in ()).throw(layout.NativeLayoutRejected('retained_nonfinite')))


def _discovery_shape(value):
    layout.require(type(value) is dict and 0<len(value)<=MAX_DISCOVERY_ENTRIES,'retained_discovery_shape')
    for name,row in value.items():
        layout.require(type(name) is str and 0<len(name)<=4096 and chr(0) not in name
                       and type(row) is list and len(row)==3
                       and type(row[0]) is int and 0<=row[0]<2**63
                       and type(row[1]) is int and 0<=row[1]<=4*1024*1024
                       and type(row[2]) is bool,'retained_discovery_entry')
    return value


def _empty_active(home,snapshot):
    raw=layout._read_aux(home,'runtime/active_sessions.json',snapshot,MAX_ACTIVE_BYTES)
    value=_json(raw)
    layout.require(type(value) is dict and set(value)=={'entries'}
                   and type(value['entries']) is list and not value['entries'],
                   'retained_active_sessions_not_empty')


def validate_receipt(receipt):
    layout.require(type(receipt) is RetainedProfileExpectation
                   and receipt.native_feature==FEATURE,'retained_receipt_type_or_feature')
    layout.require(type(receipt.home) is str and Path(receipt.home).is_absolute()
                   and type(receipt.epoch) is int and receipt.epoch>0
                   and type(receipt.instance_id) is str and bool(receipt.instance_id)
                   and type(receipt.discovery_sha256) is str
                   and re.fullmatch('[0-9a-f]{64}',receipt.discovery_sha256) is not None,
                   'retained_receipt_fields')
    identities=(receipt.home_identity,*receipt.database_identities) if type(receipt.database_identities) is tuple else ()
    layout.require(len(identities)==4 and all(type(v) is tuple and len(v)==2
                   and all(type(n) is int and n>0 for n in v) for v in identities)
                   and len(set(identities))==4,'retained_receipt_identities')


def validate_snapshot(home,snapshot,receipt):
    validate_receipt(receipt)
    layout.require(str(home)==receipt.home and snapshot['profile'][:2]==receipt.home_identity,
                   'retained_profile_identity')
    names=('state.db','runs_idempotency.db','response_store.db')
    layout.require(tuple(snapshot[name][:2] for name in names)==receipt.database_identities,
                   'retained_database_identity')
    raw=layout._read_aux(home,'cache/tool_discovery_cache.json',snapshot,MAX_DISCOVERY_BYTES)
    layout.require(hashlib.sha256(raw).hexdigest()==receipt.discovery_sha256,'retained_discovery_changed')
    _discovery_shape(_json(raw));_empty_active(home,snapshot)


def capture(owner):
    """Capture after normal close and before caller lease release; no DB opens."""
    from gateway_store_startup import NativeStoreStartup
    from gateway_prepared_consumer import PreparedRuntimeConsumer,verify_imports
    layout.require(type(owner) is NativeStoreStartup and owner._stage=='CLOSED',
                   'retained_owner_not_closed')
    owner._owned()
    c=owner._prepared_consumer
    layout.require(type(c) is PreparedRuntimeConsumer and c._owner is owner
                   and c._stage=='DETACHED' and c._finite_turn is True
                   and c._selected_feature==FEATURE and c._binding._stage=='DETACHED'
                   and c._bundle._stage=='DETACHED','retained_consumer_not_closed')
    verify_imports(c._source_proof)
    root,hashes=c._source_proof
    import tools.registry as registry
    layout.require(Path(registry.__file__).resolve()==root/'tools/registry.py',
                   'retained_registry_source')
    home=owner._held._home
    args=(home,owner._actor[1],owner._actor[2],owner._expected.state_identity[0])
    first=layout._snapshot(*args,include_response=True,include_prepared=True,include_retained=True)
    # Candidate paths originate in the prequalified native source manifest, NEVER in cache data.
    expected={}
    for name,digest in hashes.items():
        path=Path(name);parts=path.parts
        candidate=(len(parts)==2 and parts[0]=='tools' and path.suffix=='.py')
        candidate=candidate or (len(parts)==3 and parts[0]=='tools' and parts[2]=='tool.py'
                                and str(Path(*parts[:2])/'__init__.py').replace(chr(92),'/') in hashes)
        if not candidate or path.name in ('__init__.py','registry.py','mcp_tool.py'):continue
        target=root/path
        layout.require(target.resolve()==target and hashlib.sha256(target.read_bytes()).hexdigest()==digest,
                       'retained_tool_source_changed')
        stat=target.stat()
        expected[str(target)]=[stat.st_mtime_ns,stat.st_size,registry._module_registers_tools(target)]
    raw=layout._read_aux(home,'cache/tool_discovery_cache.json',first,MAX_DISCOVERY_BYTES)
    layout.require(_discovery_shape(_json(raw))==expected,'retained_discovery_not_native')
    _empty_active(home,first)
    receipt=RetainedProfileExpectation(FEATURE,str(home),first['profile'][:2],
        tuple(first[name][:2] for name in ('state.db','runs_idempotency.db','response_store.db')),
        owner._expected.epoch,owner._expected.instance_id,hashlib.sha256(raw).hexdigest())
    validate_snapshot(home,first,receipt)
    layout.require(first==layout._snapshot(*args,include_response=True,include_prepared=True,include_retained=True),
                   'retained_capture_changed')
    # Run the unchanged pinned SOUL/schema checks too; receipt adds only narrow retained paths.
    layout.inspect_profile(home,uid=args[1],gid=args[2],device=args[3],
                           include_response=True,include_prepared=True,retained=receipt)
    owner._owned();verify_imports(c._source_proof)
    return receipt
