# R122Q6 - independent real caller-owned GatewayRunner qualification

R122C4 owns the ONE optional native implementation. This branch contributes
independent native before/after tests and immutable source custody, not a parallel
runner or modified native methods. All496 existing harness sources are unchanged.
The native test copy starts from2bc50496 and uses the exact reviewed seven-file
candidate; the installed vendor and source locks remain unchanged.

## Default control and the ownership seam

A genuine unpatched GatewayRunner constructor in a fresh profile opens one
registry-owned SQLite connection even when a caller owns a separate state handle.
Its native SessionStore and search wrapper correctly share that default handle.
Ordinary initialize_session_authority then advances the caller-visible epoch1->2.
This is normal standalone startup, not called an upstream bug. Default resources
were closed without closing the independent caller state prematurely; registry
refcounts returned to zero, ownership and temporary profile were released.

The optional path constructs the REAL GatewayRunner using explicit immutable
caller expectation/state/config. Real native SessionStore and AsyncSessionDB
select that already-open caller SessionDB. Native configuration, constructor and
SessionAuthority class are not replaced by test doubles. The new preparation
path reuses the accepted epoch/instance without bump, recovery, admission,
new SQLite connection, registry acquisition or caller ownership takeover.

Prepared authority is deliberately retiring, runner is draining/not running,
descriptor has no capabilities or served profiles. Ordinary service start/stop,
API startup and the old epoch-advancing authority initialization reject before
effects. This is PREPARED construction, NOT a working agent service or listener.
The three-store API borrowed_runner_conflict remains unchanged.

## Real ownership bug found beyond initial green tests

The first independent24 native methods passed, as did original24. Six extra
independent prepared-owner methods revealed15 failed assertions: changing the
Python authority epoch/instance/home/runner, its retiring/retired flags, descriptor
identity or values, adding a foreign registry slot or changing running/draining
flags was not rejected by the initial selector. SQLite epoch equality alone was
insufficient. The original narrower4-case probe independently reproduced3 fails.

Correction is in the existing native borrowed helper, not a second owner layer.
The exact prepared authority, single-profile registry, descriptor identity and
values, and inactive/draining flags are checked on selection and before detach.
The final metadata update after facade detach cannot silently be retried when
its outcome is unknown. Other six native candidate files stay identical. The
SAME independent test-driver bytes now pass all30 methods without weakening any
assertion. Original failing receipts and all initial source bytes are retained.

Raw pre-fix report counted15 failing subtest identities as15 failed tests. The
separate drift-before-accounting.json correctly states30 methods:24 passing and
6 failing parent methods with15 assertions. The raw record is not rewritten.
Current all-pass count30 has no such ambiguity.

## Independent acceptance actually executed

Current native00230/30 PASS on Windows includes original24 plus six owner-drift
methods. Tests use fresh native SQLite/ProfileOwnership and a real event loop.
Cases cover exact handle/epoch, repeat one-shot/config refusal, preserved queued
work and terminal history, existing worker rows, closed handles, profile switch/
reacquisition, native lock contention and open transactions, wrapper mutation,
normal detach, live background-task retention and pending result retention.

A background asyncio Task in a negative fixture is explicitly test-owned; it is
not a real running agent claim. The observer/constructor does not cancel it. The
fixture completes/removes it before cleanup. Similarly explicit data/field faults
are restored ONLY by tests, not production recovery. No synthetic admission is
used to make the borrowed runner appear active. Public admission stays closed.

Construction/selection/preparation/detach are watched for zero new SQLite/raw
state opens and zero row changes; SQL traces are SELECT/PRAGMA. This is not a
zero-filesystem-I/O claim for config loads or ordinary native mutation code.
All30 temporary case profiles were removed, profile ownership released, and
native registry generations/refcounts returned to zero.461 actually imported
native sources match immutable base2bc50496 or the seven explicit candidate
hashes. Seven offline receipt checks bind those results and current QA bytes;
they are not seven new native executions.

The full combined harness suite is pending original implementation/artifact plus
this QA integration; the previous3162 standard count and focused/native successes
are not relabelled as a new full run. Native upstream full suite is NOT RUN.
The old23 platform/opt-in standard skips are not implicitly executed here.

## Honest environmental and runtime scope

The event loop is created before the audit guard solely for its framework wakeup
socket, not an HTTP listener. Native version-diagnostic git subprocess probes and
an optional urllib3 IPv6 bind were attempted and DENIED by the audit hook; these
must not be described as zero attempted external actions. No effective provider,
model, public listener, WSL/root/mount, package install or runtime upgrade occurred.
Existing SQLite DELETE-mode fallback warning remains in stderr.

The real runner constructor is tested, but full agent/model/tool execution,
shared replay/response API lifetime, full Linux isolation, active-work HTTP and
all-work drain remain unaccepted. These cooperative in-process references are
not a capability against malicious same-process mutation or a cross-store atomic
ownership guarantee. Caller must coordinate all other users before releasing
state. Existing blocked cleanup/physical probe attempts remain blocked/not rerun.
C120P9 stays HOLD. Main/push/CIqueue/production/user data are unchanged.

Next: preserve the original immutable patch/history, run one exact combined
standard suite, then deliver the staged feature without activating it. Subsequent
integration must join the existing three-store caller and API lifetime contract,
not delete borrowed_runner_conflict or fabricate private state after construction.
