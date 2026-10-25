# T143A7 - Typed retained-startup transfer and real interpreter replacement

## Accepted scope

A new bounded codec transfers the existing three startup expectation types across
a trusted exec boundary. Two actual ordinary-user Linux experiments complete a
native finite API job, close the original owner, replace Python with os.execve,
reopen the same profile, replay the saved request without computation, run one new
request and close normally. The normal and controlled-computation-error cases use
identical source and archive; only the declared failure flag differs.

This is an orderly exec of a fresh interpreter with the SAME OS PID and starttime.
It is stronger than the previous two owners in one Python interpreter, but it is
NOT crash/power-loss/new-PID recovery or current kernel confinement acceptance.
The generic codec takes an independently trusted expected_home. The fixed-target
projection wrappers are separately contract-tested, not invoked as a fabricated
kernel success inside this ordinary-user experiment.

## Minimal product addition

Only new packages/claw-hermes/gateway_retained_handoff.py is product code. No old
runtime file, native source, source manifest, startup policy, schedule or store
owner changes. It serializes PreparedStoreExpectation, PreparedResponseExpectation
and RetainedProfileExpectation and reconstructs those exact existing types using
the original validators. No native agent import, file/database operation, eval,
pickle, process launch, key generation or runtime permission is introduced.

The wire protocol is versioned, canonical UTF-8 JSON, at most16KiB. Unknown or
missing fields, duplicate keys at every level, noninteger numbers, bool-as-int,
overflow, malformed/deep/truncated JSON, ambiguous noncanonical representation,
wrong source/schema pin and unexpected identity shape are rejected. Receipt home
must equal the separately supplied canonical home; callers must NEVER learn this
trust input from candidate JSON. DELETE-mode, prior epoch/instance and exact three
distinct database identities on the same device must agree. Bounds and validators
are repeated even for frozen dataclasses.

encode_projected consumes only the trusted direct successful projection result
for the fixed /run/alaz-state/profile. It checks currentPID/version, preserved host
user namespace, one state directory, no ambient host exports, required completed
flags and matching profile identities. decode_projected never accepts another
home. These are consistency checks, NOT a signature/authentication or attestation
that a dictionary's claimed kernel stages really occurred. A remote/untrusted
caller cannot be granted authority merely because its JSON validates.

Original NativeStoreStartup remains responsible for the actual mount/profile
lease, cold SQL/schema checks, existing store identities, prior generation and
new runtime epoch. No general launcher or side-channel execution is exposed.

## Real Linux experiment

Fixed inspected driver t143a7_linux_exec.py derives the existing accepted R140
native experiment, not a substitute scheduler. Existing P71C alazgateway runs as
UID23001/GID23003 with Python3.12. The transport checks the unchanged1162 dependency
file hashes, safely extracts a hash-pinned archive, then runs the one fixed child
with a bounded timeout. No installer/root/mount/namespace/service action.

First owner opens the actual three stores under the native lease and real cold
helpers, accepts epoch1 and computes17+25+8 ->50 (or the controlled model error).
The actual SessionAuthority/finite runner/physical thread and native
commit_and_publish/settle_session_input produce the persistent result. The fixture
does NOT write terminal admission rows. Exact retry does not compute again, and
conflicting input under the same ID is refused. Resources and sessions retire,
the consumer detaches, all three connections close, a retained receipt is captured
while the caller still holds the lease, then the caller releases it.

Before exec the event loop/default executor closes, native registries are empty
and no tasks remain. The original result, trace/imports, PID/startticks, trusted
mount observation, helper hashes and transport digest are recorded. A controlled
caller-owned environment carries the bounded codec data; the profile path is
separately specified by fixed launch arguments. No shell or arbitrary entrypoint.
The original audit records the exact os.exec event.

os.execve replaces the interpreter, preserving PID/starttime. The fresh interpreter
has no previous model objects, tasks or registry references. It validates the
wire, repeats actual mount/lease/cold/schema checks and opens the same three DB
inodes at epoch2. Generated helper files stay in place and unchanged at startup.
The original request returns exactly the prior result AND usage with computation
count0 in this interpreter. A fresh request runs once, at epoch2/generation2, with
the prior admission/result unchanged. Conflicting reused ID is still refused.
Normal native shutdown again closes three handles, registry0 is observed before
fixture cleanup, a second receipt is captured and the caller releases its lease.

Both cases exited0. All native/OS calls are real except the explicitly bounded
AIAgent factory/computation/close fixture. Cold helpers execute in real separate
interpreters twice per owner. Exactly three parent SQLite opens after exec occur
at startup and none during its turn. Actual function/stack evidence identifies
native settlement and non-main-thread computation. Temporary profile/transport
are removed after successful ownership release, never before reopen to make a
layout check pass. Failure-fixture cleanup was not used for the accepted cases.

## Independent findings and evidence

Initial codec candidate passed24 own tests; independent H14321 tests exposed five
missing projected-result consistency checks. Foreign PID, unsupported version,
ambient exports, changed user namespace and wrong state-directory count were not
all refused. This was a trusted-input validation gap, not a demonstrated escape.
Candidate002 adds those checks. EXACT SAME independent test bytes changed outcome
from16PASS/5FAIL to21PASS/0FAIL. Raw failed source/log/results and fixed equivalents
are retained with hashes. No old failing expectation was weakened.

H143's separately explored alternative codec was archived, not combined into the
product. Final T143 product/H143 independent roles are fixed, and no peer tree was
edited. Own24codec tests plus8offline receipt checks are standard-suite subsets;
independent21 overlap semantically and must not be totalled as unique native runs.
Copying independent evidence with provenance is not a second execution.

Normal imported native source counts before/after exec:721/722; error718/719.
Union722 files match immutable native d151 Git bytes and fit the current756-source
manifest. All transported harness files match current source. No native patch or
source manifest is promoted or rewritten. The same codec hash binds unit tests,
independent tests and both actual Linux experiments.

## Regression and remaining gate

The one full standard suite has its own terminal report; focused/native success
is not used to infer it. All620prior source/config/test bytes remain unchanged;
five new files add the codec, two fixed QA scripts and two test modules. All11
native patches remain unchanged. Main and installed Hermes are not changed by
an experiment or static check. Existing33user dirty files must stay byte-exact.

Next, the current supervised launcher must explicitly carry this typed transfer
between its completed retained projection and the post-exec original owner, then
run the current756-source native flow under actual namespace/seccomp/Landlock with
host-file/socket/ambient-FD/reentry canaries. Historic F126 root launcher remains
unchanged and old prepared-only evidence is NOT current finite-work acceptance.
Previous tool-denied root/bootstrap/cleanup operations are not retried here.

Authenticated HTTP, externally persisted/authenticated receipt trust, forced
termination/power-loss recovery, actual model/tool/memory-manager and cost budgets
remain separate gates. Clean exec here cannot establish those properties.

## Completed full regression verified on continuation

Full001 completed3566total/3543PASS/23SKIP/0ERROR/0FAIL with recorded exit0.
The exact raw log, before/after625source hashes and11patch hashes were checked
against the current checkout. All620old sources remain unchanged and skip IDs/
reasons are identical. This continuation did not replay the completed suite or
normal/error Linux jobs. R144 resumes only the existing T143 publication workflow.
