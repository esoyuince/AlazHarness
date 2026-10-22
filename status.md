# AlazHarness — status

## D3B-PREOPEN-P108E — SCOPED QUALIFIED; LOCAL DELIVERY PENDING

Branch alaz/d3b-preopen-p108e; worktree scratch/worktrees/d3b-preopen-p108e.
Base d24f8d2654c4a866445bf0b3d1e31f085ca34de7. One implemented helper path:
packages/claw-hermes/gateway_store_preopen.py + scripts/run_store_preopen.py.
Prior403 files unchanged. Do not merge parallel S108E's different runtime;
retain it separately for comparison/independent QA rather than duplicating paths.

### Implemented and verified

Under held final native ProfileLease, a fixed fresh interpreter checks both
existing private files before writable native constructors. Cold DELETE mode
only; every journal/WAL/SHM sidecar refuses explicit recovery. Normal SQLite
mode=ro locking, never immutable/nolock. Independent schema/UUID/app/inode/epoch
pins, SQL/size/time bounds and existing P107A constructor metadata on SAME
readonly connection. Content/metadata stable; no repair/migration/admission.
Parent opens no DB descriptor/connection, retains lease and reaps helper.

Actual P71C ordinaryUID23001 native002:37 nested checks/9 refusal cases PASS.
Separate fresh provisioning then finalexec/currentLandlock/native ProfileLease,
preflight -> real native SessionDB/RunStore open -> existing live gate, epoch0.
Actual competitorBUSY before+after helper, acquisition only after native close.
Native product unchanged; first failure was QA expecting later rather than
parent-level symlink refusal. Test fixture run-field collision also corrected
without assertion/product changes; original logs and source snapshots retained.

NEW fullWindows2662=2639PASS/23SKIP/0ERROR/0FAIL exit0;408 hashes stable.
All403 preexisting sources unchanged. Windows29unit+5receipt and Linux34/34
are subsets/platform repeats;23 old platform/opt-in skips NOT rerun.
No own temporary code/profile or live process remains. Shared P71C not stopped;
defaultUbuntu, CI queue/config, root user changes and production untouched.

### Remaining boundary

No fullP102 network/mount/cgroup startup, HTTP listener or provider call here.
Preflight is a cooperative snapshot and known marker prerequisite, NOT proof
all native constructor writes are absent, paired recovery, power-loss safety
or enduring launch/retry authority. Caller must apply accepted finite layout,
keep all writers drained and trust preparation. Next compose one fixed PRODUCT
startup entrypoint through preflight/native open/live gate/explicit recovery
before readiness; then run it under full confinement and broker ledger/send.
LegacyIPCv2 CLOSED/fullD3B OPEN; old R91F/G82C blocked work untouched.

### Records

Report docs/D3B-PREOPEN-P108E.md.
Evidence evidence/d3b-preopen-p108e/summary.json, native-002-stdout.txt,
full-windows-result.json, full-sources-before/after.json, cleanup.json.
Native002 request010, Linuxselected015, cleanup017 and full014 terminal0.
Local static/selected commit follows; read Git HEAD/delivery for exact pointers.
No main/push, root/mount/account/service/model/provider operation.
Prior current status and parent retained byte-for-byte in
 docs/status-history/p108e-work-log.md and p108e-parent-d24f8d2.md.
