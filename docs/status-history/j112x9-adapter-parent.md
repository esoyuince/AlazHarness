# AlazHarness - status

## D3B-API-BORROW-B112X9 - SCOPED NATIVE PATCH PASS; NOT ACTIVATED

Branch alaz/d3b-api-borrow-b112x9; base31abe58. Native feature cc16c10b16a0ca8d80b23fd9be3f0e59ee605075 descends from complementary response commit e19a945342c94138c685ac919b208d558ddcc53a. Installed vendor main/source lock/gitlink unchanged. One API adapter seam plus one ResponseStore canonical-state seam, no duplicate runtime.

BorrowedAPIStores binds real three stores once, exact home/process/thread/connections. APIServerAdapter constructor/selection reuses those objects with no extra SQLite opens; borrowed disconnect never closes caller stores or rolls back their transactions, refuses busy/unknown counters, drains resources, and terminally retains unknown cleanup on cancellation/error. Default status writer is NOT started by borrowed teardown. connect() deliberately REFUSES; work/model routes remain closed.

Actual Windows native adapter27/27 methods PASS with actual native stores; HTTP fault awaitables explicitly doubled.309 actual imported native source hashes match featureGit. Linux original vs borrowed ResponseStore comparisons PASS with real competitors: lock remainsBUSY both, releases only at owner close; borrowed0 extra canonical connections and committed terminal settlement, uncommitted/TEMP false terminal refused. Original upstream lock-corruption NOT observed.8 offline receipt tests PASS. Full standard harness regression pending combined branch; native full upstream suiteNOTRUN.

Evidence evidence/d3b-api-borrow-b112x9/; report docs/D3B-API-BORROW-B112X9.md; manifest config/hermes-api-borrow-b112x9.json; patch patches/hermes/b112x9-borrowed-api-stores.patch. All first fixture/aggregate failures retained. All427 existing harness sources unchanged. Owned temp profiles absent; no root/mount/production/CI/main/push/provider action.

Next preserve complementary A112X7D harness history, run ONE complete combined standard suite/static, then source-locked canonical artifact delivery. No runtime activation until third-store prepared schema/layout/preopen + A109 ownership and healthy-busy policy are implemented. Prior status/worklogs archived docs/status-history/b112x9-*.md. All own native calls terminal; fullD3B OPEN/legacyIPCv2 CLOSED.
