# AlazHarness - status

## D3B-WORK-HEALTH-W115B6 - IN PROGRESS

Branch alaz/d3b-work-health-w115b6; base9717704. Add a bounded read-only work-state
consistency policy: idle, owned busy, unobservable transition, recovery-required.
Use native admission/worker/replay/response identities and a separately captured
trusted owner inventory, not pending counts or model assertions. No native
scheduler replacement, no caller-store mutation or connection reopen. The policy
alone does not prove filesystem/lease integrity or process liveness, and never
authorizes dispatch, retry, close or HTTP. Existing startup/quiescent HTTP remains
unchanged; live producer adapter/full isolation is a later acceptance boundary.

Own work is pure policy + native SQL snapshot reader + focused/unit and genuine
native owned-temp Windows tests; no WSL/root/cleanup query, listener, provider or
source-pin activation. Prior blocked cleanup and L113 refinement NOT retried.
454 baseline source files captured. Next implement exact cross-store matching,
observe current native schemas using fixed featurecc16c10, then complete
regression/static and clean ancestry-compatible delivery. Main/push unchanged.


### Policy complete; actual native probe in progress

43 pure policy methods PASS. Two additive modules select idle/owned busy versus
transition/unobservable/recovery-required, exact cross-store identities, fresh
producer revision, and sticky uncertainty. Reader uses existing native handles
and native mutexes; it is not connected to HTTP or real producer capture yet.
Request e115b601-49bc-47a3-b31a-000000000010 is running real Windows/native
metadata probes against279 immutable exported files. Source files frozen until
terminal; no WSL/root query or blocked cleanup attempt.


### Complementary ownership and one selected policy

Concurrent B115W6 owns the pure work-health policy. Select its current module
byte-for-byte; own broader policy draft/43 tests are preserved as historical
candidate text, not a second installed policy. W115B6 owns native bounded reader
and independent real-native data mapping. Shared policy has single-active-owner
limit and rejects delegated workers pending their own acceptance. Reader adds no
scheduler or HTTP grant. Native00122/23: test forgot explicit response commit;
reader correctly refused open transaction. Original failure retained; next probe
uses the selected policy and explicit native commit, not weaker transaction rules.
