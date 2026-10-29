# Desktop update — October 28, 2026

Use the desktop Harness shortcut and START-HERE.md for daily work. Local inference is now manual-only, excluded from team dispatch, and off by default. The older command examples below are optional advanced operations. Current verification is in STATUS.md.

# Use your agent workbench

## What goes where

- Windows desktop: Ubuntu 24.04 in WSL2, VS Code Remote WSL, Omnigent, native
  Claude/Codex workers, Pi and the local CUDA model endpoint.
- M2 Pro / 16GB: VS Code, the same workbench, cloud models, shared-memory access.
  Its local endpoint can be an SSH tunnel to the desktop. An offline small-model
  fallback is optional and is not installed by this package.
- Hindsight Cloud: durable shared memory reachable while the desktop is off.
- Optional independent Linux server: central Omnigent coordination. Both
  machines register as hosts. Local Omnigent servers also work for the first MVP;
  central Hindsight and Git still provide shared knowledge and task records.

## 1. Install on each machine

Keep the extracted package in a permanent directory. The launcher points there.
Never copy an existing .venv between operating systems.

### Windows desktop

Run this from the extracted package in PowerShell:

```powershell
.\scripts\setup-windows.ps1
```

If Ubuntu is newly installed, open it once, create the Linux username, reboot if
Windows requests it, and rerun. The package is copied to `~/agent-workbench` inside
Ubuntu. Use Ubuntu's terminal for the following commands. Store project repos in
`~/projects`, and open them with VS Code's WSL connection for Linux filesystem I/O.

### MacBook

Install Apple's command-line developer tools (`xcode-select --install`) if Git is
missing. The installer uses Node.js 22+ and tmux. It installs tmux with Homebrew
when Homebrew is already present; otherwise it explains the missing prerequisite.
It downloads a checksum-verified private Node runtime if the system Node is too
old or absent. Install Homebrew from https://brew.sh if needed.
Then run:

```bash
cd /path/to/agent-workbench
bash scripts/setup.sh
export PATH="$HOME/.local/bin:$PATH"
```

Add that PATH export to ~/.zshrc on the Mac or ~/.bashrc in Ubuntu if it is not
already there. Restart VS Code afterward so its tasks inherit the launcher path.

The installer uses an isolated Python environment and local npm prefix. It does
not overwrite your native Claude/Codex settings. Workbench's own Omnigent provider
config lives in `~/.config/agent-workbench/omnigent`, not `~/.omnigent/config.yaml`.

## 2. Sign in once on each machine

Use the pinned installed CLIs, not an unrelated system executable:

```bash
workbench auth claude
workbench auth codex
```

Complete the normal provider login. Subscription features and rate limits follow
your accounts. This package cannot create subscriptions or complete an account's
interactive login without the owner. It does not copy OAuth credentials between
harnesses. API-key/BYOK configuration is available through Omnigent's normal setup
flow if desired; the supplied defaults use native subscription providers.

## 3. Connect shared memory

Create or use your Hindsight Cloud account at https://ui.hindsight.vectorize.io
and obtain an API token. On BOTH machines:

```bash
workbench configure
```

Paste the token at the hidden prompt. It is stored with file mode 0600 outside
your projects and never written into their Git files. Use the SAME account/server
on both machines. To use an owned server instead:

```bash
workbench configure --memory-url https://memory.your-domain.example
```

Project memory is accessed through Hindsight's native MCP endpoint, advertising
only recall, sync_retain, and get_document to limit schema overhead. These tools
still call the real Hindsight service. Filtering tool descriptions is not a
server authorization boundary. This MVP relies on explicit agent memory calls;
it does not claim to capture every native transcript automatically.

## 4. Initialize a project

```bash
workbench init ~/projects/my-app --id personal/my-app
cd ~/projects/my-app
git add .agent .vscode/tasks.json
git commit -m "Configure shared agent workbench"
git push
```

Use a stable owner/project ID, and the SAME ID on both machines. It is hashed into
a stable bank ID, independent of local paths or harness. Different project IDs
get different banks. Clone/pull the repository on the Mac, then run the same init
command there with its local path. If you already had .vscode/tasks.json, init
preserves it; add equivalent process tasks manually or use the terminal commands.

Existing AGENTS.md and native harness configurations are preserved. Generated
bundles are outside Git and rebuilt on launch from the supplied role templates.
Edit the package templates to tune the workflow, and keep those edits versioned.

## 5. Verify memory and local inference

```bash
workbench doctor --project ~/projects/my-app --live --write-check
```

This checks the MCP handshake, required tools, a fresh random verification fact,
its recall result with the correct document ID, and the retrieved original source.
Application-level JSON errors also fail, even when MCP reports transport success.
The fixed deployment-check document is synthetic; avoid simultaneous write checks
in the same bank. This is a roundtrip test, not a general reasoning benchmark.
The command also checks CLI presence, native login, generated specs, advertised
local model and gateway configuration. Add `--inference-check` after starting the
local model/gateway to verify actual generation and a structured tool roundtrip.
Login status alone does not prove a frontier model request succeeds: try one
short real turn with each worker.

BLOCKED means a component is not ready. The command returns nonzero on any failed
check and saves a local verification report; it never calls a missing integration
successful. A Mac without a reachable desktop local endpoint reports that component
blocked even if its frontier workers and memory are usable.

## 6. Configure the desktop local model

Use a current CUDA-enabled llama.cpp build in WSL and confirm `nvidia-smi` works.
The Windows NVIDIA driver supplies WSL GPU support; avoid installing a second
Linux display driver into WSL. Acquire the desired GGUF from its trusted publisher.
The initial profile targets Qwen3.8-27B IQ3_S because a 16GB GPU must also fit KV
cache and runtime buffers. Actual model support, quantization quality and speed
must be verified on this GPU; no GPU was attached to the preparation workspace.

```bash
bash scripts/local-model.sh /path/to/Qwen3.8-27B-IQ3_S.gguf
```

This initially requests 36,864 context, one generation, Q8 KV cache and GPU layers.
It enables the Jinja chat template for tools and disables silent context shifting.
If the runtime rejects quantized hybrid caches, use a supported cache configuration;
reduce GPU layers/context or use a smaller model if VRAM is insufficient. These
settings are a starting profile, not a measured performance guarantee.

The backend listens on 8081. In another terminal, start the bounded gateway:

```bash
workbench configure --local-backend-url http://127.0.0.1:8081/v1 --local-url http://127.0.0.1:8082/v1 --local-model qwen3.8-27b
workbench gateway
```

Leave that terminal open. In a third terminal:

```bash
workbench doctor --project ~/projects/my-app --live --inference-check
workbench launch local --project ~/projects/my-app --prompt "Read .agent/PROJECT.json and report its project ID."
```

The gateway uses the same llama.cpp server's `/v1/chat/completions/input_tokens`
endpoint on the complete request, including tools, template and tool results.
Use a current llama.cpp build that supports it; unavailable counting blocks the
request instead of estimating. Text/tool messages only: this MVP rejects image
and audio content. It caps input at 24,576 tokens and output at 8,192, with 1,024
tokens of additional headroom in the 36,864 profile. One request runs at a time;
another receives HTTP 429. An oversized request is rejected without truncation.
Checkpoint, narrow the task, and start a fresh session. Direct calls to 8081
bypass the gateway. These settings preserve space; they cannot guarantee quality.

For portable access over Tailscale, use SSH forwarding rather than publishing the
unauthenticated local inference listener. The SSH destination must be able to
reach the WSL listener; an SSH server INSIDE WSL works directly. A Windows-host
SSH server may need Windows-to-WSL localhost forwarding verified first.

```bash
ssh -N -L 8082:127.0.0.1:8082 YOUR_SSH_USER@YOUR_DESKTOP_TAILSCALE_HOST
```

Then the Mac uses `http://127.0.0.1:8082/v1` and the gateway on the desktop; do not
start another gateway on that Mac port. The desktop's single gateway admits one
request across both machines. Its default bearer key `local` is for the loopback/
SSH-tunnel workflow, not a credential for publishing the listener on a LAN.
If you set LOCAL_MODEL_API_KEY, use the same value in the backend and both clients.
If the desktop is asleep,
local inference is unavailable; your hosted memory and cloud workers still work.

## 7. Daily work from VS Code

Open the project, then Terminal > Run Task > Agents: coordinator. Other tasks
launch Claude, Codex, local, or research directly. Or use:

```bash
workbench launch coordinator --project ~/projects/my-app
workbench launch coordinator --project ~/projects/my-app --brain codex
workbench launch research --project ~/projects/my-app
workbench launch claude --project ~/projects/my-app
workbench launch codex --project ~/projects/my-app
```

The Omnigent web UI supplies session supervision and takeover. The VS Code tasks
are the reliable MVP integration; they do not pretend to implement a full custom
Copilot extension. You can keep using Copilot for inline suggestions independently.

Example task:

> Read the project state. Research the current authentication design and propose
> acceptance criteria for fixing refresh-token races. Use one bounded investigation
> per independent question, then implement in a separate worktree and have another
> actual model provider review the fixed diff. Record evidence and the next action.

The coordinator uses one implementer for small tasks and independent review for
substantial work. It targets <=3 active workers and one local generation. The
dispatch policy limits sends per turn, not total concurrency; the overall worker
limit is currently a prompt rule. Children cannot create their own agent trees.
Native workers retain their own permission behavior. The human merges changes.

Research uses the live Keenable MCP search/fetch endpoint shipped in Omnigent's
own example; its public service has availability and rate limits. Freshness must
be reported as unverified when it is unavailable. Worker write scopes and reviewer
read-only behavior are workflow rules, not an OS isolation guarantee.

## 8. Switch devices or models

Before leaving the desktop:

```bash
workbench checkpoint auth-race --project ~/projects/my-app \
  --summary "Reproduction added; fix pending" \
  --next "Inspect refresh lock ownership" \
  --evidence "docs/research/auth-race.md"
```

Review/commit/push the task record and your changes. On the Mac, pull the same
branch before starting a fresh session. Ask it to read the task record and recall
relevant decisions. A dirty worktree does not travel with a commit: commit the
changes or transfer a saved patch as a separate artifact. One worker owns each
task record; parallel workers use separate task IDs. This MVP uses Git for task
synchronization, not live distributed locking or automatic Git push/pull.

Use `--continue` to resume a compatible Omnigent session. Switching harnesses is
best treated as a fresh session with a task handoff, not transferred hidden reasoning.

Attach an exact, bounded task packet to that fresh session:

```bash
workbench packet auth-race --file docs/research/auth-race.md
workbench launch codex --task auth-race --file docs/research/auth-race.md
```

Run from the project, or supply `--project`. Included files must be tracked UTF-8
files inside the repo, <=16KB each; the packet caps its serialized data at 24KB
and includes hashes and current Git state. It rejects oversized input instead of
silently cutting evidence. Choose files carefully: this is not a secret scanner.
Packet bytes do not equal model tokens; the gateway counts the full local request.

Save curated knowledge before publishing it:

```bash
workbench memory save docs/research/auth-race.md --task auth-race --kind verified-finding --source docs/repro.md
workbench memory flush
git add .agent/findings
```

Write a concise finding with verification commands/results in that source file;
choose `agent-claim` for unverified results and `user-decision` for an actual user
decision. The workbench records project, task, observed date, Git revision/dirty
state, original source and text. Findings remain in .agent/findings during an
outage. Review, commit and push them for the other machine; `memory flush` can be
retried there. Stable document IDs prevent retries from creating separate named
documents; this is convergent publication, not an exactly-once transaction.
Per-server/project receipts live privately on each machine, so another machine
may republish the same document. Retain original files as the recovery source.

## 9. Optional independent Omnigent server

The deploy/ directory includes a single-instance Docker server with persistent
SQLite/artifacts and built-in account auth. Use an owned Linux machine; the cloud
workspace used to prepare this package is not permanent hosting. Start with:

```bash
bash deploy/start.sh
```

It generates first-run secrets privately. Access is loopback-only initially; use
an SSH tunnel or an authenticated HTTPS/Tailscale endpoint. Configure the server's
external base URL and allowed origin before remote browser use. Log in with the
account name `admin` and the generated password (see deploy/README.md).

On each client:

```bash
workbench configure --server-url https://YOUR_OMNIGENT_HOST
```

Run the package's pinned Omnigent with `OMNIGENT_CONFIG_HOME` pointing at the
workbench config, log into that URL, then register the machine:

```bash
export OMNIGENT_CONFIG_HOME="$HOME/.config/agent-workbench/omnigent"
./.venv/bin/omnigent login https://YOUR_OMNIGENT_HOST
./.venv/bin/omnigent host --server https://YOUR_OMNIGENT_HOST --background
```

`omnigent host enable --server ...` can install its per-user persistent service
after the foreground setup and actual credentials work. On WSL, Windows sleep and
WSL shutdown still stop workers; service installation is not an always-on guarantee.

## 10. Improve after the MVP

Every `workbench launch` prints a run ID and saves start/end time, exit status,
Git state and a fingerprint of the workbench settings, templates, code and locks.
Native CLI settings and remote server changes are outside that fingerprint.
Exit status does not mean the task was accepted. Review it with actual evidence:

```bash
workbench outcome RUN_ID --accepted yes --task-type coding --model ACTUAL_PROVIDER_AND_MODEL --evidence docs/test-results.md --corrections 0
workbench score --project .
```

Optionally add measured `--input-tokens`, `--output-tokens` and `--cost-usd`.
Include attempts, repairs and review in the reported total for that launch; do not
double-count separate launches. Omit usage you cannot measure. Scores group by
project, task type, actual model and config fingerprint; cost per accepted run is
reported only with complete cost coverage and at least one accepted run. It is
descriptive evidence, not an automatic model ranking or causal benchmark.

Run records are private files under ~/.config/agent-workbench/runs; gateway
request metadata is under inference. No prompt, completion or secret is stored
in these added traces. Native harnesses/Omnigent may retain their own transcripts.
Gateway requests do not currently correlate to native child session IDs, and
frontier usage/tool traces are not automatically imported into these run records.

Initialize again to add .agent/skills/improve/SKILL.md to existing projects; an
existing skill is preserved. Load this procedure for a measured improvement,
not every turn. It defines a fixed budget, held-out tasks, immutable acceptance
during the comparison, evidence and rollback. This is procedural guidance, not
an OS-enforced independent evaluator. See [the improvement notes](IMPROVEMENTS.md)
for the research choices and live acceptance scenarios. Run `bash scripts/check.sh`
before adopting a harness change; the installer runs it as well. There is no
background optimizer, automatic fine-tuning or competing memory database.

Keep the original specs and evidence in Git/durable storage, and export Hindsight
banks periodically. Never sync live database files through OneDrive. To uninstall,
stop any host services you enabled, remove the workbench launcher and package, and
keep/export memory and project records until you decide they are no longer needed.
