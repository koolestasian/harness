# Harness usability audit

October 28, 2026. Playwright Chromium against the actual loopback panel. No live POST requests, model generation, or GPU starts. Screenshots and measurements: ../artifacts/ui-evidence/audit-before/. Separate controlled fixtures will exercise writes.

The target is a personal launcher: readable text, quick task entry, usage bars on the home page, recognizable past work, and low explanation overhead. This is a focused usability audit, not an independent accessibility certification.

| Priority | Observed problem and evidence | User impact | Implementation and acceptance criterion |
| --- | --- | --- | --- |
| High | Sessions begin at y=818 on a 1280×800 laptop, y=1226 on a 390px phone. | Continuing a conversation requires scrolling past the entire composer and verbose quota section. | Remove duplicated introductory copy, reduce unused prompt height, compact usage without moving it off home. Aim for sessions above y=700 on laptop and y=1000 on phone with the measured usage fixture. |
| High | Native progress uses undefined --green; tracks look fully filled even when live Codex reports 50% remaining. | The bars communicate the wrong amount. | Explicit semantic fill and neutral track; assert 0/50/100%, missing, and low remaining states. Unknown is text plus a neutral marker, never a fake filled bar. |
| High | Usage copy contains literal question marks: Claude ? Research ? Team, Check usage ?, refreshes automatically. | The page looks broken and qualifications are hard to parse. | Rewrite short provider-specific labels, readable separators and external links. Keep Claude uncertainty explicit. No guessed quota. |
| High | Typed audit draft disappears after reload. | A routine refresh can destroy work before submission. | Store drafts per project in sessionStorage, restore after reload, preserve across switching projects, clear only after a successful submission of that same text. Do not save API keys. |
| High | 9 live rows have only 5 unique names; repeated Codex and Health check headings identify an agent rather than the task. | Finding a previous task requires opening rows one by one. | Persist a bounded task title for new tasks, use it in rows and search, retain honest legacy labels. Expose direct session links in the row. |
| Medium | Three historical failed checks automatically expand into identical messages. | Old errors dominate recent work and stretch the list. | Auto-expand only active tasks. Keep failures visibly labeled and details one click away. |
| Medium | Project selection and session list scope are disconnected: all projects appear under a selected project without explanation. | The selected project feels unreliable. | Default list to current project with explicit Current project / All projects control; always show a running task in the composer status even when it belongs elsewhere. |
| Medium | Agent selection resets on reload; project selector truncates the folder name. The original project reload probe selected an already-active project, so that result alone does not prove persistence. | Repetitive setup and weak orientation. | Remember project and agent preferences in localStorage; show full path via existing context/title. Test with two distinct projects. |
| Medium | Polling rebuilds usage and changed session DOM. | Keyboard focus and reading position can be lost during updates. | Skip identical usage renders; preserve focused session control, expansions and scroll positions during changed output. Test after simulated polling. |
| Medium | Starting/loading states disable controls without durable inline request errors; other refreshes can re-enable a pending control. | Unclear failure recovery and duplicate requests. | Pending-state guards for operations; inline task errors that survive the toast timeout; contextual busy/setup explanation beside the composer. |
| Medium | Home usage links measured 16px high; top local-status link 22.5px. | Small click areas despite larger body text. | Increase hit areas to at least 32px for utility links and 40px for primary controls without reducing typography. |
| Low | Connections repeats several sentences around every input. | Setup requires reading more than making decisions. | Shorten redundant instructions; retain key storage, provider billing, and local-model consequences where the user acts. |

Other observations: no horizontal overflow or JavaScript errors in the initial live run at 320/390/1280/1440. Controls had associated labels. A skip link appeared in full-page captures, but direct DOM inspection showed it outside the viewport and unfocused; treat that as a screenshot artifact rather than a proven UI defect. Do not remove keyboard skip navigation.

Implementation remains plain HTML/CSS/JS plus a small bounded title field in the existing Python job record. No new product dependency, coordinator, provider integration, synthetic sessions, or generated quota data.
## Implemented and verified

All planned fixes above are implemented. New sessions store a redacted first-line title capped at 120 characters. Existing records retain their original agent labels; no invented task titles were added. Drafts persist only in the same browser tab and are separated by project; project/agent preferences persist in that browser. API keys are never placed in browser storage.

Measured live results with quota data loaded:

| Measurement | Before | After |
| --- | ---: | ---: |
| Sessions start, 1280px laptop | 818px | 665px |
| Sessions start, 390px phone | 1226px | 958px |
| Workspace height, 1280px | 1982px | 1423px |
| Draft survives reload | No | Yes |
| Horizontal overflow, tested live widths | None | None |
| JavaScript errors | None | None |

The live workspace defaults to the selected project and collapses old failures. Eight current-project records remain intact; the ninth record is accessible through All projects. After the reload preference probe switches project, the visible count changes as expected. Quotas remain asynchronous: the initial checking state can briefly appear after restarting the panel. Unknown quotas remain explicitly unknown. With known quotas, the controlled fixture independently measures the session list at 666px on laptop and 959px on phone.

Validation:
- 26 Python unit tests pass, including title length, secret redaction and persisted job metadata with worker launch mocked.
- Playwright Chromium passes all three screens at 320/390/768/1024/1280/1440px. Functional checks include title search, direct links, scopes, empty/failure/disconnect states, zero/full/unknown quotas, per-project drafts, preferences, keyboard submission, skip navigation, dialog focus, polling focus/expansion, cross-project busy tasks and historical failure collapse.
- All functional write requests use isolated mocks. The live audit permits GET requests only.
- Before/after screenshots were inspected. See ../artifacts/ui-evidence/audit-before, ../artifacts/ui-evidence/audit-after, and ../artifacts/ui-evidence/checks.json. Generic preview screenshots use fictional data; live audit screenshots show the actual panel.
- git diff --check passes for changed implementation files.

Deployment: copied only ui/index.html and desktop_ui.py into the installed WSL runtime, after confirming no active tasks. Restarted only workbench-ui.service. Backups are under /home/user/agent-workbench/evidence/before-usability-audit. Updated relevant source manifest entries. Local model and gateway MainPID remained 0. Release ZIPs were not rebuilt.