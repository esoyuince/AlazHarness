# S121R4 - explicit caller-owned native SessionStore state

Optional native patch on feature94321058, staged in the harness but NOT installed.
The new source is native commit2bc50496bebe21f948dd2e86f553ef1e22904ed2. Exactly
three native files change: small SessionStore constructor and persistence seams,
plus session_borrowed_state.py. No new registry, executor, writer or scheduler.

## Why this seam is needed

The existing SessionStore constructor opens an active-profile registry-owned
state connection. Its private _db setter after construction cannot prove zero
extra opens and does not express the caller's lifetime. This is intended default
behavior, not an upstream data-corruption bug. An independent original-source
control observed the extra registry connection and verified caller state survived
its cleanup. The default path remains unchanged.

The new explicit keyword SessionStore(..., session_db=existing_state) selects an
already-open genuine caller-owned SessionDB BEFORE constructor priming. It never
acquires a registry handle, opens a replacement, adopts a different connection or
closes that caller state. The dedicated binding fixes the canonical home/path,
connection, mutex, process, file identity/application generation and original
native profile-lock handle. A release/reacquire is not the same profile owner.

## Supported scope and refusals

This opt-in mode is deliberately single/default-home: multiplex_profiles=False
and write_sessions_json=False are required explicitly. Existing named/multiplexed
profiles continue to use the old mode. Active home, explicit DB path and routing
keys must remain in the selected home; changed facade configuration/session path,
state handle, owner, generation, attachments, closed connections or repinning are
rejected. An active SQLite transaction is retained, not committed/rolled back;
a busy native state mutex is refused without taking it from its owner.

Routing uses the real primary SQLite implementation and genuine session creation,
lookup/reuse/admission/claim/settlement APIs. Borrowed initialization loads the
primary index only: it does not migrate/import a legacy JSON index or invoke the
default stale-entry repair sweep. Primary load or write failures cannot silently
fall back to sessions.json. Direct legacy import/save is also refused. This does
not turn every native session/transcript/recovery method into a zero-I/O or
side-effect-free operation; normal requested native mutations still have their
own semantics and are not cross-file transactions.

close_all_db_handles() in this mode detaches only the facade. It refuses open
transactions or known cached/inflight/dirty facade work; repeated successful
detach is harmless and later access is rejected without reopening. The caller
must coordinate/drain external users and owns actual state close and profile
release. This is NOT a global all-work quiescence proof, an atomic race-free
shutdown against unrelated same-process callers, or store-release authority.
The native profile ownership map is checked but not acquired/released here.

## Actual tests and first outcomes

23 actual-native Windows cases PASS on the selected three-file patch. They use
real SessionDB, SessionStore, profile ownership, registry and runtime transitions;
no native class/factory is substituted and no post-construction private handle
assignment is used. Constructor/selector/detach audit records zero extra SQLite
connections and no row writes. State and profile remain usable after detach.
A real secondary thread selects the same handle; native primary routing and
queue/claim/settlement use the same caller DB. Default registry mode is a separate
positive control. Negative cases alter only fresh owned fixture objects/data.

The independent S121S1 native002 suite has24 PASS methods on exactly the same
three source hashes, including missing routing schema and no-raw-open observation
controls. It overlaps the23 owner cases, so this is NOT47 independent scenarios.
Its original baseline is intentionally the native default, not a mocked bypass.
Original independent history/results are preserved on integration.

The first own run was21/23: two tests assumed sessions/ did not preexist. A
stage-by-stage real native diagnosis showed imports initialized that scaffold
BEFORE facade construction. Product code did not change. Tests now compare the
whole pre/post profile-entry snapshot. The original failing result and QA source
are retained, not rewritten as success. Independent initial tests found the same
fixture assumption and preserved their first failures separately.

261 native source imports from the owner suite were verified: three explicit
patch files match their tested bytes; the rest were reread from immutable Git.
The patch applies to a fresh original export with exact output hashes and rejects
a second application. Seven offline receipt checks bind that evidence; they are
not seven new native executions. Runtime assertions and receipt-count tests are
kept distinct. No upstream native full pytest suite was executed.

The watched selectors performed zero new SQLite connects. Seven denied import-
time subprocess attempts were Git version discovery, not model/provider calls;
the historical audit field named networkDenied includes those events. There were
no successful external commands/network effects during this native fixture.
Existing native DELETE-journal fallback warnings are preserved; no SQLite/Python
or dependency upgrade is performed. Candidate profiles removed, ownership and
native registry reference counts returned to zero.

## Delivery boundary and next step

The original490 harness source/config files remain unchanged. This task adds the
optional patch/config, fixed QA and offline receipts. The complete harness run
must be performed on the combined source with independent QA before final
acceptance; native-only or static PASS is not a full regression claim.

BorrowedAPIStores still refuses gateway_runner through borrowed_runner_conflict.
That file and guard are byte-unchanged. No listener, full GatewayRunner/AIAgent,
three-store bootstrap, active-work HTTP or Linux profile/mount-isolation acceptance
is implied by SessionStore reuse. The next step is an explicit same-owner
canonical runner lifecycle that can be qualified before adapter compatibility is
changed. No private reattachment after opening and no guard removal shortcut.

Installed vendor/source lock remainseb75627; maincc7ceba/push/CI/production/
accounts unchanged. No WSL/root/provider/model call or blocked-operation retry.
C120P9 optional physical-stack extension stays HOLD and is not reactivated.
Current status.md and summary/delivery records identify the exact terminal scope.
