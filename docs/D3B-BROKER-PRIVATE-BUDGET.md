# D3B - Broker-private durable budget authority (scoped acceptance)

**Branch:** alaz/d3b-budget-c84f, 19 October 2026.
**Status:** COMPONENT PASS; overall D3B NOT ACCEPTED.

## Problem and trust boundary

The earlier Gateway-native SQLite ledger is useful for canonical claims,
but a compromised or misconfigured Gateway may change its own rows. Those rows
cannot be the sole independent spending or single-use authority.

This opt-in slice adds a *broker-owned* durable budget DB in a separate,
trusted-host-provisioned directory. A trusted operator initializes the budget
exactly once; the broker refuses absent, moved, relinked, inconsistent or
unconfirmed authority instead of creating/resetting it. No running broker
ever calls the bootstrap initializer.

The broker verifies the original grant, policy/scope/route and live Gateway
claim, then commits its own reservation BEFORE any physical HTTP send.
Reservations never automatically refund after disconnect, HTTP error,
unknown commit acknowledgment, broker restart or Gateway ledger rewrite.
Tickets are single use across broker lifetimes. Every reservation consumes
the policy's declared full per-attempt token/cost exposure. Actual usage
invoices and tokenization are NOT verified.

The private authority is protected by trusted-host filesystem placement
and existing opt-in guards, not by a new OS identity. The same host UID,
host administrator, filesystem mount ownership, broad IPC isolation and
provider-side billing remain distinct risks. This is NOT a proof that a
malicious host process cannot rewrite the private database.

## Code and explicit opt-in

- `packages/claw-hermes/broker_budget.py`: validated strict settings,
  host-side one-time provisioning, SQLite DELETE/FULL transactions,
  hash-chained reservations, immutable policy binding, per-lifetime replay
  detection carried across restarts, response observations and fail-closed
  private storage uncertainty.
- `packages/claw-hermes/provider_egress.py`: optional
  `BrokerConfig.budget_authority`; existing unenabled config remains
  unchanged. Private policy must match the public execution fingerprint.
- `packages/claw-hermes/provider_broker.py`: private budget opened before
  starting broker IPC; reserve-before-send; persist an observation after
  provider HTTP; bounded, non-sensitive refusal codes only.
- `scripts/initialize_broker_budget.py`: trusted explicit initialization
  only. No automatic retry, reset, refund, credentials or provider calls.
- `scripts/qa/native_budget_gateway.py` and
  `scripts/qa/native_budget_ext4.py`: opt-in real Hermes Gateway +
  original aiohttp broker, scripted local HTTP provider, verified native
  Linux code snapshot, existing combined netns/Landlock protections.

A supported `max_completion_tokens` ceiling is mutually exclusive with
`max_tokens` and subject to the same policy maximum. The known provider
fields align with the already validated Gateway request contract, never
permit multiple completions, and reject unknown spending knobs. Serialized
input bytes now have a strict conservative cap rather than a four-bytes-
per-token approximation. Neither method is a tokenizer or invoice guarantee.

## Native acceptance (scripted origin only)

All four accepted native runs used the **same 188-source-file snapshot**,
which was SHA-256 verified before and after native execution. The
real Hermes Gateway ran in the same PID behind the combined
network-namespace and Landlock launcher. Only test-owned Linux directories,
Unix sockets, fixtures and local loopback HTTP were used. No external model,
paid provider, user profile, production Gateway, autonomous memory promotion,
or global broker installation was used.

| Scenario | Run ID | Persisted broker reservations | Broker HTTP responses | Result |
|---|---|---:|---:|---|
| Normal | bgta19-normal4 | 4 | 4 | PASS |
| Token-exposure limit | bgta19-limit1 | 3 | 3 | PASS |
| Candidate disconnect | bgta19-disconnect1 | 4 | 3 | PASS |
| Review revoked | bgta19-revoke1 | 3 | 3 | PASS |

The difference of 4 reservations / 3 responses in the disconnect case
is deliberate: a lost response must not regain exposure capacity.
The offline native transport tests additionally exercised actual Linux
AF_UNIX IPC plus local HTTP: Gateway-owned ledger reset, broker restart,
lost commit ACK, HTTP 500 without refund, and missing private authority.

First failures remain preserved (NOT counted as accepted runs):

- `native-bgta19-normal1.json`: direct WSL v9fs + Landlock source-open
  denial. This did not prove or test private-budget acceptance.
- `gateway-bgta19-normal2.json`: native ext4 snapshot worked, but first
  request was rejected before physical HTTP.
- `gateway-bgta19-normal3.json`: specific
  `broker_private_budget_payload` rejection identified the mismatch
  between broker allowlist and the existing Gateway payload vocabulary.
  Bounded fields and output ceiling were reconciled before the final
  successful native runs.

## Regressions and source custody

- Windows Node **v24.19.0**: full unittest discovery **1980 tests, exit 0**,
  **5 Linux-only tests skipped**. Full output:
  `evidence/d3b-budget-c84f/full-standard-windows.txt`.
- Native Linux prepared interpreter: **42 broker-focused tests, exit 0,
  skip 0**, including all five real Linux IPC/HTTP cases and three
  current-source acceptance checks. Output:
  `evidence/d3b-budget-c84f/linux-budget-unit-final.txt`.
- `python -B scripts/ci_check.py`: exit 0, static PASS,
  **1980** discovered. Not a runtime/security certificate.
- A diagnostic earlier full Linux run (1947 discovered) is retained as
  `full-standard-linux.txt`, explicitly **FAIL**: it used Node 26 instead
  of the required Node 24 for a historical wire test, and a historical
  D2B2 QA test compared an immutable old receipt against new branch bytes.
  The historical test now validates its exact original Git commit
  `35099bda644ebe042a4fab40649604fb837bb367`, and the new D3B
  acceptance test separately SHA-verifies *current* sources. The full
  Linux suite has not been rerun with the correct Node 24 toolchain.
- `git diff --check`: no whitespace defects before publication.

All final snapshot manifests and receipts reside under
`evidence/d3b-budget-c84f/`. Static QA checks current file SHA against
each of the four final snapshots. The historical D2B2 source commit remains
immutable and prior test failures are not rewritten into passing evidence.

## What is NOT accepted

- The separately accepted IPC pathname/abstract socket projection from
  `alaz/d3b-ipc-a731` has NOT been integrated into this budget branch.
- A different OS UID/PID or a fully separate security principal for Gateway
  and private broker has NOT been demonstrated.
- A hostile same-UID process with host-level filesystem reachability has
  not been excluded from modifying private budget storage.
- Real provider pricing, model token accounting, post-charge invoice
  reconciliation, production default activation, and paid model calls
  remain untested/unenabled.
- The full D3B end-to-end product acceptance and autonomous learning/
  memory changes remain OPEN.

## Reproduction and continuation

From the trusted local working copy and explicitly prepared test Linux
runtime (with a **fresh** run-id on every invocation):

```text
wsl.exe -d Ubuntu -- python3 -B /mnt/c/Antigravity/AlazHarness/scratch/worktrees/d3b-budget-c84f/scripts/qa/native_budget_ext4.py --run-id <fresh-run-id> --scenario normal
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

Use the native Linux prepared Python with aiohttp for Linux socket tests.
Before replaying an interrupted native run, read its existing receipt,
output and process state instead of blindly resending. Do not share
broker bootstrap secrets, use a real model, enable auto memory, or merge
into main as part of a diagnostic rerun.

**Next:** publish this scope under its own branch with exact source
and CI evidence; then create a NEW integration worktree combining accepted
IPC restrictions and this broker-private budget authority, rerun real
Gateway 4/4 plus negative mount/socket/kernel tests, and only then consider
a higher D3B acceptance decision.
