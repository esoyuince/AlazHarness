# AlazHarness - status

## R154A1 - IN PROGRESS: source installation dispatched

Goal: advance P1 from the accepted exact-source candidate to a verified Linux
installation, then the original supervised readiness path.
Base main: 16830bd56e8c9b6a23e1bd60435ffb4b04793a9d.
Branch: alaz/m1-install-readiness-r154a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-install-readiness-r154a1.
Native source: d1516731308de8e87130dc68124e69aad35d6911, unchanged.
R153 source candidate: e03f7fd4e47fea6a58b749564ab350aeb4237a26.
Archive SHA256: e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b.

### Completed

- Live main/origin/remote base and original root33 file bytes verified.
- Isolated worktree created; previous and initial status preserved in status-history.
- Ordinary read-only lab probe PASS: all1162 installed dependency hashes exact,
  root-controlled ancestry/entries, Python3.12.3 SHAe50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f.
- Added exact-candidate installer and read-only verification modes. It copies only
  approved source/dependency bytes, atomically publishes an absent destination,
  emits a checked receipt, preserves partial evidence and never launches native code.
- Source installer SHAa56782d4e09bed38983c387d4b882e3db3866409e8e96e1f092d36517fc53525.
- Linux owned-fixture suite36PASS/0SKIP, exit0. Windows16PASS/20Linux-onlySKIP,
  raw unittest exit0. A CRLF skip-count reporting error made the outer wrapper
  exit1; raw output and erroneous summary preserved, corrected without replay.
- Fixed operator runner SHA06755f6d866a30b208c80ce23dab30e99326077d0b632211b42d9f6dcac18a14.
- Frozen input bundle d043a57a87e2c6f75a02e4295e316bbba899dec40b14df6e9e9a2b2d4e0519a2,
  19989136bytes in scratch/install-candidates/r154a1-install-002.
- Actual ordinary-user real-candidate preflight PASS, exit0:
  834sources +1162dependencies + interpreter/target ancestry verified.
  Request37332750-9cd8-4129-a638-bcbb22556154 is terminal; no replay.
  Temporary preflight input retained at /tmp/alaz-r154a1-preflight-4g2xcrrj in P71C.
- All earlier primary-agent requests have terminal observed receipts; current install is listed below.

### Next step / exact boundary

Independent exact-byte installer and operator reviews found no remaining blocker.
Two operator reporting/mode findings were fixed before application; original001 is
SUPERSEDED_NOT_APPLIED. Revised runner Linux11PASS; Windows10PASS/1Linux-onlySKIP.
The four source/dependency candidate payloads are byte-identical to accepted preflight.
Privileged source-only installation was dispatched in the dedicated P71C lab to
fresh /opt/alaz-r154a1-input and /opt/alaz-r154a1.
Request3d5848d2-aae5-4a82-bd76-904504df6154 is PENDING at this checkpoint.
Inspect its terminal receipt and frozen attempt002; never replay an unknown action.
No image, mount, cgroup, native startup, service, provider or old cleanup is part
of the source installer. Read-only installed verification follows an accepted apply.

The later readiness path still requires a real retained receipt from the same
actual supervised ext4 image through the original native owner/finite lifecycle.
No copied QA profile, rewritten device/inode record, guard weakening, automatic
replay or forced cleanup. Historical denied operations are not retried.

P1 IN PROGRESS. Installed current-source readiness, full D3B, M1 and prod NOT ACCEPTED.
Installation outcome is not yet accepted at this checkpoint. Real model calls remain zero.

Evidence: evidence/m1-install-readiness-r154a1/.
Roadmap: docs/PRODUCT-ROADMAP.md.
Previous report: docs/M1-PRODUCT-PATH-R153A1.md.
