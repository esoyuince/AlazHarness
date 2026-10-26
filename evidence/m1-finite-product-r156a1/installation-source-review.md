# R156 install preparation / installer source review

## Verdict and scope

**No concrete pre-run blocker found in the reviewed installation phase.** The R156 renderer preserves the reviewed R154 one-shot, source-only installation lifecycle while binding it to new fixed R156 paths and actual candidate pins. The original installer creates an exclusive fresh tree, verifies all source/dependency bytes, publishes without replacement and leaves uncertain evidence in place. It does not run installed native/model code or perform mounts, services, downloads, overlays, retries, cleanup or repairs.

This was read-only source/AST/hash inspection. The reviewer did not execute the renderer, installer, operator, tests, WSL or any privileged action. Candidate-specific generated operator and transport review remains the parent's final check once actual candidate pins are available. The late acceptance/caller templates were not reviewed as part of this installation verdict.

## Sources checked

| Local file | SHA256 independently observed |
|---|---|
| `/workspace/scratch/288e2938ab4c/r154-runner/scripts/qa/r154a1_install_candidate.py` | `06755f6d866a30b208c80ce23dab30e99326077d0b632211b42d9f6dcac18a14` |
| `/workspace/scratch/288e2938ab4c/r156-acceptance/scripts/build_projected_candidate.py` | `7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b` |
| `/workspace/scratch/288e2938ab4c/r156-acceptance/scripts/install_projected_candidate.py` | `f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6` |
| `/workspace/scratch/288e2938ab4c/r156-acceptance/scripts/qa/r156a1_prepare.py` | `c41125d4fc9850de6a858c08882d26c8a32e0b6022c4905b55c9d7ab56cdef44` at first hash observation; acceptance-phase code was still being edited |

The first three hashes match the corresponding constants in `r156a1_prepare.py`. The separately pinned acceptance template also matched at inspection, but matching a hash is not a review of its late acceptance behavior. The original R154 embedded Linux transport SHA256 is `2ef978afd7667803459cbe4cfc1c030dcc1a2f305bf9ee272bd52a7181b5f44c`.

## Binding and renderer review

`r156a1_prepare.py:191–212` requires exact installation-binding fields and fixed native feature, builder/installer/interpreter pins, dependency root, and installation/acceptance paths. New paths are `/opt/alaz-r156a1-install-input` and `/opt/alaz-r156a1`; accepted dependencies remain `/opt/alaz-f126c1a6/dependencies`. The actual harness commit, manifest/archive SHA256 and source count come from candidate verification.

`verified_candidate(:254–282)` reads hash-pinned builder/installer/candidate bytes and calls only the reviewed installer's `prepare_bytes`. That verification is bounded source inspection; it does not call install/preflight/WSL. The native feature must remain d151 and the accepted dependency inventory must contain 1162 files. `prepare_install(:309–328)` renders only after this verification and marks the output explicitly prepared/not-run, not installed or accepted.

`render_install_operator(:215–251)` changes:

- The fixed input and destination paths.
- Harness commit, archive/manifest pins and exact source-file count.
- Reviewed builder pin and R156 report-kind labels.
- The concrete host repository/candidate paths and explanatory docstring.

It uses AST-selected spans and constants while preserving all other bytes. The embedded transport is rendered separately, then inserted as an ordinary string literal. Independent AST inspection found each old transport constant targeted by the installation renderer exactly once, including count 834. No incidental repeated literal is being changed. The P71C distro, native d151 feature, interpreter pin, dependency root, commands, root/namespace checks, timeouts and mutation sequence are unchanged.

`publish(:285–306)` writes only a fresh directory under the repository's `scratch/r156-preparation`, refuses aliases/existing output, uses exclusive file creation and readback, and makes no external application or lab call.

## Operator authority and exact effect boundary

R154 original lines 68–107 (preserved in the generated Linux transport except explicit literals) verify:

- Fixed P71C distro and dedicated lab marker; absence of the Windows mount.
- Linux x86_64, `/usr/bin/python3.12`, isolated/no-bytecode/no-optimization flags and the exact interpreter SHA256.
- Real/effective/saved UID/GID all zero and initial UID/GID maps.
- Root-owned non-writable ancestry and entirely absent input/destination paths.
- Exact source/manifest/archive/native/dependency bindings and bounded transport ZIP bytes.
- Exactly the four intended regular ZIP entries, stored encoding, member sizes and SHA256 values.

Transport lines 108–123 stage only the candidate manifest/archive and reviewed builder/installer into the fresh fixed input root, then invoke the exact installer once with `-I -B`, explicit approved pins and clean `PATH/LANG/HOME`. The transport contains no native entry, service, mount or provider invocation. Root privilege is used only for this dedicated lab filesystem installation phase.

Host operator `current_sources(:188–195)` binds its own rendered bytes, installer bytes and builder. `prepare(:220–256)` freezes bundle/intent/transport/runner. `apply(:259–301)` rechecks those exact bytes and original workspace HEAD before creating an exclusive `execution-start.json` and spawning the fixed WSL/root transport. Native feature and candidate commit are separate from the host workspace HEAD, which is intentionally observed at preparation and must remain unchanged at apply.

## Installer effects and source verification

`install_projected_candidate.py:246–343` verifies manifest/archive digests, exact harness/native identity, source metadata, regular-only archive inventory, native manifest equality, dependency inventory/digests and explicitly non-executed claims. The builder's `verify_archive(:322 onward)` validates path safety, archive revision, regular-file type, no links/sparse entries, metadata, sizes, per-file SHA256 and inventory completeness. It does not extract executable code into the host or call package managers.

Installer `preflight(:448–462)` verifies interpreter identity and reads the entire existing dependency tree through no-follow directory descriptors. `_tree(:182–231)` rejects links, hardlinks, extra/missing files or directories, case collisions, modified digests and size overruns. Trusted roots require root ownership and no group/other write permission.

`install(:483–546)` requires the root/initial-userns/fixed-interpreter actor. It then:

1. Requires absent destination, creates one random exclusive sibling staging directory, and opens its original descriptor.
2. Materializes source and accepted dependency bytes with exclusive/no-follow writes and fixed modes; reads back the complete tree.
3. Rechecks the original dependency tree and interpreter before publication.
4. Uses `renameat2(..., RENAME_NOREPLACE)` to publish the new destination.
5. Writes, rereads and atomically publishes the installation receipt only after the tree is fully verified and published.

Exceptions retain the staging/final path, including any uncertain pending/final receipt. There is no deletion or overlay fallback. The returned receipt says installed source only, with execution/readiness/finite/model claims false. `verify_installed(:549–569)` is a separate read-only exact-tree/receipt check and rejects extra pending files.

## Unknown outcomes / no replay

The Linux transport records `installerSpawnAttempted` before Popen. A timeout or exception without terminal observation becomes `INSTALLER_OUTCOME_UNKNOWN`, with `processMayBeRunning=True`; it never kills, retries or declares installation. It records the actual installer PID when available. A successful installer exit is insufficient by itself: exact candidate/native/interpreter/count/readback fields are checked before `INSTALLED_SOURCE_ONLY`.

Host `installation_terminal(:198–217)` preserves unknown from malformed transport output, unobserved installer terminal state, explicit unknown or a still-running installer. Host communicate timeout records UNKNOWN without kill/retry. Exclusive `execution-start.json` prevents replay of the same prepared attempt. A spawn or receipt-write exception outside normal receipt handling still leaves the start record and must be treated as unaccepted/unknown by the parent; absence of terminal.json is never permission to reapply. Different host attempt names cannot overlay the fixed Linux input/destination because both must remain absent.

The installed receipt is filesystem/source evidence, not native acceptance. Later acceptance-source preparation must bind the actual receipt bytes and installed candidate, and its target must verify those installed bytes again. This review makes no claim that the new candidate has already been installed or accepted.

## Final concrete pre-run checks retained for parent

The final generated operator/transport must contain the actual reviewed candidate commit, archive/manifest hashes and source-file count, and its runner SHA must be passed exactly. Candidate ZIP must fit the inherited 24 MiB bound (otherwise preparation refuses before the root call). Freeze the current preparation file hash after acceptance-phase edits if it is included in a review record. Observe any launched operation to its real terminal receipt; an unavailable/missing/timeout receipt is not a retry grant.
