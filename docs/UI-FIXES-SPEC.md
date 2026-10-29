# UI fixes specification

October 29, 2026. Source: the impeccable critique of `package/agent-workbench/ui/index.html` (score 21/40), recorded in AgentHub (`f6b606b1ecd1`). Brief: Apple Human Interface Guidelines and Apple Style Guide, maximum ease of use.

Acceptance tests: `scripts/check-ui-fixes.py` (one section per workstream). Regression suite: `scripts/check-ui.py`. Both mock every API; neither starts a model or writes to the real panel.

## Rules for every workstream

- **Edit only your copy.** Each worker gets its own copy of `index.html`. Never edit the project's `index.html`, `scripts/`, `docs/` or the installed runtime in WSL.
- **Stay in your regions.** Edit existing code only in the regions your workstream owns (listed below). Put new CSS, markup and JS between your own anchor comments: `/* ws-<name>:begin */ … /* ws-<name>:end */` in the stylesheet, `<!-- ws-<name>:begin -->` after the toast in the markup, and `// ws-<name>:begin` before the boot line in the script. New elements that must live inside an existing element owned by someone else are created from your JS, not by editing their markup.
- **Leave the model controls alone.** Don't change `#taskModel`, `#taskEffort`, `#reloadTaskModels`, `#applyLocalModel`, `#taskModelHint`, `#effortHint`, `.model-controls`, `loadTaskModels`, `updateEfforts`, `saveTaskSelection` or `taskPreference`, including their labels.
- **No dependencies.** Plain HTML, CSS and JS in the single file. The live server sends a CSP that allows inline scripts and styles but not `eval` or remote resources.
- **Apple writing style.** Button and menu labels in Title Case. Sentences with a period. A typographic apostrophe (’, U+2019). An ellipsis (…, U+2026) only on controls that open a dialog or need more input. No developer jargon in visible copy.
- **Accessibility floor.** Every new control is at least 44×44 CSS px, reachable by keyboard, and has an accessible name. Text contrast is at least 4.5:1 and UI boundaries at least 3:1 in light and dark. Animations stop under `prefers-reduced-motion: reduce`.
- **Use the shared helper.** `localStatus()` (already in the file) returns `off`, `starting`, `ready` or `unknown` (disconnected). Use it instead of reading `state.local` directly.
- **Done means:** your section of `check-ui-fixes.py` passes and `check-ui.py` still passes against your copy. Other sections are expected to fail on your copy; ignore them.

## Wave 1, workstream S: system status you can trust

Owns: `api()`, `refresh()` (all of it), `view()`, the rail status markup (`.rail-bottom`), the top bar's `#topGpu` link, `#connectionError`, and the CSS rules `.top-status`, `.dot`, `.rail-status`, `.connection-error`.

- **S1 Local model states.** `#topGpu` gets `data-state` equal to `localStatus()`.
  - `#gpuSummary` reads "Local model off", "Local model starting…", "Local model ready" or "Local model status unknown".
  - `#gpuState` on System reads "Off", "Starting…", "Ready" or "Unknown".
  - Never use the danger color for these states. Add an `--attention` token (light and dark, at least 4.5:1 on the top bar) for starting and ready.
  - Starting shows a small indeterminate spinner `.gpu-spinner` inside `#topGpu` (`aria-hidden`). It doesn't animate under reduced motion.
  - `#gpuToggle` never has the `danger` class. It reads "Start Local Model…" when off, "Stop Local Model" when starting or ready, and is disabled when unknown.
- **S2 Free GPU.** A `#freeGpu` button, "Free GPU", appears in the top bar only while the model is starting or ready.
  - With no running local task, clicking it stops the model through `action()` with `api('local',{action:'stop'})`.
  - If a job with role `local` is running or stopping, it opens `#freeGpuDialog` instead. Title "Stop the local model?", text "The running local task will stop too.", buttons `#cancelFreeGpu` "Cancel" (focused first) and `#confirmFreeGpu` "Stop Model".
- **S3 Announcements.** Add a visually hidden `#gpuLive` region (`aria-live="polite"`).
  - On a change to ready, it announces "Local model ready.".
  - On a change from starting or ready to off, it announces "Local model stopped. The GPU is free.".
  - Nothing is announced on first load.
- **S4 One disconnect banner.** `#connectionError` holds `#connectionMessage` and a `#retryConnection` button, "Try Again", which calls `refresh()` and is `aria-busy` while it runs.
  - Never connected: the message is "Can’t reach Harness.".
  - After a connection was lost: "Can’t reach Harness. Showing information from 9:11 PM." (time of the last good refresh, `toLocaleTimeString` with numeric hour and 2-digit minute). `#main` gets `data-stale="true"`, removed on the next good refresh.
- **S5 No eternal loading text.** If the first refresh fails:
  - `#project` has one option, "Unavailable".
  - `#homeUsageTime` reads "Usage unavailable".
  - `#sessions` shows an empty state: heading "Sessions unavailable", text "Harness isn’t responding.".
  - `#panelStatus` reads "Disconnected".
  - No visible "Loading…" or "Checking…" text remains in the rail or the Workspace view.
- **S6 Plain errors.** `api()` maps failures to these messages:
  - Network failure: "Can’t reach Harness. Check that it’s running, then try again."
  - Response that isn't JSON: "Harness sent an unexpected response (HTTP 500). Try again." (with the real status).
  - JSON with an `error` string: that string, unchanged.
  - JSON without `error` on a non-OK status: "Request failed (HTTP 409). Try again."
- **S7 Completion signal.** When a job that was running or stopping on the previous refresh becomes `done`, prefix `document.title` with "✓ Done · " and announce "Task finished: <title>." in a visually hidden `#taskLive` region (`aria-live="polite"`). Failed: prefix "Failed · ", announce "Task failed: <title>.". Use the job title, falling back to the agent name.
  - Stopped and interrupted get no prefix.
  - The prefix clears on the next `keydown` or `pointerdown`, or on a view change.
  - Nothing happens on first load.
- **S8 Live status.** `.rail-status` gets `role="status"`. Its dot reflects the connection: `data-connected="true|false"`, success color when connected, danger color when not, with the text unchanged.

## Wave 1, workstream C: the composer only starts tasks that can run

Owns: `updateRun()`, the `hints` object, the `.run-context` markup and `#agentSetup` (including its click handler), and the CSS rules `.run-context`, `.submit-group`, `.shortcut`, `#run`.

Messages go in `#runHint`. When Start Task is disabled, a reason is always shown.

- **C1 Sign-in.** The required account is `codex` for Codex, `claude` for Claude, Team (`coordinator`) and Research.
  - If `state.auth[account] === false`, Start Task is disabled and the hint reads "Sign in to Claude to use Research." (`Sign in to <Account> to use <Agent>.`). `#agentSetup` shows "Open Connections" (`#connections`). A `#checkAuth` button, "Check Again", calls `api('accounts',{})` through `action()`.
  - If `auth[account]` is `undefined` (still checking), don't block.
  - `#checkAuth` is hidden otherwise.
- **C2 Agent hints** (they no longer claim "signed-in"):

  | Agent | Hint |
  |---|---|
  | Codex | "Runs with your Codex account." |
  | Claude | "Runs with your Claude account." |
  | Team | "Claude leads a team of cloud agents." |
  | Research | "Claude searches the web and project memory." |
  | Cloud | "Runs on your hosted model. Billed by your provider." |
  | Local | "Runs on this computer’s GPU." |

- **C3 Quota warning (warn, never block).** A `#quotaWarning` element (`role="status"`) under the hint, hidden by default.
  - **Codex:** use the window with the least left. At 0% left or less: "Codex’s 5-hour allowance is used up. It resets at <time>." Under 20% left: "Codex has 8% of its 5-hour allowance left." Window names: 300 minutes is "5-hour", 10080 is "weekly", anything else is "<n>-minute".
  - **Cloud** (usage available): "Your OpenRouter spending limit is used up." at 0 remaining, or "Your OpenRouter spending limit is almost used up ($4.00 left)." under 20%. Use "OpenCode" when that is the provider.
  - **Reset time:** time only if the reset is within 24 hours, otherwise short weekday plus time.
  - **Other agents:** hidden.
- **C4 No project.** Start Task is disabled and the hint reads "Add a project to start a task.". `#agentSetup` shows "Add Project…" and opens `#projectDialog` (it must not change the hash).
- **C5 Disconnected** (`state` is null): the hint reads "Start Task is unavailable while Harness is disconnected.", and `#agentSetup` and `#checkAuth` are hidden.
- **C6 Local agent.**
  - Off: the hint reads "The local model is off." and a `#startLocalInline` button, "Start Local Model…", opens `#localDialog` without any network call. `#agentSetup` is hidden.
  - Starting: "The local model is starting. This can take a minute.", Start disabled, inline button hidden.
  - Ready: normal hint, Start enabled (subject to the existing local-model mismatch rule).
- **C7 Busy.** Start Task reads "Task running…" and is disabled. The hint reads "Claude is running in harness. Start another task when it finishes." `#agentSetup` "View Task" behaves as today. `#prompt` stays editable.
- **C8 Hosted model not set up:** "Connect a hosted model in Connections first." with `#agentSetup` "Open Connections".
- **C9 Kept as is:** the existing local-mismatch and loading-models behavior, and the Health Check and `#gpuToggle` disabling at the end of `updateRun()`.

## Wave 1, workstream D: session rows you can scan

Owns: `jobResult()`, `renderJobs()`, the session search/filter/scope listeners, the Sessions markup (`.session-section`), and every session CSS rule, including the session parts of the 1100px, 680px and `@container(max-width:45rem)` rules (other workstreams must not edit those three lines).

- **D1 One open action, not nested.** Each job renders as `div.session-row[data-id]` containing the existing `details.session` (keeping `data-id`, `data-state` and today's open/expand behavior).
  - Jobs with a URL also get `a.session-open` as a sibling of the `details`, never inside `summary`. It is visible without expanding the row. Its accessible name is "Open <title> session in a new tab", and the ↗ glyph is in an `aria-hidden` span.
  - Remove the duplicate "Open Session ↗" link inside the body.
  - No `summary` contains a link or button.
- **D2 Meta line.** `.session-project` shows the agent name (when the row has a title), the project name only in All Projects scope, the model and effort when requested, and the time (D3), separated by " · ".
- **D3 Relative time, at every width.** A `time.session-time` element inside the meta line, with `datetime` (ISO) and `title` (full `toLocaleString`). Text:

  | Age | Text |
  |---|---|
  | Under 45 s | "Just now" |
  | Under 60 min | "N min ago" |
  | Under 24 h | "N hr ago" |
  | Previous calendar day | "Yesterday" |
  | Older | `toLocaleDateString` short month and day ("Oct 28") |

  Remove the Started column and the `.session-columns` header row.
- **D4 Group repeats.** Consecutive jobs with the same display title, role, project and state, where the state is `failed` or `interrupted`, become one row showing the newest. It gets a `.session-repeat` badge reading "×3" with `aria-label="3 times"`. `#taskCount` still counts jobs.
- **D5 Show more.** Render 12 rows. If more remain, show a `#showMoreSessions` button, "Show 12 More" (or "Show N More" for fewer), that adds 12 rows per click. Reset to 12 when the search, filter, scope or project changes.
- **D6 Running rows.** For running or stopping jobs without an answer, `.session-answer` shows "Running · 2 min 5 s" (or "Stopping…"), the latest non-empty output line, and an indeterminate `progress.session-progress` labelled "Task in progress".
  - Elapsed formats: "45 s", "2 min 5 s", "1 hr 3 min".
  - The elapsed text updates every second in place (`[data-elapsed]`) without rebuilding the list.
  - Never show "Preparing the session…".
- **D7 Plain results.** The raw output stays in the log, whose summary is renamed "Execution Log".

  | State | Text |
  |---|---|
  | Failed (no answer) | "The task didn’t finish. Open Execution Log for details." |
  | Stopped | "You stopped this task." |
  | Interrupted | "Harness closed before this task finished." |
  | Done (no reply) | "The task finished, but no reply was captured. Open the session to review it." |

- **D8 Focus after Stop.** If focus was on a row's Stop Task button and that button is gone after re-rendering, focus that row's summary. If the row is gone, focus `#prompt`.
- **D9 Empty states.** This Project with no sessions: heading "No sessions in this project", text "Start a task above, or show sessions from all projects.", and a "Show All Projects" button that switches the scope. All Projects with none: keep "No sessions yet". Keep "No matching sessions" and Clear Filters.
- **D10 Tool order at 390px.** Tab order of search, scope and filter follows their visual order. Reorder the DOM and drop the `grid-row` overrides that reorder them.

## Wave 1, workstream A: accessibility details

Owns: the root color tokens and their dark and increased-contrast variants, the base `button`/`a` rules, the rail markup and CSS (brand, `#project`, `#addProject`, `.nav`, the 800px and 560px rail rules), `h1`, `renderHomeUsage()` and the usage CSS, `showToast()` and `.toast`, `action()`, both dialogs' markup, and the handlers for `#addProject`, `#projectForm`, `#cancelProject`, `#gpuToggle`, `#cancelLocalModel` and `#confirmLocalModel`. It must not edit the session lines listed under D.

- **A1 Field boundaries at least 3:1.** In light and dark, the borders of `.composer`, `#agent`, `#project`, `#sessionScope`, `#sessionSearch`, `#sessionFilter`, `#provider`, `#apiKey` and `#model` reach at least 3:1 against both the control's own background and its container's. `#agent` needs a real border.
- **A2 Hover contrast.** Every enabled button and link keeps text contrast of at least 4.5:1 while hovered, in light and dark. Today `#addProject` fails because `button:hover` beats `.add-project`.
- **A3 Low quota not by color alone.** When a bar is under 20% left, its label adds " · Low" (for example "8% left · Low"). It stays in `aria-valuetext`.
- **A4 Dialog errors.**
  - When saving `#projectDialog` fails, focus moves to `#projectPath`, which gets `aria-invalid="true"` and `aria-describedby` including `projectError`. Typing clears `aria-invalid`.
  - Clicking the backdrop closes `#projectDialog`, and closes `#localDialog` when no start is pending.
- **A5 Error toasts persist.** Error toasts stay until dismissed with a `#toastClose` button, "Close". Info toasts still hide after 7 seconds.
- **A6 Reflow at 200% text.** With the root font size at 200%, the sidebar is at most 40% of the viewport width at 768px and 1440px. `.nav a` and `h1` don't use `overflow-wrap:anywhere`, so words don't break mid-word. No horizontal overflow on any screen.
- **A7 Rail order at 390px.** The rail's tab order follows its visual order (no CSS `order` that reorders focusable items). Nav links are at least 8px apart.
- **A8 Kept as is:** the local dialog still focuses Cancel first, and Escape returns focus to `#gpuToggle`.

## Wave 2, workstream W: words, header and docs (after the wave 1 merge)

A single worker, on the merged file.

- **One vocabulary.** Glossary: Harness (the app), Hosted Model (the OpenRouter or OpenCode agent, also its Connections section), Codex, Claude, Team, Research, Local Model, System (the screen; the `#diagnostics` hash stays), Health Check (a System section). Replace "Workbench" and "Cloud Model" in visible copy.
- **Header.** The Workspace `h1` is the project name ("No Project" when none), with the path as its subtitle. The top bar shows only the view name. Remove `#projectName` and the "/" separator.
- **Labels.**
  - "Add Project…" without the "+" (an `aria-hidden` plus icon is fine).
  - "Project ID (Optional)".
  - A Linux-style placeholder.
  - Save Connection disabled until a field changes.
- **Usage strip.**
  - Unknown usage is text only (no dashed track).
  - One unavailable message.
  - No duplicate Claude usage link.
  - The OpenRouter card reads "$25.00 left of $50.00".
  - Weekly reset shows the date when it's more than 24 hours away.
- **Copy cleanup.**
  - Remove dead hidden markup (`.rail-caption`, the hidden rail paragraph).
  - Move "Team tasks use cloud models." into the Team hint.
  - Times use the locale default everywhere.
- **Backend messages** in `desktop_ui.py`:
  - "Local model is off. Use Turn on local model first." becomes "The local model is off. Start it in System first."
  - The cloud message becomes "Connect a hosted model in Connections first."
  - Update the test regex.
- **Docs.** Sync `docs/START-HERE.md` and `docs/DAILY-WORKFLOW.md` with the current labels.
- **Tests.** Update `check-ui.py` for any intentional text changes. Its acceptance section is `copy`, written after the merge.

## Wave 3, workstream P: polish

- **Type ramp.** Move to an Apple-like ramp: 13, 15, 17, 20, 22 and 28 px (as rem). Bring spacing onto a 4/8 px grid.
- **Visual check.** Re-check all screens in light, dark and increased contrast at 390, 768, 1024 and 1440 px.
- **Done means:** no behavior changes, and every suite passes.
