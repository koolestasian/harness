# Desktop update — October 28, 2026

Use the desktop Harness shortcut and START-HERE.md for daily work. Local inference is now manual-only, excluded from team dispatch, and off by default. The older command examples below are optional advanced operations. Current verification is in STATUS.md.

# Start the local installation from VS Code on the Windows desktop

The Codex desktop app can start a new local task with Work in > This computer.
Alternatively, the following VS Code route attaches an agent directly to WSL
files on the desktop. The existing cloud chat does not move its files or history
there automatically. The local agent receives the package and handoff below.

1. Open an Administrator PowerShell. Run `wsl --list --verbose`. Reuse Ubuntu if
   it is already installed with VERSION 2. Otherwise install Ubuntu 24.04 using
   `wsl --install -d Ubuntu-24.04`. Restart if requested, then launch Ubuntu once
   and create its Linux username/password.
2. Install VS Code on Windows. Install Microsoft's WSL extension.
3. Download/extract the package. Arrange the inner folder so
   `C:\Users\user\Downloads\agent-workbench\workbench.py` exists. If Downloads is
   elsewhere, substitute its actual /mnt/<drive>/... path in the command below.
4. In an Ubuntu terminal, run:

```bash
mkdir -p ~/agent-workbench
cp -R /mnt/c/Users/user/Downloads/agent-workbench/. ~/agent-workbench/
cd ~/agent-workbench
code .
```

5. Confirm VS Code shows WSL: Ubuntu or WSL: Ubuntu-24.04 at bottom-left.
   Install OpenAI's Codex extension, and use Install in WSL if the Extensions
   view offers it. Open Codex from its sidebar icon or the Command Palette command
   Codex: Open Codex Sidebar, then sign in. Start a chat working locally in the
   open folder. Ask it to run `pwd` and `uname -a` before installation; its path
   should be /home/<Linux-user>/agent-workbench, and the kernel should be WSL.
6. Give the agent the following handoff:

```text
Continue installing this prepared agent-workbench MVP on my desktop.
Read README.md, STATUS.md, docs/GUIDE.md and templates/PROTOCOL.md first.
I authorize the installation and routine reversible setup work.

Desktop: Windows 11 Pro, RTX 4080 SUPER 16GB, Ryzen 9 7900X, 64GB RAM.
Portable client: 14-inch MacBook Pro M2 Pro with 16GB unified memory.

First verify that your shell is actually inside this desktop's WSL2 environment.
Use the existing package and preserve existing native agent and editor settings.
Install the pinned tools with scripts/setup.sh; connect my native Claude/Codex
accounts and Hindsight shared memory. Guide me through account sign-in or hidden
credential prompts when required. Keep credentials out of the repository/chat.

Use a new demonstration Git repository for initial checks, then initialize my
chosen project with a stable project ID when supplied. Configure and test CUDA
inference, starting with the 36,864-context local profile. Verify runtime/model
compatibility and actual VRAM use before declaring the 27B profile usable.
Start the bounded local gateway on 8082 in front of llama.cpp on 8081. Use a build
supporting /v1/chat/completions/input_tokens. Run doctor --live --write-check
--inference-check --project PATH; verify source fidelity and real tool generation.
Configure useful VS Code launch tasks, verify real retain/recall, and run a real
short turn with each available harness. Set up durable server hosting when an
owned target/account is available. Prepare the Mac client instructions.

Update STATUS.md with verified results, exact commands and remaining blockers.
The cloud preparation passed fifteen automated checks and server auth/restart checks; it
did not install on my personal machines or verify their GPU/account access.
```

If you prefer to run the package installer yourself before opening the agent:

```bash
bash scripts/setup.sh
export PATH="$HOME/.local/bin:$PATH"
workbench auth codex
workbench auth claude
workbench configure
```

The final command asks for the Hindsight token using a hidden local prompt. The
full guide covers project initialization, launch commands, handoffs and verification.
