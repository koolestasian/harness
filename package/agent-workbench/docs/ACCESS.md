# Connecting the installer to your desktop

The desktop reported its Tailscale IPv4 address and a running Windows OpenSSH
service. Those establish local prerequisites, not a route from a cloud workspace.
This preparation environment reported `vpn_configured: false`, no TCP grants,
and a refused connection to its TCP gateway. No Windows password was tested and
no connection reached the desktop's SSH port.

The user found a Local / desktop execution-environment option. Select that for
the installation conversation and send a new message after switching, so the
agent can inspect the actual local execution context before running installers.
If switching creates a new local conversation, include this package and tell it:

> Continue installing this agent-workbench MVP on my desktop. I authorize the
> setup. Read README.md, STATUS.md and docs/GUIDE.md, inspect the actual machine,
> preserve existing settings, install into WSL2, connect real Hindsight and model
> accounts, run live checks, and update STATUS.md with evidence. Do not mark
> unavailable integrations ready.

Alternatively configure Tailscale in the cloud environment using the app's
connection settings and allow the intended private SSH destination. The cloud
environment also needs a usable SSH authentication method and verified host key.
Local Tailscale being online does not automatically join the cloud environment
to the same tailnet. Do not paste private keys or passwords into the chat.
