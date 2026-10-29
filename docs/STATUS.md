# Harness desktop status — October 28, 2026

Ready for daily cloud-agent work. Open **Harness** on the desktop, or ../launchers/Harness.cmd
in this folder. No terminal commands are needed. See START-HERE.md.

## Copilot compatibility — October 28, 2026

This workspace now has Copilot project instructions, three focused custom
agents, three reusable skills, and a portable `.mcp.json` connection to the
existing Windows AgentHub. Open it with `../launchers/Open-Copilot.cmd`; follow
[COPILOT-START.md](COPILOT-START.md). The existing panel and installed WSL
runtime were preserved. This integration lives in the workspace root; the
previous source ZIP archives were not repackaged as Copilot workspaces.

Actual checks for this change:

- VS Code reports 1.144.0. Its CLI reports GitHub Copilot Chat 0.72.0 already
  installed; no extension update or account/subscription change was needed.
- `../scripts/check-copilot.py`, using the existing AgentHub Python environment:
  workspace JSON parsed; the exact configured server initialized; required
  memory/checkpoint tools were discovered; project-scoped memory search passed.
- All six custom-agent/skill YAML headers parsed using the existing WSL PyYAML
  dependency; required names/descriptions and skill directory names checked.
- Existing source regression suite: **23 tests passed**. No inference check ran.
- Local model/gateway services are disabled with `MainPID=0`; no Windows
  llama-server, llmster or LM Studio process was found. The model unit retains
  its earlier failed state, but has no running process. Copilot local routing
  is explicitly false in this workspace's settings; the installed editor
  contains that setting identifier.

Desktop first-use check: opened this workspace and selected the Copilot session
target. All three Harness agents appeared in the picker, and all three skills
appeared in slash completion. Ran `/harness-networking` with a fictional
contact opt-out case and a project-memory lookup. Copilot loaded the skill,
Fusion selected hosted GPT-5.6 Luna from the available plan, and the session
requested `agenthub: memory_search`. That call is waiting for the user's
**Allow in this Session** click; final memory retrieval and the resulting answer
are not verified yet. The standalone configured-server check passed again.

The user subsequently confirmed connecting from the Mac through SSH and opening
Copilot. Windows VS Code Server diagnostic logs are present; the configured
AgentHub protocol check passed again and both inference services remain disabled
with `MainPID=0`. Memory retrieval inside the Mac-facing Copilot chat still needs
a direct check; that interface is not visible to this session's Windows tools.

These are compatibility checks, not measured Copilot quality benchmarks.
Existing Hindsight banks were not migrated into AgentHub. No new package
dependency or GPU startup was added.

### Mac reconnect investigation

The user reported **Automatic reconnect gave up after 10 attempts** under Codex.
PC diagnostics found SSH running, a VS Code agent-host proxy repeatedly failing
with `ECONNREFUSED` at its recorded loopback upstream, and a separate Codex
`thread not found` error. A client reconnect was observed but reused the same
failed upstream. The user reports the official remote-server recovery command
also did not resolve it. No server data or processes were deleted by this agent.

The SSH editor server package is **1.143.1**, while the managed Agent Host package
is **1.144.0**. Updating and fully restarting VS Code on the Mac was recommended;
this is a compatibility hypothesis, not a demonstrated cause or verified fix.

As a fallback, the workspace now keeps the **Local** editor harness available
and turns off automatic Copilot-harness preference. It still uses hosted Copilot
models; local GPU routing remains false. Added matching editor-format
`.vscode/mcp.json` alongside the portable Copilot config. The updated memory
check passed JSON parsing, configuration parity, real server initialization,
tool discovery and project memory search. Actual Mac fallback chat and recovery
of the newer Agent Host remain unverified pending the user's client-side check.

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
corrections are retained in ../benchmarks/REPORT.md and its results directory.

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

## Agent limits and recommendations ? 2026-10-28

Added Agents & limits for all six panel roles, shared-account explanations, provider usage links, and task-text suggestions (keyword heuristics, not measured quality rankings). Codex quota uses read-only app-server account/rateLimits/read. OpenRouter uses GET /api/v1/key; key cap is distinguished from account balance. Claude quota is unavailable through this connection; Research and Team identify shared Claude allowance. Local model stays manual-only. Quota snapshots refresh in background every five minutes, with manual refresh.

Validation: 25 unittest checks passed in WSL, including exhausted and unavailable quota cases; Node syntax check passed; live HTTP8787 served new view and actual Codex/OpenRouter quota snapshot. Synced desktop_ui.py and ui/index.html to /home/user/agent-workbench with .pre-usage backups, restarted only workbench-ui. Model failed/inactive and gateway inactive; no inference run. Visual browser QA not performed. Release ZIPs not regenerated. No active tracked Harness task.

Protocol sources: https://learn.chatgpt.com/docs/app-server ; https://openrouter.ai/docs/api_reference/limits (consulted 2026-10-28).

## UI redesign · October 28, 2026

Replaced the card dashboard with a warm neutral workspace, compact project rail and task composer, native agent selection, and searchable/filterable session rows with expandable replies. Connections and manual GPU controls now have dedicated screens. Research and rationale: UI-DESIGN.md.

Validation: 25 Python regression tests passed. ../scripts/check-ui.py passed in Chromium with mocked APIs across all three screens at 320/390/768/1024/1440 px; no JavaScript errors or horizontal overflow. Inspected desktop and mobile renders in ../artifacts/ui-evidence. Browser interactions cover keyboard submission, stop, project selection, dialog focus/escape, session search/filter/expansion, setup paths, empty states and disconnects. Screenshot data is fictional.

Deployment: synchronized only ui/index.html to the installed WSL runtime, preserving index.before-workspace-redesign.html there. Updated the maintained HTML manifest entry. A separate real-panel Chromium check loaded all three screens, confirmed active navigation and no JavaScript errors, with GET requests only. Local model and gateway MainPID remained 0. No model starts, service restarts or release ZIP rebuilds.`n2026-10-28 home-page correction: Compact usage strip directly below task composer shows Codex remaining bars for each window/reset time, OpenRouter key remaining bar, shared Claude/Research/Team unavailable marker and usage link, local quota status. Preserved current redesigned UI. HTML synced to installed runtime with index.pre-home-limits.html backup; no restart. Node syntax and mocked DOM rendering checks passed (58/81 percent, zero, unknown). Live HTTP confirms strip. Visual QA blocked by CUA sandbox runner pipe-in failure.

## Usability audit and fixes · October 28, 2026

Playwright audit and implementation completed; detailed evidence and outcomes in UI-AUDIT.md. Fixed quota fills/punctuation, page density, per-project drafts and scope, preference persistence, task titles/direct links, historical failure expansion, and pending/focus/error states. Large typography retained. 26 Python tests pass; expanded browser suite passes six widths with mocked writes. GET-only live re-audit confirms draft/project reload persistence, no JavaScript errors/overflow; sessions move from y818 to665 on laptop and y1226 to958 on phone with quotas loaded.

Synced HTML and desktop_ui.py to WSL, backed up originals and restarted only the idle UI service. No active task interrupted; model/gateway MainPID0. New task titles only; legacy records unchanged. Drafts are per-tab sessionStorage; project/agent choices localStorage; no browser-stored keys. Release ZIPs unchanged.

2026-10-28 folder organization: guides moved to docs/, launch scripts to launchers/, existing ZIPs to releases/, workflow exports to docs/exports/, UI evidence/previews/log to artifacts/. Source and frozen benchmarks retained. Root README maps folders; root Harness.cmd and two PowerShell forwarders preserve desktop shortcuts. VS Code tasks and browser-check evidence paths updated. Installed runtime unchanged.

Organization checks: 26 application unit tests pass; moved PowerShell launch scripts parse; all local README/docs Markdown links resolve; VS Code task file targets exist; browser-check Python scripts parse and their new artifacts/ui-evidence path exists. Launchers were not executed (avoids opening apps or stopping unrelated processes).

## Apple-guided interface · October 28, 2026

Applied the relevant Apple Style Guide and HIG guidance to the web UI. See APPLE-UI.md for the source checklist and implementation scope. Neutral sidebar/content, restrained blue actions, system typography with existing large text, consistent labels, light/dark/increased-contrast appearances, 44px buttons, optional desktop sidebar, draft Undo, labeled local-model confirmation and inline dialog errors. Existing home usage bars and audit fixes retained.

26 Python tests pass. Playwright passes six base widths plus light/dark, increased contrast, forced colors, reduced motion and 200% text reflow. GET-only live audit has no JavaScript errors/overflow; laptop sessions y690 and 390px sessions y972 with live quotas. Only HTML synced; backup index.before-apple-style.html. No service restart or inference start. Release ZIPs unchanged.
## Critique fixes · October 29, 2026

The impeccable critique (21/40) was turned into a spec, [UI-FIXES-SPEC.md](UI-FIXES-SPEC.md), and 40 mocked acceptance checks, `../scripts/check-ui-fixes.py`. Parallel workers built the fixes on separate copies of the panel; the copies were then merged and verified.

Changes:
- **Local model status:** one trustworthy state everywhere (Off, Starting…, Ready, Unknown), shown in an attention color rather than error red, a Free GPU button, and spoken announcements.
- **Disconnects:** a single banner with Try Again and a "Showing information from …" time, dimmed out-of-date data, and no loading text left on screen forever.
- **Errors:** plain-language messages instead of raw developer text.
- **Task completion:** a "✓ Done" prefix in the tab title and an announcement.
- **Start Task:** disabled for signed-out accounts, with a stated reason in every case, plus quota warnings and an inline Start Local Model….
- **Session rows:** an Open link outside the row disclosure, relative times at every width, grouped repeats, Show More, a live running view, plain result text, and focus kept after Stop.
- **Accessibility:** field borders at least 3:1, hover contrast fixed, a text Low cue on quotas, invalid fields focused, error toasts that persist, a sidebar that reflows at 200% text, and rail tab order matching the screen.
- **Wording:** one vocabulary (Hosted Model, Harness, System), the project name as the page title, a simpler usage strip, Save Connection enabled only after a change, and updated docs.
- **Polish:** an Apple-style type ramp and a 4/8px spacing grid.

The Model, Refresh models and Thinking effort controls are unchanged, as the user asked.

Validation: check-ui-fixes passes 40/40, `../scripts/check-ui.py` passes, and 29 Python unit tests pass, including a new test for the backend messages. The visual review covered light, dark and increased contrast at 320 to 1440px. The installed WSL runtime has not been synced yet and still serves the previous panel.

Deployment (October 29, 2026, with the user's approval): with no task running, `ui/index.html` and `desktop_ui.py` were synced to /home/user/agent-workbench. Backups are `ui/index.before-critique-fixes.html` and `desktop_ui.before-critique-fixes.py`. Only workbench-ui was restarted, and it served HTTP 200 afterward. A GET-only browser check of the live panel at 1440px light and 390px dark showed Connected, no page errors and no overflow. The local model and gateway stayed off (MainPID 0).
