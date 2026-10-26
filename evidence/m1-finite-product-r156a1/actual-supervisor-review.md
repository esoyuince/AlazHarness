# R156 actual evidence — independent supervisor review

## Scope and conclusion

Read-only review of the supplied R156 actual records and generated fixed QA
sources. No native runtime, remote operation, new test suite or product-source
edit was performed. The evidence supports **ACCEPTED: same installed source,
same supervised ext4 image, seed then fixed projected native finite lifecycle,
normal ordered close, explicit scripted model fixture**. No contradictory
parent/worker/finite-child/close observation was found in these records.

This is a bounded P1 sub-deliverable. It is not full P1, M1 or production
acceptance, a real provider call, real broker exchange, restart replay, or a
successful UNKNOWN recovery experiment.

## Reviewed material

- `r156-actual/native-evidence/image001/{result.json,stdout.txt,stderr.txt,intent.json,execution-start.json,ordinary-proof.json}`
- `r156-actual/native-evidence/ordinary001/{result.json,stdout.txt,stderr.txt}`
- `r156-actual/acceptance001/installation-{binding,receipt}.json`
- Generated caller/transport/host/seed/assertion sources under
  `r156-actual/acceptance001/scripts/`.
- `r156-finite/PRODUCT-ROADMAP.md` and the previously reviewed supervisor,
  retained launcher, pure finite protocol and runtime control implementation.

The image result SHA-256 is
`6a67c078680fa4cb41ae29547c3c9e6e7048f7aeb49327384c37822ea0e88931`.

## Source and byte bindings

The observed installation is `/opt/alaz-r156a1`, harness commit
`e641a5000810efb2a453ae847f689b422f7d41a7`, native feature
`d1516731308de8e87130dc68124e69aad35d6911`, 838 source files and 1,162 dependency
files. Its receipt SHA is
`a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845`, matching the
actual receipt bytes, caller installation record and seed record.

All four generated input source sizes/hashes match `intent.json`. The generated
transport and host runner also match their intent hashes. Recalculated host
stdout/stderr hashes, nested transport and child output sizes/hashes, decoded
caller/owner frames, intent hash, execution-start hash and seed handoff hash
match their recorded values.

`ordinaryProofSha256` refers to the host runner's canonical **proof binding
manifest**, not `ordinary001/result.json`. The subsequently supplied
`image001/ordinary-proof.json` is 945 bytes and independently hashes to
`c44c6e0806b6cd60bd33f4d410268bcdbd4e06bfe4333b6e77502989e10dfa71`, matching both
intent and result. Its rows for the supplied ordinary result/stdout/stderr also
match their actual sizes and hashes. The earlier local-extract limitation for
this outer binding is resolved. The generated host code verifies the complete
six-file ordinary proof inventory before the image operation.

## Actual ownership and close observations

| Role | PID / start ticks | Observed result |
|---|---|---|
| Original root caller | 7 / 8733 | Caller terminal observed, exit 0 |
| Original mount worker | 10 | Same PID and token in MOUNTED and UNMOUNTED |
| Seed child | 11 / 8919 | Explicit parent PID 7, complete capture, exit 0 |
| Fixed finite child | 16 / 9977 | Same PID/ticks in supervisor and capture; owner PID 16; exit 0 |
| Metadata socket fixture | 9 / 8893 | Complete capture, exit 0 after volume close |
| Formatter | 8 | Complete capture, exit 0 |

The seed and original worker identify `mnt:[4026532224]`. The image is the fresh
64 MiB `/srv/alaz-r156a1/images/state.ext4` on `/dev/loop0`. Seed profile identity
is `(1792,12)` and its three database identities are `(1792,26)`, `(1792,30)`,
`(1792,31)`. Its handoff is epoch 1 and instance `r156a1-seed`; the finite owner
reports epoch 2. These seed identities are distinct from the ordinary proof's
separate temporary profile, consistent with the fresh same-image seed design.

The recorded event order is:

`SEED_COMPLETED → PROJECTED_FINITE_ATTEMPT → PROJECTED_FINITE_COMPLETED →
NORMAL_STOP → NORMAL_FINISH → VOLUME_CLOSED → VERIFY_NORMAL_CLOSE → COMPLETE`.

The finite close receipt says consumer DETACHED, owner CLOSED, the same three
connections physically closed, registry reference count zero, models closed,
zero rows changed by retirement and caller profile lease released. The original
volume finish separately reports users gone, loop attachment gone, fence removed
after cleanup and image lease released last. `volumeStage` is CLOSED and
`originalRetainedVolumes` is empty. Host mount namespace and mount table checks
both passed. Retained files/image paths are not claimed to have been deleted.

## Finite work and scope

Four case receipts are normal, exact replay, new request, controlled application
error. Cumulative computation counts are `1,1,2,3`. Normal and replay have the
same request/admission/result hashes; normal, new and error have three distinct
admission IDs. The application error is terminal `failed`, while the fixed child
itself completes with exit 0 and the normal original close.

Native profiling records `run_api_turn`, `execute_finite_admission`, `run_sync`,
`commit_and_publish` and `settle_session_input`. Coroutine profile event counts
are not unique request counts. `run_sync`, commit/publish and settlement each
record 3 events here.

`observedAfterUnknown` is false. All recorded owned attempts are COMPLETED;
caller and transport are terminal exit 0. No automatic retry or cleanup is
claimed. This run therefore supports normal/error completion and close, not a
new actual timeout/UNKNOWN-custody acceptance. The earlier focused tests remain
separate evidence for those branches.

The runtime explicitly declares model factory/computation/close doubled, three
scripted model invocations and zero real provider calls. Local qualification
admission/publication is true; general runtime admission, service start, full
D3B, M1 and production readiness are false. The broker is a metadata socket
fixture with no real broker exchange acceptance.

The supplied records report communication completed within its 240-second
outer deadline; seed total is 10,069 ms. The parent confirmed the separate
Bridge observation `executionMs=43597`, or 43.597 seconds, and records that
measurement explicitly as overall Bridge operation time. It is not a separately
measured finite-child duration or a numeric duration field in these JSON records.
The source budget remains 35 + 60 + 15 = 110 < 120 seconds with live remaining
budget checks before seed and finite spawn.

## Preserved diagnostics

Finite stderr is 4,513 bytes and its hash matches the captured original bytes.
It contains the deliberate controlled-model-failure traceback, SQLite warnings
describing DELETE journal mode, and an import diagnostic for
`agent.secret_sources.command`. The success must retain these diagnostics.
They do not contradict this explicitly scripted finite acceptance. Real
provider/credential packaging and the supported SQLite/runtime policy need an
explicit disposition before a broader P2/provider-readiness claim; this review
does not assume that the missing command secret source is required or optional
for the eventual selected provider path.

## Roadmap wording and next slice

Suggested current status:

> P1 IN PROGRESS. R156A1's installed same-image native finite sub-deliverable is
> ACCEPTED on e641a500: fresh seed, one fixed finite child, normal/exact replay/
> new request/terminal application error and original ordered close. Model
> computation remains an explicit scripted fixture; real broker/provider,
> daily-use control, restart replay, full M1 and production acceptance are open.

Update the P1 table's "native acceptance open" text and the R156 source-only
section. Also replace the stale sentence saying that finite integration and
acceptance remain open. Keep the historical R153–R155 findings as historical
facts, and retain the unchanged L145 readiness-only target's actual scope.

The concrete next P1 gate is a separate positive invocation of the **existing
readiness-only sibling on this same 838-file installation and a fresh image**,
with its seed/readiness/original ordered-close evidence. R156 already proves the
six startup checks within the current finite entry, so this next gate targets
the other fixed operation. It requires neither repeated finite qualification
nor new runtime code. The remaining P1 criteria should then be mapped explicitly
to current-source evidence for sign-off.

Local-control implementation is P2 source work and may proceed in parallel:
reuse the existing control components for start, bounded submit, observe,
result/usage, original cancellation semantics and close through the accepted
owner path. Define one selected provider/model, a narrow tool set, and explicit
token/time/cost limits before a real provider experiment. Preserve the scripted
mode's distinct identity. The next real-provider acceptance must establish the
actual broker exchange and selected task/tool path. P2–P5 remain open; this one
lifecycle does not produce a measured delivery velocity or a new production date.
