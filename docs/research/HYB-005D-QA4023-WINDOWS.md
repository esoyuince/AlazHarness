# HYB-005D independent QA4023: Windows AppContainer feasibility

Status: selected OS file/process controls observed twice; **complete network and
Hermes integration NOT ACCEPTED**. The two final native runs intentionally exit1
because localhost produced timeouts rather than the required explicit denial.
Primary247a owns integration/Git publication; this package changes only QA files.

## What actually ran

The existing Windows Framework64 C# compiler built a standalone native-API probe.
No download, package installation, external model, actual credential or Hermes
process was used. Windows version observed:10.0.26200.9711. Every run uses a new
unpredictable AppContainer moniker and refuses profile creation failure. It never
reuses or deletes another existing AppContainer. Both final profiles were deleted
by their creating parent after all children exited; only test files remain in runtime.

The unrestricted positive-control child first demonstrated working IPv4/IPv6
loopback listeners, reading/writing the synthetic private fixture, allowed-file
read/write, fake environment-secret visibility and parent PROCESS_VM_READ access.
Then CreateProcessW with SECURITY_CAPABILITIES(no capabilities) launched a second
child suspended. The PARENT inspected its actual token before resume: exact new
AppContainer SID, TokenIsAppContainer=true, capability count0 and Low integrity.
The parent assigned a kill-on-close, one-active-process Job Object before resume;
inherited handles are disabled. This is not merely a child claiming it is sandboxed.

## Final observations (two same-source repetitions)

| Check | Baseline | Restricted process |
|---|---|---|
| Synthetic secret environment variable | Visible | Absent |
| New private test file read/write | Allowed | ERROR_ACCESS_DENIED5 |
| Explicit allowlisted file read | Allowed | Allowed |
| Write into read-only allowlist directory | Allowed | ERROR_ACCESS_DENIED5 |
| Open parent with PROCESS_VM_READ | Allowed | ERROR_ACCESS_DENIED5 |
| IPv4/IPv6 live loopback sentinel | One message per family | Connect timeout10060; no extra message |
| TEST-NET192.0.2.1:9 TCP attempt | Not attempted | WSAEACCES10013 |
| Separate hanging restricted process | Not applicable | Job terminated at deadline, exit91, handle signaled |

The timeout child is a third separate process, not a repeated network attempt.
For each final run the baseline and restricted test exit0; the parent strict
network gate exits1. All three process handles are confirmed exited, both listener
threads stop, synthetic secret contents remain unchanged, and profile deletion
returns0. **No localhost timeout has been relabeled as explicit policy denial.**
The observed lack of packets in the controlled window supports non-delivery only;
it does not prove every potential network path or protocol is unavailable.

## Preserved preparation failures

Trial01: synthetic baseline passed; attempting to set Low mandatory integrity on
our own new output directory returned5. No elevation or global ACL workaround was
used. The subsequent probe uses Windows' own newly created AppContainer profile
for writable output and explicit RX ACLs only on new project test directories.

Trial02: CreateProcessW returned203 when the trusted launcher lacked LOCALAPPDATA.
Only that necessary directory path was added to the trusted launcher's explicit
allowlist. The child receives its own unique AppContainer profile path. We did
not pass through the full host environment, PATH, HOME, proxy controls or keys.
The baseline03 then launched the real restricted process and exposed the current
localhost timeouts. Earlier source/receipts remain under separate trial directories.

## What this does NOT deliver

This is a regular AppContainer test, not LPAC, an arbitrary-command launcher or
an isolated Hermes runtime. Regular AppContainers can access certain shared
system resources; the fixture tests are not a universal filesystem denial proof.
The credentials tested are an artificial environment value and a fresh private
file, not real accounts, Windows credential manager or network impersonation.
The single-active-process job is assigned, but arbitrary descendant/breakaway,
registry/COM, kernel exploit resistance and LPAC capability policies were not tested.

The existing Hermes Gateway/API/budget process is untouched. The no-network
container cannot yet call the existing loopback model endpoint. A separately
reviewed bounded IPC and trusted credential-owning provider boundary are required;
a loopback exemption is NOT automatically authorized. No firewall, exemption,
user account, permanent service or existing source tree was changed.
If the trusted parent is externally killed while creating/deleting a profile,
its own finally block cannot guarantee profile cleanup. That lifecycle case is
not qualified by the normal cleanup and owned-child deadline tests here.

## Reproduce

```powershell
python -B scripts/qa/run_windows_appcontainer_probe.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\fresh-appcontainer-probe
python -B -m unittest discover -s tests -p test_windows_appcontainer_contract_qa4023.py -v
```

Output must be fresh. First command is an opt-in OS experiment and currently has
an expected **strict failure** on this machine's loopback denial-code requirement.
Do not change the expected error to a timeout to make it green. Ordinary Linux CI
runs only the second, synthetic conformance tests; it never compiles or launches
Windows processes. A hypothetical passing JSON fixture is not native acceptance.

## Sources and receipts

Microsoft's documented AppContainer launch/token/profile mechanism:
https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer
https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation
https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteappcontainerprofile

A primary reproduction of caller LOCALAPPDATA/error203 informed the debugging
hypothesis; our fresh local trial then confirmed successful CreateProcess:
https://github.com/Convira/convira-sandbox/issues/1

Final records: evidence/hyb-005d-qa4023/final01-native.json and final02-native.json.
Offline conformance: offline-tests.json/.txt. Historical trial failures are
separate files; raw private fixtures and executables remain Git-ignored runtime.
No root test count should add these OS observations to the standard unittest total.

## Standard-suite verification and separate Linux cross-check

The33 Windows receipt/environment unit cases pass; they validate synthetic records,
not a running Windows sandbox. An initial full discovery executed1050 tests with
exit0, but another writer added the Linux probe script during that run. Its source-
set qualification stays NOT_ACCEPTED in full-standard.json; it was not repurposed
as final evidence. The subsequent stable full suite passed1062/1062, exit0/skip0,
with184 measured code/config files unchanged and no additions. The33 Windows
cases and65 Linux adapter/lifecycle cases are included in1062, not added again.

Separately, the primary's SIX final alaz-server Linux/Docker tool cases were read
retrospectively over the existing connection. The exact current module88fd6d1a...
and probe7bd87920... match their staged server source files. Native observation,
prestart validation, ownership, lifecycle exit records and read-only capsule
content hashes agree for all six cases. This is NOT six more container runs.
The original v1 module7a26e1f1... was not silently treated as the final module.

Windows and Linux serialization produce distinct raw file hashes; canonical JSON
equality identifies the corresponding final observation and both raw hashes are
recorded. Server source files retain exact byte hashes. The qualified transferred
layout is scripts/run_isolated_tool_probe.py and packages/claw-hermes/isolated_tool.py,
not flat root files. Initial reviewer lookup assumptions were corrected without
changing native results, source files, assertions or starting any container.

See linux-final-corroboration.json and final-standard.json/.txt. The retrospective
check observed Linux host-loopback refusal111 and external IPv4/IPv6/UDP refusal101,
empty effective capabilities, no-new-privileges and seccomp. Timeout/cancel records
confirm owned container exit137 without OOM and removal as recorded. These support
the primary's isolated TOOL slice only, not provider/Gateway/M1 integration. Our
Windows strict loopback-denial assertion remains failed in both final runs.

No product code, native ledger, provider path, secrets or upstream pin was modified
by QA4023. Final Git publication and exact-commit CI remain the primary integration
owner's step; a local green unittest count is not a server receipt.
