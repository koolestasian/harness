# First Harness workflow benchmarks

Measured on the Windows desktop in WSL2 on October 28, 2026. Local inference
remained off throughout. The useful result is a workflow diagnosis, not a model
leaderboard: project repairs and handoffs worked, while native answer delivery
needed a fix and freshness labels need a clearer contract.

## What ran

The frozen [plan](PLAN.md) and [runner](run.py) defined 12 fresh native turns,
one at a time, with a 150-second timeout and no baseline retries. They used
synthetic contacts and disposable Git repositories, not the user's real work.
The actual observed defaults were `gpt-5.6-sol` for native Codex and
`claude-opus-5-5` for native Claude / Claude research. The Codex research session
did not expose a model ID in the captured metadata; it stays unknown.

Installed versions: Omnigent 0.20.0, Claude Code 2.1.312, Codex 0.165.0, Pi 1.4.0.
No paid OpenRouter/OpenCode calls or GPU generations were made.

The original machine scores are preserved in
[baseline-results.json](results-20261028-v1/baseline-results.json). They contain
checker defects and are not the final quality assessment. The separate
[reviewed results](results-20261028-v1/reviewed-results.json) use persisted session
answers, raw Git output, tool traces and the unchanged functional acceptance
criteria. Both the baseline and the corrections are inspectable.

## Task results

Durations below include native startup, tool work and process completion. They
are monotonic elapsed measurements, not first-token latency or model-only time.

| Workflow case | Codex | Claude | Evidence-based outcome |
| --- | ---: | ---: | --- |
| Frozen-source synthesis | 20.08 s | 16.89 s | Both preserved the current manual-local decision and measured numbers. Claude correctly kept freshness false. Codex set it true despite using supplied notes only. |
| Networking follow-up drafts | 21.21 s | 16.07 s | Both selected Avery + Casey, excluded the opt-out, included the promised paper, and stayed under 80 words per draft. No invented meeting found in the reviewed drafts. |
| Async token-cache repair | 44.40 s | 35.93 s | Both passed all six external functional checks and changed only token_cache.py. |
| Current primary-source research | 28.27 s | 24.66 s | Both retrieved the official VS Code page with live=true and returned the exact integrated-browser command. |

These paired rows each have one observation per worker. Different native
defaults, warm caches, startup state and tool behavior are confounders. Claude
returning sooner in these samples is not proof of a stable speed advantage.

The source-synthesis freshness flag is a useful failure but also a prompt-design
warning. The prompt named `freshness_verified` without explicitly defining it as
an external live check. The frozen expected value was false; Codex did not meet
that criterion. This is not evidence of fabricated source content or malicious
intent. Future task contracts should separate source date, supplied-file status
and live retrieval instead of asking one ambiguous boolean to cover all three.

## Coding checks

The public baseline failed before each worker acted, so this was a real repair
rather than a passing fixture. Each candidate was then evaluated outside its
allowed edit scope:

| Functional scenario | Codex | Claude |
| --- | --- | --- |
| 25 concurrent callers share one refresh | Pass | Pass |
| Valid token is reused | Pass | Pass |
| Exact expiry/skew boundary triggers refresh | Pass | Pass |
| Failed refresh can be retried | Pass | Pass |
| Cancelling a waiter does not cancel the owner | Pass | Pass |
| Cancelling an owner does not deadlock the next caller | Pass | Pass |
| Scope: only token_cache.py changed | Pass | Pass |

The six functional checks are six scenarios within one coding problem, not six
independent coding tasks. They do not cover production authentication security,
all race interleavings or a large application. The candidate diffs are saved as
[Codex diff](results-20261028-v1/codex-coding.diff) and
[Claude diff](results-20261028-v1/claude-coding.diff).

## Handoffs

| Direction | Write turn | Fresh read turn | Result |
| --- | ---: | ---: | --- |
| Codex → Claude | 33.23 s | 15.85 s | Exact unique marker, next action, project ID and SHA256 recovered; reader left files unchanged |
| Claude → Codex | 16.36 s | 10.25 s | Same five criteria passed |

Both directions used actual tracked source files and `workbench checkpoint` /
`--task --file` packets in fresh sessions. This establishes explicit file-based
handoff behavior. It does not establish automatic chat-history transfer,
cross-device synchronization or general memory quality. The Mac was not tested.

## The most important defect: completed answers missing from the CLI

All 12 baseline processes exited 0, but only **9 of 12** CLI transcripts contained
the full persisted final reply. Three Claude native turns had incomplete CLI
delivery: source synthesis, networking drafts and handoff writing. The full
answers were present in Omnigent's session store. The handoff file itself was
also correctly written.

This was a delivery defect in the deployed native path, not three failed model
answers. An exit code and a short "done" label were insufficient evidence that
the user had actually received the result.

The panel now reads the completed assistant message from the persisted session
after the process ends. It ignores tool-result text, redacts known credentials,
and reports an absent final reply instead of silently substituting "completed".

Repair validation was separate from the frozen baseline:

- All **3 known missing replies** were recovered exactly using the new helper.
- A new regression covers missing CLI text, message type and URL restrictions.
- **23 regression checks passed** after the delivery change and VS Code no-GPU check.
- Two additional, distinct live panel prompts matched the persisted answer:
  Claude 12.75 s and Codex 14.48 s. Neither fresh turn happened to reproduce the
  streaming loss, so these two runs alone do not estimate the future failure rate.

See [repair evidence](results-20261028-v1/delivery-repair-evidence.json). Baseline
scores remain unchanged; repaired behavior is not relabeled as baseline success.

## Research and networking interpretation

Live research passed for both harness choices. Session tool traces show a
`search_web_pages` call followed by `fetch_page_content` with `live: true`, and
the returned official page contains the exact command. The search snippets had
an older acquisition date; the subsequent live fetch is why the freshness check
passed. Merely citing the right URL would not have been enough.

Networking passed the bounded draft contract in both cases. The reviewed drafts
respected the opt-out and did not repeat the injected canary. The available tool
traces contain file reads; no mail/contact connector was part of these trials.
Actual contact delivery, reply rate, relationship quality and user editing time
were not measured. A draft saying "here is the paper" still needs the user to
attach or link that paper before sending.

These fixtures also contained an instruction-like snippet that contradicted
the user's task. Both workers ignored it in the reviewed answers. Four synthetic
examples are not a general prompt-injection security evaluation.

## Panel responsiveness and GPU behavior

Fifty consecutive warm `/api/status` reads on this desktop measured:

| Measure | Result |
| --- | ---: |
| Median | 4.06 ms |
| p95, nearest-rank | 4.71 ms |
| Maximum | 5.45 ms |

This is loopback status API latency with no competing benchmark job, not browser
paint time, cold WSL startup or task completion. It does not establish gaming
performance. Every sample reported the local model off. Services were verified
inactive and disabled; no local inference was used to collect these numbers.

Per-turn times use a monotonic clock. The UTC start/end interval in the manifest
is 274.1 seconds, while the summed turn measurements are 283.2 seconds. That
clock/collection discrepancy is unresolved, so no whole-suite wall-clock speed
claim is made. Use the individual measurements cautiously and repeat timing
under a checked clock before making performance decisions.

## Usage and cost limits

The native session metadata exposed reference cost estimates for 11 of 12 turns,
summing to **$1.9281**. This is not a measured charge to the user's subscription
or an API bill. Actual incremental dollar cost remains unknown. Claude native
turns lacked usable token counts in the captured metadata, and the Codex research
turn lacked model/usage metadata. Do not compare provider economics from this run.

For example, the Codex source case reported 31,929 cumulative tokens including
26,752 cached input tokens across the turn. That is not proof of a single 32k
prompt. It does motivate inspecting context/tool overhead and improving usage
coverage before adding a router or claiming a cost saving.

## Evaluator corrections and validity limits

Three evaluator issues were retained transparently:

1. The scope check reused a Git helper that strips leading whitespace. Git
   porcelain requires those columns. Raw output confirms only token_cache.py
   changed in both coding cases.
2. Exact equality rejected opt-out explanations containing "Blair Stone" and
   active-decision prose containing the correct decision. Semantic review accepts
   those representations; the actual acceptance criterion was not a demand for
   one arbitrary string spelling.
3. CLI-only answer parsing treated missing delivery as missing content. The
   persisted answers establish content correctness while delivery remains a
   separate baseline failure.

Post-run adjudication is by the same assistant with explicit external checks,
not a blind independent human evaluation. The controller and workers share an
OS account; the held-out checker is outside the allowed file scope but not an
adversarial security boundary. Project identities were distinct across cases,
but the runner's `benchmark/repos/...` naming must gain a run-specific namespace
before future repeats to avoid reusing memory banks.

One observation per task/worker is too small for confidence intervals or a
general model ranking. The broad "11 of 12 content criteria passed" summary
includes artifact-writing setup turns and is less useful than the case results.
No candidate prompt or model was tuned to these fixtures and reranked as an
independent improvement.

## Improvements worth discussing

| Priority | Improvement | Evidence / next acceptance test |
| --- | --- | --- |
| Fixed now | Recover persisted answers in the panel | Three baseline losses recovered; regression + two separate live validations |
| Next | Research/output contracts and prompt starters | Separate supplied-file evidence from live verification; test on new contradictions and failed fetches |
| Next | Per-session observability | Expose actual model, source type, completed checks and missing usage; never equate estimated price with billed cost |
| Next | Bounded daily templates | Research brief, promised follow-ups and project handoff should be easy to start; measure user corrections and time saved |
| After that | Context/tool overhead audit | Capture assembled input and tool schema sizes on representative tasks, then compare one pruning change on held-out cases |
| After that | Memory robustness | New cases for supersession, project-scope recall, source fidelity and memory outage; existing source files must remain usable |
| When authorized | Hosted/open-model and local tests | Provider key + credits for hosted generation; a non-gaming window for local quality/VRAM tests |

My recommendation is to use the personal workspace and a single cloud worker
for daily tasks now. Add a second reviewer when the consequence justifies it.
The next investment should be clearer task contracts and visible evidence, not
another agent framework or background GPU service. The real-world pilot should
track whether you accepted the research/draft/patch, how much you corrected, and
whether it saved you time over your existing workflow.

## Reproduction and artifacts

- [Frozen plan](PLAN.md), [runner](run.py), [post-run reviewer](review.py).
- [Machine-readable reviewed results](results-20261028-v1/reviewed-results.json).
- [Summary CSV](results-20261028-v1/summary.csv).
- Per-case `.log`, `.answer.txt`, `.trace.json` and coding `.diff` files in the
  same results folder. All task content in those files is synthetic.
- Source plan SHA256: `7bd4c887d71a95e2fa76d9476641d67b092a0f9b3de2c9c3fa66b23042afe985`.
- Baseline runner SHA256: `fd171b0a2e458b9078d6293f7d22f5a89e1bca3509658e40b06c1a0e47c9ffb5`.

Baseline native evidence remains at
`/home/user/agent-workbench/evidence/benchmark-20261028-v1`. Repeating the runner
is an explicit set of cloud-agent turns, not an automatic background job; fix
the run-specific namespace before interpreting a repeat as memory-independent.
