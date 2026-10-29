#!/usr/bin/env bash
set -euo pipefail
WORKBENCH_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$WORKBENCH_ROOT/deploy/bootstrap.py"
docker compose --env-file "$WORKBENCH_ROOT/deploy/.env" -f "$WORKBENCH_ROOT/deploy/compose.yaml" up -d --build
printf '\nServer started on loopback http://localhost:6767. Read deploy/README.md to retrieve the first-run login and configure remote HTTPS access.\n'
