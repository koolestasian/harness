# Open Harness

**Copilot is now supported directly in this project.** Double-click
**../launchers/Open-Copilot.cmd**, open Chat and choose the Copilot session target and a hosted
model. See [COPILOT-START.md](COPILOT-START.md) for agents, slash workflows and
shared memory. The original desktop app below remains available.

Double-click **Harness** on your desktop. Pick a project, choose Codex or Claude,
type your task and press **Start Task**. Use **Open ↗** on a session for follow-up
chat and permission prompts. No terminal commands are needed.

For hosted open models, open **Connections**, choose **OpenRouter** or
**OpenCode Console**, paste the provider's API key, choose **Load Models**, select a model and choose
**Save Connection**. Then choose **Hosted Model** as the agent in your workspace. Existing provider credits or
billing are required. Loading a model list does not run inference.

The local model stays **off** when you open Harness. When you want it, press
**Start Local Model…** in **System**, wait for Ready, then choose **Local Model** as
the agent. Press **Stop Local Model** (or **Free GPU** at the top) when finished. The desktop **Stop Local Model**
shortcut also stops local inference immediately, even if a task is stuck.

The local profile does not connect to hosted memory or web tools. Team workers
use the existing shared project memory. They never switch to your GPU.

**Add Project…** accepts an existing Git folder and an optional stable ID such as
`personal/my-app`. Windows and Linux folder paths are supported. The included
demonstration project is ready to try.

If something fails, use **System → Run Health Check**, or inspect the task's
output. Reopen Harness if the panel asks you to reload after an update.

The control panel lives at http://127.0.0.1:8787 while Harness is running.
See ARCHITECTURE.md for the reviewed design and provider tradeoffs.

## VS Code and daily use

Use **Terminal > Run Task > Harness: open**. For an editor tab, use **Browser: Open Integrated Browser** and enter http://127.0.0.1:8787.

Select **personal-workbench** for the prepared research, networking and project notes. See DAILY-WORKFLOW.md and ../benchmarks/REPORT.md for examples and measured limits.
