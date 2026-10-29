#!/usr/bin/env bash
set -euo pipefail
WORKBENCH_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKBENCH_ROOT"
for WORKBENCH_SCRIPT in scripts/*.sh deploy/*.sh; do
  bash -n "$WORKBENCH_SCRIPT"
done
exec .venv/bin/python -m unittest discover -s tests -v
