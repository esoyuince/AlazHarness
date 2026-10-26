# R156 native finite qualification source review

## Scope and verdict

Read-only review of harness commit `4823ebbca5f039aee1e9a4a209e40a48c015044a`, the exact native `d1516731308de8e87130dc68124e69aad35d6911` source snapshots, and the in-progress R156 runtime/protocol. No native execution, WSL invocation, tests, model/provider calls, primary-repository edits, staging, or lifecycle mutations were performed by this reviewer.

The source supports the proposed **bounded scripted-model qualification**: retain the native owner, runner, authority, API admission, worker, SQLite settlement, replay and retirement, while replacing only the `run_agent.AIAgent` factory/computation/close object. It does not establish real-model, HTTP-service, signed broker exchange, finite CLI/unattended policy, or projected-kernel acceptance. Actual installed projected execution is still required to qualify import/filesystem/thread/timing compatibility.

No API/result/retirement contract blocker was found in the reviewed runtime. The added cached-agent reuse path was checked independently against exact native reset/fallback/message-count code, because the prior l139c6 source executes one computation plus replay rather than all three computations in one session.

## Exact sources and provenance

Harness snapshot root: `/workspace/scratch/288e2938ab4c/r156-source/tree`.

Native snapshot root: `/workspace/scratch/288e2938ab4c/r156-source/native`.

Parent verified export manifests against the exact commits; this reviewer independently computed the following native SHA256 hashes and checked equality against **both** pinned finite and retained manifests.

| Native path | SHA256 |
|---|---|
| `gateway/session_api_turn.py` | `feb785e12a153024b929efdf850ac69572342def6ddf3790d96473f4b140a63f` |
| `gateway/session_results.py` | `e62666693967073b90e81e9dc841056ac4d747bc64e52de1605ea9975b1e614e` |
| `gateway/session_finite.py` | `65b9ddd09dfabf23cc96efc2cffa32d8d5c1ce808589a2271e1fc8b6e7ec6db4` |
| `gateway/session_execution.py` | `6d89e284dbbac756d0e8acc97b7468c511d164ba8ef6f8a694e3a69582f8d660` |
| `gateway/session_ingress.py` | `72c99c8936e3ba3bcb962f94779a8855aa35f929bbe360990aff84fec6efcc6c` |
| `gateway/session_settlement_recovery.py` | `382e5a753a9a61fda756e7a1c9fe21a067a955cc81c31359e5a1bcd407766b36` |
| `gateway/run_borrowed_cleanup.py` | `8ca5b7a76534a45de883a138c38bc1ac6c2aac27984e6d910f29cc68adb3da1b` |
| `gateway/run_turn_runner.py` | `b0b5ea1f583a350695108c47f3f8a2c7201700d8a2dde1e56e0a73858979802c` |
| `gateway/run_agent_cache.py` | `9f72a451903e0dec87c45e86a48641d73f05f25c94478c938faac6a286841a30` |
| `gateway/run_config_loaders.py` | `732a1a5c498d755c06c7d89bff1559d6ee11663c7841aa4c45101ecf6ee1a34a` |

For `gateway/run.py`, only the exact `_init_cached_agent_for_turn` excerpt at source lines 4189–4209 was supplied/read. Its export records full-file SHA256 `a58cb57ce253c00258e77928eea16199d5b2fe58468a8cfa6a4d46fdb296703a`, matching the pinned manifest; this is not a claim to have read or independently hashed that entire file.

| Harness path | SHA256 |
|---|---|
| `packages/claw-hermes/gateway_prepared_consumer.py` | `d5ce29480570d140363deda7fe8740ad7ddb1f5e579d0befbd790ca68a0f5cc6` |
| `packages/claw-hermes/gateway_consumer_api.py` | `e686828344d4c554416348730a226cc586ffaa635d451ff55d3b1734c6ad7168` |
| `packages/claw-hermes/gateway_consumer_admission.py` | `7f42c035f641c22f85b5c7fe04b5bd8011b1d529f61720ee88281722affd06da` |
| `scripts/qa/l139c6_linux_owner_finite.py` | `df36866a52c75363f59300e05292f93576911b55281811e6bcf14a5c43246d38` |
| `scripts/qa/f135c6_native_finite_close.py` | `48b95cabb5a788998113d370fef07a5b7e3c2ccf1c955210207d9de298943d09` |
| `config/finite-close-f135c6-sources.json` | `30095cdda6fadecaf332b5a5dbf8c2f3e43ad550d8dfd08adfe5469f26a324f4` |
| `config/retained-profile-r140c6-sources.json` | `0af0852042217675b8398e2f64c7e509935726b992d91b4bdf4080512b35f8e4` |

The finite manifest pins 755 native Python sources; retained pins 756. Both name the same d151 native feature. Their purpose fields explicitly exclude model/provider/HTTP/kernel acceptance. `gateway_prepared_consumer.py:33–77` hashes all selected source files and rejects imported native Python outside the exact manifest. Retained finite preparation selects the retained closure at `:159–165`.

## Native API and settlement contract

### Admission and result

`gateway/session_api_turn.py` exposes:

```python
async def run_api_turn(adapter, *, approval_notify_callback=None,
                       approval_session_key=None, **kwargs)
```

The fixed runtime supplies `session_id`, `request_id`, `user_message`, and `conversation_history=[]`. API admission creates payload text and `api_turn_v1` history/settings, with fixed principal `api`. Logical session canonicalization and admission-open checks remain native. `_admit_api_payload` tries terminal replay before binding/creating new work. `_one_target` rejects reuse of a principal/API request ID against another target. `observe_api_turn` observes the durable row before registering a waiter, shields the native waiter, and returns the saved `(result, usage)` tuple. `_settled_api_result` reads the native saved result; it is not the model's raw dictionary.

The current SQL readback correctly filters `principal_id='api' AND request_id=?`, requires exactly one row, and checks terminal status, expected outcome, the current owner epoch and target session. It compares the API tuple to `(saved['result'], saved['usage'])` from the original `admission_result`. Exact replay must preserve the admission ID, saved/API digests and computation count. New request IDs must produce separate admissions. Normal/new fixed answers are verified after native result processing.

`gateway/session_results.py:49–64` promotes failed/error flags to outcome `failed`, sets `failed=True` and `completed=False`, compacts and redacts the result. `finish_result(:67–89)` rechecks epoch/generation and returns an already committed result without rewriting it; otherwise it calls original `settle_session_input`. `admission_result(:92–99)` reads only terminal records.

### Worker and owner settlement

Exact native entry:

```python
async def execute_finite_admission(authority, ref, row)
def commit_and_publish(authority, live, ref, row, response, outcome,
                       captured, settlement)
```

The finite wrapper delegates to original `execute_admission` under the native scopes. Ingress (`session_ingress.py:189–285`) restores the API event, obtains native API execution context, calls `authority.runner._handle_message`, captures result/usage, and hands the completion to the authority. A missing executed result becomes an API failure, not a completed apology. `run_turn_runner.py:1107–1121` writes the actual worker result into the native execution context.

`session_settlement_recovery.py:86–115` runs `prepare_result -> finish_result -> publication -> media release` on the worker side. Storage encoding/writes remain outside the event-stream lock. `settle_with_retry(:123–140)` uses original tracked mutation tasks and shielded worker settlement. The qualification must never call these lower-level functions directly to synthesize successful completion.

### Meaning of “finite”

`execute_finite_admission` derives its finite context from `row['payload'].get('finite', False)`. Ordinary `run_api_turn` does not add `finite=True`. The proposed entry is bounded scripted API work using the finite-close generation; this does not prove native finite CLI policy or unattended approval semantics. The protocol's explicit scripted qualification scope is compatible with this distinction.

## Model seam and configuration

The sanctioned prior l139c6 source (`:83–115`) patches only `run_agent.AIAgent` while retaining original `run_api_turn`, authority scheduling, physical `run_sync`, settlement, stores and retirement. Its source explicitly says actual Linux owner behavior is exercised but confinement/HTTP is not. f135c6 is an earlier Windows fixture and does not establish native kernel acceptance.

Native `GatewaySessionAgentMixin._build_fresh_agent`, `session_execution.py:151–186`, calls `ctx.AIAgent(...)` with original state DB from `runner._session_db`, model/runtime arguments, toolset selections and context. The current fixture supplies the prior fields used by callbacks/usage/close and asserts computation occurs away from the main thread against that same DB. `run_turn_runner.py:382–460` assigns callbacks before observer wiring, so absent constructor-time callback attributes in the fixture are not a discovered defect. `:886–951` calls the fixture and captures per-turn usage; real approval bookkeeping is still registered/unregistered around it.

Cached reuse is compatible with the fixture's ordinary mutable Python instance. `run.py:4189–4209` assigns activity markers and API counters, with an optional guarded flush-index reset. `run_config_loaders.py:557–585` reads fallback attributes through defaults and assigns the new chain/model/index; no absent mandatory fixture method is called. Its refresh code returns None when config.yaml is absent (`:542–545`). `run_agent_cache.py:600–632` rebaselines the cache message count after the native turn, so the next ordinary turn does not falsely look like an external transcript mutation. These inspections remove the pending cached-reuse source concern; actual execution is still unverified here.

Projected exec uses exact clean environment fields (`gateway_retained_launch.py:75–83,152–199`): PATH/LANG, HOME and HERMES_HOME at the retained projected profile, private TMPDIR/TMP/TEMP, and bounded transfer records. The runtime adds only an inert OpenAI provider/key/base URL and disabled agent timeout/warning. Those values resolve factory arguments but grant no network use. The fixture prevents the real model constructor/computation from running.

`session_ingress.py:288–309` takes the single-profile borrowed execution scope when `multiplex_profiles=False` and no native provenance home exists. It therefore does not take the explicit external secret hydration branch in that case. Prior l139c6 asserts no config.yaml exists before or after execution; this is prior source evidence, not an observation of the new confined target.

## Smallest viable sequence

1. Validate fixed projected transfer/live identity and confinement before any lease or store access; create no arbitrary command/prompt/provider settings from input.
2. Reserve original profile lease. Construct original `NativeStoreStartup` with state/response/retained expectations and prepared layout; start it and retain original three store connections and current epoch.
3. On one original loop, prepare with `GatewayConfig(multiplex_profiles=False, write_sessions_json=False)` and explicit `PlatformConfig(extra={'key': inert, 'model_name': inert})`; select local admission + canonical API + finite close, with retained closure selected by original owner receipt.
4. Publish original adapter, activate original admission, and replace only the model factory with the declared finite fixture.
5. Run normal, exact replay, new request, controlled model error through original `run_api_turn`, awaiting original authority session/mutation tasks without cancellation. Read original terminal rows and saved results. Require computations 1,1,2,3 and three unique admissions.
6. Seal admission with `begin_drain`; await original `retire_idle_runtime`; call original `retire_idle_api_sessions`; `finish_drain`; await `detach`. Require unchanged connection identities, unchanged SQL total_changes across retirement, zero state registry references, and all fixture instances closed.
7. Confirm no owned/live loop tasks, retire the idle default executor while the stores/lease are held, close original owner, verify all three physical SQLite handles are closed, then release the caller lease. Emit validated result only after these checks.
8. Any unknown/timeout keeps strong original references and does not run test-fixture cleanup, cancel workers, force-close stores, prune registries or retry admission. The external supervisor's observation of the original child determines completion.

Native `run_borrowed_cleanup.py:13–50,84–145` verifies no physical worker threads, idle session obligations, API-owned agent caches and no unqualified memory manager. It shields off-loop agent close and releases original maps only after repeated identity checks. Partial effects become `ADMISSION_UNKNOWN`. Current ordering matches these requirements and l139c6 `:111–124`.

## Projection and dependency requirements

- Exact installed native closure plus harness entry/helper files; readonly Python 3.12 executable, stdlib and shared-library roots; the accepted dependency inventory. `linux-prepared-dependencies-l125p1.json` describes a CPython 3.12 x86_64 import prerequisite, explicitly not a complete agent/plugin distribution: 30 runtime packages, plus pip as installer tooling. Runtime packages include aiohttp/aiohappyeyeballs/aiosignal, anyio, attrs, certifi, charset-normalizer, click, concurrent-log-handler, frozenlist, h11/httpcore/httpx, idna, jiter, markdown-it-py/mdurl, multidict, portalocker, propcache, psutil, Pygments, python-dotenv, requests, rich, ruamel.yaml/ruamel.yaml.clib, typing_extensions, urllib3 and yarl. The actual installed accepted inventory, not just wheel metadata, remains the acceptance input.
- Writable original retained ext4 profile and private tmpfs scratch; original cold preopen helpers are the only allowed subprocesses. Threads/executors and SQLite must function inside the projected cgroup/resource limits. No new provider or tool execution dependency is authorized by the scripted model seam.
- `urllib3.util.connection._has_ipv6` performs an import-time bind probe. Parent confirmed this is reachable under the projected socket policy. Current runtime qualifies only the exact pinned probe, raises EACCES before bind, and verifies its socket closed/HAS_IPV6=False. It is a denial exception in audit accounting, not permission to bind. Count may be zero if import already occurred, otherwise one.
- Projection pins and bind-mounts the existing broker socket inode (`gateway_projection.py:201–217`) and checks principal identity. The current fixture needs no socket exchange. R155's broker (`r155a1_linux_accept.py:392–409`) is a metadata socket holder with zero listeners/providers. Signed provider-broker `ready()`/`send()` (`provider_broker.py:154–164`) are separate contracts and are not exercised here.

## Review observations and unknowns

1. **Reported improvement resolved:** original runtime checked `attempt.denied` only before drain. Parent added and reviewer verified audit/probe rechecks before owner close and before caller lease release (current runtime lines 300–301 and 314–315). A swallowed forbidden attempt during retirement cannot now yield successful completion through that gap.
2. **Cached model reuse source check completed:** exact native reset/fallback/message-count code is compatible with the declared mutable fixture as described above. No missing fixture field/method blocker was found.
3. Exact confined import/config/tool-registry compatibility, worker availability, deadline sufficiency and all normal/replay/new/error outcomes have **not** been executed by this reviewer. Source review cannot replace that acceptance.
4. Model exception result shape is native failure/`completed=False`; it is deliberately not promised to equal a particular raw RuntimeError string. Timeout/unknown execution is not an accepted application-error case.
5. Native “finite” CLI/unattended context, general prompts, real tools/providers, HTTP listener, signed broker exchange, restart replay and full D3B remain outside this slice.

Last local runtime hash observed during final review: `e4dd1f8e02f895cae2a770e7f32cab768ef9ba6f14616d9a5441c29f09b8492a`. This implementation was actively edited by the parent during review; immutable accepted build receipts must identify the eventual candidate separately.

## Bridge receipt status

Own inventory lane session: `ed508f80-d71d-4953-97e4-47fde3c57327`.

Completed read batch: `5b6a1156-1905-43f1-a7cd-9b83aaab0140` (harness consumer/QA source, hashes above).

Read-only request `eb80d156-e48b-4707-83bf-33f09a196dd2` had a call aborted after 794.4 seconds. A later receipt query returned `Native request is unavailable`, structured `INVALID_ARGUMENT`. Its terminal execution state therefore remains unobservable. It was never replayed. All subsequent review used parent's immutable local source exports.
