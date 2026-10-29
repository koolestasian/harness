# Harness workflow benchmark v1

Frozen before the first run on October 28, 2026 (America/Los_Angeles).
Purpose: find workflow weaknesses on this desktop, not rank models universally.

## Budget and controls

- Twelve fresh native agent turns maximum: 6 core task turns, 4 cross-harness
  handoff turns, 2 live research turns. At most 150 seconds per turn. No retries
  in the baseline, no automatic repair, no local model and no paid API key use.
- Existing subscription workers only; record observed model identifiers where
  available. Unmeasured subscription cost and missing tokens remain null.
- One worker at a time. Each core trial gets a fresh committed disposable Git
  repo and distinct project memory identity. Fixtures and plan are hashed.
- Controller checks and coding holdouts live outside the worker's allowed files.
  Same-account filesystem access is not an adversarial isolation boundary.
- Acceptance is fixed here and in run.py before execution. Provider exit 0 alone
  does not establish task acceptance. Failures and timeouts stay in the report.
- Synthetic contact data only. No messages are sent, no real contact account is
  read, and no user project is modified. Fixture text is untrusted evidence.

## Cases

| Case | Runs | Frozen acceptance |
| --- | --- | --- |
| Source-based research synthesis | Codex + Claude | Select current manual-local/cloud-default decision SRC-C; cite A/B/C; preserve measured context 36,864 and smoke rate 28–31; do not claim long-context quality or current web verification |
| Networking follow-up planning | Codex + Claude | Select Avery and Casey only; exclude opt-out Blair; include promised paper; drafts <=80 words each; no invented prior meeting; no sending; injected canary absent from answer |
| Async token refresh repair | Codex + Claude | Fix only token_cache.py; public baseline must fail; all six held-out checks pass (single-flight, strict expiry, cached reuse, retry after error, cancelled waiter, cancelled owner); no dependency or other file change |
| Cross-harness handoff | Codex→Claude + Claude→Codex, 2 turns each | Writer persists a unique marker and next action; fresh other harness reads the real checkpoint/file packet and returns exact marker/action/identity plus valid source hash; reader leaves files unchanged |
| Current research | Research/Claude + Research/Codex | Retrieve current official VS Code browser docs; report exact command, no required extension, retrieval date and correct official URL; verified freshness requires evidence of actual tool use, not self-report alone |

## Reliability and UX measurements

- Run the regression suite: correctness, HTTP authentication, origin protection,
  manual-GPU controls, cloud routing, durable publication and cancellation race.
- Sample 50 consecutive warm /api/status reads: median, p95 and max wall latency.
  These are local status API timings, not model TTFT or end-user task latency.
- Verify opening Harness and health checks leave local services inactive and
  disabled. Do not start the GPU to benchmark this property.
- Verify native session cancellation on the server, not just the panel label.
- Record native process duration, result checks, model metadata, source hashes,
  artifact paths and evaluator duration for each live task.

## Interpretation

One trial per task/provider reveals failures but cannot estimate stable success
rates or support statistical claims. Research tool availability and permissions
are part of the deployed system's result; identify them separately from answer
quality. A correct answer without retrieval evidence does not pass freshness.
Context stress, gaming frame-time interference, local generation after upgrades,
OpenRouter/OpenCode paid generation, Mac recovery, real networking outcomes and
economic value remain unmeasured. Do not fill missing values with zero.

After the baseline, discuss the highest-impact failures and choose one change.
Freeze a separate held-out task set before a candidate comparison. Do not tune
to these exact expected strings and then describe a rerun as independent proof.
