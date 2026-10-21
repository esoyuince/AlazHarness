# D3B exact-source installation candidate — S10E

Status: source export only. NOT installed, NOT a positive UID transition, NOT D3B acceptance.
Active branch: `alaz/d3b-principal-launch-21oct`.
Source revision: `802fade74d5b08b26f975738d4aa8d7546dc9cac`.
This task adds export/validation tooling; all pre-existing product code stays unchanged.

## Delivered source boundary

The source candidate contains 57 exact Git blobs, 505793 source bytes, in a
563200-byte uncompressed Git archive. SHA-256:

`8c0bbad498ccc877edbce85af535dd0fcd68b2dbf21b72858487577942424451`

Archive prefix: `alazharness-broker/`. The companion `manifest.json` records
every relative filename, original Git blob, file mode, length and SHA-256.
It includes the fixed three broker entrypoints, packages, licenses/security
and upstream provenance manifests. It does NOT contain private configurations,
budgets, state databases, user homes, a Python interpreter, dependencies,
a complete Hermes Gateway checkout, system identities or a launch permission.
The included packages support the broker import graph; their presence is not
acceptance of every optional host/Gateway component or a complete runtime.

Candidate A (relative to this worktree):
`scratch/principal-install/802fade-s10e-a/broker-source.tar`.
Candidate B: `scratch/principal-install/802fade-s10e-b/`.
Binary candidates remain ignored local files, not tracked evidence or a release.
A copied manifest alone is not trusted authority: verify the expected archive
hash/source revision through an independently trusted channel before installation.

## Export behavior

`scripts/qa/export_principal_source.py` accepts a full immutable commit SHA and
an ABSENT destination beneath this worktree's ignored `scratch/principal-install`.
It reuses Git archive and the existing bounded credential/private-path scanners.
Every archived file must match its original Git blob exactly. Missing/extra or
case-colliding names, links, special files, traversal, unexpected modes, oversized
payloads, sparse files and nonzero data after the archive terminator are refused.
There is no archive extraction, source execution, elevation, network download,
installation or overwriting in the exporter. A partial write is retained for
inspection, not automatically deleted or retried.

The first actual archive failed exact metadata comparison: local Git autocrlf
expanded LICENSE from1081 bytes to1102 bytes. No candidate directory was created.
The exporter now fixes core.autocrlf=false, core.eol=lf and tar.umask=0022 for
this invocation only; Git configuration and product bytes are not modified.
The raw failure, diagnostic and correction are retained. Exact blob checks were
not relaxed. A real temporary Git-repository test covers autocrlf=true, repeatable
archive/manifest output, ignored untracked private files and no-overwrite behavior.

Reproduce as an ordinary development user, choosing a NEW absolute output:

```text
python -B scripts/qa/export_principal_source.py --commit 802fade74d5b08b26f975738d4aa8d7546dc9cac --output <worktree>/scratch/principal-install/<fresh-name>
```

## The missing authorization / environment gate

The prior denied privileged invocation is NOT retried or bypassed. Current
connected Ubuntu was observed read-only as UID/GID1000. Only /opt and /srv
entries containing alaz/harness and account names containing alaz/broker were
checked; no matches were found. This is a limited observation, not an exhaustive
claim that no Linux deployment exists. The developer-writable Windows/WSL
checkout is NOT a trusted privileged installation.

Before a positive run the operator must designate a disposable isolated Linux
installation and explicitly authorize its setup and one-shot privileged test.
The scope should name the instance, trusted installation path, per-run test
state root, the two nonzero host UIDs and shared primary GID, what may be created,
and cleanup/retention. No production service, existing account, sudo policy,
setuid helper, default WSL installation or existing agent state is in scope.
A tool/OS denial still stops execution; approval is not a bypass mechanism.
Do not use nobody or user-namespace UID remapping as a substitute for dedicated
actual host identities. No such positive setup was performed in this task.

## Exact preparation plan — operator scope, NOT executed here

1. Establish a fresh isolated test instance, not the production server. Keep
   evidence outside writable Gateway state. Verify native Linux x86_64, initial
   host UID/GID namespace maps, trusted Python and libseccomp availability.
2. Independently verify the candidate hash and 57-file inventory. Copy only
   validated regular files into a new root-controlled installation such as
   `/opt/alazharness-broker/802fade`. All ancestors, code, interpreter and loaded
   dependencies must be root-controlled and not group/world writable. The
   interpreter path supplied to the contract must resolve to a real executable
   satisfying the existing launcher checks, not an unreviewed symlink. The
   archive's stored UID/GID does not certify actual destination ownership.
3. Provision or designate distinct nonzero host Gateway/broker UIDs and one
   dedicated primary socket GID in THAT isolated instance, under the explicit
   approval. Record exact IDs and initial user namespace. The broker must have
   no supplementary groups; all real/effective/saved/filesystem IDs must agree.
4. Prepare a new per-run state layout under a root-controlled parent, for
   example `/srv/alazharness-d3b/<short-run-id>`. The socket pathname including
   `/egress.sock` must fit the existing100-byte contract bound. Do not use /tmp
   as a trusted ancestor; it is writable by other users and is rejected.

| Object | Owner/group | Required mode | Exposure |
|---|---|---|---|
| Installation and ancestors | root-controlled | No group/world write; code normally0644, directories0755 | Read-only source |
| Launcher contract | root | 0600 | Controller only |
| Private config parent | broker UID, designated GID | 0700 | No Gateway access |
| Broker config | broker UID | 0600, single link | Dummy credentials only |
| Private budget directory | broker UID, designated GID | 0700 | No Gateway access |
| budget.sqlite3 | broker UID, designated GID | 0600, single link | Initialize explicitly before launch |
| Empty socket directory | broker UID, designated GID | 0710 | Gateway may traverse only |
| egress.sock (created by broker) | broker UID, designated GID | 0660 | Selected IPC endpoint |

5. Use the existing explicit broker-budget initializer only in the approved
   isolated setup; never have runtime create a missing authority implicitly.
   Keep config, budget and socket directory nonoverlapping. Use dummy local
   provider settings and no live tokens. Provisioning code needs a separately
   reviewed execution; this document is not an automatic installer.
6. Derive the config hash, pinned principal, and command digest from the
   INSTALLED paths/revision. The fixed target argv contains the installation
   path, so a developer-checkout digest is NOT valid after relocation. Preserve
   the strict contract and post-exec checks rather than adding a fallback.
7. Before any send test, specify broker read-only access to live Gateway
   state.db/epoch/grants separately. A successful ping does not exercise that
   path. Never expose private broker config/budget to Gateway to solve it.
   aiohttp and its dependencies must be independently pinned/trusted for an
   actual provider-dispatch test; this source bundle does not install them.

## Positive acceptance sequence — still NOT RUN

First run only the fixed broker path in the approved installation. Observe
actual controller and post-exec process state: PID continuity, eight UID/GID
slots, empty groups, all five capability sets zero, no_new_privs, pinned host
namespace/maps, inherited and reinstalled known filter, exact executed image.
Then connect under the designated Gateway identity and verify SO_PEERCRED on
both ends. Observe the actual socket owner/group/mode, not only JSON claims.

Attempt both read AND write access to the PRESENT private budget/config from
Gateway; require explicit EACCES/EPERM, with positive owner controls and
before/after content/inode checks. Missing files or a timeout are not denial
proof. Test wrong identity/config, safe termination, controlled restart with
fresh socket output and retained private budget, rebind/replay and cleanup.
Use a dummy local provider for a distinct send/accounting gate after the live
Gateway-state read path is prepared. Do not infer send success from ping.

Even that broker-stage proof would NOT close full D3B: trusted Gateway
network/filesystem projection preserving the host identity remains a separate
implementation gate. Both IPC v2 prepare/project gates remain closed. Do not
remove them, widen v1 permissions or activate autonomous/production work.

## Evidence and scope

All new evidence: `evidence/d3b-install-export-s10e/`. Candidate exports are
source artifacts only. Relocation checks use an owned temporary directory and
an ordinary user, manually copy validated regular bytes, and import five
modules in a fresh isolated interpreter. They never invoke main/launch,
start a broker, change UID, install dependencies or create a privileged setup.
Results, source freeze and final commit are recorded after their terminal
receipts; previous successful2203 suite is not counted as a new execution.

References for archive semantics (not acceptance evidence): official Git
`git-archive` documentation and Python `tarfile` documentation. Export does
not rely on extractall or its default extraction filter.

## Current completed export observations

Windows focused17/17 and Linux focused17/17 passed. The two Windows archive
AND manifest copies are byte-identical. Native Linux Git independently
recreated the exact563200 archive bytes and the same57 original source blobs.
The first WSL exporter invocation on the Windows worktree failed because its
.git pointer contains a Windows C:/ path. That failure is preserved; the
subsequent comparison reads the existing common object store via its explicit
Linux path, changes no Git configuration or worktree registration, and performs
no privileged operation. It is not a successful Linux invocation of build()
on that Windows-style worktree. A normal native Linux Git checkout is needed
for the normal Linux CLI path; its real temporary-repository test passed.

`linux-relocation.json`:10/10 checks PASS_SOURCE_RELOCATION_ONLY. All57 files
retained their Git hashes after manual copy into a fresh owned temporary tree.
Five real modules imported under isolated Python from that relocated tree;
no main/launch/broker was invoked. No bytecode or source mutation occurred,
the tree was removed and the parent's identity remained unchanged.

The standard full suite and final local static results are recorded separately
after completion. No previous full-suite result is reused for this new helper.

## Final scoped result

New full Windows standard execution:2220 total /2215 PASS /5 SKIP /0 failures /
0 errors, test runner exit0. Counts are collected directly from unittest's
result object, not a CRLF-sensitive footer regex. The focused17 cases are a
subset; do not add them to the full total. Same17 cases pass separately on
Linux. Ten owned relocation checks pass; those are import/source observations,
not successful broker execution. All333 current source/config/test hashes are
stable across full execution; all331 pre-existing sources remain unchanged.
The current local static gate is recorded in static-final.txt once terminal.

Both initial failures are retained: the Windows LICENSE conversion refusal,
and Linux Git refusing the Windows-style worktree pointer. Native common-store
read produced the exact same archive without modifying either configuration
or registration. Raw evidence is kept byte-for-byte, including original JSON
line endings. The binary candidates are in ignored scratch only.

No install, account, root action, service change, real model, push or main
update occurred. The next positive gate requires an explicit environment and
bounded setup/execution approval, not another inventory/test-count increase.
Read this worktree's Git HEAD for the local tooling/evidence commit; the source
candidate intentionally continues to identify the already-qualified802fade.
