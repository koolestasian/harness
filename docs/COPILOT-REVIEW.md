# Copilot versus the custom Harness — October 28, 2026

Recommendation (inference): use VS Code/Copilot as the primary daily interface,
retain the project's useful files and memory, and keep manual local inference
as an optional separate capability. Do not migrate or delete anything solely
on this recommendation; the user has requested research, not a migration.

## Current primary-source findings

- VS Code 1.144 stable was released October 28. The installed desktop CLI reports
  1.144.0. It includes the Agent Host/shared Copilot harness, a unified Agents
  window, model comparisons and expanded cloud/session workflows.
- Copilot Fusion became generally available October 28. It can select Single,
  Cascade or Critique execution patterns. Fusion bills the models actually used;
  GitHub's efficiency benchmarks are vendor claims, not measurements on our tasks.
- The same release offers opt-in experimental local-model routing. Keep
  chat.copilot.localModel.enabled off and do not enable Local model auto routing
  for this user's cloud-first/gaming workflow.
- GitHub-verified MCP connectors are rolling out in public preview. GitHub lists
  26 services including Slack, Notion, Figma and Linear. This does not establish
  Gmail/contacts/LinkedIn availability for this account.
- Paid-plan cloud sessions can continue with the desktop offline. Their workspaces
  are separate; uncommitted desktop files do not follow automatically. Some
  documentation still marks the interactive cloud experience experimental.
- VS Code supports distinct Copilot, Local, Claude and Codex harness routes.
  A Claude model in a Copilot session is not the Claude harness. Provider/account
  selection determines billing. Native Codex Agent Host integration and Copilot
  Agent Host BYOK have experimental requirements; generic Copilot access does not
  imply use of existing ChatGPT or Claude subscription allowances.
- VS Code's Custom Endpoint supports Chat Completions, Responses and Messages.
  This is a plausible OpenRouter/OpenCode route, but paid generation, exact
  provider compatibility and access in the chosen harness need a live test.
- Plan page checked today lists Pro $10/month, Pro+ $39/month and Max $100/month,
  with AI Credits rather than a promise of unlimited model usage. Some third-party
  agent paths require Pro+/Max; choose based on the actual route, not model names.

## Why this fits the user

The user prioritizes easy VS Code operation, independent Mac use, broad model
choice and zero unsolicited local GPU use. A supported editor/agent interface
removes the separate control panel, service and native CLI-stream repair layer
from most daily work. Our custom setup already required a reply-delivery repair,
and its polished launcher remains Windows/systemd-specific.

Keep personal-workbench notes/templates, project source and acceptance criteria,
curated Hindsight records, original sources and the benchmark fixtures. Those
are portable assets. Copilot MCP compatibility and instruction discovery should
be tested explicitly; current tool setup does not migrate automatically.

Networking remains draft-only until an actual sending integration is configured
and explicitly authorized. Local inference remains manual, with no Fusion local
routing. No model was started and no account, subscription or editor setting
was changed during this research.

## Proposed pilot, not yet run

Use Copilot for one coding repair, one source-backed research brief, one networking
follow-up draft and one Mac session. Keep the existing harness available as a
fallback. Evaluate correctness, missing replies, provenance, corrections, time,
observed model and actual usage coverage. Use new held-out task variants; do not
claim quality superiority from the vendor announcement or our previous non-Copilot
benchmark. Retire the extra orchestration only if the pilot covers real needs.

## Sources

- https://code.visualstudio.com/updates/v1_144
- https://code.visualstudio.com/docs/agents/run/agent-harnesses
- https://code.visualstudio.com/docs/agent-customization/language-models
- https://code.visualstudio.com/docs/agents/reference/mcp-configuration
- https://github.blog/changelog/2026-10-28-route-and-orchestrate-models-with-github-copilot-fusion/
- https://github.blog/changelog/2026-10-28-github-copilot-fusion-now-supports-selection-of-local-models/
- https://github.blog/changelog/2026-10-28-connect-your-tools-to-copilot-without-all-the-setup/
- https://github.blog/changelog/2026-10-28-work-from-anywhere-with-a-new-connected-copilot-cloud-experience/
- https://github.com/features/copilot/plans
- Local evidence: code --version; ../benchmarks/REPORT.md; MAC-CLIENT.md.
