# Run Harness from your Mac

The fastest current route is to use the existing desktop from your Mac. Your PC
must be awake and signed in, with Harness open. Both devices need Tailscale on
the same account. This does not start the desktop GPU model.

On the Mac, open Terminal and run:

```sh
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8787:127.0.0.1:8787 \
  -L 127.0.0.1:6767:127.0.0.1:6767 YOUR_SSH_USER@YOUR_DESKTOP_HOST
```

Leave that terminal open and visit http://127.0.0.1:8787 in Safari/Chrome or VS
Code's integrated browser. Port 6767 also makes Open session links work. Ctrl+C
disconnects this foreground tunnel. Tasks edit PC files, not Mac-only files.

Use your existing SSH key or Windows account password, not the Windows Hello
PIN. On first connection compare the previously observed desktop fingerprint:
SHA256:tS/amD7moQjHqNbdFK6cf+FanmarFxtkLSrza0xZKqY.
Investigate a mismatch rather than bypassing a host-key warning.

## Optional daily launcher

Copy Harness-Mac.command and Disconnect-Harness-Mac.command to the Mac, for
example to Downloads. Run once:

```sh
chmod +x ~/Downloads/Harness-Mac.command ~/Downloads/Disconnect-Harness-Mac.command
```

Then double-click Harness-Mac.command to connect and open the browser. It uses
normal SSH authentication and keeps its tunnel in the background. Double-click
Disconnect-Harness-Mac.command to close only that tunnel. These scripts install
nothing, copy no credentials, and issue no remote commands or model starts.

## Independent Mac use while the PC is off

The package includes a macOS installer. Copy agent-workbench-desktop.zip to the
Mac and extract it into a permanent folder. In its agent-workbench directory:

```sh
bash scripts/setup.sh
export PATH="$HOME/.local/bin:$PATH"
workbench auth codex
workbench auth claude
workbench configure
```

The installer needs Git and tmux; it uses existing Homebrew for tmux and can
install a private checksum-verified Node runtime. It creates a fresh Mac Python
environment. Do not copy the Windows .venv or OAuth files. Enter the Hindsight
token through the hidden local prompt, never chat.

Clone the project, initialize it with the same stable project ID as on the PC,
then run workbench ui and open http://127.0.0.1:8787. Keep that terminal open.
Add/select your Mac-local Git repository in the panel before running a task.
Enter cloud provider keys separately in Connections when needed.

The current workbench open shortcut and GPU controls use Linux systemd. On the
Mac use workbench ui; a polished native Mac launcher and end-to-end installation
remain unverified. The local-model button does not control the desktop GPU in
this independent mode. Hosted memory is shared by project ID; code and dirty
files still need explicit Git synchronization.

## Verification

Desktop panel HTTP 200 through Windows localhost was checked. Both GPU services
are inactive. Authenticated Mac-to-PC SSH, macOS shell execution and native Mac
agent turns have not been tested from this Windows session. The launcher has a
shell syntax check only; no actual Mac connection is claimed.

References: https://man.openbsd.org/ssh.1 and
https://tailscale.com/docs/reference/ssh-over-tailscale.
