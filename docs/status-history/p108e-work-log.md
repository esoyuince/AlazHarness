# AlazHarness — status

## D3B-PREOPEN-P108E — IN PROGRESS

OWNERSHIP: P108E has implemented packages/claw-hermes/gateway_store_preopen.py
and scripts/run_store_preopen.py (fixed worker+parent). Keep this product owner
stable. Parallel S108E had no product files at observed17:48 local read; it
should provide complementary QA, not a second runtime. No role swapping or
editing its files. The next work here is qualifying THIS source.

Active branch alaz/d3b-preopen-p108e; worktree scratch/worktrees/d3b-preopen-p108e.
Base recorded in evidence/d3b-preopen-p108e/baseline.json (canonical d24f8d2).
Implement fixed read-only helper BEFORE writable native store construction;
reuse PreparedStoreExpectation, native ProfileLease, mount observer, schema_digest
and P107A constructor-metadata prerequisite. Old P107E has no product source and
is preserved untouched; no duplicate preopen implementation will be introduced.

Existing403 sources frozen. New helper subprocess never invokes native store
constructors, uses mode=ro with normal SQLite locks (no immutable/nolock), rejects
cold-sidecar/recovery ambiguity, validates trusted pins and marker prerequisites,
and returns a snapshot not HTTP/retry authority. Parent holds native lease and
mount checks; child closes cannot cancel parent's SQLite locks. No root/mount,
CI queue/config, production, paid model, main/push or old denied R91F/G82C action.
Use only owned temporary profiles, ordinary UID23001 in approved P71C for native
validation. Preserve concurrent branches. No pending command yet.

Previous canonical status retained byte-for-byte in
 docs/status-history/p108e-parent-d24f8d2.md. Keep this current file bounded.


### Native002 terminal; full regression in progress

Actual native002 completed exit0:37 target predicates/9 refusals, separate readonly child then actual native constructors/live gate; old version/repair/missing-backfill/sidecar/permission/link cases unchanged, parentSQLiteBUSY before+after helper then acquire only after native close. No parent DB opens during gate. First native001 failure was only QA expected later rather than earlier symlink refusal; preserved, product unchanged. Five receipt tests nowPASS after renaming a fixture field that shadowed unittest.run; no assertion/source changes. Unit29PASS. Full request a107b270-9c02-479b-a99e-004200000014 starts408-source freeze; all403 originals unchanged. Do not edit product/QA/test sources until terminal. No main/push/CI/production work.
