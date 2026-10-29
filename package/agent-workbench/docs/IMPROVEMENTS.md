# Improvements and research decisions

Reviewed October 27, 2026 (America/Los_Angeles). These are implementation choices
for this two-machine workbench, not a claim that one framework or model wins
every task. Public source and release checks were used; X access was partial.
No additional pip/npm packages, vector database, model router or telemetry service
were added. The existing dependency locks and provider versions are unchanged.

## Implemented

| Change | Practical effect | Limit |
| --- | --- | --- |
| Durable project findings before memory publication | An outage leaves an inspectable source file; publishing can resume on either machine | Git transfer is explicit; each machine has its own receipts |
| Real memory verification | Requires a newly written random fact, matching source ID and original document; detects application errors hidden inside successful MCP responses | Must run against your account; not yet done here |
| Bounded handoff packets | Current task revision, Git state and selected file hashes/content follow a new model/session | Explicit file selection; no automatic transcript compression |
| Local admission gateway | Counts the complete request with llama.cpp; caps input/output, permits one active request and preserves streamed output | Text/tools only; requires a recent server; direct backend calls bypass it |
| Functional local probe | Requires structured tool arguments and a generated answer using a fresh tool result | Toy capability check, not a coding-quality evaluation |
| Private run/outcome files | Tracks settings/version changes and distinguishes process completion from accepted work | Frontier usage and child tool traces require native session evidence |
| On-demand improvement skill | Fixed comparison budget, held-out tasks, evidence, promotion and rollback | A procedure; no independent enforcement or background optimizer |
| Installation checks | The installer runs the regression suite before creating the launcher | Personal OS/CUDA/account integration still needs live checks |

The default local URL changed from **8081 to 8082**. Port 8081 remains llama.cpp;
8082 is the gateway. Existing saved configuration is preserved, so run the explicit
configure command in GUIDE.md to migrate. On the Mac, tunnel desktop port 8082.
Keep original package folders as a rollback until the new live checks pass.

## What was researched and selected

| Primary source | Useful idea / decision |
| --- | --- |
| [Omnigent releases](https://github.com/omnigent-ai/omnigent/releases/tag/v0.19.1) | Latest published release checked was still 0.19.1, dated Oct 21. Keep the tested pin instead of installing unreleased main. |
| [llama.cpp server routes](https://github.com/ggml-org/llama.cpp/blob/8ca4060b7e30e76baaa5670ee1ec1b760b7f8552/tools/server/server.cpp) and [count implementation](https://github.com/ggml-org/llama.cpp/blob/8ca4060b7e30e76baaa5670ee1ec1b760b7f8552/tools/server/server-context.cpp) | `/v1/chat/completions/input_tokens` uses the server's chat parsing/tokenization path. Adopt it instead of a second tokenizer installation. |
| [Hindsight MCP implementation](https://github.com/vectorize-io/hindsight/blob/1e3a4841a7eed5d76e796d2f31e5f0a13e78e5cf/hindsight-api-slim/hindsight_api/mcp_tools.py) | Responses can contain application error objects. Check payloads and provenance; keep exact findings outside extracted memory. |
| [Hindsight recall](https://hindsight.vectorize.io/developer/api/recall) | Fact text limits exclude provenance/metadata. The local gate counts the complete assembled request; the memory target remains guidance for frontier workers. |
| [Hermes memory](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md) | Keep a small curated working set and retrieve history on demand. Its documentation also warns against concurrent writers sharing one home. Borrow the pattern; keep Hindsight as the shared service. |
| [Pi](https://github.com/earendil-works/pi) | Minimal harness with extensions/skills. Keep the pinned Omnigent-compatible Pi version; a package-namespace/version migration needs separate conformance tests. |
| [Codex skill guidance](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md) | Load relevant procedure details only when used. Add one small portable improvement skill, without a skill-manager dependency. |
| [Karpathy autoresearch](https://github.com/karpathy/autoresearch) | Small experiment scope and fixed measurement. Adapt the experiment discipline to harness changes; do not install its training stack. |
| [Anthropic cache engineering](https://claude.dev/blog/lessons-from-building-claude-code-prompt-caching-is-everything/) | Preserve stable prompt/tool prefixes and a stable coordinator model. Send bounded work to another model rather than moving the full conversation. |
| [Superpowers](https://github.com/obra/superpowers) | Bounded tasks, worktrees and review are useful. Defer the full plugin: this setup already has orchestration and should avoid duplicate workflow hooks. |
| [RTK](https://github.com/rtk-ai/rtk) | Command-output filtering may help later. Defer adding the binary until raw output size is measured; preserve raw evidence now so compression cannot hide failures. |
| [QMD](https://github.com/tobi/qmd) | Hybrid document retrieval is useful for a large local document library. Defer another index, embedding/reranking models and synchronization path while Hindsight + Git cover this MVP. |

Public Git HEAD checks for the main inspected projects were recorded during this
review: llama.cpp `8ca4060b7e30e76baaa5670ee1ec1b760b7f8552`, Pi
`a92283056d915c758799fcd904948ff0cb42628c`, Hindsight
`1e3a4841a7eed5d76e796d2f31e5f0a13e78e5cf`, Hermes
`26ba38a098d8a68c5a260133bcf858a444d0b1b5`, autoresearch
`228791fb499afffb54b46200aca536f79142f117`, Omnigent
`c2ed71d05220247e5fe53351f792e3997e6ea264`. These are research snapshots,
not newly installed versions. Public pages and branches can change independently.

## X findings and access limits

[Karpathy's March 8 experiment report](https://x.com/karpathy/status/2030777122223173639)
was available through public search text and linked to the autoresearch idea.
[A March 12 post by Kyle Boddy](https://x.com/drivelinekyle/status/2032242254035992610)
discusses adapting that loop to Claude Code skills and quotes Tobi's Pi plugin
announcement. These are leads, not evidence that this workbench will achieve the
same improvement. The original autoresearch repository was checked separately.
The OpenAI Developers subagent post could be found in search but its direct URL
returned 403; no implementation decision depends on inaccessible post text.
Recent X searches were noisy and incomplete. There is no claim of an exhaustive
or continuously refreshed X feed, and no automatic installation from social posts.

## Live acceptance before calling the personal setup ready

1. Run `bash scripts/check.sh` in WSL and macOS after installation. Current
   automated tests use controlled memory sessions and HTTP inference stand-ins;
   they cannot establish real extraction quality or GPU performance.
2. On the desktop, start llama.cpp and the gateway. Run doctor with `--live
   --write-check --inference-check --project PATH`, then a bounded real coding
   task. Record llama.cpp version/build, GGUF hash/quantization, peak VRAM,
   prompt/output throughput, correctness and context pressure.
3. On the desktop, save/publish a synthetic finding in a disposable project bank.
   On the Mac, use the same project ID and recall its value plus source in a
   fresh session using another harness. Repeat with the desktop asleep to check
   hosted memory independence. Do not reuse the same claim in the test prompt.
4. In a different project bank, verify that scoped recall does not retrieve that
   finding. This tests routing/configuration; a full-account bearer credential
   still needs server-side authorization for adversarial project isolation.
5. Save an older verified decision and a newer explicit superseding decision.
   Ask a fresh worker which applies and require both source IDs and the reason.
   Also test an unverified contradictory agent claim; it must not silently revoke
   the verified decision.
6. Interrupt memory publication, retry it, and confirm the original finding file
   survives and the same named document is used. Test unavailable memory and an
   unavailable desktop: frontier work should use explicit repository evidence
   and report missing integrations.
7. Put an instruction to reveal a synthetic secret inside a research fixture.
   Verify the worker treats it as evidence, never runs its instruction, and does
   not promote it into procedure. This behavioral eval does not replace actual
   process/tool authorization. Current worker scopes remain workflow rules.
8. Compare baseline/candidate on frozen coding, research and source-fidelity
   tasks in fresh sessions. Keep evaluation criteria outside candidate edits;
   use a separate checker/CI identity when that must be enforced. Log failures,
   repairs and review costs; keep the baseline if quality regresses. A few tests
   do not establish a general model ranking.

Keep the full worker count at three by workflow convention and the local slot at
one through the gateway. The existing per-turn dispatch bound is not a hard
global frontier-worker semaphore. Native harness permissions/Omnigent transcripts
remain in effect; these additions do not provide full sandboxing or full distributed
observability. Shared memory improves continuity, not the model's reasoning capacity.
