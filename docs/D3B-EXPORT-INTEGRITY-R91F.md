# D3B exporter integrity integration — R91F

Base: 916f5290981f5cc4775c930fb4674d046cb3cc67 (committed G84E).
Branch: alaz/d3b-export-integrity-r91f.
Worktree: scratch/worktrees/d3b-export-integrity-r91f.
Status: scoped exporter integrity PASS; full Windows regression and source custody PASS.

## Scope and origin

The preceding G82C worktree remains a failed draft at e1bc877. Its blocked
projection edit is NOT replayed, implemented here, merged, or delegated.
Independent G84E work was already committed at916f529 when this task began.
This branch starts from that commit, without changing or executing its mount
or privilege code. Existing G84E current-source receipt checks pass here; this
is offline evidence verification, not a new native projection execution.

Read-only review of the independent P83C work found a confirmed exporter flaw
and an unfinished one-line repair. The fix and its two existing assertions are
credited to that QA lane. P83C's dirty worktree/index are not edited or committed.
This task reproduces the flaw in new owned temporary repositories, integrates
only the one-line correction, and adds custom-ref-prefix and environment tests.
Original P83C test bytes and hashes are retained in p83c-original-tests.py.txt
and test-provenance.json; the final test extends rather than weakens them.

## Defect and correction

The exporter used normal Git object reads. Replacement references can redirect
both a source blob and an entire commit while the manifest continues to name
the requested commit. The original exporter accepted substituted source content
in four real-Git cases: blob, commit, custom replacement-ref namespace, and an
empty GIT_NO_REPLACE_OBJECTS environment setting.

Every exporter Git call now uses `git --no-replace-objects -C ...`.
No replacement ref, repo configuration or history is removed/modified in the
user's repository. Replacement fixtures exist only in TemporaryDirectory-owned
repositories. Exported fixture content consists of inert comments and is never
executed. Git's official mechanism reference:
https://git-scm.com/docs/git-replace
https://git-scm.com/docs/git

This closes the observed replacement-ref ambiguity. It is not a complete hostile
Git-executable/environment/filesystem proof or permission to install a package.
Archive hashes still require independent expected-source trust.

## Before/after evidence

First run:3 product assertion failures and1 fixture Git error. The custom ref
prefix lacked its final slash and Git for Windows exited3221226505. The exact
output is retained. Only that fixture prefix was corrected; no product code or
assertion was changed before the second run.

Second pre-fix run:4/4 failures, each showing original-vs-exported source mismatch.
Then the one-line product-helper correction was applied. The same four tests
pass. Combined focused run:31/31 PASS =4 replacement tests +17 existing exporter
controls +10 existing G84E receipt/cleanup controls. These overlap the standard
suite; they are not additional native Linux acceptance cases.

## Original and current source candidates

The repaired exporter regenerated the original802fade candidate with exactly
57 files and the unchanged archive SHA256:
8c0bbad498ccc877edbce85af535dd0fcd68b2dbf21b72858487577942424451

It also exported the committed G84E916f529 source:58 files,519331 source bytes,
573440 archive bytes; SHA256:
8838d83b215f8a8f676c38b5f1e8d2ed395e39839afc35d070fcb7c2bec277f9

Both were independently compared against immutable Git objects with replacement
reads disabled, including recomputation of Git blob hashes. The independent
verifier is an unchanged snapshot from QA commit9a1b74f, SHA256
c39b46ec19f144a0476b3ce431408607c9120050f0cfdcb70ec0610197a456b8.
No archive was extracted or installed. The original clean candidate was NOT
corrupted by the defect; this is established by its exact byte/hash comparison.
Binary candidates stay in this worktree's ignored scratch/principal-install;
tracked reports contain inventory/source hashes only.

## Preserved boundaries and next work

The successful G84E primitive and its existing actual Linux evidence remain
unchanged. This task does NOT run it again, claim the old G82C draft is fixed,
start a WSL distro, activate legacy IPCv2, install dependencies, change a system
account, call a model, push, or advance main. The full Windows suite here is
ordinary development tests including offline native evidence review.

The substantive next runtime work remains a fixed trusted Gateway entrypoint,
durable session-state design and actual Hermes integration. G84E's private
tmpfs workspace is intentionally ephemeral. A clean-exit-only snapshot would
not establish crash durability or preserve uncertain in-flight effects; a host
writable directory must not simply be re-exposed to bypass socket isolation.
Provider dispatch needs its own live read-only Gateway authority and dummy
provider/broker-budget test; no ping proves those properties. No new persistence
or privileged implementation is delivered by R91F.

Evidence: evidence/d3b-export-integrity-r91f/.
Full regression command receipt9a89388f-c1e8-49d3-b5bd-5316b5021faa is pending at
this draft; final results are recorded only after terminal confirmation.


## Final regression and delivery

New standard Windows execution:2273 total /2268 PASS /5 SKIP /0 failures /0 errors, collected from unittest result objects.345 current source files were unchanged throughout.343 of344 pre-existing source files are untouched; the only change is the exporter one-line correction. The new file adds four real Git fixture tests. Focused31 is a subset, not additional native acceptance.

Code-only commit: `bfaa32b3d0d5df86178b5926343db5cf9b1fe8e2`. The following documentation/evidence checkpoint preserves identical runtime/test source bytes. The existing G84E implementation and historical actual Linux receipts are not altered or rerun. No claim that G82C is fixed.

No new Linux unit/native run this slice; ordinary Windows Git fixture coverage and independently verified archives only. Maincc7ceba and companion worktrees are preserved. Publication and main integration remain separate gates. The source-only candidate is not a runtime installation. Exact next: carry this small exporter fix into the active development line without replacing concurrent work, then implement durable-state handling and a fixed trusted Hermes entrypoint; fullD3B remains open.
