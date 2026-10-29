#!/usr/bin/env python3
"""Check the real loopback server's auth and optional restart persistence."""
import argparse
import http.cookiejar
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--restart", action="store_true")
args = parser.parse_args()
settings = dict(line.split("=", 1) for line in (root / ".env").read_text().splitlines()
                if line and not line.startswith("#"))
url = "http://127.0.0.1:6767"


def wait_ready():
    for _ in range(80):
        try:
            with urlopen(url + "/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            time.sleep(0.5)
    raise SystemExit("Server health did not become ready.")


def verify():
    wait_ready()
    try:
        urlopen(url + "/v1/sessions", timeout=5)
        raise SystemExit("FAIL: unauthenticated session access was accepted.")
    except HTTPError as error:
        assert error.code in (401, 403), error.code
    client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    body = json.dumps({"username": "admin", "password": settings["OMNIGENT_ACCOUNTS_INIT_ADMIN_PASSWORD"]}).encode()
    with client.open(Request(url + "/auth/login", data=body,
                             headers={"Content-Type": "application/json"}), timeout=10) as response:
        assert response.status == 200
    with client.open(url + "/v1/sessions", timeout=10) as response:
        assert response.status == 200
    return {"health": True, "anonymous_rejected": True, "authenticated_sessions": True}


result = {"before_restart": verify()}
if args.restart:
    subprocess.run(["docker", "compose", "--env-file", str(root / ".env"), "-f",
                    str(root / "compose.yaml"), "restart", "omnigent"], check=True)
    result["after_restart"] = verify()
print(json.dumps(result, indent=2))
