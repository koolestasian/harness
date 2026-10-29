#!/bin/zsh
# Disconnect only the tunnel created by Harness-Mac.command.
ssh -S "$HOME/.ssh/harness-desktop-control" -O exit YOUR_SSH_USER@YOUR_DESKTOP_HOST
