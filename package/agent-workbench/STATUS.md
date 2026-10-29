# Harness desktop status — October 28, 2026

Ready for daily cloud-agent work. Open **Harness** on the desktop, or Harness.cmd
in this folder. No terminal commands are needed. See START-HERE.md.

## Delivered

- A local control panel at http://127.0.0.1:8787 with project selection, task
  launch/output, session links, cancellation, provider setup and diagnostics.
- Desktop shortcuts: Harness and Stop Local Model.
- Claude/Codex subscription workers remain the default; both are authenticated.
- OpenRouter and OpenCode Console pay-as-you-go integrations through existing Pi.
  Connect the chosen provider key and model in Connections. Keys stay privately
  on disk outside this repo and are never returned to the browser.
- OpenRouter live catalog: 391 tool-capable models loaded through the UI.
- GPU inference is strictly opt-in. Opening the app, running diagnostics or
  starting a cloud task cannot start it. Both local services are disabled for
  startup. Team dispatch excludes local, even if the model is manually on.
- Local model profile has no hosted memory or web MCP connection. No automatic
  cloud fallback to local inference exists.
- The older AgentHub login script also no longer starts LM Studio by default.
- GPU stop is immediate (kills stuck inference), with no wait for CUDA batches.
- Standard library backend and buildless HTML/CSS/JS. No new package dependency.
- Runtime/source locks updated together: Omnigent 0.20.0, Pi 1.4.0, Claude Code
  2.1.312, Codex 0.165.0; Node 22.23.4 retained as compatible.

## Actual checks

- 23 automated regression/HTTP checks passed.
- Full live doctor with write-check returned 0. Verified a new shared-memory fact
  and retrieved original source. An intentionally off local model is healthy.
- Browser UI launched real Codex and Claude tasks; both read the demonstration
  project ID personal/workbench-demo and exited 0 without edits.
- Real cancellation verified against Omnigent: session status idle and no active
  response. A native turn-start race was repaired and regression checked.
- Host/origin/anti-CSRF checks, key redaction/storage, cloud provider config,
  removal of automatic local dispatch and rejection of off-local launches tested.
- Final local model status: off; workbench-model and workbench-gateway disabled;
  no llama-server or Windows LM Studio model processes running.

## Deliberately not run / still needs input

- No local GPU model was started during this redesign, respecting gaming use.
  Prior 36,864-context inference passed on the previous runtime. Generation on
  the newly updated Pi/Omnigent versions remains unverified until manual use.
- OpenRouter/OpenCode paid generation needs the user's provider key and available
  credits. No key or payment was created, copied from another harness, or guessed.
- OpenCode Go was reviewed but is not represented as a generic Console key;
  this connection uses paid Console endpoints. See ARCHITECTURE.md.
- Only the demo project is initialized; add your real Git project from the app.
- Mac end-to-end access and optional independent server hosting remain unverified.

## Locations / checkpoint

Permanent installation: /home/user/agent-workbench in Ubuntu-24.04 WSL2.
Control-panel service: workbench-ui.service (starts only when the app is opened).
State: ~/.config/agent-workbench; API keys mode 0600; native account files preserved.
Demo: /home/user/projects/workbench-demo; stable ID personal/workbench-demo.
Evidence: /home/user/agent-workbench/evidence/desktop-ui-checks.txt,
doctor-cloud-default.txt, panel-smoke-results.json, panel-cancellation.json.
The model service's batch tuning remains 512 / 128 with 36,864 context, one slot.

User decision: keep inference off while gaming; local model starts only from an
explicit user action. Next optional action: paste a provider key in Connections,
choose a model, then run a small cloud task to verify that account's model access.

## Workflow and benchmark follow-up

VS Code now has Harness: open and Harness: stop local model user tasks. A
personal-workbench repository with empty research/networking/project templates
is ready at /home/user/projects/personal-workbench (ID personal/workbench).
Read DAILY-WORKFLOW.md. No mail, contact or social account was connected or sent to.

Twelve frozen baseline native turns covered source synthesis, networking drafts,
concurrent token-refresh repair, both cross-harness handoffs and live research.
Both coding candidates passed all six external functional checks; both live
research paths performed a real official-page fetch. Raw results and evaluator
corrections are retained in benchmarks/REPORT.md and its results directory.

Three completed replies were incomplete in the native CLI stream although the
session store had the full answer. The panel now reads the persisted final
assistant reply. All three known losses were recovered; two distinct additional
live panel validation turns matched the persisted answer. A new regression and
VS Code no-GPU test bring the final suite to 23 passing checks. This does not
establish a future delivery failure rate or a universal model ranking.

No local inference was used. OpenRouter/OpenCode paid model quality, Mac access,
real networking outcomes, large-codebase behavior and gaming frame-time effects
remain unmeasured. Next discussion: task templates, explicit provenance/freshness
contracts, complete native usage visibility and a user-reviewed daily pilot.

## Model and effort controls — 2026-10-28

Added next-task model and effort selectors to the existing panel. Codex discovery uses the installed app-server model/list metadata and per-model effort ladders. Claude uses CLI aliases (Sonnet/Opus/Haiku); cloud models use the connected provider catalog, with effort offered when reasoning is advertised. Providers may normalize effort; requested settings are recorded, not claimed as observed execution. Team selections apply to its lead only. Browser preferences remember selections per backend/provider. Local GGUF files under ~/models are selectable while stopped; selection writes private runtime configuration, with the service override applied only on explicit Start. Existing local gateway alias/context limits remain unchanged. Local effort is unavailable because this profile does not advertise it. No model downloads or GPU inference were performed.

Validation: 28 CPU-only unit tests passed, including settings-to-executor propagation and local selection validation. Real Codex model metadata and one local GGUF discovered without generation. Mocked Chromium suite passed at widths 320–1440, including model/high-effort task payload, keyboard submission, no horizontal overflow, dark/light appearance and existing workflow checks. Composer height budgets expanded for the added controls. Runtime synchronization and live endpoint checks recorded separately in the session checkpoint.

Live synchronization completed: workbench.py, desktop_ui.py and ui/index.html match maintained source byte-for-byte. Existing runtime files backed up under evidence/model-controls-backup-20261028-213045. Only workbench-ui.service restarted after checking for active jobs. Live authenticated metadata endpoints returned 8 Codex models, 1 downloaded local model and 3 Claude aliases. Local state remains off; model service was already failed/inactive and gateway inactive. No actual cloud generation or local model-switch/start was performed; local start integration remains covered by inspection rather than GPU execution. Release ZIPs were not rebuilt.

## Models browser, single Claude agent and Claude usage — 2026-10-29

- New **Models** page. *Downloaded* lists the GGUF files in ~/models (split
  files listed once), with quantization, size and a 16 GB GPU fit estimate, and
  lets you choose the Local Model while it is stopped. *Discover* searches public
  Hugging Face GGUF repositories (most downloaded first), lists complete
  downloads per quantization, and downloads one into ~/models through
  `.partial/`. Progress, speed, cancel and ranged resume are supported. Only
  files listed by that repository can be fetched. Gated repos are marked and
  not downloaded. Downloading or choosing never starts the GPU.
- Agent picker reduced to Codex, Claude, Hosted Model and Local Model; Team and
  Research were removed from the UI (CLI roles remain). Claude models: Fable 5.1,
  Opus 5.5, Sonnet 5.5, Haiku 5.5, each with low/medium/high/xhigh/max effort.
- Claude usage: reads the 5-hour and weekly plan windows from the same account
  endpoint Claude Code's /usage uses, with the saved sign-in. It never refreshes
  or writes credentials; an expired sign-in shows a note until the next Claude task.

Checks: 36 unit tests pass (8 new). Mocked Chromium suite 45/45 (new `models`
section plus status/composer/sessions/a11y/copy) and check-ui.py passed; screenshots in
artifacts/ui-evidence/models. Live after sync: panel returned real Claude windows,
four Claude models, real Hugging Face search/file lists; a real 88 MB GGUF downloaded
into a temporary folder with a ranged resume and matched Hugging Face's SHA-256
(folder deleted). Synced desktop_ui.py and ui/index.html byte-identical; backup
evidence/models-browser-backup-20261029-014206; only workbench-ui restarted with no
active tasks. Not run: no model was downloaded into ~/models, no local model start,
no Claude generation on each listed model (plan access per model is unverified).
