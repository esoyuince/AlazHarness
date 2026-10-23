# J122C4 - caller-owned real runner construction, exact prepared authority

One optional native implementation from R122C4 and independent R122Q6 acceptance,
with both original histories retained. Seven native source files extend staged
feature2bc50496; new native feature6b8124ab remains STAGED / NOT INSTALLED.
The actual GatewayRunner constructor now accepts a local one-shot caller-state
contract and reuses its real native SessionStore/AsyncSessionDB/SessionAuthority.
No duplicate runner facade, scheduler, connection registry or work engine.

## Qualified constructor and preparation boundary

The caller supplies an already-open, profile-owned native SessionDB and an
already-accepted exact epoch/instance. Construction does not begin another epoch,
recover/backfill pending rows, run caller DB maintenance or open another state
connection. The default path stays on its original behavior. Real SessionStore
borrowing is selected before eager acquisition, not by private replacement later.
The same state backs both native sync and async facades and the native authority.

Authority preparation is intentionally NOT service activation. Native authority
is retiring, runner draining, capabilities/served profiles empty. Its actual
admission gate refuses. No tickets, cron ownership or recovery are published.
Ordinary start/stop/direct teardown and old authority initialization refuse before
side effects, rather than invoking a shutdown path that closes caller state or
an initializer that advances the epoch. Existing borrowed_runner_conflict stays
byte-identical. No endpoint can opt itself in with request data.

Explicit facade detach keeps caller DB and profile ownership intact. Active DB
transactions/mutexes, native background work/executor, pending authority results,
dirty transcripts or unknown state refuse rather than cancel, rollback or discard.
Exact bound prepared authority, original single registry and descriptor/flags are
rechecked before selecting state or detaching. A post-detach partial failure is
kept unknown instead of silently retryable; dedicated fault injection of that
rare post-effect branch was not part of the native suite.

## Regression before final acceptance

Initial native24 passed. Additional actual-native checks found that prepared
owner drift was insufficiently checked: authority epoch, replaced descriptor
and a foreign registry slot could be accepted. This is a flaw in the unshipped
candidate, not a claim about upstream default behavior. Its failing4-case result
(1PASS/3FAIL) and exact original source remain immutable evidence.

Independent tests broadened that defect to six parent methods with15 failed
assertions over a30-method suite. The original raw summary incorrectly counted
subtest IDs as parent cases; corrected accounting is explicitly separate, leaving
raw data intact. The native helper was corrected, not its negative assertions.
Current original28/28 and SAME independent30/30 methods pass on exact same seven
source hashes. Six integration files were unchanged by the helper correction.

## Actual native evidence and controlled environment

Both packages call the full real native constructor and real authority class,
with no replacement native methods. Genuine Windows SQLite, process/profile
ownership, mutexes, threads and event loop are used in fresh temporary profiles.
Observed construction/preparation/selection/detach leave row counts, accepted
epoch and registry unchanged and open no extra SQLite connection. Independent
original control confirms default runner still opens its registry state and
normal default authority initialization advances the epoch; intended behavior.

28 and30 are overlapping packages, not58 unique scenarios. Their watched cases
are not proof of arbitrary unobserved code paths. This is not complete AIAgent,
active worker execution, all-three-store API, HTTP readiness, mount validation,
full Linux isolation, official upstream full pytest or power-loss qualification.
Native imports match immutable base2bc Git plus exact modified sources (467 in
original,461 independent). Final profile directories, native ownership, registry
counts and pending tasks are clean in the respective evidence.

The first smoke failed on Windows asyncio framework socketpair setup after the
native constructor; its test audit was installed too early. That failure remains.
Later event-loop setup is done before auditing native imports/calls. Seven optional
Git/version subprocess probes and one urllib3 IPv6 bind were denied during imports
in original final suite, with caller frames recorded. Do not describe that as zero
attempts. No actual native-test-phase provider/model/listener operation occurred.
Native SQLite DELETE fallback warning remains; no package/interpreter upgrade.

## Source-preserving artifact delivery

Native commit6b8124ab is a six-file integration plus one helper. Fresh exported
base patch application reproduces all seven test hashes; duplicate apply refuses.
Config explicitly marks STAGED_NOT_INSTALLED. Installed vendor/source lock and
main are unchanged. The first commit command lacked configured native author;
HEAD/index were checked unchanged and only the existing harness identity was
supplied command-locally, with no global or repository config change.

Original evidence trees, early successful/failed suites and source snapshots are
preserved by immutable merge. Fourteen offline receipt tests (7+7) are standard
suite subsets, not14 native runs. One fresh complete combined standard regression
runs on505 source/config/test files and6patches; all496 old harness files stay
unchanged. Exact terminal full/static numbers are in summary.json when completed,
not inferred from prior full3162 or two native packages. Existing platform/opt-in
skips stay skips. The union command's first compile error occurred before any
test/effect and is retained; no product change or hidden test retry resulted.

## Exact next gate

Bind this prepared native runner to the SAME three-store owner and accepted
profile/mount lifetime. Define compatible borrowed API attachment and necessary
native local-epoch mappings, preserving the guard until the contract is proved.
Requalify task observations against the new source and actual admission/settlement
path, then same-path isolated active-work HTTP before service activation. The
current prepared descriptor is not health/admission permission, and a saved async
wrapper is not an independently revocable capability against hostile local code.

No WSL/root/mount/provider/model/production/account/CIqueue/main/push action.
Earlier blocked cleanup/refinement/physical-probe work remains blocked, not
rerouted. C120P9 optional frame probe stays HOLD. Full D3B, broker live accounting,
cross-store atomic recovery and power-loss safety remain OPEN.

## Terminal combined regression

NEW complete Windows3176=3153PASS/23SKIP/0ERROR/0FAIL, exit0.505 source/config/test
hashes and6patch hashes stable; all496 baseline sources unchanged.82 original
parent evidence Git blobs retained.14 offline receipts are standard subsets,
not native reruns. Original28 and independent30 actual-native packages match
same7product hashes and remain overlapping scopes. Native patch remains staged,
not installed; service/admission/API/isolation acceptance remains open.
Local static-final.txt follows and is not a remote CI or production result.
