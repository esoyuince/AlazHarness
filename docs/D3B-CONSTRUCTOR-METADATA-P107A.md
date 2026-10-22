# P107A — native constructor metadata prerequisite

Base08e53df, branch alaz/d3b-preopen-p107a. Complement to the separate P107E
read-only preconstructor helper, NOT another helper or storage implementation.
Native Hermes pin: eb75627faf532fa6ffbdae59a0d14b0b385fc780.

## Independent finding

Four fresh owned native profiles were prepared with the actual SessionDB,
RunIdempotencyStore and ProfileOwnership classes. After all DB connections
closed, deliberate QA-only mutations produced an old schema_version, an
fts_stale marker, or a missing message_uid_backfill marker. An unchanged
profile was the positive control. No native method was replaced or mocked.

For fts_stale and missing-backfill cases, the full SQLite schema fingerprint,
version31, application generation, store UUID, epoch rows and file inode all
still matched the original prepared state. Nevertheless a subsequent REAL
writable SessionDB constructor removed fts_stale or inserted the completed
backfill marker. Thus those schema/identity observations alone do not exclude
constructor data repair. The old-version case advanced version30 to31.
Even the clean-control constructor changed database bytes without changing
the schema: do NOT equate a valid prepared profile with a zero-write constructor.

These writable calls after marker refusal are intentional diagnostic actions
ONLY in the newly created QA profiles, never runtime adoption/repair. The test
is not a startup entrypoint that would continue after rejection. The original
unmodified observation and a fresh complete run including the new prerequisite
are preserved separately; four repeated cases are not eight distinct scenarios.

## New narrow product slice

packages/claw-hermes/gateway_constructor_metadata.py observes an EXISTING
query-only SQLite connection AFTER independent schema qualification and BEFORE
any writable constructor. It opens no file/connection, writes no SQL, closes
nothing, changes no PRAGMA and advances no epoch. It checks the pinned version,
requires message_uid_backfill exactly '1', and refuses presence of six known
repair/cursor indicators regardless of whether their value looks false/empty:
fts_stale, fts_cjk_stale, fts_rebuild_deferral, fts_rebuild_high_water,
fts_optimize_available, message_uid_backfill_id.

Main-qualified SQL prevents TEMP tables hiding the real metadata. Results are
bounded; duplicate metadata is not silently reduced to the last/first row.
Unknown auxiliary metadata is not deleted or declared safe. Successful output
explicitly says allConstructorSideEffectsExcluded=false, nativeConstructorMayWrite=true,
schemaDigestVerifiedHere=false and runtimeAdmissionAuthorized=false. This is
one prerequisite for the complete startup policy, not global constructor safety,
request readiness, automatic reconciliation or permission to retry unknown work.

The caller must retain its native profile reservation and bounded SQLite query
policy. The function preserves caller-owned connections/read transactions and
does not replace authorization/progress callbacks. It does not qualify disk
location, read-only open flags or full schema by itself; the independent
preopen helper owns those responsibilities. No general recursive profile or
kernel permission changes are introduced.

## Actual execution / evidence

Both native runs used ordinary UID23001/GID23003 in the already approved
AlazHarness-D3B-P71C distribution. Code and profiles were new owned temporary
paths. Actual pinned276 native Python files and31 existing dependency files were
transported with recorded hashes; no package installation, upstream patch,
privileged command, mount, provider/model or personal state access occurred.

Current marker-native run: four child cases completed; clean control accepted,
old-version/stale-FTS/missing-backfill refused with exact bounded reason codes.
All read-only observations kept total_changes=0 and asserted identical file
SHA256 before/after the observation. The later native constructor changes are
recorded as the separate deliberate QA stage, not attributed to the guard.
Profile locks were released normally; temporary code/profiles were removed.

Unit tests use actual SQLite with small fixtures, not an emulated SQL engine.
19 methods cover known keys and values, schema version, duplicate/missing rows,
query-only policy, active read transactions, closed/missing objects, row factory,
TEMP shadowing, bounded reads, no raw file open and conservative output claims.
Five offline receipt methods bind current source hashes to native rows/results
and immutable upstream inventories. Windows and Linux both run the same24
methods; those repeats are not extra scenarios or new native executions.
The full suite result is recorded only after its terminal receipt/source freeze.

## Integration boundary

At this checkpoint P107E's fixed read-only helper is a parallel work item. This
branch does not replace it or claim it has called this prerequisite. Add the
call immediately after trusted schema/version/UUID/application/epoch checks,
using the SAME existing read-only SQLite state connection, before it is closed
and before ANY writable SessionDB invocation. Fail closed on repair metadata.
Then qualify that combined fixed startup sequence and existing live-store gate
under actual full confinement before HTTP admission. Untested general home,
paired atomic recovery and power-loss remain outside acceptance.

Existing399 source files remain unchanged. No CI queue/config, production,
account/service, defaultUbuntu, published main or remote update. Root worktree
changes are preserved. The lab is shared with the parallel task and is not
terminated by this task. Current status.md remains short, older canonical
history kept via the original snapshot and existing history files.

Evidence: evidence/d3b-preopen-p107a/ (effects-*, marker-native-*, unit/receipt
results, source manifests and final summary). Script:
scripts/qa/p107a_constructor_effects.py.

## Primary references used for design boundaries

- SQLite URI filenames: https://www.sqlite.org/uri.html — mode=ro versus
  immutable/nolock; immutable disables locking/change detection and is not used.
- SQLite file corruption guidance: https://www.sqlite.org/howtocorrupt.html —
  independent raw close in the same process can cancel SQLite POSIX locks;
  journal files must not be removed to fake a clean database.
- SQLite security guidance: https://www.sqlite.org/security.html — trusted-schema,
  authorizer and bounded query budgets belong in the preopen connection owner.
These are background references, not substitutes for local execution evidence.

## Final current-source result

Fresh fullWindows2628=2605PASS/23SKIP/0ERROR/0FAIL, exit0. All403 hashes stable; all399 prior source files unchanged. Windows/Linux selected24/24 each, including5 receipt tests: subsets/platform repeat, not added to full total. Four actual native cases completed; first repetition kept separate. The23 existing platform/opt-in skips were not newly run. Cleanup independent audit CLEAN. Preopen/helper wiring and fixed full startup NOT accepted here.

## Canonical delivery

Tested code/evidence commit `2d527e55d6611c544f8fa6ad2759f0f548046259` fast-forwarded from `08e53df8c6ea18791c874eabd8c3d13ebc979579` to the local canonical development branch. All403 source bytes remain identical to the full qualification. The marker prerequisite is available but is NOT automatically connected to the separate preopen helper or listener. This follow-up changes documentation/static delivery only; no main/push or new native run. Read current status.md for the next work item.
