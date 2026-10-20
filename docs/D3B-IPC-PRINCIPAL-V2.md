# D3B IPC principal v2 — scoped checkpoint (20 October 2026)

Branch: `alaz/d3b-ipc-principal-20oct`. Base: `46766be`.

## Implemented (negative-only; default closed)

- Version 1 projected-root IPC remains unchanged.
- Version 2 `projected_root_principal` is explicit and requires an exact `principalContract` validated by the existing host-principal policy.
- `inspect_principal_socket` validates the socket owner, designated group, exact 0710 parent and 0660 socket using host-principal checks. Its result explicitly has `mountAuthorized: false`.
- `prepare` and `project` reject version 2 *before* mounting or granting filesystem authority; a trusted separate-UID launcher does not yet exist.
- Negative tests cover invalid contract, equal UIDs, invalid socket, identity proof, and inability to bypass the runtime gate.

## Evidence / limits

- Windows IPC unittest discovery: **41/41 PASS** (20 Oct 2026).
- Ubuntu WSL IPC unittest discovery: **41/41 PASS** (20 Oct 2026).
- Windows host-principal regression: **44/44 PASS** (20 Oct 2026).
- Static CI at earlier 41-test snapshot: **PASS**, **2075** tests discovered. This is a static gate, not a runtime acceptance.
- No real separate-host-UID positive run, privileged account provisioning, real Gateway-broker test, paid provider or production setting change.
- No proof yet that distinct host identities cannot access broker budget data or that only the selected socket is reachable.
- Full D3B **NOT ACCEPTED**.

## 20 October 2026 — WSL environment readiness check (read-only)

- Cloudflare Bridge reached unprivileged Ubuntu WSL: uid/gid 1000/1000 (`ender`), user namespace `user:[4026531837]`.
- `unshare`, `setpriv`, and `runuser` are installed; this establishes only tool availability, not permission to create a separate host principal.
- Existing `nobody` UID/GID 65534 is a system nologin identity, **not** a provisioned dedicated broker account. No account, group, sudo, filesystem ownership, or host service was modified.
- Existing user's supplemental groups include `sudo`; strict broker policy requires no supplemental groups and a trusted-designated group. Current user cannot simply stand in for the broker.
- The first combined read-only WSL probe hit a 15-second deadline; no residual `wsl.exe` process was found by a subsequent process listing. Later narrower probes succeeded.
- Fresh Ubuntu IPC contract regression: **41/41 PASS**. This is not two-host-UID runtime acceptance.
- The next positive test remains blocked on explicitly trusted two-UID launch/provisioning and the still fail-closed v2 mount path. Do not use `nobody`, `sudo`, or user namespace remapping as an acceptance shortcut.

## Next gate

1. Build a trusted Linux two-UID launcher in a separate, test-only environment, with UID/GID, user-namespace, socket directory and budget storage provisioned explicitly.
2. Rework projection under a newly versioned, opt-in path while preserving v1 semantics. Verify inode/pid/peer at time of use and fail closed on rebind.
3. Run positive two-host-UID Gateway/broker tests and negative unrelated-socket/mount, budget access, restart, replay and ACK-loss cases with source hashes.
4. Only then consider feature publication or full D3B acceptance. Preserve prior evidence and do not merge to main merely from these unit tests.
