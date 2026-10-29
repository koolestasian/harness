# Harness architecture review · October 28, 2026

The desktop should run cloud agents by default and spend GPU resources only on
an explicit local session. The previous setup violated that expectation in three
places: Start-Workbench started inference, the coordinator advertised a local
worker, and AgentHub's Windows login script loaded a model in LM Studio.

All three paths have been changed. Opening Harness starts a small loopback web
control panel. GPU services stay disabled at login and WSL startup. Only the
panel's explicit Turn on local model button starts them. The coordinator's
worker list excludes local, even when the GPU model is running. No automatic
cloud-to-local fallback exists. The emergency desktop shortcut kills local
inference immediately rather than waiting for a CUDA batch to finish.

## Components kept

- Omnigent remains the session, permission, takeover and supervision layer.
- Native Claude and Codex use the existing signed-in subscription accounts.
- Pi remains the one worker for hosted open models and manual local inference.
- Hindsight stays the shared project memory; Git stays the durable task record.
- llama.cpp and the bounded gateway remain installed but off by default.
- The panel uses Python's standard library plus plain HTML/CSS/JavaScript.
  No frontend framework, SDK, database, Electron shell or new service dependency.

The panel is a small front door, not a replacement transcript system. Start a
task there, then use Open session for the existing Omnigent chat, permissions,
and follow-up conversation. It runs on 127.0.0.1:8787 with Host validation,
per-process anti-CSRF tokens, same-origin POST checks and no CORS allowance.
Keys are mode-0600 files outside the repo and are never returned to the browser.
Task output is private on disk, bounded, and redacted for known key values.

## Provider choice

| Option | Fit here | Integration |
| --- | --- | --- |
| Existing Claude/Codex accounts | Default everyday work, no GPU | Native workers, already signed in |
| OpenRouter | Broad hosted model choice and a live tool-capable catalog | Existing Pi through its OpenAI-compatible gateway |
| OpenCode Console pay-as-you-go | Curated coding models | Same Pi gateway, current Console endpoint |
| OpenCode Go | Optional coding subscription, separate session requirements | Reviewed, not silently treated as generic pay-as-you-go |
| Local llama.cpp | User-selected local/private chat and explicit local file tasks | Manual-only, no hosted memory or web MCP attached |

OpenRouter is the first hosted open-model option because it has a public live
model catalog with tool capabilities, context and pricing. The panel loads only
tool-capable models; no inference or purchase occurs when loading the catalog.
The key and exact model are user choices. Hosted policy/privacy varies by model
and upstream provider; a provider connection is not a promise of unrestricted
responses. Privacy controls and spending limits should be set in that account.

OpenCode's current Console works with other harnesses and translates text models
between API families. Free-tier chat models are restricted to the OpenCode app.
Go requires typical coding-agent traffic and stable session information. We
support the paid Console gateway here; we have not installed a second OpenCode
app or pretended a Go subscription is an interchangeable API key.

## Updates and compatibility

Checked upstream metadata and updated the private installation and source locks:
Omnigent 0.20.0, Pi 1.4.0, Claude Code 2.1.312 and Codex 0.165.0.
Node 22.23.4 remains compatible. No native user authentication files were copied.
Omnigent 0.20 requires agent working directories relative to the workspace;
generated profiles now use `cwd: .`, verified by a real native Codex UI launch.

No background updater or automatic optimizer was added. Versions stay pinned
and are changed together with the relevant checks, preventing the Pi minimum-
version failure seen in the original package. The existing AgentHub daemon can
keep running for memory; its startup now loads LM Studio only with an explicit
StartLocalModel switch. The Harness app never launches LM Studio.

## Evidence and limits

The current check report is /home/user/agent-workbench/evidence/desktop-ui-checks.txt.
Browser QA covers connection catalog loading and a real native cloud task while
local remains off. The GPU Start control is tested with mocked service commands;
it is deliberately not exercised on the gaming PC during this task. Local
generation with the newest Pi/Omnigent versions therefore remains unverified.
No OpenRouter or OpenCode key has been provided, so paid cloud generation remains
unverified. The integration is configured through Connections, not by editing code.

## Sources reviewed

- https://github.com/omnigent-ai/omnigent/releases/tag/v0.20.0
- Installed Omnigent 0.20 parser, session client, provider resolver and CLI help.
- https://openrouter.ai/docs/quickstart
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/api/v1/models (live catalog checked October 28)
- https://opencode.ai/v2/docs/console/harnesses/
- https://opencode.ai/v2/docs/console/harnesses/pi/
- https://opencode.ai/v2/docs/console/api/inference/
- https://opencode.ai/v2/docs/console/go/
- Official npm registry metadata for the three pinned agent packages.

The useful upstream ideas were provider independence, explicit capability-based
model selection and reuse of a native session UI. Adding another orchestration
framework, model router, database or desktop runtime would duplicate components
already installed and make this personal workbench harder to run.
