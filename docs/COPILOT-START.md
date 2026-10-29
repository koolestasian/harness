# Use Harness with Copilot

**Mac SSH recovery:** the newer Agent Host connection currently fails on this
PC. This workspace now keeps **Local** visible and disables automatic preference
for the Copilot harness. In the SSH editor's **Chat** view, start a new chat,
choose **Local** as the session target, then select a hosted Copilot model.
The Local harness uses the editor's extension host and does not depend on the
failed Agent Host connection. It is not available in the separate Agents window.
The Local harness name does not mean local-model inference. GPU routing remains
off. This is a fallback; the newer Copilot/Codex Agent Host connection is not
claimed repaired. Keep the SSH editor open while its Local session works.

The failing SSH editor server reports **1.143.1**, while its managed Agent Host
reports **1.144.0**. Update VS Code on the Mac with **Check for Updates**, save
edits, quit VS Code fully with **Command-Q**, then reopen and reconnect SSH.
This aligns the client/server versions before retesting; the mismatch is a
possible contributor, not a proven root cause. Select Copilot explicitly to
test its newer host, or Local to use the fallback.

Both `.vscode/mcp.json` (editor format) and `.mcp.json` (Copilot format) point to
the existing AgentHub server; the connection check verifies that they match.

Double-click **../launchers/Open-Copilot.cmd**, or open **this Harness folder** in Windows VS Code. Open **Chat**, choose the
**Copilot** session target, select a hosted model and describe your task.
Sign in to GitHub if VS Code asks. This setup does not purchase a plan or
change your account. No Harness terminal or browser panel is needed for Copilot.

## Everyday work

Choose **Harness Research**, **Harness Networking** or **Harness Review** in the
agent picker for focused work. Research can read web sources; networking and
review list reading/search tools only. None of these roles has a shell or
sending tool in its declared tool list. These are tool selections, not an OS
sandbox; review the running session's tool inventory on first use.

In a regular Copilot session, type `/` and choose a workflow:

| Workflow | Example |
| --- | --- |
| `/harness-research` | Compare the current options for my project, citing primary sources. |
| `/harness-networking` | Draft a follow-up to this contact using the attached notes. |
| `/harness-project` | Fix this bug and run the relevant checks. |

These are skills in `.github/skills`, not Local-only `.prompt.md` files. The
instructions in `.github/copilot-instructions.md` provide this project's context.
Model choice stays in your picker; no model names or subscription tiers are pinned.

## Shared memory

The root `.mcp.json` connects Copilot to your **existing Windows AgentHub** using
its private Python environment. It needs no API key, npm install or GPU model.
If VS Code asks you to trust/start that server, inspect the two AgentHub paths
and allow it to connect. Memory data remains outside OneDrive in AgentHub's
existing data directory; retrieved cloud-allowed snippets enter your hosted
Copilot session. Local-only records are excluded by the server's tools.

On the first memory lookup, Copilot may display **Allow tool from agenthub?**
for **agenthub: memory_search**. Choose **Allow in this Session** to permit
lookups in that session. Keep the default manual permissions for other tools.

Start with: **Recall this project's recent decisions from AgentHub.** End with:
**Save the decisions and actual checks, and checkpoint any tracked task.**
The focused agents allow memory search only; use the regular Copilot agent to
save a checkpoint. The MCP connection does not launch queued workers itself.

Use **Terminal > Run Task > Harness: check Copilot memory** for a connection
check. It tests the exact workspace configuration and a project-scoped recall,
without printing memory contents, changing memory or starting a model.

The original Harness panel continues to use its existing Hindsight banks.
AgentHub and Hindsight are separate memory stores; this change does not migrate
old conversations or merge their histories.

## GPU and the original app

Copilot local model routing is explicitly disabled for this workspace. Use a
hosted model in the picker. For a local-model task, open **Harness: open** from
**Terminal > Run Task**, then explicitly turn the local model on in the panel.
Use **Harness: stop local model** or the desktop stop shortcut when finished.
Opening either interface does not start inference.

## If customizations do not appear

Run **Developer: Reload Window**, start a new Copilot chat, then use
**Chat: Open Customizations** to inspect the agents and skills. Open the whole
Harness folder, not only `../package/agent-workbench`. Check the selected session
target is Copilot. Account policy or a missing sign-in can restrict availability.

## Mac SSH: automatic reconnect gives up

For **Automatic reconnect gave up after 10 attempts**, first use **File >
Close Remote Connection** on the Mac, reconnect with **Remote-SSH: Connect to
Host**, and reopen this folder. Start a new chat with **Copilot** as the session
target. A stale Codex chat can reference a thread missing from the current
server; continuing that chat is separate from verifying Copilot connectivity.

If reconnecting reuses the same failed agent connection, save open edits and
run **Remote-SSH: Kill VS Code Server on Host...** from the Mac Command Palette.
Select the PC, reconnect, reopen this folder and start a fresh Copilot chat.
Use the official command rather than deleting server or extension directories
by hand. This recovery step must be run from the client that owns the connection.

If that also fails, use the **Local** fallback described at the top of this
guide. It still supports hosted Copilot models, project instructions, skills
and custom agents. It does not provide Agent Host session continuity; keep
the editor open. No automatic tool approvals are enabled by this configuration.

During the October 28 investigation, SSH remained running while VS Code's
remote agent proxy reported `ECONNREFUSED` at its recorded loopback upstream.
The Codex extension also reported `thread not found`. These observations
identify failed agent/session connections; they do not establish why the
upstream listener disappeared. In the observed case, a simple client reconnect
reused the failed upstream. The server recovery command was then recommended;
its result still needs to be observed in the Mac client.

See Microsoft's [Remote SSH troubleshooting](https://code.visualstudio.com/docs/remote/troubleshooting)
and [remote agent sessions](https://code.visualstudio.com/docs/agents/run/remote-agent-sessions).

The MCP paths target this Windows desktop. A separate Mac checkout or WSL
remote window needs an AgentHub server accessible on that host and corresponding
paths in `.mcp.json`; the Python source/skills do not require Windows. Do not
expose the memory service publicly to make it reachable. To use the prepared
Windows MCP connection from your Mac, use VS Code Remote SSH to this PC and open
this folder. See `MAC-CLIENT.md` for the existing PC connection details.

## Compatibility references

Configuration follows the current October 28, 2026 documentation:
[Copilot agents](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference),
[skills](https://code.visualstudio.com/docs/agent-customization/agent-skills), and
[portable MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).
Copilot quality/latency has not been benchmarked here; the old benchmark results
remain evidence about the original Harness only.
