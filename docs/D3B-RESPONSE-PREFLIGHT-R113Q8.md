# R113Q8 - cold response-store preflight, before writable native construction

Basea3951d7. Adds gateway_response_preopen.py and one fixed isolated interpreter
worker. ConcurrentL113F6 owns live verification and optional existing A109
three-store sequencing; this task does not create another startup owner.

## Trusted input and narrow acceptance

PreparedResponseExpectation pins native featurecc16c10, the exact13-entry native
SQLite schema digestc4b66ce0, response file device/inode, and constructor limits
100 body/1000 identity records. Its identity is distinct from both existing
stores on the same device. Expectations must come from trusted provisioning,
not from an untrusted candidate. Actual native ResponseStore produced the schema
in an independently owned preparation step; no handmade substitute native engine.

The parent holds an actual ProfileLease and matches mount observations for all
three files. It NEVER opens a raw DB descriptor or SQLite connection. It invokes
scripts/run_response_preopen.py with fixed argv/minimal env/closed inherited fds.
The helper validates its parent/ordinaryUID, private700/600 files, single-link
identity, normal SQLite header and absence of every journal/WAL/SHM sidecar.
It reads mode=ro, not immutable/nolock; extensions disabled, trusted_schemaOFF,
query_onlyON, strict SQL authorizer and bounded size/opcode/time budgets.
All reads are main-qualified and the pinned schema excludes surprises/views/
triggers/migrations. Before/after SHA256 and metadata must remain exact.

Known constructor mutation conditions are rejected: any unsettled identity,
body or settled-identity retention pressure, missing prepared columns, unexpected
versions, corrupt/nonobject bodies, invalid identity bindings/times, orphaned
admission/output/conversation records. Nothing is created, repaired, evicted,
settled, made retryable or silently recovered. Missing cached response bodies are
allowed when their settled identities legitimately outlive LRU bodies. The fixed
limits and clean-only policy are not a general migration or busy-serving policy.

A success is COLD_RESPONSE_PREFLIGHT_VERIFIED. It explicitly does NOT prove
canonical outcome equivalence for response records, every possible constructor
side effect, paired recovery, physical persistence or permission to start HTTP.
Path/content checks assume a cooperative exclusively owned lifecycle, not hostile
same-UID or host-root replacement and every possible ABA race.

## Actual tests

44 methods run with real SQLite on Windows and Linux. Parent transport/lease
contracts in those units are explicitly doubled.6 offline receipt methods bind
that evidence/source/log data and are not extra native executions.

The separate ordinary P71C native test uses actual SessionDB, replay store,
ResponseStore from the pinned source feature, native ProfileOwnership/ProfileLease
and real fixed-helper processes, with no native class/factory replacements.
Empty and populated stores pass, the response file bytes remain exact, and a
subsequent qualified native reopen reports zero response row modifications.
13 refusal cases cover pending identity, old schema, malformed data, orphan
records, over-limit eviction, three sidecars, identity/mode, missing/link and
actual busy SQLite state.47 overlapping assertions pass; these are not47 trials.

A separate SQLite competitor receives BUSY before and after the helper refuses
a locked response DB, then succeeds only after the owning connection closes.
This establishes that helper descriptor cleanup does not drop the parent's lock.
Audit hooks observe zero parent raw data opens/SQLite connections during checks.
The ordinary helper/native workload has no listener/provider/root/mount action;
this is NOT full isolation or the combined A109 integration acceptance.

First schema discovery stopped before creation because the stripped Windows test
environment had no USERPROFILE; only owned HOME/USERPROFILE were provided on retry.
The first SQL-budget unit fixture was too small to trigger the1000-opcode callback;
using100 valid rows exercised the unchanged product budget. Both first failures
remain recorded and neither rejection policy nor production settings was relaxed.
Native SQLite selected DELETE via its existing safety branch; no runtime was
upgraded and no WAL test or physical-power-loss claim is made.

## Delivery boundary

All434 prior source/config/test files remain unchanged. Only5 executable/test
sources are added. Native feature/source-lock/vendor is not activated. All copied
native files were read from exact Git feature blobs and existing dependency hashes;
no package was installed. Temporary Linux data/code was removed. The full standard
suite is reserved for the final joint tree with live/start/close work; focused
success is not full-suite proof. Current status.md records that boundary.

Next: source-identical integration into the ONE existing startup, verify response
preflight precedes any native writable constructors and epoch mutation, retain
response-first close order and active-transaction refusal, and run a fresh whole
suite. Full third-store namespace/remount/adapter readiness and healthy-busy work
policy remain separate tests. LegacyIPCv2 CLOSED/fullD3B OPEN, no main/push or CI
production/defaultUbuntu/service changes.
