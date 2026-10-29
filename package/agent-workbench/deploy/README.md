# Optional independent coordination server

Run on an owned, persistent Linux machine with Docker Compose v2:

```bash
bash deploy/start.sh
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
```

The server uses one persistent Docker volume containing SQLite, artifacts and
account state. It is single-instance. It is bound only to 127.0.0.1:6767. Hindsight
Cloud remains a separate memory service; this Compose stack does not provision a
Hindsight account or model API credentials.

Open deploy/.env locally to retrieve OMNIGENT_ACCOUNTS_INIT_ADMIN_PASSWORD. Sign
in as `admin`. Keep that file private. Later edits of the bootstrap password do
not reset an existing account. The generated cookie secret must survive restarts.

For private Tailscale access on THIS server (after connecting its own Tailscale):

```bash
tailscale serve --bg http://127.0.0.1:6767
```

Use the HTTPS URL Tailscale prints. Set BOTH of these in deploy/.env to that URL:

```dotenv
OMNIGENT_ACCOUNTS_BASE_URL=https://YOUR_SERVER.YOUR_TAILNET.ts.net
OMNIGENT_WS_ALLOWED_ORIGINS=https://YOUR_SERVER.YOUR_TAILNET.ts.net
```

Recreate with `bash deploy/start.sh`. This uses private Tailscale Serve; it does
not turn on public Funnel access. The desktop and Mac must reach the same endpoint
and complete Omnigent login/host registration. For SSH-only access, forward port
6767 from the server and use localhost; forwarding alone is not permanent hosting.

Check `/health` and verify that an unauthenticated request to `/v1/sessions` is
rejected, then verify a real authenticated host connects. A health check alone
does not establish that models, hosts or shared memory work.

Back up the named volume with the server stopped, or use SQLite's backup API plus
an artifact backup. Retain the credentials/config files. Do not use `docker compose
down -v` unless you intend to delete the database, artifacts and account state.

The Dockerfile supports an optional BuildKit `proxy_ca` secret for managed build
environments. Ordinary machines do not need it. Keep inherited proxies and CA
trust when building inside a managed cloud environment; never disable TLS checks.
