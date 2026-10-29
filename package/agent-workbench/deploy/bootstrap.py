#!/usr/bin/env python3
"""Generate first-run account secrets without displaying them."""
import os
from pathlib import Path
import secrets

path = Path(__file__).resolve().parent / ".env"
if not path.exists():
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write("OMNIGENT_ACCOUNTS_INIT_ADMIN_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
        stream.write("OMNIGENT_ACCOUNTS_COOKIE_SECRET=" + secrets.token_hex(32) + "\n")
        stream.write("OMNIGENT_ACCOUNTS_BASE_URL=http://localhost:6767\n")
        stream.write("OMNIGENT_WS_ALLOWED_ORIGINS=http://localhost:6767\n")
    print("Created deploy/.env with mode 0600. Secrets were not printed.")
else:
    print("Preserved existing deploy/.env.")
