# Security policy

AlazHarness is an experimental, pre-runtime project, not a security boundary or
a production-ready autonomous agent. A successful preparation CI run does not
prove runtime isolation, safe tool execution, or resistance to prompt injection.

Do not publish credentials, private prompts, personal agent memories or server
addresses in issues. Report a suspected vulnerability privately using GitHub's
Security / Report a vulnerability feature when available. Otherwise contact the
maintainer privately before publishing reproduction details involving secrets.

The root repository is public. Operational configuration and credentials live
outside this repository. CI accepts trusted repository events only; external
fork and draft PRs are blocked from automatic execution on shared infrastructure.
No model API keys, personal agent profiles, Docker socket or host SSH keys are
mounted into the preparation test container.

`ci_check.py` performs a bounded pattern-based secret check on root tracked files;
it is an additional hygiene check, not proof that all possible secrets are absent.
Upstream submodules, historical commits, binaries and credentials require separate
review before publication or redistribution. Never post a detected secret value
in a log; report only the file path and detector name.
