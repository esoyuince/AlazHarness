# AlazHarness - status

## D3B-RESPONSE-PREFLIGHT-R113Q8 - IN PROGRESS

Branch alaz/d3b-response-preflight-r113q8; worktree scratch/worktrees/d3b-response-preflight-r113q8; basea3951d7. Add bounded read-only prepared response_store.db verification before native migration/settlement/eviction. Reuse existing preopen/profile/mount primitives, not another startup owner. Preserve default two-store path and frozen native patch series. No listener, work/model/provider activation, source-lock/vendor install, root/mount/CI/main/push changes.

434 baseline source/config/test files captured. Trusted expectations must be supplied by separate owned provisioning, never learned from suspect candidate. Exact schema/current feature pin, file identity, normal SQLite locks, no sidecar recovery, reject pending response identity or over-limit constructor evictions. First implement/test narrow verifier, then integrate only after same-path evidence; do not label a standalone check full three-store startup. Prior complete handoff archived docs/status-history/r113q8-parent.md. No pending native job.


### Complementary API contract fixed
Concurrent L113F6 owns response live/close + optional existing A109 integration, no duplicate startup here. This branch owns packages/claw-hermes/gateway_response_preopen.py and scripts/run_response_preopen.py.
Public type PreparedResponseExpectation(native_feature, schema_sha256, response_identity, max_size=100, max_identities=1000); native_feature=cc16c10b16a0ca8d80b23fd9be3f0e59ee605075, schema_sha256=c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4. These defaults are the ONLY accepted constructor bounds; no dynamic policy.
Public verify_response_preopen(held, expected_mount, expected, canonical_expected, *, timeout_seconds=12): metadata-only parent checks existing native lease/mount + third-file mount/identity, fixed separate worker reads normal mode=ro. canonical_expected is existing live.PreparedStoreExpectation; third inode must be distinct and same device. Output state COLD_RESPONSE_PREFLIGHT_VERIFIED, expected feature/schema/identity/limits and explicit no-write/no-constructor/no-admission flags. Parent retains lease; worker never touches existing caller connections. Expose verify_response_connection(conn, expected) for same already-open RO helper checks only; it must not configure/close a live native handle.
Reject sidecars, wrong schema/identity, readonly policy mismatch, any unsettled response identity and constructor eviction pressure before opening native constructors. Cross-store terminal equivalence is NOT inferred. Pure observation, no creation/repair, no second native startup owner. Schema freshly measured from actual pinned ResponseStore; first discovery failed before creation because the isolated Windows environment omitted USERPROFILE, fixed by owned temp HOME/USERPROFILE, raw failure retained.


### Response preflight native run in progress

44 focused real-SQLite/parent-contract tests PASS Windows (query tests real SQLite; parent process/lease boundaries doubled). Budget fixture initially below hook threshold; corrected to100 valid rows, product budget not changed, first failure retained. Actual native Linux request b113df60-804f-426c-a07f-12405aa10013 running: fresh native three files, real ProfileLease, normal separate RO helper, refusal/no-write cases and interprocess SQLite lock controls. No root/mount/HTTP or A109 integration claimed. Product API now implemented as declared; freeze all current sources until result.
