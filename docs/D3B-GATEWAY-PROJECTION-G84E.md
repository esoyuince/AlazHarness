# D3B trusted Gateway projection primitive — G84E

Status: scoped native confinement PASS; not a production Gateway launcher or full D3B.
Active branch: `alaz/d3b-principal-launch-21oct`; base `69d72e9`.
Old broker installation remains the exact57-file candidate from `802fade`.
This slice adds one new product primitive, three lab-only QA scripts, and tests.
No pre-existing product/test/config source is changed.

## Implemented boundary

`packages/claw-hermes/gateway_projection.py` supplies an irreversible `enter`
primitive for an ALREADY AUTHORIZED, fresh, single-threaded host-root child in
a trusted installation. It does not elevate, start a daemon, accept arbitrary
commands, provision an account, or offer an unconfined retry. Failure requires
the caller to exit the dedicated process. It is not exposed by the existing
combined guard or by a production privileged entrypoint.

It reuses existing principal, filesystem-policy, socket-inode, tree-inspection,
capability-drop, FD-cleanup, seccomp and Landlock implementations. A version2
principal contract is mandatory; legacy ipc_view.prepare/project still reject
version2. A separate code path prevents silently changing legacy semantics.

Root controller predicates check actual kernel identity, initial host user
namespace and required capabilities before inspecting the projection. Only
mount, network and System V IPC namespaces are created. No user-namespace UID
remapping occurs. Root's mount propagation is made private before construction.
The old root is detached by pivot_root in the child and never exposed to the
Gateway. The parent mount view remains unchanged.

Readonly exports require root-controlled ancestors and tree contents. Existing
sockets/devices/FIFOs and nested mounts are rejected, not silently traversed.
The runtime roots are deliberately narrow to exclude WSL-specific submounts.
After projection, the selected broker socket is the SAME pinned inode and
retains its real broker UID/GID/mode. Its parent directory is SYNTHETIC with
broker UID/shared GID0710; it is NOT a bind of the real broker directory, and
its inode is not claimed to match the host parent. Sibling files/sockets are
therefore absent. Source socket custody is rechecked at binding and before
pivot, and projected socket metadata is checked afterward. The root supervisor
and declared root-controlled exports remain trusted; this is not an atomic
lease against a hostile privileged host/ABA mutation or kernel compromise.

Writable host directories are NOT bound. Each declared empty workspace becomes
fresh private tmpfs with Gateway ownership0700 and nodev/nosuid/noexec. This
also excludes a host socket injected into the original workspace AFTER launch.
The synthetic root is remounted readonly/noexec; separately selected executable
runtime mounts stay usable. Runtime-created local sockets/loopback still work.

After construction, the existing irreversible drop mechanism selects the real
Gateway UID23001/GID23003, clears supplementary groups and all capabilities,
sets no_new_privs and verifies saved/filesystem IDs plus preserved initial maps.
Existing seccomp restrictions are installed, inherited FDs are closed, then
Landlock is applied. Fixed self process metadata is allowed; no arbitrary
process subtree or descriptor data read is granted. A fresh exec to the fixed
lab target verifies these conditions persist into a new interpreter.

## Authorized native environment

Only the user-approved `AlazHarness-D3B-P71C` disposable WSL distribution was
used. Existing Ubuntu, production server, default/global WSL settings, accounts,
packages, /opt/alazharness-broker/802fade and old /srv/alaz-p71c acceptance remain
unchanged. New component files live at /opt/alazharness-gateway-g84e; fresh test
runs use /srv/alaz-g84e/n01,n02,n03. No previous used run was replayed.

The controller creates an outer private network namespace for its benign host
listeners. The Gateway then creates a DIFFERENT network namespace itself.
Both preserve the initial host user namespace. This is a controlled WSL test,
not independent-hypervisor isolation certification.

## Native acceptance n03 — actual execution, not mocked/reconciled

The final command exits0 with PASS_SCOPED_GATEWAY_PROJECTION. Eighteen supervisor
checks and23 post-exec target checks pass. These overlap and are not41 distinct
security properties. The real target executes under UID23001; the unchanged
broker under UID23002 sees two authenticated pings, including the actual
ProviderBrokerClient.ready implementation. SO_PEERCRED at the client identifies
the expected live broker PID/UID/GID. Supervisor /proc observations independently
confirm the target PID, argv, real/saved/filesystem IDs and namespace maps.

The target verifies no groups, all five capability sets zero, NNP1/seccomp2,
three changed namespaces and unchanged host user namespace. An inherited high
numbered host file descriptor is EBADF in the target but remains open in its
parent. Private workspace file I/O, a new pathname Unix socket, and new TCP
loopback work; namespace-creation and recvmsg syscalls are denied with EPERM.

Positive controls under the SAME Gateway UID outside the projection connect
to each fixture before rejection is claimed. The projected process gets:

| Target | Actual outcome |
|---|---|
| Host loopback TCP listener | ECONNREFUSED111 |
| Host abstract Unix listener | ECONNREFUSED111 |
| Unrelated host pathname socket | ENOENT2 |
| Socket beside the authorized broker socket | ENOENT2 |
| Socket injected late into host workspace | ENOENT2 |
| Present bound protected regular canary, read AND write | EACCES13 |
| Actual broker socket | Two authenticated successful pings |

Private broker config and budget paths are absent from the projected root;
this is PATH HIDING, not a new EACCES observation on those files. P71C previously
proved their ACL read/write-open denial. The separate PRESENT canary is readable
by the host positive control but denied by the projected target. Missing files,
timeouts or dead fixture listeners are never accepted as that canary proof.

The host workspace does not receive the target's private file or runtime socket.
The parent mount table is unchanged. Broker exits cleanly, removes its socket,
records no active requests and zero provider attempts/responses. Private old
config/budget hashes and inode metadata remain unchanged, as do all57 old
installed source files. The new primitive/QA source hashes match before/after.

Controlling evidence: native-n03.json, native-n03-source.json, its actual raw
stdout/stderr and command intent. Unit receipt checks compare these source pins
to CURRENT files; they do not turn an earlier source revision into new acceptance.

## Preserved failures and repairs

n01: full /usr export contained three WSL nested mounts, so the product correctly
refused before confinement. The controller then used verified submount-free
Python runtime roots. No product check was removed or weakened. Full diagnostic
and original QA source are retained.

n02: actual communication reached two pings, but the QA finalizer tried to read
stderr after communicate() closed it. That ValueError interrupted its remaining
cleanup/report. No n02 PASS is claimed. The retained raw failure was followed
by explicit live PID/command/UID verification, targeted SIGTERM, socket-removal
verification and empty-anchor cleanup. Later, only the three known stale n02
fixture socket files were removed after verifying no owned process remained.
The original contract/ready/shutdown records remain. No global kill/cleanup.

The diagnostic helper now detects closed/absent streams and cannot let an I/O
error skip owned cleanup. Five regression cases cover it. The fixed QA source
was installed with a checked old hash, and n03 ran afresh in new paths. The
success above is a REAL new native execution, not editing/reinterpreting n02.
The product projection module itself did not change between n01 and n03.

The first Linux unit-launch wrapper returned1 with no output; the reason is
UNKNOWN and that record remains. A separate actual execution of the unchanged
33 tests returned0 with all33 named outcomes and complete output in
linux-unit-diagnostic.txt. Copied sources/fixtures were independently rehashed.
Do not describe this as a corrected result of the first silent invocation.

## Tests, scope and delivery

Windows and Linux focused suites each contain33 tests:23 contract/identity/order
cases,5 native source/receipt checks and5 cleanup regression cases. They are
not33 new Linux namespace launches. Full Windows and static gates are reported
separately once terminal; source files are frozen during execution.

This closes a lower-level real two-UID, private-root/network/IPC confinement
primitive with one broker socket for these sources and fixtures. It does NOT
run Hermes Gateway, persist its sessions, perform provider dispatch, certify
a production root launcher, activate old IPCv2 or close full D3B. The current
writable directories are intentionally ephemeral. Simply binding writable
Gateway host state back in would reintroduce the late-socket class of exposure.

Next: choose/implement safe persistent state and a fixed trusted Gateway
entrypoint/post-exec contract on top of this primitive; then run the real pinned
Hermes Gateway. Provider dispatch is a distinct gate: broker readonly access
to actual live Gateway state.db/epoch/grants, a dummy local provider, private
budget limits, restart/replay/rebind and unknown outcomes must be exercised.
No real credentials/model/provider send are authorized by this primitive.

Kernel references consulted for mechanism semantics, not acceptance evidence:
https://docs.kernel.org/userspace-api/landlock.html
https://man7.org/linux/man-pages/man2/pivot_root.2.html
https://man7.org/linux/man-pages/man7/network_namespaces.7.html
https://man7.org/linux/man-pages/man2/unshare.2.html

## Final regression, cleanup and local delivery

Full Windows standard execution: **2269 total /2264 PASS /5 SKIP /0 failures /
0 errors**, exit0,287.922 seconds. Results use the unittest result object, not
footer parsing. The33 focused cases are a subset of this full suite. A separate
Linux execution passed33/33 with complete named output. The earlier silent
Linux wrapper exit1 remains UNKNOWN; it was not retroactively called success.
All344 frozen package/script/test/config files match before/after/final bytes.
All338 pre-existing sources remain unchanged. New product and lab runner source
pins match the fresh n03 native receipt and staged Git content exactly.

The final lab audit found zero owned live broker/Gateway processes, no broker
sockets and none of the three projection anchors. Only the three known stale
n02 fixture socket entries were removed, with exact owner/type checks. Original
P71C acceptance/config/budget and57 installed product files are intact. Only
AlazHarness-D3B-P71C was stopped; existing Ubuntu remains default and stopped.
No global shutdown, account/package change, production action or model call.
New test files/receipts and the stopped disposable disk remain for inspection.

Local static gate PASS with2269 discovered tests; the final receipt is stored
separately. It is not remote CI or an additional runtime acceptance. Git diff
format checks pass. No squash, force-push, main change or publication. Read this
worktree's Git HEAD for the local implementation/evidence commit. The candidate
broker source remains802fade; the newly added projection is bound by its own
exact source hash in native-n03-source.json and summary.json.
