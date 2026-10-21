# Native profile ownership lifecycle — L99D

Branch: `alaz/d3b-profile-lease-l99d`; base `bb30a99`.
Status: native profile-lock scope PASS; full regression recorded separately.
This is not a complete persistent Gateway implementation or full D3B acceptance.

## Reused implementation, not a second lock system

`packages/claw-hermes/gateway_profile_lease.py` uses the pinned Hermes
`gateway.runtime_ownership.process_ownership` singleton. The actual lock and
release logic is upstream `ProfileOwnership` and `gateway.status`; neither was
modified, copied into the product tree, or reimplemented. Upstream source pin:
`eb75627faf532fa6ffbdae59a0d14b0b385fc780`.

The adapter requires an existing canonical private0700 profile, its existing
own single-link0600 gateway.lock, explicit HERMES_HOME, final ordinary Linux
UID/GID and main thread. Both state.db and runs_idempotency.db must already
satisfy the qualified mount observer. It neither provisions a missing profile
nor adopts somebody else's lock. Import paths/installation must already be
trusted; this callable is not a network capability or request parser.

Under the native mutex, acquire native reservation between two mount checks.
Recheck the lock's open descriptor, pathname inode, owner/group/mode and
non-inheritance. A partial pre-admission failure closes only the newly acquired
reservation, not a pre-existing or enlarged reservation set. Preserve native
live-writer retention. The adapter never invokes the native foreign-lock
recovery proactively, deletes a lock pathname, starts a listener, opens a DB,
changes a journal, mounts a volume, changes UID or dispatches a model.

`lease.finish()` is explicit: the fixed entrypoint must first drain ALL async
work, managed children and writers. Native registered threads are an additional
guard, NOT an inventory of every possible writer. If a registered thread is
alive the native close retains the lock and finish refuses. Never call the
native per-home release to defeat this guard. Once drained, close retains the
lock file inode while releasing ownership. Finish is process/thread-bound:
a forked child cannot explicitly unlock the parent's shared native lock.

Acquire only AFTER the final exec and ambient-descriptor cleanup. An earlier
bootstrap lock would be closed by those operations. The adapter exposes no
force, replacement, watchdog or supervisor restart path. Actual persistent
volume ownership, namespace isolation, recovery/epoch binding and admission
remain future fixed-entrypoint work. An ext4 name does not prove power-loss
durability. A cooperative file lock is not isolation from malicious code
running under the same UID/in the same process; no such guarantee is claimed.

## Review adjustment

Before native execution, review identified that a writable profile directory's
link count legitimately changes when subdirectories are created. Directory
identity now pins device/inode/mode/owner/group, not its changing link count.
Lock files still require exactly one link. Two new regressions cover normal
profile growth and this metadata distinction. No old implementation changed.

## Executed native proof

User-approved disposable `AlazHarness-D3B-P71C`, existing alazgateway UID23001 /
GID23003, ordinary fixed Python execution. No root command, account/service or
mount/namespace mutation. Temporary code/profile directories only.

26 actual native conditions passed, including:

- Real native singleton reservation and non-inheritable open lock descriptor.
- Four distinct rival interpreter invocations refused with `profile_already_owned`
  and exit77; no overwriting of the current owner's lock record.
- Same-process duplicate adapter reservation refused, original retained.
- Profile subdirectory creation allowed without weakening lock-file checks.
- A forked child refused finish; its exit did not release the parent's lock.
- A real registered writer thread kept the native reservation while finish
  refused; a second process remained excluded until the writer stopped.
- After normal drain/close, a fresh process acquired the SAME lock inode.
- Another real owner emitted readiness and deliberately exited73 via os._exit
  without native close/finalizers. It was reaped. A fresh process then acquired
  the same lock inode, proving OS release for that exited owner.
- Both dummy SQLite files retained exact content/device/inodes. No gateway.pid,
  replay-store execution, Gateway listener or provider request was created.
- All copied sources stayed unchanged; owned processes and temporary trees
  were absent in the final audit. User identity and mount table unchanged.

This is an actual native lock test, not a simulated fcntl/msvcrt call. The two
SQLite files use a dummy schema. They are NOT the Hermes state/replay stores,
no transaction recovery is claimed, and deliberate process exit is not an OS
crash or power-cut experiment.26 predicates overlap, not26 Gateway startups.

## Source and dependency provenance

The9 normally imported Hermes source files were compared byte-for-byte against
no-replacement immutable Git objects. The existing prepared Windows environment
supplied ruamel.yaml0.18.16;31 Python sources matched its installed RECORD hash.
Temporary Linux imports used these exact sources, not a stubbed gateway.status
or alternative lock helper. All actually imported source paths are recorded
and matched to the transport manifest, including native runtime_ownership and
status. No package was installed or updated and no vendor checkout was edited.
The full runtime dependency closure is NOT established by this small import
closure. Source copies were only transient inside the owned test code directory;
the committed repository retains hashes/provenance, not an upstream code dump.

## Test and transport distinctions

Windows focused23/23 PASS, Linux focused23/23 PASS. These use an explicit
native-owner double for lifecycle sequencing; they are not the native proof.
Three offline receipt checks verify actual terminal evidence and source pins;
these are part of the standard suite, not a new native run. Full Windows result
will be appended only after its terminal result; no old full run is reused.

Initial environment observations are retained:

1. Worktree/freeze creation succeeded, followed by a cp1254 stdout failure while
   printing a vendor header. Effects were verified; creation was not repeated.
2. System Windows Python could not import ruamel. The existing prepared Hermes
   interpreter then ran a native lock cycle and supplied verified dependency
   sources. No package installation or artificial replacement module was used.
3. First WSL invocation requested the account's default shell, which is nologin;
   it returned 'This account is currently not available.' before Python began.
   The subsequent invocation uses the SAME documented --exec /usr/bin/python3.12
   direct-program form used by N97K. No login shell was opened or enabled and no
   account/security setting changed. Original output and collector JSON parsing
   failure are preserved. The final native002 run is a distinct fresh execution.

The lab was stopped after its owned-process/file audit. Default Ubuntu was
observed running during a check and stopped at the final list; this task never
issued a start, terminate or configuration command for Ubuntu. Its transient
state is not attributed to this task. No global WSL shutdown occurred.

## Integration boundary and exact next step

The adapter currently has no call from the real Gateway entrypoint. It qualifies
the missing profile ownership lifecycle component only. It must be composed with
the existing final-UID startup, durable storage domain, native DB/epoch/recovery
validation and all-work-drained teardown before exposing actual admission.
Do not replace G84E's private tmpfs with a general host-writable directory simply
to make persistence appear to work. Broker live read-only authority and local
mock-provider sends remain separate untested integration requirements here.

R91F's blocked collector/provenance correction remains untouched and unresolved.
No failed result or receipt was rewritten, no test removed, no denied action
replayed or routed through another connector. Existing349 sources are frozen.
No production, model, push or main update. Legacy IPCv2 remains closed.

Evidence directory: `evidence/d3b-profile-lease-l99d/`.
Mechanism references (not acceptance evidence): Linux man-pages flock(2),
Python fcntl API and Microsoft WSL --exec command help. The executed local
proof, terminal subprocess states and source hashes control this scoped result.

## Final standard regression

Fresh full Windows execution2332 total =2327 PASS /5 SKIP /0 failures /0 errors,
exit0. Counts came directly from unittest result objects. All353 current
source/config/script/test hashes stayed unchanged;349 pre-existing source files
were not edited. Windows23 and receipt3 are subsets of the full suite; Linux23
are platform repeats. Native26 are overlapping actual observations, not26
independent Gateway starts. The full suite does not import/execute the blocked
R91F branch or turn that branch's historical failure into a pass.

The first shell invocation, missing system-Python dependency and initial stdout
encoding failure remain recorded. None was a product runtime failure relabeled
PASS. The direct native002 run and its terminal exit0 are separate evidence.
Local static is executed after full tests, not concurrently. Production/main,
prior failed drafts, vendor and default Ubuntu configuration are untouched.

Initial static checker failed JSONDecodeError because native001 shell stdout was plain text incorrectly named .json. The identical raw bytes now reside in native-001-stdout.txt; raw-output-extension-review.json records both paths and SHA256. No scanner rule, test or product source was changed. The first static-final.txt remains the failed output; static-after-format.txt is the separate terminal rerun.
