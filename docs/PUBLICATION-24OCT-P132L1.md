# Reviewed development publication - 24 October 2026 / P132L1

The user approved branch publication, exact-SHA CI verification, and a
history-preserving main fast-forward before continuing runtime integration.
This is a development baseline, NOT a release, deployment or M1/M2 acceptance.

## Fixed starting range

Old remote main: `cc7ceba8f850da7652a647e984cbae2c45c8fdea`.
Reviewed code head: `d0418ad0fdde8e8faa04916e6b28c2e6a8857c02`.
164 commits are ahead, no main-side divergence. The pending range includes
prepared Linux confinement, native caller-owned storage/admission/retirement,
and canonical API publication; it is not only the last adapter patch.
Pending file/commit listings and object hashes remain in the evidence directory.

## Publication review and preserved scope

All164 pending commit trees,5365 unique historical paths,3248 reachable new
blob versions and164 commit objects were reviewed (92795880 bytes). No configured
credential pattern, forbidden private path, unreviewed binary/large object or
unsupported mode was found. This bounded pattern scan is not proof every
conceivable secret is absent. Source pins, gitlinks, submodule config and root
license are unchanged. Ten copied upstream payloads were reproduced from their
pinned vendor sources including retained licenses. The legacy dirty root tree
and installed vendor are separately fingerprinted and not staged.

The584 source/config/test hashes and10 patch hashes match the actual completed
J131D6 full run:3395total,3372PASS,23SKIP,zero errors/failures,exit0. Publication
adds only documentation/evidence; no new full/native/runtime experiment is inferred.
Current native5ff88189 remains a staged patch, not installedeb75627. Programmatic
API admission is accepted, but complete finite agent execution, same-owner harness
publication integration, active isolation/HTTP and model accounting remain OPEN.

## Remote write sequence

Push ONLY alaz/d3b-principal-launch-21oct after the local static gate. Check GitHub
alaz/local-ci for its exact SHA. Re-read remote main; require reviewed ancestry
and use non-forced fast-forward. Preserve every commit, branch/worktree and source
lock; no squash, force-push, global Git/CI configuration, fork-main or deployment.
Record actual results separately; a local PASS does not substitute for remoteCI.
After main publication, continue on a short feature branch from accepted main.
At this document's preparation push/main/remoteCI are not yet complete.

## First pushed CI outcome and bounded portability repair

Branch ea7b48257ae741c81ff385bac596ceb884d02caf was pushed and verified. Its
exact-SHA alaz/local-ci FAILED: full3395,33 failure assertions,8errors,5Linuxskips.
The container did not time out or run out of memory. Main was NOT advanced.
The raw public status and sanitized failing-test log sections are preserved.

Three portability assumptions were corrected without altering runtime code:
(1) Positive layout unit fixtures used root UID/GID0 inside CI, which production
correctly rejects. Only root-run test ownership metadata is now mapped to the
explicit nonroot fixture identity; actual type/mode/device/links/descriptor logic
and production zero-ID refusal remain unchanged. NonrootLinux keeps native IDs.
(2) One historical C# probe was recorded with229CRLF lines, but Linux checkout
usedLF. A single-path Git attribute pinsCRLF for exact historical raw bytes;
content, recorded hashes, and production source stay unchanged.
(3) An exporter test assumed empty GIT_NO_REPLACE_OBJECTS enabled replacement refs
on every Git build. It now proves the actual replacement while the variable is
absent, then verifies the same original-byte export with the variable empty.
No assertion about the exporter or its security behavior was removed.

Three old test/helper versions are archived by exact name and hash against the
accepted source manifest. Historical native/kernel results keep their original
bytes and scope; no expected digest or old outcome is rewritten. Six added tests
cover owner-ID mapping, foreign owner/mode refusals, nonroot identity, original
root refusal, exact C# bytes and historical-generation fail-closed behavior.
The existing71selected Windows methods pass; a new complete standard run is
recorded separately. Remote success is still required before main.

No CI service, executor limits, image, permissions or policy were changed. Server
CI artifacts were read via its existing owner gitmirror only; no server writes.

## Repair local acceptance

FullWindows3401=3378PASS/23SKIP/0ERROR/0FAIL, exit0.586source/config/test hashes and10patches fixed; same23Windows skips.71focused methods PASS. The runtime/native implementation and source locks are unchanged. This local result does not waive the required next exact-SHA remote CI.
