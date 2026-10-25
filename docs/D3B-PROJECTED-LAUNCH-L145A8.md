# L145A8 — Fixed retained projection launcher and guarded receiver

## Accepted implementation scope

Two additive product files connect the existing retained projection and codec to
a fixed interpreter target. No old runtime, native source, source manifest or
source-lock file changes. gateway_retained_launch.launch calls actual
state.enter in retained mode, then encode_projected, live observation and a fixed
os.execve. The final script decodes at the fixed target, validates live inherited
state and invokes the ORIGINAL profile lease and NativeStoreStartup.

The shipped target is intentionally readiness-only: open the existing three
stores under their original checks, close them, then release the caller lease.
It does NOT start finite work, a model, listener or agent admission. The previous
normal-user finite/exec proofs remain valid but do not qualify this new kernel
path. No current positive kernel-isolated startup/workload was executed here.

## Launch and receiver boundaries

The trusted supervisor must already be the authorized dedicated child in the
existing volume namespace/cgroup. This helper performs no elevation, provisioning,
namespace join or new supervisor. It does not expose a generic CLI or arbitrary
workload callback. The original state.enter still owns root/controller/volume
validation, read-only source exports, bind/pivot, identity drop, seccomp and
Landlock. A failure anywhere is fatal to that dedicated child; no unconfined
fallback or automatic retry is provided.

Launch prechecks the existing typed three-part expectation, new instance ID,
exact supervised VolumeBinding, exported private scratch path and read-only
Python/installation/target paths. Only a direct complete state.enter result goes
to the original fixed-target codec. Actual live UID/GID/groups/thread/capabilities,
NNP, namespace identities and seccomp status are checked, then the fixed target
mount is captured. argv is always /usr/bin/python3.12 -I -B followed by this
installation's scripts/run_retained_projected.py; payload cannot choose it.

The new interpreter receives only PATH, LANG, HOME, HERMES_HOME, temporary path
variables and two bounded data fields. The entire parent environment is not
inherited. The retained codec is unchanged. Context is canonical bounded JSON
binding the wire digest, PID, principal, namespaces, exact mount and instance ID.
The receiver requires fixed Python, isolated/no-bytecode mode, exact environment
keys/values, fixedTARGET, strict context shapes, generation and identity agreement.
Live kernel fields and mount are then reobserved before any profile lease or SQL.

Both transfer and context are TRUSTED CALLER DATA, not signed authorization or
independent kernel attestation. Matching claimed namespaces in untrusted JSON
cannot authenticate a caller. Seccomp status does not prove the exact loaded
filter; the inherited original projection chain is essential. Landlock is NOT
queried as an attestation by the receiver. No hostile same-process Python, hostile
host root or externally persisted receipt authenticity is claimed.

The receiver hands existing typed state/response/retained expectations to the
original NativeStoreStartup with retained prepared layout. It does not replace
its live mount/lease/schema/previous-epoch/constructor checks. Startup or close
failure leaves the ownership protocol to the dedicated process failure; there
is no finally that clears registries, rolls back unknown effects, releases an
unconfirmed lease or retries. Readiness result sets work/service/full acceptance
flags false. Old launchers and defaults are untouched; this is opt-in integration.

## Reproduced lifetime defect and correction

Initial own35 tests:34PASS/1ERROR. The target attempted to read owner.expectation
AFTER normal close; the original owner permits that property only while VERIFIED.
The correction snapshots its epoch before close and lease release. Same original
35test bytes now pass; failed raw log/source retained. Four added tests use the
ORIGINAL NativeStoreStartup implementation and three real in-memory SQLite
connections, with native constructors/cold/mount dependencies explicitly doubled.
They verify actual reverse close order before caller release, and no forced close
or release after cold/epoch/close uncertainty.

Independent C142 first corrected two mistakes in its own fixture (IPC input fields
and accidentally retaining a constructor Mock instead of the actual class); those
records are not called product defects. Its final29-byte-identical driver then
reproduced the ORIGINAL expectation descriptor/_owned error on candidate001,
28PASS/1ERROR, and passed29/29 on candidate002 without changed expectations. Raw
source, before/after logs, exact driver and provenance are retained. Peer data
was copied, not rerun or rewritten. No competing alternative launcher is shipped.

## Actual Linux refusal evidence

Five fresh ordinary-user Linux Python3.12 -I -B interpreters ran the exact fixed
final entrypoint. A runpy wrapper was used explicitly only to install observation
profile/audit hooks before source imports; product/kernel functions were NOT
replaced. Cases: missing wire, malformed wire, extra environment, foreign PID,
and otherwise well-shaped transfer in an actually unconfined process.

All five target executions refused with exit2; each validating test process and
the outer transport exited0. No profile was created; no reserve_profile, native
startup, SQLite connection, subprocess launch or network action occurred. Actual
UID23001/GID23003, supplementary group23003 and NNP0 were observed. The unconfined
case reached original _live and failed; earlier malformed cases did not. Actual
mount tables and namespaces remained unchanged. Audit would have refused a profile
or SQL operation, but none was attempted: no audit-denial was relabelled a normal
product refusal. The transport's own temporary source directory was removed.

Only fixed source bytes were transferred, with strict archive path/size/hash
checks and current loaded-module hashes. No dependencies installed, personal
profile examined, root command, namespace/mount setup or previously denied root
bootstrap/cleanup retried. This proves actual receiver NEGATIVE behavior only,
not successful confinement, startup in isolation, execve inside isolation, or
kernel canary coverage. Previous ordinary-user positive exec is a different scope.

## Regression and custody

Own39control tests +6offline receipts form45 focused methods. Independent29 tests
overlap with them and are not added as74unique runtime cases. The five Linux
refusal processes are actual separate executions, not39mock kernel experiments.
Existing625source/config/test files and11native patches are unchanged. Six new
source files include two product files, two fixed negative-QA scripts and two
standard test modules. One full standard regression is recorded separately with
source before/after hashes, all raw logs and unchanged23skip IDs/reasons.

Root33user dirty files, installed nativeeb75627, optional d151 and main d304a57
are protected. Product code alone does not grant current kernel acceptance.

## Remaining gate

The existing trusted supervisor must invoke this exact opt-in launch path in an
authorized dedicated volume child, with a complete current-source installation
and appropriate original read-only/writable exports. The new source has not been
installed in the privileged lab; old F126 prepared-only source cannot stand in.
Previous denied operations must not be replayed or routed through another tool.

First qualify real projected readiness/open/close using this exact fixed target;
then admit actual native finite normal/error/replay/new work and verify result/
physical-worker/ordered close under isolation. Confirm host path/socket/ambient-FD/
namespace reentry canaries and all source/dependency hashes. HTTP/authentication,
crash/power-loss, real model/tool/memory-manager/budgets remain separate gates.
This package is additive code plus contract/negative evidence, not deployment.

## Complete standard regression

Fresh full3611:3588PASS23SKIP0ERROR0FAIL, actual command022 terminalexit0.
631source/config/test files and11patches are identical before/after/current.
All625baseline source files remain unchanged. Six new files are the product
helper/entrypoint, two fixed negativeLinuxQA scripts and two test modules.
Same23skip IDs/reasons. Own45focused and independent29 overlap; no positive
kernel/native acceptance is inferred. Failed initial lifetime test and exact
before/after independent29 are retained with source hashes and provenance.
