# HYB-005A — independent host-gate QA72d4

Status: PLANNED; primary6f88 owns production implementation. This report authorizes
no production profile mutation, extra scheduler, paid inference or broad replay.
The previous main independent604 run is evidence/main-integration-qa and is not
HYB005 acceptance. Current native runtime work is separate.

## Required negative boundaries

A newly issued one-use request document must bind immutable body, key, profile,
principal/scope, endpoint and runtime identity. The caller cannot supply an
arbitrary local path, authenticated transport or trust context to the network
handler. JSON fields and token text must have bounded strict types. Malformed or
contradictory evidence refuses without emitting a new native admission/model call.

The native SessionDB owner must persist the consumed request before the first
forwarding byte. Lost acceptance ACK, exception, caller cancellation and process
restart must not re-enable consumption. If a claim was consumed before dispatch
and no work exists, retain explicit unverified/unknown instead of automatic retry.

Legacy/unissued keys, prior unknown work and audit-closed requests must not bypass
this gate, even if the native replay row is pruned. Same key/different content is
a conflict. Closed-audit lookup cannot assume its old reservation row remains.
A fresh key for a different explicitly authorized operation is not a retry of an
ambiguous operation by merely renaming it. No inference from a missing key.

## Plugin and protocol review

The added native Gateway route must run existing authentication BEFORE revealing
state or issuing/consuming permission. Unsupported profile/grant/session/model
routing must be explicitly rejected. An in-process native plugin bridge is not
proof that upstream raw POST /v1/runs is globally gated. Direct raw bypass, OS
isolation, tool permissions and model/token/currency budgets remain separate.

In-process concurrency, independent clients and restart scenarios need separate
claims: sequential duplicate HTTP is not concurrency proof; a single SQLite
commit does not make subsequent HTTP atomic. An at-most-once dispatch permit
is a deliberate availability tradeoff, not exactly-once external execution.

## Evidence to add after implementation

Real route identity/auth/negative HTTP and selected-body mutation checks; one
native success through the actual Agent/read_file chain; concurrent consume and
lost-ACK/reopen; existing closed and unknown native profiles without mutation;
strict readonly observer behavior and unchanged historical sources. Synthetic
SQLite and scripted fake transport tests are labeled as such, not native Gateway.
Actual request budget = dispatch count only unless all provider calls are covered.
