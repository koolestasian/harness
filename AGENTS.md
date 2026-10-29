# Harness source

Maintained application source is in `package/agent-workbench/`. Run its unit tests from that directory with `python3 -m unittest discover -s tests`. Browser checks run from the repository root in an environment with Playwright and Chromium installed; all API writes must remain mocked.

Local inference is manual-only. Never start models, gateways, local workers, or GPU benchmarks as part of setup verification, diagnostics, or cloud work. Do not rerun the cloud-agent benchmark without explicit authorization.

Keep credentials and native account state outside the repository. Public benchmark evidence is a sanitized historical export; preserve measurements and disclose evaluator corrections. Document completed behavior separately from planned cloud/mobile work.
