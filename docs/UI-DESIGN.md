# Harness interface direction

Reviewed October 28, 2026.

Harness is a small task launcher and session index. The workspace should prioritize the prompt and previous work; account setup and GPU controls belong on dedicated screens.

The redesign uses a warm, neutral canvas, a dark project rail, restrained type sizes, one primary action, and flat session rows. Agent selection is a compact native control. Session rows expose status and start time, with expandable answers and execution logs. Search and status filters work on the sessions returned by the existing API. Hash navigation supports browser back/forward and direct links.

These are design choices for this product, not a claim that one visual style defines good design in 2026.

## References and application

- [Linear, March 12, 2026: A calmer interface for a product in motion](https://linear.app/now/behind-the-latest-design-refresh). Applied the distinction between navigation and working content, consistent placement, and quieter separators.
- [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines). Applied native semantics, keyboard submission, visible focus, recovery paths, readable status text, and responsive checks.
- [OpenCode UI source](https://github.com/anomalyco/opencode/tree/dev/packages/ui/src), including [base tokens](https://github.com/anomalyco/opencode/blob/dev/packages/ui/src/styles/base.css) and [theme](https://github.com/anomalyco/opencode/blob/dev/packages/ui/src/styles/theme.css). Reviewed compact control sizing, neutral surfaces, and typography hierarchy. No application framework or source was copied.
- [Omnigent](https://github.com/omnigent-ai/omnigent) and its [web application](https://github.com/omnigent-ai/omnigent/tree/main/web). Retained the existing session application for follow-up conversation and permissions.

This checkout has no Git remote configured. The GitHub review concerned these relevant upstream repositories.

## Validation

Run the existing regression suite from ../package/agent-workbench with the installed runtime Python. UI browser checks are in ../scripts/check-ui.py; run with a separate Python environment containing Playwright and Chromium. Playwright is a verification tool, not an application dependency.

The browser suite mocks all API responses and writes. It checks search, filters, expansion during polling, setup links, keyboard submission, stopping, project switching, dialog focus/escape, empty states, disconnect handling, and all three screens at 320, 390, 768, 1024 and 1440 px.

PNG previews in ../artifacts/ui-evidence use fictional session data. checks.json records the browser checks. Real model inference was not part of validation.