# R122C4 - real caller-owned GatewayRunner construction and prepared authority

This optional native change extends the existing GatewayRunner constructor. It
is not a replacement runner, fake facade, scheduler, task registry or API gate.
The default constructor remains on its original path. The caller provides an
explicit native SessionDB, fixed config and ALREADY ACCEPTED epoch/instance.
The actual constructor initializes its original config, settings, lifecycle,
caches, SessionStore, async facade and ancillary native objects without opening
another SQLite state connection or running caller-owned DB maintenance.

## Ownership boundary

CallerOwnedRunnerState is a local one-shot reference, not serialized capability.
It selects the prior S121 native SessionStore borrowed constructor BEFORE eager
registry priming. The actual AsyncSessionDB wraps that same state. It refuses
unknown/nonterminal work before construction/preparation, wrong epoch/instance,
wrong profile/file/handle/config, mutex contention, transactions and owner loss.
It neither advances runtime_epoch nor recovers/backfills/settles existing rows.
A consumed constructor reference cannot silently bootstrap a second runner.

initialize_gateway_runtime recognizes the explicit contract and constructs the
real native SessionAuthority and SessionAuthorities with the same epoch/state.
The authority stays RETIRING and the runner DRAINING; descriptor capabilities
and served profiles remain empty. Its real admission gate refuses runtime_draining.
No tickets, cron binding, local recovery or new worker is installed. These missing
service steps are deliberate NOT ACCEPTED boundaries, not faked successes.

The original regular runner startup/stop/internal teardown and old authority
initializer are refused BEFORE side effects for this mode. Normal shutdown
would otherwise call db.close directly and normal authority init would bump the
epoch/recover records. The caller-owned option does neither. Default callers
without this option retain the original behavior. Native API borrowed_runner_conflict
is byte-identical and has NOT been removed or bypassed.

Explicit close_all_session_db_handles in this mode only detaches its own facade.
It requires exact owner/descriptor/registry, no active native executor/tasks or
pending native state. It does not cancel tasks, join workers, prune maps or discard
dirty data to force a clean result. Caller connection/profile remain usable/owned.
A post-facade partial failure is DETACH_UNKNOWN and cannot be silently retried;
that defensive branch is not claimed as separately fault-injected by this suite.

## Prepared identity regression found and fixed

Initial24 native cases passed, but four extra actual-native checks found three
failures: changed authority epoch, replaced descriptor and an extra registry slot
were not rejected at selection/detachment. Original failed receipts and exact
source bytes are retained. The new helper alone was tightened; the six native
integration files were unchanged. Selection/detach now recheck the real authority
object/runner/profile/instance/epoch, single original registry and original descriptor
with non-running/draining/retiring flags. This remains cooperative same-process
consistency, not an attestation against hostile code with arbitrary object access.

The final complete native28-method run includes the four regression checks and
passes. Independent R122Q6 broadened the class to six prepared-identity methods
with multiple assertions; its initial failed30-case run and corrected30/30 current
run remain separate evidence. They execute the exact same final seven product
hashes; overlapping28/30 packages are not58 independent scenarios.

## What ran and what did not

The actual full GatewayRunner constructor and actual SessionAuthority were used,
not object.__new__ or replacement native methods. Current28 cases use genuine
SQLite, native profile ownership, registry, locks and Windows threads. All watched
boundaries retain zero new SQLite connections, unchanged total_changes/epoch
and registry count. Existing default construction was also positively checked.
All28 temp profiles were removed, profile ownership released, registry counts
zero, and no pending asyncio tasks remained.467 actual native imports matched
immutable base2bc50496 or the exact seven-file change. Current source commit is
recorded in config/hermes-runner-borrow-r122c4.json; fresh patch apply produces
those exact bytes, a second apply is refused. Installed vendor/source locks stay
unchanged. This patch is STAGED, NOT INSTALLED.

The first smoke's native constructor succeeded but its subsequent Windows event
loop creation hit the test's own socketpair ban. That FAIL is retained. Later
framework loop initialization precedes native instrumentation. During audited
native imports, seven optional version-info Git subprocess probes and one urllib3
IPv6 bind were DENIED; no native-test-phase external event was observed. Those
attempts are explicitly recorded, not hidden as zero attempts. Config loading
is real but constrained by that offline test environment. No model/provider or
service listener was started. Native journal fallback warning stays unchanged;
no interpreter/package upgrade or official native full pytest suite occurred.

Seven offline source/result/patch custody tests belong to the harness standard
suite; they do not rerun the native constructor. A new combined full harness
regression is required after original and independent histories are merged.
The earlier full3162/3139 is not current acceptance of these added artifacts.

## Next boundary remains explicit

This closes the real runner CONSTRUCTION + existing-epoch authority-preparation
seam, not the all-three-store active service. Work still requires one combined
caller-owned state/replay/response lifetime, appropriate local epoch mappings,
profile/mount validation, task observers qualified for the updated native source,
and an explicit compatible borrowed-API attachment contract. Only after same-path
lifecycle/isolation proof may HTTP readiness or admission open. Never remove the
existing guard or privately rewire objects after an eager constructor to fake it.

No root/WSL/mount/production/accounts/CIqueue/main/push/model action. Earlier
blocked root/physical-probe/refinement operations remain blocked and not replayed.
C120P9 extra physical stack probe remains HOLD. Full D3B, broker live accounting,
cross-store recovery/atomicity and power-loss safety remain open.
