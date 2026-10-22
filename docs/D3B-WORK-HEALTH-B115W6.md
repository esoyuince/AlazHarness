# B115W6 - bounded work-health policy and native-data compatibility

This additive module is a read-only DECISION CORE, not a new scheduler or a live
HTTP service. It leaves all454 existing source/config/test files unchanged. The
single selected gateway_work_health.py belongs to this branch; W115B6 owns the
complementary native reader. Neither implies an installed Hermes feature update.

## Meaning of the five decisions

| Decision | Evidence interpretation | Not authorized |
| --- | --- | --- |
| IDLE | No active rows or live owners in a complete fresh verified snapshot. | Dispatch or store release. |
| BUSY | Native committed identities match the separately observed live owner. | Another job, retry, settlement or close. |
| DRAINING | Explicit drain remains latched while ownership is retained. | Reopening intake or automatic cancellation. |
| RECONCILE_REQUIRED | Unknown/stale/unowned work, identity loss, or uncertain shutdown. | Replay, takeover, repair or automatic recovery. |
| UNOBSERVABLE | Active transaction, stale/incomplete/changing or malformed evidence. | A positive healthy/idle assertion. |

An owned queued admission is not an error. Native queued generation is NULL and
is not invented as zero. Started/settling owner generation must match current
session generation and current runtime epoch. Process identity includes a start
token as well as PID; old native rows cannot prove a new process is their owner.
This initial policy allows one executing/settling owner globally; bounded queued
work may coexist. Delegated workers are conservatively unresolved until their
own live adoption/liveness contract is accepted.

Settlement spans separate databases. While the SAME verified live task is in
SETTLING, the canonical admission may already be terminal while replay/response
records are still finishing. It remains BUSY and grants no write authority.
Remove that task before completing its records and reconciliation is required;
terminal status in one database never silently makes the whole system idle.
ADMITTING/unqualified transitions are UNOBSERVABLE, not fabricated consistency.

WorkHealthSession latches proven reconciliation and drain. Merely restoring old
rows cannot clear a reconciliation fault; transient unavailable observations may
be repeated when a NEW fresh stable observation is possible. The policy neither
opens a connection nor mutates a row, cancels a task, settles a response, advances
an epoch, releases ownership or invokes recovery. Every public decision explicitly
denies runtime admission, retry and store release. Its 'healthy' field concerns
ONLY the supplied work model, not independently established service readiness.

## Trust boundary still outside this module

RuntimeIdentity and WorkSnapshot are local typed data, not capabilities. A future
trusted adapter collector must bind all three real handles, the native profile,
process identity, live asyncio/task owners, request identity/fingerprints and
producer revisions before and after observation. It must prove no omitted active
owner or worker. It must NOT derive task_alive/storage_verified/complete from
pending DB rows or accept those flags from HTTP/model/user-controlled JSON.

The current policy consumes explicit completeness, storage-verification and live
owner assertions. It does not itself prove them. Expected run/response fingerprints
and scope/key matching remain the collector/reader integration boundary; merely
having matching run IDs does not establish a request fingerprint. A separate
read-only reader may expose binding metadata but must not mint those trust flags.
Existing strict cold/quiescent HTTP gates remain unchanged and unrelaxed.

## Tests actually executed

37 focused deterministic policy methods passed, including ownership/epoch/session
fences, dead task, partial settlement, bounded immutable inventories, duplicate
JSON keys, stale snapshots, transaction contention, PID reuse, drain and sticky
reconciliation. File/descriptor opens are forbidden during tested policy decisions.

16 native-data scenarios passed on Windows using real SessionDB, replay store,
ResponseStore, runtime transitions and ProfileOwnership at native featurecc16c10.
Actual queue/start/terminal/response-settlement data is read from main-qualified
SQL; TEMP tables cannot hide pending rows. Policy execution is watched for zero
SQLite connects/raw file opens and unchanged total_changes. Native classes and
methods were not replaced. Each test uses fresh owned temporary homes, and final
profile release/temp removal are confirmed.

CRITICAL: the live task list, process-start token and storage-verification flags
in those16 cases are explicit TEST FIXTURES. This proves native data mapping and
policy semantics, NOT a real adapter collector, real executing agent, Linux
isolation or healthy/busy HTTP acceptance. Explicit native recovery is used ONLY
by one fault fixture to create unknown data; the policy never invokes it.
The existing native DELETE journal fallback warning is preserved in stderr; no
interpreter/library upgrade or configuration change was performed.

All imported native modules were reread as immutable no-replacement Git blobs and
matched to the actually imported SHA256 map. Five offline receipt checks retain
that source and scope binding. They are not five additional native executions.
The fresh complete standard regression is reserved for the combined policy/reader
branch; focused/native PASS must not be relabelled a full standard PASS.

## Retained tooling events and ownership

The initial unit source-write attempt included an unpaired Unicode surrogate;
compile refused before the test file was written or run. Constructing that value
inside the test with chr preserved the intended invalid-input case. Native data
had NULL queued generation, observed directly from the pinned native schema.

Both parallel tasks discovered a potential duplicate policy. W115B6 selected our
exact module before this task attempted to read its earlier draft. That read
stopped at FileNotFoundError before copying/deleting any own product source. One
policy remains selected; snapshots and both task logs preserve the chronology.
No parallel working file was overwritten, and no second engine is shipped.

Prior root-cleanup and early-source-check tool blocks remain BLOCKED; no WSL/root
command or alternate-route retry occurred. No provider/model/production/accounts/
CIqueue/main/push action. Installed native source locks/gitlinks remain unchanged.

## Next gate

Combine the source-identical native reader and its genuine read-only tests with
this policy, run one fresh complete standard suite, then implement the actual
trusted producer snapshot boundary. Only AFTER actor/handle/liveness/revision and
fingerprint validation and same-path isolation tests may HTTP report this model.
Native API work routes, live broker send/accounting and fullD3B remain closed/open
respectively; this module does not confer cross-store atomicity or powerloss safety.
