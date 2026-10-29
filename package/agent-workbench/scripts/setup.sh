#!/usr/bin/env bash
set -euo pipefail
WORKBENCH_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "$(uname -s)" in
  Darwin)
    if ! command -v tmux >/dev/null; then
      if ! command -v brew >/dev/null; then
        echo 'tmux is required. Install Homebrew from https://brew.sh, then rerun this installer.' >&2
        exit 1
      fi
      brew install tmux
    fi
    ;;
  Linux)
    if ! command -v tmux >/dev/null || ! command -v bwrap >/dev/null || ! command -v git >/dev/null; then
      if [ "$(id -u)" = 0 ]; then
        WORKBENCH_SUDO=()
      elif command -v sudo >/dev/null; then
        WORKBENCH_SUDO=(sudo)
      else
        echo 'A system prerequisite is missing (tmux/bubblewrap/git), and this account has no sudo. Ask the host administrator to install it, then rerun.' >&2
        exit 1
      fi
      "${WORKBENCH_SUDO[@]}" apt-get update
      "${WORKBENCH_SUDO[@]}" apt-get install -y tmux bubblewrap git curl ca-certificates
    fi
    ;;
  *) echo 'Use macOS or Ubuntu under WSL2.' >&2; exit 1 ;;
esac
if ! command -v uv >/dev/null; then
  curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh -o /tmp/workbench-uv-install.sh
  sh /tmp/workbench-uv-install.sh
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v node >/dev/null || ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
  WORKBENCH_NODE_VERSION=v22.23.4
  case "$(uname -s)" in Darwin) WORKBENCH_NODE_OS=darwin;; Linux) WORKBENCH_NODE_OS=linux;; esac
  case "$(uname -m)" in arm64|aarch64) WORKBENCH_NODE_ARCH=arm64;; x86_64) WORKBENCH_NODE_ARCH=x64;; *) exit 1;; esac
  WORKBENCH_NODE_FILE="node-$WORKBENCH_NODE_VERSION-$WORKBENCH_NODE_OS-$WORKBENCH_NODE_ARCH.tar.gz"
  WORKBENCH_DOWNLOAD="$(mktemp -d)"
  curl --proto '=https' --tlsv1.2 -fLsS "https://nodejs.org/dist/$WORKBENCH_NODE_VERSION/$WORKBENCH_NODE_FILE" -o "$WORKBENCH_DOWNLOAD/$WORKBENCH_NODE_FILE"
  curl --proto '=https' --tlsv1.2 -fLsS "https://nodejs.org/dist/$WORKBENCH_NODE_VERSION/SHASUMS256.txt" -o "$WORKBENCH_DOWNLOAD/SHASUMS256.txt"
  (cd "$WORKBENCH_DOWNLOAD"
   awk -v f="$WORKBENCH_NODE_FILE" '$2==f' SHASUMS256.txt > selected.sha256
   test -s selected.sha256
   if command -v sha256sum >/dev/null; then sha256sum -c selected.sha256; else shasum -a 256 -c selected.sha256; fi)
  mkdir -p "$WORKBENCH_ROOT/.tools/node"
  tar -xzf "$WORKBENCH_DOWNLOAD/$WORKBENCH_NODE_FILE" -C "$WORKBENCH_ROOT/.tools/node" --strip-components=1
  rm -r "$WORKBENCH_DOWNLOAD"
  export PATH="$WORKBENCH_ROOT/.tools/node/bin:$PATH"
fi
if [ ! -x "$WORKBENCH_ROOT/.venv/bin/python" ]; then
  uv venv --python 3.12 "$WORKBENCH_ROOT/.venv"
fi
uv pip sync --python "$WORKBENCH_ROOT/.venv/bin/python" "$WORKBENCH_ROOT/requirements.lock"
"$WORKBENCH_ROOT/.venv/bin/python" - "$WORKBENCH_ROOT" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1]); pins=json.loads((root/'versions.json').read_text())
packages={k:v for k,v in pins.items() if k in ['@anthropic-ai/claude-code','@openai/codex','@earendil-works/pi-coding-agent']}
(root/'.tools').mkdir(exist_ok=True)
(root/'.tools/package.json').write_text(json.dumps({'private':True,'dependencies':packages},indent=2))
PY
cp "$WORKBENCH_ROOT/cli-package-lock.json" "$WORKBENCH_ROOT/.tools/package-lock.json"
npm ci --prefix "$WORKBENCH_ROOT/.tools" --no-audit --no-fund
bash "$WORKBENCH_ROOT/scripts/check.sh"
mkdir -p "$HOME/.local/bin"
"$WORKBENCH_ROOT/.venv/bin/python" - "$WORKBENCH_ROOT" <<'PY'
import pathlib,shlex,sys
root=pathlib.Path(sys.argv[1]); launcher=pathlib.Path.home()/'.local/bin/workbench'
if launcher.exists() and 'agent-workbench launcher' not in launcher.read_text():
    raise SystemExit('Existing ~/.local/bin/workbench is not ours; refusing to replace it.')
launcher.write_text('#!/bin/sh\n# agent-workbench launcher\nexec '+shlex.quote(str(root/'.venv/bin/python'))+' '+shlex.quote(str(root/'workbench.py'))+' "$@"\n')
launcher.chmod(0o755)
if sys.platform.startswith('linux') and pathlib.Path('/run/systemd/system').exists():
    service=pathlib.Path.home()/'.config/systemd/user/workbench-ui.service'
    service.parent.mkdir(parents=True,exist_ok=True)
    service.write_text('[Unit]\nDescription=Harness control panel (no GPU inference)\n[Service]\nExecStart='+str(launcher)+' ui\nRestart=on-failure\nRestartSec=3\n')
PY
printf '\nInstalled. Run:\n  export PATH="$HOME/.local/bin:$PATH"\n  workbench configure\n  workbench doctor\n\nRead docs/GUIDE.md for account login, shared memory and local inference.\n'
