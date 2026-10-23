# J121S1 - optional SessionStore caller ownership, unified acceptance

One native implementation S121R4 plus independent S121S1 acceptance. Original
harness/native histories and raw evidence remain intact. Native feature2bc50496
extends94321058 in only three files. Config/hermes-session-borrow-s121r4.json
selects a STAGED, NOT INSTALLED patch. Installed vendor and source locks stay
unchanged; the complete shared canonical GatewayRunner bootstrap is not claimed.

## Explicit borrowed constructor, default unchanged

SessionStore(..., session_db=state) validates a caller-owned live native SessionDB
before the normal eager constructor reaches any registry acquisition. Same home,
native file/handle/application generation, actual process profile ownership and
explicit single-home/SQLite-only configuration are required. It selects the same
handle for the active/default routing access; foreign scopes/keys/paths cannot
silently become another home or cause a new connection. Repinning is refused.

The existing default constructor still acquires its ordinary registry-owned
connection, preserving multiplexed behavior. An independent unpatched control
shows one additional SQLite open and a different handle if a caller state exists.
This is intentional default behavior, not described as an upstream bug. New
borrowed construction/selection/detach observes zero extra SQLite connections,
registry acquisitions, raw DB opens or row changes in the watched boundary.

Borrowed facade detachment does not close caller state or release its profile.
A held native mutex, open transaction, dirty transcript or in-flight facade entry
refuses detachment without waiting, discarding work or automatic rollback. Closed
or changed state/profile ownership is not repaired/reopened. The caller remains
responsible for coordinating other users of the shared connection and full drain;
a cooperative per-call check is not global exclusive use or an atomic shutdown.

Explicit borrowed mode refuses legacy JSON routing import or fallback. Real
primary routing/metadata/admission uses caller state in the original native test
suite. A separate query-only SQLite write failure confirms no sessions.json
fallback is created. Existing native mutation code may read its file header;
that mutation-failure test explicitly permits/reports that read. It does NOT
support a blanket zero-filesystem-I/O claim for all SessionStore operations.

## Real tests, source identity and preserved first outcomes

S121R4 native00223/23 and independent S121S1 native00224/24 PASS on actual native
classes in fresh Windows temporary profiles. The suites overlap and are not47
distinct scenarios. One checks real primary routing and canonical admission;
the other independently checks scope, configuration, connection, locks, dirty
state, generation, schema failure, JSON refusal, cross-thread selection and
caller-preserving close. No native class/method substitution. Profile ownership
and registry counts return to zero; temporary profiles are removed.

Three modified source hashes match both runs and native feature2bc50496 exactly.
Unmodified actual native imports are separately checked against immutable943Git
(261 in original run;250 in independent run). Fresh patch application reproduces
the exact tested bytes and duplicate application is refused. No gitlink/source
lock is silently promoted. Four previous patches plus this fifth patch are frozen
with the combined source set.

Both initial fixture runs retained failures caused by assuming sessions/ was
absent. A separate positive control proves native imports prepare that directory
before caller state/facade construction. Corrected tests compare before/after
inventory; product bytes did not change. The independent first outcome21/24
(2FAIL/1ERROR) and original21/23 remain recorded as failures. Native journal
fallback warnings remain in logs; no dependency or interpreter upgrade happened.

Fourteen offline receipt tests (7+7) are standard-suite subsets, not native runs.
The new complete combined standard regression is recorded in this joint evidence
directory; previous C120A or focused/native successes cannot substitute for it.
Existing23 platform/opt-in skips stay skips, and no complete native upstream
pytest suite, Linux mount/network isolation or HTTP listener test is claimed.

## Exact remaining boundary

This is the missing SessionStore constructor ownership seam, NOT the full runner
bootstrap. Native API borrowed_runner_conflict is byte-for-byte unchanged. Do
not set private state after construction or remove that guard to simulate a
shared bootstrap. Next needs an explicit compatible canonical runner/authority
construction and all-three caller-owned lifetime; then same-path profile/mount/
active-work readiness and isolation qualification before any API activation.

Current native adapter/listener, broker live-ledger/dummy-provider accounting,
fullD3B/cross-store recovery/power-loss safety are still unaccepted. Existing
healthy/busy observation and quiescent diagnostics stay unchanged. C120P9 extra
frame probe remains HOLD. Earlier tool blocks remain blocked, not rerun via any
route. No root/WSL/model/provider/main/push/CIqueue/production/account action.

The final summary/delivery records terminal full/static results and the exact
canonical continuation. This union adds only staged artifact/config/QA to the
harness; all490 original harness sources are unchanged.

## Terminal new combined regression

Fresh fullWindows3162=3139PASS/23SKIP/0ERROR/0FAIL, exit0.496 source/config/test
hashes and5 patch hashes stable; all490 original harness sources unchanged.
50 parent evidence Git blobs retained.14 offline receipts are standard subsets,
not additional native runs. Original23 and independent24 native methods share
the exact same three native product hashes and remain separate overlapping
acceptance scopes. No installed feature, shared runner, active HTTP or source
lock activation. Local static-final.txt is a local gate, not remote CI.
