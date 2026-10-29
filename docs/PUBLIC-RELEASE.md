# Public source release

Prepared October 29, 2026.

This is a reviewed source export of the personal Harness workspace. It includes the maintained application, launchers, design notes, tests, and benchmark evidence. It excludes private runtime state, live account screenshots, local MCP connection files, setup scratch history, old distribution ZIPs, and unreviewed document/image exports.

## Evidence handling

The original local `benchmarks/results-20261028-v1/` directory was left intact. In this public copy, personal filesystem identifiers and SSH targets are replaced with generic examples. Numeric measurements, acceptance results, and evaluator corrections are preserved.

Original plan and runner SHA256 values in the report identify the original run inputs. They are provenance, not a claim that every sanitized public file is byte-identical to its local original. Recorded handoff source hashes are historical observations; path substitution can change the bytes of a quoted packet. [`PUBLIC-MANIFEST.sha256`](PUBLIC-MANIFEST.sha256) records the SHA256 of every published file as committed.

Screenshots in `docs/media/` use the published application with mocked APIs. Projects, tasks, quotas, provider state, and usage are fictional. They illustrate the interface, not measured provider availability or current balances.

## Publication checks

- 36 Python unit tests passed against the public copy using the existing installed dependency environment (rerun before the first public push).
- Responsive Playwright suite passed across six widths and accessibility/appearance modes with mocked APIs.
- Detailed acceptance suite passed all 40 checks, including documentation consistency.
- Gitleaks 8.30.1 directory scan found no secrets. Additional pattern review checked personal paths, private hosts, credential formats, and sensitive file types. This bounded review cannot guarantee detection of every possible secret.

Dependency pins were retained. No installer, native agent, paid model call, local inference service, or GPU benchmark was launched for publication. Third-party implementations and model weights are not vendored here; upstream licensing remains separate.

The initial placeholder commit was retained. New publication commits use the account's GitHub no-reply address.
