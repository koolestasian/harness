# Using Harness every day

## From VS Code

The **Harness: open** and **Harness: stop local model** tasks are now installed
in your VS Code user tasks. They are available through **Terminal → Run Task**
or **Ctrl+Shift+P → Tasks: Run Task**. The demo and newly initialized workspaces
also include project tasks. The open task starts the panel, never the GPU.

To keep the panel inside your editor:

1. Run **Harness: open** once to start the lightweight panel.
2. Press **Ctrl+Shift+P → Browser: Open Integrated Browser**.
3. Enter `http://127.0.0.1:8787`.
4. Move that browser tab beside your code. Use **Open ↗** on a session for
   follow-up chat or permission prompts.

You can also keep Harness in Chrome beside VS Code. Both use the same files
when the selected project is the folder open in your editor. Prefer opening
Linux projects through VS Code's WSL connection for Linux filesystem I/O.

Harness does not replace Copilot suggestions or automatically import your
Codex-extension chat. A Harness session, a Codex-extension chat and this chat
are separate conversations. Share explicit project files, decisions and task
checkpoints when changing tools; don't assume hidden chat history follows you.

Official references: [VS Code tasks](https://code.visualstudio.com/docs/debugtest/tasks),
[integrated browser](https://code.visualstudio.com/docs/debugtest/integrated-browser).

## Your personal workspace is ready

Select **personal-workbench** in Harness. Its folder is
`/home/user/projects/personal-workbench`, with stable ID `personal/workbench`.
It is a local Git repository; it has not been published or pushed anywhere.

| Folder | Purpose |
| --- | --- |
| `inbox/` | Questions, links, ideas and quick notes |
| `research/` | Source-backed briefs and decisions |
| `networking/` | Contact notes, promised follow-ups and unsent drafts |
| `projects/ACTIVE.md` | Desired outcomes, next actions and evidence |
| `weekly/` | Review open loops and choose next priorities |
| `.agent/` | Project identity, checkpoint records and reusable procedures |

The contact CSV is intentionally empty. Add only information you want your
chosen agent provider to process. Your Gmail, contacts, LinkedIn and calendar
are not automatically connected to Harness workers just because they are
available in this desktop chat. There is no automatic outreach or scraping.

## A practical daily loop

**Morning, 5 minutes:** put today's questions and commitments in the inbox. Ask
Claude to suggest three priorities from your own notes. Review the result.

**Focused work:** use one short task at a time. Choose **Codex** for implementation,
**Claude** for synthesis/drafting, **Research** for live source work, or **Team**
when independent work/review would justify its added time. These are starting
habits, not claims that one model is universally better.

**End of a task:** review its output, diff and checks. Save the decision and next
action to a file. A successful process exit does not establish a correct result.

**End of day, 5 minutes:** update promised follow-ups and the next action for
each active project. Create a checkpoint before switching models or devices.

**Weekly, 15 minutes:** review stale research, overdue promises and project
blockers. Keep the useful findings and their sources; don't save entire noisy
transcripts as knowledge.

## Research

Start with a decision, not an open-ended topic. Use **Research** with a bounded
question and a source/output contract. For example:

> Read inbox/search-options.md. Compare two approaches for the decision in that
> file. Use current primary sources, record retrieval dates, separate measured
> facts from assumptions, and name what you couldn't verify. Write a one-page
> brief to research/search-options.md with a recommendation and three acceptance
> criteria. Do not install anything or change application code.

For supplied notes only, use Claude or Codex and explicitly say **use only these
files; do not claim live verification**. Read the actual sources behind important
claims. If the web service is unavailable, the correct result is a stated gap.

## Professional networking

Use the contact tracker to keep promises and context, not to mass-message people.
Create a dated source note after an interaction. Then ask:

> Read networking/OUTREACH-RULES.md, networking/people.csv and the source notes.
> Choose at most three follow-ups due this week. Respect do_not_contact. Explain
> each choice with its source note and draft a short message using only recorded
> facts. Put the drafts in networking/drafts/YYYY-MM-DD.md. Do not send anything.

Review every draft for accuracy and tone. Sending through another app requires
your explicit instruction in that app/chat; there is no automatic send step here.

For a meeting, ask for a short preparation brief from your own notes: who the
person is, your last interaction, what you promised, two questions and a useful
next step. Distinguish documented facts from research leads.

## Your projects

Use **Add Project…** once per existing Git repository. Give it a stable ID such
as `personal/my-app`. Select that project in Harness and open the same folder in
VS Code. Before editing, commit or checkpoint your current state.

> Read the project instructions and relevant files. Reproduce issue X first.
> Change only files needed to fix it, run the relevant checks, and return the
> diff summary, test evidence and remaining risks. Don't merge, publish or push.

Keep only one writer in a working tree. A separate review should inspect a
fixed diff; concurrent implementation belongs in separate worktrees. Team
dispatch has workflow limits but is not an OS sandbox or a global cost budget.

For model handoff:

> Summarize the decision, exact files changed, checks actually run, unresolved
> problems and next action in docs/handoff.md. Create a workbench task checkpoint.
> A fresh session should read that checkpoint and the exact tracked source file
> before continuing. Don't invent missing prior context.

Shared memory helps recall curated facts, while the original files remain the
authority. Handoff packets cap their size and include file hashes; select a
small relevant source rather than exporting an entire chat.

## Choosing a hosted or local model

Your signed-in Claude/Codex accounts work now. **Hosted Model** requires your
OpenRouter or paid OpenCode Console key and a selected model. Configure provider
spending/privacy limits in that account. The gateway's local token cap is not a
hosted-model dollar budget.

**Local Model** is manual-only. Start it only when you want local inference,
and stop it before gaming. Its profile has no hosted memory or web MCP attached.
The desktop **Stop Local Model** shortcut is the immediate escape hatch. Opening
Harness, VS Code tasks, benchmarks and health checks leave the GPU model off.
