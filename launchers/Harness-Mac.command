#!/bin/zsh
# Connect to the existing desktop workbench. Never starts GPU inference.
set -eu
target='YOUR_SSH_USER@YOUR_DESKTOP_HOST'
socket="$HOME/.ssh/harness-desktop-control"
mkdir -p "$HOME/.ssh"
if ! ssh -S "$socket" -O check "$target" >/dev/null 2>&1; then
  echo 'Connect Tailscale on both computers. Keep the PC awake with Harness open.'
  echo 'SSH may ask for your existing Windows account password or SSH key.'
  ssh -M -S "$socket" -fNT \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -L 127.0.0.1:8787:127.0.0.1:8787 \
    -L 127.0.0.1:6767:127.0.0.1:6767 "$target"
fi
if curl --fail --silent --max-time 5 http://127.0.0.1:8787/api/status >/dev/null; then
  open http://127.0.0.1:8787
  echo 'Harness is open. Tasks and files run on the desktop; GPU stays manual-only.'
else
  echo 'Tunnel connected. Open Harness on the PC, then run this launcher again.'
fi
