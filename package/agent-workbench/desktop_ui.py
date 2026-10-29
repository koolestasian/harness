"""Local Harness control panel. Standard library only; no inference at startup."""
from __future__ import annotations

import asyncio
from datetime import datetime
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import shlex
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlencode, urlsplit, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import workbench as w

MODELS = Path.home() / "models"
HUGGING_FACE = "https://huggingface.co"
SPLIT = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)
QUANT = re.compile(r"(?:^|[-_.])(I?Q\d_[A-Z0-9_]+|I?Q\d|BF16|F16|F32|MXFP4)(?=[-_.]|$)", re.IGNORECASE)
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9_.-]{1,96}")
# Claude Code accepts these full IDs; every current model takes the full effort ladder.
CLAUDE_MODELS = [("claude-fable-5-1", "Claude Fable 5.1"), ("claude-opus-5-5", "Claude Opus 5.5"),
                 ("claude-sonnet-5-5", "Claude Sonnet 5.5"), ("claude-haiku-5-5", "Claude Haiku 5.5")]
CLAUDE_EFFORTS = ["low", "medium", "high", "xhigh", "max"]


def systemctl(*args):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=12)


def local_control(action):
    if action == "stop":
        # Kill GPU work immediately instead of waiting for an in-flight CUDA batch.
        systemctl("disable", "workbench-model.service", "workbench-gateway.service")
        systemctl("kill", "--signal=SIGKILL", "workbench-model.service")
        systemctl("stop", "workbench-gateway.service")
        systemctl("reset-failed", "workbench-model.service")
    elif action == "start":
        selected = w.config().get("local_model_file")
        if selected:
            if selected not in {m["id"] for m in local_models()}:
                raise ValueError("Selected local model is no longer available.")
            override = Path.home() / ".config/systemd/user/workbench-model.service.d/selection.conf"
            override.parent.mkdir(parents=True, exist_ok=True)
            # Reuse the installed service's launch settings, replacing only its model file.
            service = systemctl("cat", "workbench-model.service")
            line = next((line for line in service.stdout.splitlines() if line.startswith("ExecStart=") and "--model " in line), "")
            command = shlex.split(line.removeprefix("ExecStart="))
            if "--model" not in command:
                raise ValueError("Local service has no model setting.")
            command[command.index("--model") + 1] = selected
            def quote(value):
                return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'
            override.write_text("[Service]\nExecStart=\nExecStart=" + " ".join(map(quote, command)) + "\n")
            if systemctl("daemon-reload").returncode:
                raise ValueError("Could not reload local model settings.")
        # --no-block makes loading visible without tying up the control panel.
        result = systemctl("start", "--no-block", "workbench-model.service", "workbench-gateway.service")
        if result.returncode:
            raise ValueError("Could not start the model. Check its service in Diagnostics.")
    else:
        raise ValueError("Unknown local model action.")


def clean_output(text):
    for key, value in w.environment().items():
        if any(word in key for word in ("API_KEY", "TOKEN", "SECRET")) and value and len(value) > 6:
            text = text.replace(value, "[hidden]")
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def session_answer(url):
    """Read the persisted reply; native CLI streaming can omit final chunks."""
    if not url or not re.fullmatch(r"http://127\.0\.0\.1:6767/c/[a-f0-9]{32}", url):
        return ""
    endpoint = url.replace("/c/", "/v1/sessions/") + "/items?limit=100&order=desc"
    data = w.http_json(endpoint, w.environment().get("OMNIGENT_API_KEY", ""), timeout=5)
    for item in data.get("data", []):
        if item.get("type") == "message" and item.get("role") == "assistant" and item.get("status") == "completed":
            return clean_output("\n".join(part["text"] for part in item.get("content", [])
                                         if part.get("type") == "output_text" and isinstance(part.get("text"), str)))
    return ""


def catalog(provider):
    spec = w.CLOUD_PROVIDERS.get(provider)
    if not spec:
        raise ValueError("Unknown provider.")
    request = Request(spec["models_url"], headers={"User-Agent": "Harness/1.0"})
    key = w.environment().get(spec["key"])
    if key:
        request.add_header("Authorization", "Bearer " + key)
    with urlopen(request, timeout=20) as response:
        data = json.load(response)["data"]
    models = []
    for model in data:
        if provider == "openrouter" and "tools" not in model.get("supported_parameters", []):
            continue
        models.append({"id": model["id"], "name": model.get("name", model["id"]),
                       "context": min(int(model.get("context_length", 65536)), 131072),
                       "efforts": ["low", "medium", "high"] if "reasoning" in model.get("supported_parameters", []) else [],
                       "pricing": model.get("pricing", {})})
    return sorted(models, key=lambda model: model["name"].lower())


async def codex_limits(method="account/rateLimits/read", params=None):
    """Read account metadata only; never create a thread or turn."""
    process = await asyncio.create_subprocess_exec(
        "codex", "app-server", env=w.environment(), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    async def request(identifier, method, params=None):
        process.stdin.write((json.dumps({"id": identifier, "method": method, "params": params}) + "\n").encode())
        await process.stdin.drain()
        while line := await process.stdout.readline():
            reply = json.loads(line)
            if reply.get("id") == identifier:
                if "error" in reply:
                    raise ValueError("Account limits unavailable")
                return reply["result"]
        raise ValueError("Account connection closed")
    try:
        await request(1, "initialize", {"clientInfo": {"name": "harness_usage", "version": "1.0"}})
        process.stdin.write(b'{"method":"initialized"}\n')
        await process.stdin.drain()
        return await request(2, method, params)
    finally:
        if process.returncode is None:
            process.terminate()
        await process.wait()


def quant(name):
    found = QUANT.search(Path(name).name.removesuffix(".gguf").removesuffix(".GGUF"))
    return found.group(1).upper() if found else ""


def local_models():
    """Downloaded GGUF files; a split model is listed once, by its first part."""
    models = []
    for path in sorted(MODELS.glob("*.gguf")):
        if not path.is_file() or "mmproj" in path.name.lower():
            continue
        split = SPLIT.search(path.name)
        if split and split.group(1) != "00001":
            continue
        parts = [path] if not split else [path.with_name(path.name[:split.start()] + f"-{n:05d}-of-{split.group(2)}.gguf")
                                         for n in range(1, int(split.group(2)) + 1)]
        if not all(part.is_file() for part in parts):
            continue
        name = path.name[:split.start()] if split else path.stem
        size = sum(part.stat().st_size for part in parts)
        models.append({"id": str(path.resolve()), "name": name, "quant": quant(path.name),
                       "size": size, "fit": gpu_fit(size), "efforts": []})
    return models


def hugging_face(path):
    request = Request(HUGGING_FACE + path, headers={"User-Agent": "Harness/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def discover(query):
    """Search public GGUF repositories, most downloaded first."""
    query = " ".join(str(query or "").split())[:100]
    fields = ["downloads", "likes", "gated", "lastModified", "pipeline_tag"]
    params = urlencode([("search", query), ("filter", "gguf"), ("sort", "downloads"), ("direction", "-1"),
                        ("limit", "40")] + [("expand[]", field) for field in fields])
    return [{"id": m["id"], "downloads": m.get("downloads") or 0, "likes": m.get("likes") or 0,
             "gated": bool(m.get("gated")), "updated": m.get("lastModified"), "task": m.get("pipeline_tag") or ""}
            for m in hugging_face("/api/models?" + params) if REPO.fullmatch(m.get("id", ""))]


def gpu_fit(size):
    # Estimate for the 16 GB card with the service's 36,864-token q8_0 cache; the
    # installed 12.1 GB model is known to fit.
    return "fits" if size <= 13.0e9 else "tight" if size <= 15.0e9 else "too_large"


def repo_files(repo):
    """GGUF downloads in one repository, grouping split files into one model."""
    if not isinstance(repo, str) or not REPO.fullmatch(repo) or ".." in repo:
        raise ValueError("Choose a Hugging Face model.")
    groups = {}
    for item in hugging_face(f"/api/models/{quote(repo)}/tree/main?recursive=true"):
        path = item.get("path", "")
        name = path.rsplit("/", 1)[-1]
        if item.get("type") != "file" or not name.lower().endswith(".gguf") or "mmproj" in name.lower():
            continue
        split = SPLIT.search(name)
        key = path[:len(path) - len(name) + split.start()] if split else path
        group = groups.setdefault(key, {"total": int(split.group(2)) if split else 1, "parts": []})
        group["parts"].append((path, int(item.get("size") or 0)))
    installed = {Path(m["id"]).name for m in local_models()}
    files = []
    for key, group in groups.items():
        parts = sorted(group["parts"])
        if len(parts) != group["total"]:
            continue
        name = parts[0][0].rsplit("/", 1)[-1]
        size = sum(s for _, s in parts)
        files.append({"file": parts[0][0], "name": key.rsplit("/", 1)[-1].removesuffix(".gguf").removesuffix(".GGUF"),
                      "paths": [p for p, _ in parts], "sizes": [s for _, s in parts], "size": size,
                      "quant": quant(name), "fit": gpu_fit(size), "downloaded": name in installed})
    return sorted(files, key=lambda f: f["size"])


def claude_usage():
    """Read the plan windows Claude Code's /usage shows. Never refreshes or stores credentials.

    Returns None when the saved sign-in has expired; Claude Code renews it on its next use.
    """
    oauth = json.loads((Path.home() / ".claude/.credentials.json").read_text())["claudeAiOauth"]
    if oauth.get("expiresAt", 0) / 1000 < time.time() + 60:
        return None
    request = Request("https://api.anthropic.com/api/oauth/usage", headers={
        "Authorization": "Bearer " + oauth["accessToken"], "anthropic-beta": "oauth-2025-04-20", "User-Agent": "Harness/1.0"})
    with urlopen(request, timeout=15) as response:
        data = json.load(response)
    windows = []
    for key, label in (("five_hour", ""), ("seven_day", ""), ("seven_day_opus", "Opus weekly"), ("seven_day_sonnet", "Sonnet weekly")):
        window = data.get(key)
        if isinstance(window, dict) and isinstance(window.get("utilization"), (int, float)):
            resets = window.get("resets_at")
            windows.append({"bucket": key, "label": label, "used": float(window["utilization"]),
                            "minutes": 300 if key == "five_hour" else 10080,
                            "resets": datetime.fromisoformat(resets).timestamp() if resets else None})
    return windows


def task_models(role):
    if role == "local":
        return local_models()
    if role == "codex":
        data = asyncio.run(asyncio.wait_for(codex_limits("model/list", {"includeHidden": False}), 15))
        return [{"id": m["model"], "name": m.get("displayName", m["model"]),
                 "efforts": [e["reasoningEffort"] for e in m.get("supportedReasoningEfforts", [])]}
                for m in data.get("data", []) if not m.get("hidden")]
    if role in {"claude", "research", "coordinator"}:
        return [{"id": model, "name": name, "efforts": CLAUDE_EFFORTS} for model, name in CLAUDE_MODELS]
    if role == "cloud":
        return catalog(w.config()["cloud_provider"])
    raise ValueError("Choose a supported worker.")


def usage_snapshot():
    result = {"checked": time.time(), "codex": {"status": "unavailable", "windows": []},
              "claude": {"status": "unavailable"}, "cloud": {"status": "unavailable"}}
    try:
        raw = asyncio.run(asyncio.wait_for(codex_limits(), timeout=15))
        buckets = raw.get("rateLimitsByLimitId") or {"codex": raw.get("rateLimits", {})}
        windows = []
        for name, bucket in buckets.items():
            for kind in ("primary", "secondary"):
                window = bucket.get(kind)
                if window:
                    windows.append({"bucket": name, "used": window["usedPercent"],
                                    "minutes": window.get("windowDurationMins"), "resets": window.get("resetsAt")})
        result["codex"] = {"status": "available" if windows else "unavailable", "windows": windows}
    except (OSError, ValueError, KeyError, asyncio.TimeoutError):
        pass
    try:
        windows = claude_usage()
        result["claude"] = {"status": "expired"} if windows is None else {
            "status": "available" if windows else "unavailable", "windows": windows}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    cfg, env = w.config(), w.environment()
    result["cloud"]["provider"] = cfg["cloud_provider"]
    if cfg["cloud_provider"] == "openrouter" and env.get("OPENROUTER_API_KEY"):
        try:
            data = w.http_json("https://openrouter.ai/api/v1/key", env["OPENROUTER_API_KEY"], timeout=10)["data"]
            result["cloud"].update(status="available", limit=data.get("limit"),
                                    remaining=data.get("limit_remaining"), used=data.get("usage"),
                                    reset=data.get("limit_reset"))
        except (OSError, ValueError, KeyError):
            pass
    return result


class Panel:
    def __init__(self):
        self.jobs = {}
        self.lock = threading.Lock()
        self.auth = {}
        self.usage = {}
        self.usage_refreshing = False
        self.usage_attempt = 0
        self.download = None
        self.download_cancel = threading.Event()

    def refresh_usage(self):
        with self.lock:
            if self.usage_refreshing:
                return
            self.usage_refreshing = True
            self.usage_attempt = time.time()
        def refresh():
            try:
                snapshot = usage_snapshot()
                with self.lock:
                    self.usage = snapshot
            finally:
                with self.lock:
                    self.usage_refreshing = False
        threading.Thread(target=refresh, daemon=True).start()

    def preferences(self):
        default = str(Path.home() / "projects/workbench-demo")
        return w.read_json(w.STATE / "desktop.json", {"projects": [default], "selected": default})

    def save_project(self, body):
        raw = body.get("path", "").strip()
        if re.match(r"^[A-Za-z]:[\\/]", raw):
            raw = "/mnt/" + raw[0].lower() + "/" + raw[3:].replace("\\", "/")
        repo = Path(raw).expanduser().resolve()
        if not (repo / ".agent/PROJECT.json").exists():
            w.init_project(type("Args", (), {"path": str(repo), "id": body.get("id", "").strip()})())
        w.project(repo)
        prefs = self.preferences()
        if str(repo) not in prefs["projects"]:
            prefs["projects"].append(str(repo))
        prefs["selected"] = str(repo)
        w.write_json(w.STATE / "desktop.json", prefs, private=True)
        return {"message": "Project ready."}

    def save_provider(self, body):
        provider = body.get("provider")
        if provider not in w.CLOUD_PROVIDERS:
            raise ValueError("Choose OpenRouter or OpenCode Console.")
        model = body.get("model", "").strip()
        if len(model) > 200 or model.startswith("-") or any(c.isspace() for c in model):
            raise ValueError("Enter a valid model ID.")
        key = body.get("key", "").strip()
        if len(key) > 1024 or any(c.isspace() for c in key):
            raise ValueError("API keys cannot contain whitespace.")
        if key:
            private = w.read_json(w.STATE / "secrets.json", {})
            private[w.CLOUD_PROVIDERS[provider]["key"]] = key
            w.write_json(w.STATE / "secrets.json", private, private=True)
        cfg = w.config()
        cfg.update(cloud_provider=provider, cloud_model=model,
                   cloud_context=max(8192, min(int(body.get("context", 65536)), 131072)))
        w.write_json(w.STATE / "config.json", cfg, private=True)
        return {"message": "Connection saved. Run a task to verify model access."}

    def select_local(self, body):
        if w.local_running():
            raise ValueError("Stop the local model before changing it.")
        model = body.get("model")
        if model not in {m["id"] for m in local_models()}:
            raise ValueError("Choose an installed local model.")
        cfg = w.config()
        cfg["local_model_file"] = model
        w.write_json(w.STATE / "config.json", cfg, private=True)
        return {"message": "Local model selected. Start it when you are ready."}

    def start_download(self, body):
        """Download a GGUF listed by Hugging Face into ~/models. Never starts the GPU."""
        repo, file = body.get("repo"), body.get("file")
        # Only a file the repository itself lists can be fetched; the browser cannot name a URL or path.
        entry = next((f for f in repo_files(repo) if f["file"] == file), None)
        if not entry:
            raise ValueError("That file is no longer listed in this repository.")
        if entry["downloaded"]:
            raise ValueError("This model is already downloaded.")
        MODELS.mkdir(parents=True, exist_ok=True)
        partial = MODELS / ".partial"
        resumable = sum((partial / (Path(p).name + ".part")).stat().st_size
                        for p in entry["paths"] if (partial / (Path(p).name + ".part")).is_file())
        if shutil.disk_usage(MODELS).free < entry["size"] - resumable + 2e9:
            raise ValueError("Not enough disk space for this download.")
        with self.lock:
            if self.download and self.download["state"] == "downloading":
                raise ValueError("Wait for the current download to finish, or cancel it.")
            self.download_cancel = cancel = threading.Event()
            self.download = {"repo": repo, "file": file, "name": entry["name"], "quant": entry["quant"],
                             "size": entry["size"], "done": 0, "speed": 0, "state": "downloading", "error": ""}
        threading.Thread(target=self._download, args=(repo, entry, cancel), daemon=True).start()
        return {"message": "Download started. The local model stays off."}

    def cancel_download(self):
        with self.lock:
            if not self.download or self.download["state"] != "downloading":
                return {"message": "No download in progress."}
            self.download_cancel.set()
        return {"message": "Cancelling download…"}

    def _download_progress(self, **values):
        with self.lock:
            self.download.update(values)

    def _download(self, repo, entry, cancel):
        partial = MODELS / ".partial"
        partial.mkdir(parents=True, exist_ok=True)
        temps = [partial / (Path(path).name + ".part") for path in entry["paths"]]
        started, received, finished = time.monotonic(), 0, 0
        try:
            for path, size, temp in zip(entry["paths"], entry["sizes"], temps):
                offset = temp.stat().st_size if temp.exists() else 0
                if offset > size:
                    temp.unlink()
                    offset = 0
                if offset < size:
                    headers = {"User-Agent": "Harness/1.0"} | ({"Range": f"bytes={offset}-"} if offset else {})
                    request = Request(f"{HUGGING_FACE}/{quote(repo)}/resolve/main/{quote(path)}", headers=headers)
                    with urlopen(request, timeout=30) as response:
                        if offset and response.status != 206:
                            offset = 0  # The server ignored the range; start this part again.
                        with open(temp, "ab" if offset else "wb") as stream:
                            while chunk := response.read(1 << 20):
                                if cancel.is_set():
                                    raise InterruptedError
                                stream.write(chunk)
                                offset += len(chunk)
                                received += len(chunk)
                                self._download_progress(done=finished + offset,
                                                        speed=received / max(time.monotonic() - started, .001))
                if temp.stat().st_size != size:
                    raise ValueError("The download was incomplete. Try again to resume it.")
                finished += size
            # Publish all parts together so a half-downloaded split model never appears installed.
            for path, temp in zip(entry["paths"], temps):
                os.replace(temp, MODELS / Path(path).name)
            self._download_progress(state="done", done=entry["size"], speed=0)
        except InterruptedError:
            for temp in temps:
                temp.unlink(missing_ok=True)
            self._download_progress(state="cancelled", speed=0)
        except HTTPError as error:
            message = ("This model requires accepting its terms on Hugging Face." if error.code in {401, 403}
                       else f"Hugging Face returned HTTP {error.code}. Try again to resume.")
            self._download_progress(state="failed", speed=0, error=message)
        except Exception as error:  # Includes dropped connections; the part file is kept for resuming.
            self._download_progress(state="failed", speed=0,
                                    error=str(error) if isinstance(error, ValueError) else "Download interrupted. Try again to resume it.")

    def _update_job(self, job, **values):
        with self.lock:
            job.update(values)
            saved = {k: v for k, v in job.items() if k not in {"process"}}
            w.write_json(w.STATE / "desktop-jobs" / (job["id"] + ".json"), saved, private=True)

    def start_job(self, body):
        role = body.get("role", "codex")
        if role not in {"codex", "claude", "coordinator", "research", "cloud", "local", "doctor"}:
            raise ValueError("Choose a supported worker.")
        repo, _ = w.project(body.get("project", self.preferences()["selected"]))
        prompt = body.get("prompt", "").strip()
        if role != "doctor" and not 1 <= len(prompt) <= 16000:
            raise ValueError("Describe your task (up to 16,000 characters).")
        if role == "local" and not w.local_running():
            raise ValueError("The local model is off. Start it in System first.")
        if role == "cloud" and not w.cloud_ready():
            raise ValueError("Connect a hosted model in Connections first.")
        model = body.get("model", "")
        effort = body.get("effort", "")
        if not isinstance(model, str) or len(model) > 500 or any(ord(c) < 32 for c in model) or model.startswith("-"):
            raise ValueError("Choose a valid model.")
        if effort not in {"", "low", "medium", "high", "xhigh", "max", "ultra"}:
            raise ValueError("Choose a supported effort level.")
        if role == "local" and effort:
            raise ValueError("This local profile does not advertise adjustable effort.")
        if role == "local" and model and model != w.config().get("local_model_file"):
            raise ValueError("Apply the local model selection, then start it before running.")
        title = "Health check" if role == "doctor" else clean_output(prompt.splitlines()[0])[:120]
        if role == "coordinator":
            prompt += "\nLocal GPU inference is manual-only. Do not start it or use it as a fallback."
        with self.lock:
            if any(j["state"] in {"running", "stopping"} for j in self.jobs.values()):
                raise ValueError("Finish or stop your current task before starting another.")
            job = {"id": secrets.token_hex(8), "role": role, "title": title, "project": str(repo), "state": "running",
                   "requested_model": model, "requested_effort": effort,
                   "started": time.time(), "output": "Starting…", "url": None, "exit_code": None}
            self.jobs[job["id"]] = job
        args = [str(w.ROOT / ".venv/bin/python"), "-u", str(w.ROOT / "workbench.py")]
        if role == "doctor":
            args += ["doctor", "--project", str(repo), "--live"]
        else:
            args += ["launch", role, "--project", str(repo), "--prompt", prompt]
            if model and role != "local":
                args += ["--model", model]
            if effort:
                args += ["--effort", effort]
        threading.Thread(target=self._run, args=(job, args, repo), daemon=True).start()
        return {"id": job["id"]}

    def _run(self, job, args, repo):
        try:
            process = subprocess.Popen(args, cwd=repo, env=w.environment(), start_new_session=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            job["process"] = process
            if job["state"] == "stopped":
                os.killpg(process.pid, signal.SIGTERM)
            output = ""
            for line in process.stdout:
                output = (output + clean_output(line))[-48000:]
                found = re.search(r"Omnigent session: (http://127\.0\.0\.1:6767/c/[a-f0-9]+)", output)
                self._update_job(job, output=output, url=found.group(1) if found else None)
            code = process.wait()
            answer = ""
            if job.get("url") and job["state"] not in {"stopped", "stopping"}:
                try:
                    answer = session_answer(job["url"])
                except (OSError, ValueError):
                    pass
            self._update_job(job, state=job["state"] if job["state"] in {"stopped", "stopping"} else "done" if code == 0 else "failed", exit_code=code,
                             answer=answer, delivery_warning=code == 0 and not answer)
        except Exception as error:
            self._update_job(job, state="failed", output=clean_output(str(error)))

    def stop_job(self, identifier):
        job = self.jobs.get(identifier)
        if not job or job["state"] not in {"running", "stopping"}:
            return {"message": "No running task."}
        process = job.get("process")
        self._update_job(job, state="stopping")
        # Stop the actual Omnigent session, not only its attached CLI.
        session = (job.get("url") or "").rsplit("/", 1)[-1]
        if session and re.fullmatch(r"[a-f0-9]{32}", session):
            base = "http://127.0.0.1:6767" if w.config()["server_url"] == "local" else w.config()["server_url"]
            endpoint = base + f"/v1/sessions/{session}"
            key = w.environment().get("OMNIGENT_API_KEY", "")
            started = time.monotonic()
            # A native turn can start just after the session URL is printed.
            # Reconcile that race before reporting that the task stopped.
            while time.monotonic() - started < 12:
                w.http_json(endpoint + "/events", key, {"type": "interrupt", "data": {}}, timeout=5)
                snapshot = w.http_json(endpoint + "?include_items=false&include_usage=false", key, timeout=5)
                if snapshot.get("status") != "running" and not snapshot.get("active_response_id") and time.monotonic() - started >= 3:
                    break
                time.sleep(.4)
            else:
                self._update_job(job, state="running")
                raise ValueError("Stop not confirmed yet. Retry or open the session to interrupt it.")
        if process and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        self._update_job(job, state="stopped")
        return {"message": "Stop requested."}

    def refresh_auth(self):
        for provider, args in {"codex": ["codex", "login", "status"], "claude": ["claude", "auth", "status", "--json"]}.items():
            try:
                result = subprocess.run(args, env=w.environment(), capture_output=True, text=True, timeout=12)
                self.auth[provider] = result.returncode == 0 and (provider != "claude" or json.loads(result.stdout).get("loggedIn") is True)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                self.auth[provider] = False

    def state(self):
        if time.time() - self.usage_attempt > 300:
            self.refresh_usage()
        cfg, env = w.config(), w.environment()
        local = w.local_running()
        ready = False
        if local:
            try:
                health = w.http_json(cfg["local_backend_url"].removesuffix("/v1") + "/health", env["LOCAL_MODEL_API_KEY"], timeout=1)
                ready = health.get("status") == "ok"
            except Exception:
                pass
        with self.lock:
            jobs = [{k: v for k, v in job.items() if k != "process"} for job in self.jobs.values()]
        known = {job["id"] for job in jobs}
        for path in sorted((w.STATE / "desktop-jobs").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]:
            job = w.read_json(path)
            if job["id"] in known:
                continue
            if job["state"] == "running":
                job["state"] = "interrupted"
            jobs.append(job)
        return {"local": "ready" if ready else "loading" if local else "off", "auth": self.auth,
                "usage": self.usage, "usage_refreshing": self.usage_refreshing,
                "memory": bool(env.get("HINDSIGHT_API_KEY")), "cloud_ready": w.cloud_ready(),
                "providers": {key: {"name": spec["name"], "has_key": bool(env.get(spec["key"]))} for key, spec in w.CLOUD_PROVIDERS.items()},
                "cloud_provider": cfg["cloud_provider"], "cloud_model": cfg["cloud_model"],
                "local_model_file": cfg.get("local_model_file", ""), "local_models": local_models(),
                "download": dict(self.download) if self.download else None,
                "projects": self.preferences(), "jobs": sorted(jobs, key=lambda j: j["started"], reverse=True),
                "versions": w.read_json(w.ROOT / "versions.json")}


def make_server(port, panel=None):
    panel = panel or Panel()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, code=200, html=False):
            data = value.encode() if html else json.dumps(value).encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def allowed(self):
            host = self.headers.get("Host", "")
            return host in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.allowed():
                return self.send({"error": "Invalid host."}, 403)
            path = urlsplit(self.path).path
            if path == "/":
                return self.send((w.ROOT / "ui/index.html").read_text().replace("__CSRF_TOKEN__", token), html=True)
            if path == "/api/status":
                return self.send(panel.state())
            return self.send({"error": "Not found."}, 404)

        def do_POST(self):
            if not self.allowed() or not hmac.compare_digest(self.headers.get("X-Harness-Token", ""), token):
                return self.send({"error": "Reload Harness and try again."}, 403)
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
                return self.send({"error": "Invalid origin."}, 403)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise ValueError("Request is too large or empty.")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object.")
                path = urlsplit(self.path).path
                if path == "/api/local":
                    local_control(body.get("action"))
                    result = {"message": "Model is loading. It may take a minute." if body.get("action") == "start" else "Local model off. GPU memory released."}
                elif path == "/api/project":
                    result = panel.save_project(body)
                elif path == "/api/provider":
                    result = panel.save_provider(body)
                elif path == "/api/task-models":
                    result = {"models": task_models(body.get("role"))}
                elif path == "/api/select-local":
                    result = panel.select_local(body)
                elif path == "/api/discover":
                    result = {"models": discover(body.get("query", ""))}
                elif path == "/api/model-files":
                    result = {"files": repo_files(body.get("repo"))}
                elif path == "/api/download":
                    result = panel.start_download(body)
                elif path == "/api/download-cancel":
                    result = panel.cancel_download()
                elif path == "/api/models":
                    result = {"models": catalog(body.get("provider"))}
                elif path == "/api/run":
                    result = panel.start_job(body)
                elif path == "/api/stop":
                    result = panel.stop_job(body.get("id"))
                elif path == "/api/usage":
                    panel.refresh_usage()
                    result = {"message": "Refreshing provider limits. No inference is started."}
                elif path == "/api/accounts":
                    panel.refresh_auth()
                    result = {"message": "Account status refreshed."}
                else:
                    return self.send({"error": "Not found."}, 404)
                self.send(result)
            except HTTPError as error:
                if urlsplit(self.path).path in {"/api/discover", "/api/model-files", "/api/download"}:
                    return self.send({"error": f"Hugging Face returned HTTP {error.code}. Try again later."}, 400)
                self.send({"error": f"Provider returned HTTP {error.code}. Check its key, model access, and account credits."}, 400)
            except (ValueError, OSError, subprocess.SubprocessError, KeyError) as error:
                self.send({"error": clean_output(str(error))}, 400)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.panel = panel
    return server


def serve(port=8787):
    panel = Panel()
    threading.Thread(target=panel.refresh_auth, daemon=True).start()
    server = make_server(port, panel)
    print(f"Harness ready: http://127.0.0.1:{server.server_port} (GPU model remains off)", flush=True)
    server.serve_forever()
