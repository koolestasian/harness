# Open Harness

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

Open **Models** to see the local models you have downloaded and pick the one the
Local Model agent uses. **Discover** searches Hugging Face for GGUF models, lists
each quantization with its size and an estimate of whether it fits the 16 GB GPU,
and downloads it into ~/models. Downloads resume after an interruption; choosing
or downloading a model never starts the GPU.

For **Claude**, choose a model (Fable 5.1, Opus 5.5, Sonnet 5.5 or Haiku 5.5) and a
thinking effort from Low to Max. Your Claude plan decides which models you can use.
The Claude usage bars show the same 5-hour and weekly limits as Claude Code's
`/usage`.

The local profile does not connect to hosted memory or web tools.

**Add Project…** accepts an existing Git folder and an optional stable ID such as
`personal/my-app`. Windows and Linux folder paths are supported. The included
demonstration project is ready to try.

If something fails, use **System → Run Health Check**, or inspect the task's
output. Reopen Harness if the panel asks you to reload after an update.

The control panel lives at http://127.0.0.1:8787 while Harness is running.
See ARCHITECTURE.md for the reviewed design and provider tradeoffs.

## VS Code and daily use

Use **Terminal > Run Task > Harness: open**. For an editor tab, use **Browser: Open Integrated Browser** and enter http://127.0.0.1:8787.

Select **personal-workbench** for the prepared research, networking and project notes. See DAILY-WORKFLOW.md and benchmarks/REPORT.md for examples and measured limits.
