# D3B post-exec and independent QA integration — C91A

Scope: LOCAL INTEGRATION; positive host-UID transition and full D3B NOT ACCEPTED.
Active branch: `alaz/d3b-principal-launch-21oct`.
Worktree: `scratch/worktrees/d3b-principal-launch-21oct`.
Primary input: `9469d58bf1aa9b12fed059fae8df6c51282b4644`.
Independent input: `d0414e24358a4b632080272d799296e40ae1bf94`.
Published main at the start of this work: `cc7ceba8f850da7652a647e984cbae2c45c8fdea`.

## What this closes

The primary post-exec work is no longer in progress: its terminal full standard
run recorded 2200 total / 2195 pass / 5 skip. Its nine product source files match
the independent QA's formerly uncommitted snapshot byte-for-byte in the Windows
checkout. The corresponding immutable Git blobs were also checked, with exact
LF/CRLF representation differences explicitly recorded, not arbitrary hash
fallbacks. See `inputs-and-qa-custody.json`.

This merge preserves both development histories and all original QA evidence.
There was no product conflict. `status.md` had two conflict blocks, both preserved
as historical narratives under the current integration section. An initial guard
expected one block and stopped before writing; both blocks were then inspected
and resolved. All 328 pre-existing source/config/test Git blobs equal the primary
input, and all 32 inherited QA evidence blobs equal the QA input. No product
behavior, UID policy, filter, filesystem permission or IPC gate is changed here.
Two explicitly invoked QA runners are added to this primary tree; they are not
new default-discovery test methods.

## Fresh integrated execution

All results below are new executions from the merged tree. The 330-file source
snapshot is checked before/after the groups. Historical receipts are retained
unchanged and are not relabeled as these new runs.

- Independent post-exec logic: Windows22/22 and Ubuntu22/22 PASS. Kernel privilege
  state and broker boundary calls are MOCKED; not a root-to-broker transition.
- Actual Linux files/FDs: 26/26 PASS. Fresh owned files, permission/link/race checks,
  inherited file/socket cleanup and actual exec; no privileged syscalls.
- Actual Linux post-exec: 16/16 PASS. PID/identity and no_new_privs/filter inheritance,
  known recvmsg denial, wrong-identity refusal before opening the config, cleanup.
- Actual Linux launcher: 13/13 PASS. Ordinary user rejected as controller, fixed CLI
  refusal, inherited socket cleanup; no successful different host UID observed.
- Linux selected standard principal suite: 80/80 PASS, zero skips. This is a subset
  of the standard suite, not additional to its full total.

Commands, output paths, counts, exit codes and source pins are indexed in
`evidence/d3b-launch-integrated-c91a/selected-native-summary.json`. Every result has
exit0, a nonempty expected check/test count and unchanged source hashes. The22
Windows/Linux runs repeat the same cases; native13 and26 scopes overlap in part.
No cross-platform/native totals are added into a fictitious unique test count.

Full Windows regression completed: **2200 total / 2195 PASS / 5 SKIP / 0 failures / 0 errors**, exit0, no timeout. The five skipped cases are the existing opt-in Linux budget/IPC tests; this slice does not count them as newly executed. All330 source files were unchanged before/after. See `full-windows-result.json` and the retained full verbose log. Static discovery remains separate from test execution.

## Exact remaining acceptance, not another readiness inventory

The immediate blocker is an explicitly authorized, pre-provisioned isolated
trusted installation for a REAL successful launch. The developer-writable
checkout is not such an installation. This integration does not grant privilege,
create an account, invoke root, install a helper or work around any prior denial.

The test environment must supply root-controlled interpreter/source/dependencies
and ancestors, distinct real nonzero Gateway and broker host UIDs, the designated
primary socket GID, and the pinned initial host user namespace. It must separately
prepare the broker's0600 config,0700 budget directory with0600 database, and empty
0710 socket directory. Launch and target command/config digests must refer to this
installed revision, not an older legacy argv. Source paths are part of the digest.

First positive gate: run the actual broker launcher in that authorized environment,
observe the child after exec (all UID/GID slots, supplemental groups, five capability
sets, no_new_privs, filter and namespace), then connect from the intended Gateway
identity and verify both socket peer credentials. Verify wrong identity/config,
restart, rebind and safe shutdown without provider inference. A declared UID or a
mocked observation is never evidence that another host identity actually ran.

Before a real `send` trial, also specify read-only broker access to the Gateway's
state.db/epoch/grant observations: `PermitVerifier.check_authority` opens this live
store in read-only mode. A successful ping alone does not qualify provider dispatch.
Do not grant Gateway access to the broker's config or private budget to solve that
separate read path. Access denial must include attempted read and write plus
positive owner controls, not absence of a file or a timeout.

Gateway network/mount projection remains a SECOND implementation/acceptance gate.
The existing rootless launcher changes user namespace and maps only the Gateway
UID; it cannot certify the intended host-principal deployment. IPC v2 prepare and
project remain closed. Keep them closed until the matching trusted projection is
implemented and tested for selected socket only, denied budget files, unrelated
IPC/network, peer identity, restart/rebind/replay/ACK-loss and cleanup.

No production service, real model, account provisioning, privileged installation,
GitHub push or main update belongs to this local merge. Main and old worktrees are
preserved. Main integration later requires an explicit publication review and
successful CI on the exact pushed SHA; main is a development baseline, not release.

## Source references for the remaining setup

The above prerequisite is derived from this revision's `principal_launch.py`
(`controller`, `trusted_install`, `deployment`, `drop_identity`),
`principal_target.py` (`restricted_kernel`, `prepare`), `host_principal.py`,
`provider_egress.py` (`PermitVerifier.check_authority`) and the still-closed
`ipc_view.py`. These source observations are not runtime evidence for an
unperformed privileged deployment.


## Raw-evidence formatting

The first staged whitespace check rejected raw Windows CRLF JSON preserved with -text. All reported lines were checked to contain no trailing spaces or tabs. Evidence-only cr-at-eol attributes preserve the original bytes and still reject ordinary trailing spaces; product formatting rules and inherited QA attributes are unchanged. The first diagnostic and exact explanation remain in raw-format-first.txt and raw-format-resolution.json. No test or security assertion was weakened.


## Final local handoff

Fresh full regression2200 total:2195 PASS,5 SKIP,0 failures/errors, exit0. All six selected/native tasks terminal exit0. Local static gate PASS,2200 discovered; not remote CI. Existing328 source Git blobs, inherited32 QA evidence blobs and330 working-source hashes remain unchanged; five new native/QA JSON receipts are byte-identical in Git index and on disk. Original failures remain historical evidence. The merge commit retains both input histories; read Git HEAD for the local checkpoint. Main/production unchanged, no push or privilege transition.
