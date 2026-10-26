# R155A1 - Original retained seed and supervised readiness

## Result

The actual `same-image001` acceptance completed with exit 0. The original
installed native lifecycle produced a task-free retained profile on the new
supervised image, closed its three owned databases, captured the retained
handoff while the profile lease was still held, and released that profile lease
normally. Original projected readiness then reopened that same profile under
the same live supervisor, advanced epoch 1 to epoch 2, passed all six checks and
closed. Original stop/finish completed the ordered image shutdown, with the
image lease released last. This closes the P1 same-image seed, projected
readiness and ordered-close subgate.
([Same-image acceptance](../evidence/m1-seed-readiness-r155a1/same-image001/result.json))

The prerequisite ordinary-user `ordinary007` proof also completed with exit 0
using the exact reviewed producer. Both native seed receipts record zero tasks,
model calls and listeners, with API admission unpublished. The same-image
broker was a metadata socket fixture; no real broker exchange or service
admission was accepted.
([Ordinary proof](../evidence/m1-seed-readiness-r155a1/ordinary007/result.json),
[same-image proof](../evidence/m1-seed-readiness-r155a1/same-image001/result.json))

| Gate | Recorded status |
|---|---|
| Current installed source/dependencies | PASS in the original installed verifier; receipt unchanged |
| Ordinary task-free native retained seed | PASS, ordinary007, producer and carrier exit 0 |
| Primary Windows focused tests | PASS, 113 executed passes and 7 platform skips |
| Same-image seed, projected readiness and ordered close | PASS, same-image001, epoch 1 to 2, original normal stop/finish |
| Finite normal/error work and replay/new-work through the complete path | NOT ACCEPTED |
| Full D3B, M1 and production | NOT ACCEPTED |
| Protected root/native/main state before publication | PASS; root's 33 existing file contents and all baseline repository states preserved |
| Repository static gate | PASS, 6464 files, 2 gitlinks; 3865 tests discovered, not executed |
| Exact final commit CI and main publication | Separate publication gate; authoritative post-commit observations recorded in the publication journal |

P1 remains IN PROGRESS because finite normal/error work and replay versus new
work through the complete path remain open. The ordinary proof ran on the
laboratory root filesystem. The accepted same-image invocation produced its
own seed, actual image identities and handoff, then observed readiness and normal
closure on the original live supervisor. No ordinary receipt was copied onto
the new image or rewritten to substitute its device/inode fields.

## Exact source and environment

| Item | Identity |
|---|---|
| Development base | `27eb7571211ba0b685d7893d149438d612f6e2cd` |
| Branch | `alaz/m1-seed-readiness-r155a1` |
| Packaged installed harness | `e03f7fd4e47fea6a58b749564ab350aeb4237a26` |
| Native feature | `d1516731308de8e87130dc68124e69aad35d6911` |
| Dedicated laboratory | `AlazHarness-D3B-P71C` |
| Existing installation | `/opt/alaz-r154a1` |
| Installation receipt SHA256 | `137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2` |
| Laboratory Python | `/usr/bin/python3.12`, CPython 3.12.3 |
| Python SHA256 | `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f` |
| Ordinary-proof principal | UID 23001, GID 23003, supplementary groups `[23003]` |
| Same-image seed principal | UID 23001, GID 23003, supplementary groups `[]` |

The installed source, archive and dependency inventory remain those accepted in
[R154A1](M1-INSTALL-READINESS-R154A1.md). The new producer and laboratory callers
are outside that unchanged packaged runtime inventory. No installer receipt,
native source envelope, original owner, projection or supervisor implementation
was rewritten to make this proof pass.

| R155 source | Reviewed and tested SHA256 |
|---|---|
| `scripts/bootstrap_retained_profile.py` | `2c004f6a7154d95af216517c867f1e3cafd63a05e05838f65752eca1b89c5f01` |
| `scripts/qa/r155a1_seed_child.py` | `fe598ba4e09e10b534d4f74de2d16246228e770eb00fd273d92c40ccf665cb12` |
| `scripts/qa/r155a1_linux_accept.py` | `cc80c882fc0ada181afe86f4151e8296db13c2cd922937aa3189be9f5b71933d` |
| `scripts/qa/r155a1_linux_transport.py` | `a08345f8eaa6fe179d973d28159949d5d405c4996f60ecc79bd1bc041d4119a6` |
| `scripts/qa/r155a1_accept.py` | `113ec74d47509cefc875a19dfa8b34b465db864ead3edd04c40b3d9d7e9fc4ef` |
| `scripts/qa/r155a1_ordinary_seed.py` | `b06ffe888e75406721da111c6e8d58941a2b01004bf0b544981195a364769e6f` |

The primary focused-test record contains these source hashes and all five test
file hashes. Source review establishes the reviewed contracts; runtime acceptance
comes from the separately identified execution records.
([Source/test freeze](../evidence/m1-seed-readiness-r155a1/focused-windows002/result.json))

## Actual ordinary native seed

The accepted home is `/tmp/alaz-r155a1-ordinary007/profile`. The ordinary controller
PID was 6; producer PID was 7, start ticks 6259. The process used mount namespace
`mnt:[4026532221]` and the existing ext4 root mount, with mount ID 80 and device
pair `[8,48]`. These are the observed ordinary-proof identities, not future image
identities. ([Receipt](../evidence/m1-seed-readiness-r155a1/ordinary007/result.json))

| Owned object | Actual device/inode |
|---|---|
| Profile directory | `[2096,29648]` |
| `state.db` | `[2096,29662]` |
| `runs_idempotency.db` | `[2096,29666]` |
| `response_store.db` | `[2096,29667]` |

The producer first runs the original complete installed verifier and validates a
fresh, mode-0700 home. It uses the original cold constructors, both original
preopen helpers, original profile reservation and `NativeStoreStartup`. Startup
reached epoch 1 with all six checks: `preflight`, `response_preflight`,
`before_epoch`, `response_before_epoch`, `after_epoch`, `response_after_epoch`.

The original prepared consumer remained idle: admission PREPARED, publication
NEW and no session-admission rows. Original auxiliary writers and the original
source scanner produced the retained layout. The consumer then detached, the
owner closed, and the producer physically checked all three owned connections.
Original retained capture ran while the profile lease was still held. The
handoff passed the original encode/decode round trip before normal lease release
and event-loop/executor shutdown.

| Observation | Accepted value |
|---|---|
| Owner / consumer final states | `CLOSED` / `DETACHED` |
| All three connections physically closed | true |
| Retained capture while profile lease held | true |
| Profile lease released normally | true |
| Normal loop shutdown | true |
| Outstanding asynchronous tasks / threads | 0 / 0 |
| Qualified native source files | 755 |
| Source-derived discovery cache entries | 130 |
| Full tool registration performed | false |
| Producer-observed SQLite opens | 7, including one closed schema-reference connection |
| Active-session entries | 0 |
| Qualified blocked IPv6 probe | one; socket closed; bind not performed |
| Executed tasks / real model calls / listeners | 0 / 0 / 0 |
| API admission published | false |

The handoff SHA256 is
`333161eb5c0701f59989130e2502eb5c0c6d689fadbd09c5fc72ebb33635b398`.
The source-derived cache SHA256 is
`339458215115171f7094d43cd51a611edd42c53c1ca568c7eaa823bc1ede38c9`.
Verification took 3,376 ms, the native phase 23,851 ms and the producer total
27,227 ms. The controller observed 28,165 ms for its child. These are one actual
proof's measurements, not a general latency or capacity guarantee.
([Full accepted proof](../evidence/m1-seed-readiness-r155a1/ordinary007/result.json))

The actual linked SQLite version was 3.45.1. The original stores selected DELETE
journaling and emitted their original diagnostics. The proof does not enable
WAL, alter that runtime policy or treat the warnings as a new dependency upgrade.
The original handoff records `journal_mode: delete`.

## Supervised same-image implementation

The fixed child joins the original worker's cgroup and mount namespace, creates
the new profile on that mounted image, drops to the ordinary gateway principal
and executes the fixed producer. It does not independently acquire or release
the image lease. Its live controller/worker, fence, loop, image, namespace,
cgroup and source checks remain tied to the original supervisor.

The fixed root caller uses the original supervisor's begin, attach and start
operations, seeds the mounted image, invokes original projected readiness, then
uses original stop and finish. The fixed seed budget is 35 seconds, readiness
60 seconds and close margin 15 seconds within the original worker's 120-second
lifetime. A successful receipt must show the actual second epoch, six readiness
checks, terminal children, empty cgroup, removed loop/fence and image lease
released last. The broker socket is a metadata fixture; it does not establish a
real broker exchange, provider accounting or service admission.

The host prepares frozen inputs only from a full ordinary PASS for the exact
producer. It binds the original six evidence files, ordinary driver, three
application sources, manifest, transport and host source to the prepared intent.
The ZIP is retained as exact base64 text for the repository's text-only gate.
Apply rechecks the original proof and frozen/current bytes before an exclusive
execution-start marker and one WSL invocation.

Unknown effects do not trigger automatic cleanup or replay. The root caller's
post-effect failure path preserves the same live controller PID, supervisor,
image lease and child objects, including when diagnostic construction fails.
The transport distinguishes stdout/stderr EOF from caller exit. Host custody
claims are limited to liveness observed before transport exit unless a later
independent observation establishes continuing custody.

## Actual same-image001 acceptance

Bridge operation `e2a42e11-d56e-4bc9-9f72-bc28d2c76155` completed with exit 0.
The host recorded `SAME_IMAGE_SEED_READINESS_ACCEPTED`; the Linux transport
recorded `CALLER_TERMINAL_ACCEPTED`; the original caller completed
`SAME_IMAGE_SEED_READINESS_CLOSED`. The saved result equals the terminal JSON
result and has SHA256
`6fb481f97a70d949f3ab080102e1511d8d44d09349aa74906f2219611f10b010`.
Host communication completed within its 240-second deadline, both transport
pipes completed without overflow, and the transport and caller exited 0.
([Terminal evidence](../evidence/m1-seed-readiness-r155a1/same-image001/result.json))

The prepared ordinary-proof binding identifies the original six ordinary007
evidence files, including result SHA256
`49afc18aca1d4393925cef39e00a3a0195a0333ca3a7d510b2af0c172256541c`,
and the exact ordinary driver. The manifest identifies the reviewed producer,
seed child and caller listed above. The intent also binds the unchanged reviewed
host runner and transport. The execution-start marker records the same intent,
manifest, proof and bundle identities for this invocation.
([Prepared proof](../evidence/m1-seed-readiness-r155a1/same-image001/ordinary-proof.json),
[intent](../evidence/m1-seed-readiness-r155a1/same-image001/intent.json),
[execution start](../evidence/m1-seed-readiness-r155a1/same-image001/execution-start.json))

| Frozen item | SHA256 |
|---|---|
| Intent | `2b1d4f7eae5ac979a8f3449e230e8be8156d1335bae41b07a91f55b0ad4836a5` |
| Manifest | `2b97bdf8ddd2f3b776311aba16cffce50918c4446989f544aa2668c80238f793` |
| Ordinary-proof binding | `cb79324e986166d606fcdf345da01a6dcff73c55a477e3db7ea27a6512b70abf` |
| ZIP bundle, 104,123 bytes | `7242482096d7a5f80677b94207b36dc66c30bfe244b5fcc2b93a0d35e9225268` |
| Execution-start marker | `22b370c932bec332ae64363e046581e953504d423a8e1693900ab0089b08a39f` |

The new image is `/srv/alaz-r155a1/images/state.ext4`, 67,108,864 bytes,
device/inode `[2096,29692]`, with parent identity `[2096,29686]`. The original
worker mounted this image through `/dev/loop0`, device pair `[7,0]`, in namespace
`mnt:[4026532224]`. The seed observed ext4 mount ID 167 at
`/srv/alaz-r155a1/mount` and home `/srv/alaz-r155a1/mount/profile`.

| Process or retained object | Actual identity |
|---|---|
| Linux caller | PID 7, start ticks 2465 |
| Original worker | PID 10 |
| Same-image seed | PID 11, parent PID 7, start ticks 3076 |
| Projected readiness | PID 16, start ticks 5507 |
| Profile directory | `[1792,12]` |
| `state.db` | `[1792,26]` |
| `runs_idempotency.db` | `[1792,30]` |
| `response_store.db` | `[1792,31]` |

The original supervisor token was `4bea5c03aefcbbcf01edf05ba0daab7d`; the owned
cgroup was
`/sys/fs/cgroup/alaz-r155a1/volume-4bea5c03aefcbbcf01edf05ba0daab7d`.
The mounted-worker and stop receipts contain that same token and worker PID.
The seed process ran as UID 23001/GID 23003 with empty supplementary groups.
Its exact process identity, mounted namespace and profile/database identities
matched the caller's observations through the original worker.
([Observed identities](../evidence/m1-seed-readiness-r155a1/same-image001/result.json))

The seed reached epoch 1, completed the six startup checks, detached the prepared
consumer, physically closed all three connections, captured the handoff under
the profile lease and released that lease normally. It also recorded normal
loop shutdown, zero outstanding tasks/threads, 755 qualified native files,
130 source-derived cache entries, seven SQLite opens and the one blocked IPv6
capability probe with its socket physically closed. Its retained handoff SHA256
is `626af976bae601ec0107e2ebc29613a1b39f3f78345d80df26d34f67bc8eff5d`.

Original projected readiness then reached epoch 2 with the same six checks and
returned `SUPERVISED_PROJECTED_OWNER_CLOSED`. The original owner was closed,
the readiness child was observed exited, `volumeMayClose` was true and
`observedAfterUnknown` was false. This acceptance came from the fresh mounted
seed; its identities differ from ordinary007 as expected.

The observed event sequence completed seed, projected readiness, `NORMAL_STOP`,
`NORMAL_FINISH`, `VOLUME_CLOSED` and `VERIFY_NORMAL_CLOSE` in that order. Original
stop returned `UNMOUNTED` for worker 10; the reviewed original stop also requires
that worker's terminal exit 0. Original finish returned `CLOSED` with
`ownedUsersGone`, `loopAttachmentGone`, `fenceRemovedAfterCleanup` and
`leaseReleasedLast` all true. Formatter, metadata fixture, seed and readiness
observations each record complete output and exit 0. The final original retained
volume registry was empty. The caller's final postconditions checked the empty
mountpoint and cgroup, removed owned scope and fence, absence of image loop
attachments, and unchanged image identity. Host mount namespace and mount-table
bytes remained unchanged.
([Normal-close evidence](../evidence/m1-seed-readiness-r155a1/same-image001/result.json),
[caller checks](../scripts/qa/r155a1_linux_accept.py))

The seed's verification phase took 1,188 ms, native phase 21,936 ms and total
23,125 ms. The outer Bridge operation took 83,962 ms across the host invocation.
The evidence does not provide a separate readiness duration, so none is inferred
from that outer measurement. These measurements describe this one acceptance.

The final receipt explicitly leaves finite work, real model calls, real broker
exchange, service start, runtime admission, full D3B, M1 and production
unaccepted. There was no automatic retry or failure cleanup. The normal
supervisor close is the observed ordered shutdown. The host does not claim
continuing live custody after the successful terminal transport; its
`continuingLiveCustodyVerified: false` is consistent with this completed run.

## Preserved unsuccessful attempts and corrections

Every attempt used its own evidence directory and, when created, a new profile.
The later success does not convert earlier refusals or uncertain results to PASS.

| Attempt | Observed outcome | Correction or qualification |
|---|---|---|
| [ordinary001](../evidence/m1-seed-readiness-r155a1/ordinary001/result.json) | Exit 2, `NATIVE_IMPORTS`, `bootstrap_home_not_empty` | Original imports legitimately created the cold SOUL/directory scaffold. Fresh-home checks remain before imports; original retained-layout validation remains afterward. Profiler teardown was also corrected. |
| [ordinary002](../evidence/m1-seed-readiness-r155a1/ordinary002/result.json) | Exit 2, `CREATE_COLD_STORES`, `bootstrap_database_path_forbidden` | Original schema parsing needs one temporary `:memory:` reference. Its exact source/function/globals/DDL/phase/count are now checked, and physical close is required. Store fallbacks and URI paths remain forbidden. |
| [ordinary003](../evidence/m1-seed-readiness-r155a1/ordinary003/result.json) | Exit 2, pre-native `VERIFY_INSTALLATION`, `InstallationRejected` | The original finite rejection reason was hidden by the wrapper and was not recovered. Subsequent complete independent and embedded installed verifications passed. No verifier bypass or receipt rewrite occurred. |
| [ordinary004](../evidence/m1-seed-readiness-r155a1/ordinary004/result.json) | Exit 2 at the final `RELEASE_PROFILE` latch, `bootstrap_forbidden_effect` | This revision did not retain the specific denied event. It is not retroactively assigned a proven cause. Finite event/source diagnostics were added for the next fresh attempt. |
| [ordinary005](../evidence/m1-seed-readiness-r155a1/ordinary005/result.json) | Exit 2 at the final latch; one denied `socket.bind` in `PREPARE_CONSUMER`; no native-work attempts | The exact original urllib3 IPv6 capability probe was identified. Its bind remains prevented; the producer records it separately and requires the original socket's actual close and `HAS_IPV6 == False`. |
| [ordinary006](../evidence/m1-seed-readiness-r155a1/ordinary006/result.json) | WSL exit `4294967295`; no valid Linux report | Host output reported `Wsl/Service/CreateInstance/CreateVm/HCS_E_CONNECTION_TIMEOUT`. A later read-only check passed and found no ordinary006 home or any of the four new R155 root paths. No success or automatic replay was inferred. |
| [ordinary007](../evidence/m1-seed-readiness-r155a1/ordinary007/result.json) | PASS, exit 0 | First accepted complete ordinary native proof for producer `2c004f6a...`. |

The original urllib3 source is pinned by the existing dependency verification.
Both installed and original `urllib3/util/connection.py` readbacks had SHA256
`2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74`.
Its `_has_ipv6` catches `Exception`, then explicitly closes the socket; it does
not use a `finally` block. The producer therefore observes `fileno() == -1`
rather than assuming closure. Only the exact one blocked loopback probe is
qualified; other network/process denials still prevent acceptance.
([Original source read](../evidence/m1-seed-readiness-r155a1/urllib3-ipv6-source-readonly.json))

The ordinary003 installation uncertainty remains honestly bounded. The separate
[original verifier recheck](../evidence/m1-seed-readiness-r155a1/installation-recheck-after-ordinary003.json)
and [embedded verifier check](../evidence/m1-seed-readiness-r155a1/embedded-verifier-carrier-pass.json)
passed with unchanged installed/Python identities and receipt. An earlier direct
read-only diagnostic hit its tool deadline and is preserved separately in
`embedded-verifier-direct-timeout.json`; it is not counted as a successful check.

The ordinary006 UTF-16LE error output is preserved exactly: 322 bytes, SHA256
`252a88e9f53ca956c95bbb539b26a45d8ff60fe0bba215ec63fd969b1af93dbb`.
Its tracked [stdout capture](../evidence/m1-seed-readiness-r155a1/ordinary006/stdout-capture.json)
contains the base64 bytes, encoding, digest and decoded diagnostic. The original
binary was moved, after readback, to ignored
`scratch/r155a1/raw/ordinary006-stdout-utf16le.bin`. This representation preserves
the failure while satisfying the repository text-only gate.
([Post-timeout read-only observation](../evidence/m1-seed-readiness-r155a1/post-hcs-lab-readonly.json))

## Focused tests and portability corrections

The accepted primary Windows run used CPython 3.14.3 and completed in 29,226 ms,
exit 0. Unittest discovered/processed 120 cases: **113 executed passes, 7 skips,
0 failures and 0 errors**. The skipped cases require Linux/POSIX filesystem or
selectable-pipe behavior. The actual finite Windows three-pipe Python fixture
passed; it did not invoke WSL or a native application.
([Focused-windows002](../evidence/m1-seed-readiness-r155a1/focused-windows002/result.json))

| Focused module | Discovered cases | Executed passes | Platform skips |
|---|---:|---:|---:|
| `test_retained_bootstrap.py` | 29 | 25 | 4 |
| `test_seed_child.py` | 29 | 29 | 0 |
| `test_seed_readiness_caller.py` | 24 | 24 | 0 |
| `test_seed_readiness_runner.py` | 28 | 28 | 0 |
| `test_seed_readiness_transport.py` | 10 | 7 | 3 |
| Total | 120 | 113 | 7 |

These are owned fixture/contract tests. They do not establish privileged UID,
mount, cgroup or native application acceptance. Earlier local focused results
overlap these cases and are not added into a full-regression total.

The first primary [focused run](../evidence/m1-seed-readiness-r155a1/focused-windows001/result.json)
failed and remains preserved: 115 cases, 7 skips, 15 errors and one failure, exit
1. One owned caller fixture assumed a Linux-only constant existed on Windows.
The other portability defect compared Windows path and descriptor `ctime`
values as if their semantics were identical. The actual observation showed
path creation time and descriptor change time differing while common identity
and byte hashes remained stable.

The corrected host compares device/inode/mode/size/mtime/link-count/birth-time
across Windows views. It still compares full, including-ctime stamps separately
within the descriptor and path views before and after reading, and repeats the
cross-view identity check. Non-Windows cross-view ctime remains strict. No source
hash, frozen-input, single-link or no-alias guard was removed.
([Windows metadata observation](../evidence/m1-seed-readiness-r155a1/windows-stat-view-diagnostic.json))

Source review also corrected two host defects before root application: the
reviewed seed child now has an explicit fixed hash pin, and the complete Windows
`communicate()` operation, including synchronous stdin writing, runs once in an
owned worker under a separate main-thread deadline. Timeout preserves process,
reader and worker references without close, signal, retry or cleanup. These
corrections are exercised by the accepted focused suite.

## Protected state, repository gate and publication

The [entry baseline](../evidence/m1-seed-readiness-r155a1/baseline.json) records
the original root at `58b210ac9d400b84b028a2b57dcf1a4a396f089e`. The
[pre-publication comparison](../evidence/m1-seed-readiness-r155a1/protected-state-before-publication.json)
passed: its branch/status and all 33 existing changed/untracked file byte hashes
and sizes were unchanged. The native worktree remained clean at
`d1516731308de8e87130dc68124e69aad35d6911`, and the R154 worktree remained
clean. Local main, origin/main and live remote main all remained at the clean
base `27eb7571211ba0b685d7893d149438d612f6e2cd`. The active implementation is
isolated in the R155 worktree. The original root status copy was not overwritten.

The owned staging scope is six scripts, five focused test modules, this report,
the roadmap/status updates, R155 status history and the R155 evidence tree.
The [independent closure review](../evidence/m1-seed-readiness-r155a1/independent-reviews.json)
verified the terminal/saved result, frozen bindings, raw child frames, actual
identities and ordered close. A separate bounded evidence scan passed UTF-8,
NUL, size and JSON checks. Root's staging readback confirmed all 11 current
source/test hashes equal the accepted focused002 map.

The initial index-byte preflight detected Git's CRLF-to-LF conversion in one
historical environment result. The R155 evidence directory now has a scoped
`* -text` attribute to preserve exact captured bytes, including frozen proof
inputs, on every checkout. No global Git attributes or original evidence bytes
were changed. The two explicitly selected UTF-8 unittest logs are force-added
under the existing ignore rule; that rule remains unchanged.

The [repository static gate](../evidence/m1-seed-readiness-r155a1/static001/result.json)
completed with exit 0 in 161142 ms. `python -B scripts/ci_check.py`
checked 6464 indexed repository files, 2 gitlinks and 10 selected components,
and discovered 3865 unittest cases with no errors. It does not execute
that full suite or establish runtime/model acceptance. The scan covered the
115 staged paths then present. The final report/status and scan-result metadata
are subsequently checked and staged; the exact final commit still requires CI.

Raw Windows CRLF is retained in the original environment result and the static
stdout capture. Their two explicit attribute entries classify CR as a line
ending while retaining blank-at-eol, blank-at-eof and space-before-tab checks.
The initial staging whitespace failure occurred before the scanner started;
its [record](../evidence/m1-seed-readiness-r155a1/staging-whitespace001.json)
preserves that distinction.

Publication requires `alaz/local-ci` success on the exact final pushed feature
SHA before ordinary fast-forward of main. The existing [CI contract](CI.md)
uses a 360-second budget with an immutable image, 1 CPU, 512 MiB RAM and
768 MiB RAM-plus-swap. The gate and limits are unchanged. Git publication
does not deploy a service.

The committing document cannot contain its own final commit hash. Post-commit
CI, live refs and protected-state observations belong to
`scratch/r155a1-publication/` in the R155 worktree, including
`accepted-ci-before-main.json` and `final-publication.json`.
These receipts and the live exact-SHA GitHub status determine publication;
this pre-commit document does not predict their result.

## Remaining product work

The same-image seed/readiness/ordered-close subgate is closed by same-image001.
The next P1 acceptance is finite normal and error work, replay versus new work,
and ordered shutdown through the same complete product entry. The current task-free seed
and readiness acceptance establishes the prerequisite for that work.

The roadmap's subsequent daily-use/selected real-provider and budget acceptance,
persistence and memory use, fault/operator reconciliation, and controlled pilot
gates remain separate. No percentage, production date, full D3B acceptance or
autonomous-operation claim follows from the R155 focused, ordinary or same-image
proofs.
([Product roadmap](PRODUCT-ROADMAP.md))

Evidence root: `evidence/m1-seed-readiness-r155a1/`.
Continuation owner: `status.md` and its preserved `docs/status-history/r155a1-*`
records, together with live Git and terminal operation receipts.
