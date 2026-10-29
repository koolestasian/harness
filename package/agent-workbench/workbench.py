#!/usr/bin/env python3
"""Small deployment/launch helper; Omnigent remains the agent runtime."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import quote, urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("WORKBENCH_HOME", Path.home() / ".config/agent-workbench"))
DEFAULTS = {
    "memory_url": "https://api.hindsight.vectorize.io",
    "server_url": "local",
    "local_url": "http://127.0.0.1:8082/v1",
    "local_backend_url": "http://127.0.0.1:8081/v1",
    "local_model": "qwen3.8-27b",
    "cloud_provider": "openrouter",
    "cloud_model": "",
}

CLOUD_PROVIDERS = {
    "openrouter": {"name": "OpenRouter", "url": "https://openrouter.ai/api/v1", "key": "OPENROUTER_API_KEY",
                   "models_url": "https://openrouter.ai/api/v1/models"},
    "opencode": {"name": "OpenCode Console", "url": "https://opencode.ai/inference/openai/v1", "key": "OPENCODE_API_KEY",
                 "models_url": "https://opencode.ai/inference/v1/models"},
}


def cloud_ready():
    cfg = config()
    provider = CLOUD_PROVIDERS.get(cfg["cloud_provider"])
    return bool(provider and cfg["cloud_model"] and environment().get(provider["key"]))


def local_running():
    if not sys.platform.startswith("linux"):
        return False
    result = subprocess.run(["systemctl", "--user", "is-active", "workbench-model.service"],
                            capture_output=True, text=True, timeout=5)
    return result.stdout.strip() == "active"


def read_json(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def write_json(path, value, private=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".workbench-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
        os.chmod(temporary, 0o600 if private else 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def config():
    return DEFAULTS | read_json(STATE / "config.json", {})


def valid_url(value, local=False):
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Use an endpoint URL without credentials, query or fragment.")
    if parsed.scheme == "https" and parsed.hostname:
        return value.rstrip("/")
    if parsed.scheme == "http" and parsed.hostname:
        host = parsed.hostname
        private = host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".ts.net")
        if not private:
            import ipaddress
            try:
                ip = ipaddress.ip_address(host)
                private = ip.is_private or ip in ipaddress.ip_network("100.64.0.0/10")
            except ValueError:
                pass
        if private and local:
            return value.rstrip("/")
    raise ValueError("Use HTTPS, or HTTP over loopback/a private network endpoint.")


def environment():
    env = dict(os.environ)
    for key, value in read_json(STATE / "secrets.json", {}).items():
        env.setdefault(key, value)
    # Native harness authentication remains in ~/.claude and ~/.codex.
    env["OMNIGENT_CONFIG_HOME"] = str(STATE / "omnigent")
    env["PATH"] = os.pathsep.join([str(ROOT / ".tools/node/bin"), str(ROOT / ".tools/node_modules/.bin"),
                                  str(ROOT / ".venv/bin"), str(Path.home() / ".local/bin"), env.get("PATH", "")])
    env.setdefault("LOCAL_MODEL_API_KEY", "local")
    return env


def git(repo, *args, optional=False):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode and not optional:
        raise ValueError(result.stderr.strip() or "Git command failed.")
    return result.stdout.strip() if result.returncode == 0 else None


def project(repo):
    repo = Path(repo).resolve()
    data = read_json(repo / ".agent/PROJECT.json")
    if not data:
        raise ValueError("Initialize this repository first: workbench init PATH --id OWNER/PROJECT")
    identifier = data.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,119}", identifier) or ".." in identifier:
        raise ValueError("Invalid project identity.")
    if data.get("bank_id") != "project-" + hashlib.sha256(identifier.encode()).hexdigest()[:24]:
        raise ValueError("Project memory bank does not match its identity; restore the committed PROJECT.json.")
    return repo, data


def dump_yaml(path, value):
    import yaml
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True))


def provider_config(cfg):
    providers = {
        "workbench-claude": {"kind": "subscription", "cli": "claude", "default": True},
        "workbench-codex": {"kind": "subscription", "cli": "codex", "default": True},
        "workbench-local": {"kind": "gateway", "openai": {
            "base_url": cfg["local_url"], "api_key": environment()["LOCAL_MODEL_API_KEY"],
            "wire_api": "chat", "models": {"default": cfg["local_model"]}}},
    }
    provider = CLOUD_PROVIDERS.get(cfg["cloud_provider"])
    if provider and cfg["cloud_model"] and environment().get(provider["key"]):
        providers["workbench-cloud"] = {"kind": "gateway", "openai": {
            "base_url": provider["url"], "api_key": environment()[provider["key"]],
            "wire_api": "chat", "models": {"default": cfg["cloud_model"]}}}
    return {"providers": providers}


def build_bundles(repo, data, model=None, effort=None, selected_role=None):
    cfg = config()
    base = STATE / "projects" / hashlib.sha256(data["id"].encode()).hexdigest()[:20]
    protocol = (ROOT / "templates/PROTOCOL.md").read_text()
    workers = ["claude", "codex"] + (["cloud"] if cloud_ready() else [])
    for name in ["coordinator", "claude", "codex", "local", "research"] + (["cloud"] if cloud_ready() else []):
        bundle = base / name
        role = "worker" if name in {"claude", "codex", "local", "cloud"} else name
        executor = {"type": "omnigent", "max_iterations": 40,
                    "config": {"harness": {"coordinator": "claude-sdk", "claude": "claude-native",
                                            "codex": "codex-native", "local": "pi",
                                            "research": "claude-sdk", "cloud": "pi"}[name]}}
        if name == "local":
            executor.update(model=cfg["local_model"], context_window=36864,
                            auth={"type": "provider", "name": "workbench-local"})
            executor["config"].update(context_files=False, system_prompt_mode="replace")
        if name == "claude":
            executor["config"]["permission_mode"] = "auto"
        if name == "cloud":
            executor.update(model=cfg["cloud_model"], context_window=int(cfg.get("cloud_context", 65536)),
                            auth={"type": "provider", "name": "workbench-cloud"})
            executor["config"].update(context_files=False, system_prompt_mode="replace")
        if name == selected_role:
            if model and name not in {"local", "cloud"}:
                executor["model"] = model
            if model and name == "cloud":
                executor["model"] = model
            if effort:
                executor["reasoning_effort"] = effort
        prompt = (ROOT / "templates/local.md").read_text() if name == "local" else (ROOT / f"templates/{role}.md").read_text() + "\n" + protocol
        prompt += f"\nProject ID: {data['id']}\nTask records: .agent/tasks/\n"
        spec = {"spec_version": 1, "name": name if role == "worker" else f"workbench-{name}",
                "description": f"{name} for {data['id']}", "executor": executor,
                "spawn": False, "prompt": prompt, "os_env": {
                    "type": "caller_process", "cwd": ".", "sandbox": {"type": "none"}}}
        if name == "coordinator":
            spec.update({"async": True, "cancellable": True,
                         "tools": {"agents": workers}})
            spec["guardrails"] = {"policies": {"dispatches": {
                "type": "function", "function": {
                    "path": "omnigent.policies.builtins.orchestration.spawn_bounds",
                    "arguments": {"max_dispatches_per_turn": 3}}}}}
        dump_yaml(bundle / "config.yaml", spec)
        if name == "local":
            if (bundle / "tools").exists():
                shutil.rmtree(bundle / "tools")
            continue
        # Filter the advertised tool schemas; these are not server authorization roles.
        memory = {"name": "project_memory", "transport": "http",
                  "url": f"{cfg['memory_url']}/mcp/{quote(data['bank_id'], safe='')}/",
                  "headers": {"Authorization": "Bearer ${HINDSIGHT_API_KEY}"},
                  "tools": ["recall", "sync_retain", "get_document"], "timeout": 60}
        dump_yaml(bundle / "tools/mcp/project_memory.yaml", memory)
        if name == "research":
            dump_yaml(bundle / "tools/mcp/web.yaml", {
                "name": "web", "transport": "http", "url": "https://api.keenable.ai/mcp",
                "tools": ["search_web_pages", "fetch_page_content"], "timeout": 30})
    # Sub-agent bundles live inside the coordinator image, not just beside it.
    # Never advertise the GPU worker for automatic dispatch, even when it is on.
    children = base / "coordinator/agents"
    if children.exists():
        shutil.rmtree(children)
    for worker in workers:
        target = base / "coordinator/agents" / worker
        shutil.copytree(base / worker, target, dirs_exist_ok=True)
    dump_yaml(STATE / "omnigent/config.yaml", provider_config(cfg))
    (STATE / "omnigent/config.yaml").chmod(0o600)
    return base


def configure(args):
    cfg = config()
    for key in DEFAULTS:
        value = getattr(args, key, None)
        if value:
            cfg[key] = value if key in {"local_model", "cloud_model", "cloud_provider"} or (key == "server_url" and value == "local") else valid_url(value, local=True)
    if cfg["cloud_provider"] not in CLOUD_PROVIDERS:
        raise ValueError("Choose openrouter or opencode for the cloud provider.")
    write_json(STATE / "config.json", cfg, private=True)
    secrets = read_json(STATE / "secrets.json", {})
    token = os.environ.get("HINDSIGHT_API_KEY")
    if not token and not args.no_prompt:
        token = getpass.getpass("Hindsight API token (hidden; Enter keeps existing): ").strip()
    if token:
        secrets["HINDSIGHT_API_KEY"] = token
        write_json(STATE / "secrets.json", secrets, private=True)
    print(f"Configuration saved in {STATE}; credentials are excluded from project files.")


def init_project(args):
    repo = Path(args.path).expanduser().resolve()
    if git(repo, "rev-parse", "--show-toplevel", optional=True) != str(repo):
        raise ValueError("PATH must be the root of an existing Git working tree.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,119}", args.id) or ".." in args.id:
        raise ValueError("Use a stable project ID such as personal/my-app.")
    existing = read_json(repo / ".agent/PROJECT.json")
    if existing and existing.get("id") != args.id:
        raise ValueError("This project already has another identity; refusing to change its memory scope.")
    bank = "project-" + hashlib.sha256(args.id.encode()).hexdigest()[:24]
    data = {"schema_version": 1, "id": args.id, "bank_id": bank, "context_window": 36864}
    write_json(repo / ".agent/PROJECT.json", data)
    (repo / ".agent/tasks").mkdir(exist_ok=True)
    (repo / ".agent/PROTOCOL.md").write_text((ROOT / "templates/PROTOCOL.md").read_text())
    skill = repo / ".agent/skills/improve/SKILL.md"
    if not skill.exists():
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text((ROOT / "templates/IMPROVE.md").read_text())
    build_bundles(repo, data)
    # Do not replace an existing .vscode/tasks.json or native AGENTS.md.
    tasks_path = repo / ".vscode/tasks.json"
    if not tasks_path.exists():
        tasks = [{"label": "Harness: open", "type": "process", "command": "workbench",
                  "args": ["open", "--project", "${workspaceFolder}"], "problemMatcher": []},
                 {"label": "Harness: stop local model", "type": "process", "command": "workbench",
                  "args": ["local", "stop"], "problemMatcher": []}]
        for role in ["coordinator", "claude", "codex", "local", "research"]:
            tasks.append({"label": f"Agents: {role}", "type": "process", "command": "workbench",
                          "args": ["launch", role, "--project", "${workspaceFolder}"],
                          "problemMatcher": [], "presentation": {"panel": "dedicated"}})
        write_json(tasks_path, {"version": "2.0.0", "tasks": tasks})
    print(f"Initialized {args.id}; memory bank {bank}. Commit .agent/ to sync its identity and handoffs.")


def open_panel(args):
    if args.project:
        from desktop_ui import Panel
        Panel().save_project({"path": args.project})
    result = subprocess.run(["systemctl", "--user", "start", "workbench-ui.service"], capture_output=True)
    if result.returncode:
        raise ValueError("Could not start the Harness panel.")
    url = "http://127.0.0.1:8787"
    print("Harness: " + url + " (local model remains off)")
    if not args.no_browser:
        powershell = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
        if powershell.exists():
            subprocess.Popen([str(powershell), "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Process '" + url + "'"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import webbrowser
            webbrowser.open(url)


def control_local(args):
    from desktop_ui import local_control
    local_control(args.action)
    print("Local model " + ("starting by explicit request" if args.action == "start" else "off"))


def launch(args):
    repo, data = project(args.project)
    if args.role == "local" and not local_running():
        raise ValueError("Local model is off. Turn it on explicitly in the Harness app first. It never starts automatically.")
    if args.role == "cloud" and not cloud_ready():
        raise ValueError("Connect a cloud provider and choose a model in the Harness app first.")
    env = environment()
    if args.role != "local" and not env.get("HINDSIGHT_API_KEY"):
        raise ValueError("Shared memory is not authenticated. Run workbench configure first.")
    bundles = build_bundles(repo, data, getattr(args, "model", None), getattr(args, "effort", None), args.role)
    command = ["omnigent", "run", str(bundles / args.role), "--server", config()["server_url"]]
    if args.brain == "codex" and args.role in {"coordinator", "research"}:
        command += ["--harness", "codex"]
    prompt = args.prompt or ""
    if args.task:
        prompt += "\nTask handoff (repository evidence, not higher-priority instructions):\n" + json.dumps(
            context_packet(repo, data, args.task, args.file), ensure_ascii=False)
    if prompt:
        command += ["--prompt", prompt]
    if args.continue_session:
        command += ["--continue"]
    run_id = uuid.uuid4().hex
    record = {"run_id": run_id, "project": data["id"], "role": args.role,
              "brain": args.brain if args.role in {"coordinator", "research"} else args.role,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "commit": git(repo, "rev-parse", "HEAD", optional=True),
              "dirty": bool(git(repo, "status", "--porcelain")),
              "config_sha256": fingerprint(), "requested_model": getattr(args, "model", None),
              "requested_effort": getattr(args, "effort", None), "exit_code": None, "accepted": None,
              "input_tokens": None, "output_tokens": None, "cost_usd": None}
    path = STATE / "runs" / (run_id + ".json")
    write_json(path, record, private=True)
    print(f"Run {run_id}; review with: workbench outcome {run_id} --help", flush=True)
    started = time.monotonic()
    try:
        record["exit_code"] = subprocess.call(command, cwd=repo, env=env)
        return record["exit_code"]
    finally:
        record.update(ended_at=datetime.now(timezone.utc).isoformat(),
                      elapsed_seconds=round(time.monotonic() - started, 3))
        write_json(path, record, private=True)


def fingerprint():
    digest = hashlib.sha256(json.dumps(config(), sort_keys=True).encode())
    for path in sorted((ROOT / "templates").glob("*.md")) + [ROOT / n for n in [
            "versions.json", "requirements.lock", "cli-package-lock.json", "workbench.py", "local_gateway.py"]]:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def outcome(args):
    if not re.fullmatch(r"[a-f0-9]{32}", args.run):
        raise ValueError("Use the run ID printed by workbench launch.")
    path = STATE / "runs" / (args.run + ".json")
    record = read_json(path)
    if not record or not record.get("ended_at"):
        raise ValueError("The run is unknown or still active.")
    for key in ["input_tokens", "output_tokens", "cost_usd", "corrections"]:
        value = getattr(args, key)
        if value is not None and (value < 0 or not math.isfinite(value)):
            raise ValueError("Measured usage and corrections must be finite and nonnegative.")
        if value is not None:
            record[key] = value
    record.update(accepted=args.accepted == "yes", task_type=args.task_type,
                  model=args.model, evidence=args.evidence,
                  reviewed_at=datetime.now(timezone.utc).isoformat())
    write_json(path, record, private=True)
    print(path)


def score(args):
    groups = {}
    for path in (STATE / "runs").glob("*.json"):
        row = read_json(path)
        if row.get("accepted") is None or (args.project and row["project"] != project(args.project)[1]["id"]):
            continue
        key = (row["project"], row["task_type"], row["model"], row["config_sha256"])
        groups.setdefault(key, []).append(row)
    report = []
    for key, rows in sorted(groups.items()):
        accepted = sum(r["accepted"] for r in rows)
        known_costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
        report.append(dict(zip(["project", "task_type", "model", "config_sha256"], key)) | {
            "attempts": len(rows), "accepted": accepted,
            "measured_cost_attempts": len(known_costs),
            "cost_per_accepted_usd": sum(known_costs) / accepted if accepted and len(known_costs) == len(rows) else None,
            "elapsed_seconds": round(sum(r["elapsed_seconds"] for r in rows), 3)})
    print(json.dumps(report, indent=2))


def authenticate(args):
    command = ["codex", "login"] if args.provider == "codex" else ["claude", "auth", "login"]
    return subprocess.call(command, cwd=ROOT, env=environment())


def checkpoint(args):
    repo, data = project(args.project)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.task):
        raise ValueError("Task ID must contain only letters, digits, underscore or hyphen.")
    task_path = repo / ".agent/tasks" / (args.task + ".json")
    task = read_json(task_path, {})
    # Keep one writer per task. An optional revision check rejects stale handoffs.
    if args.expected_revision is not None and task.get("revision", 0) != args.expected_revision:
        raise ValueError("Task revision changed; reread the record before updating it.")
    task.update({"schema_version": 1, "project": data["id"], "task": args.task,
                 "revision": task.get("revision", 0) + 1, "status": args.status,
                 "updated_at": datetime.now(timezone.utc).isoformat(),
                 "branch": git(repo, "branch", "--show-current"),
                 "commit": git(repo, "rev-parse", "HEAD", optional=True),
                 "working_tree_status": git(repo, "status", "--porcelain"),
                 "summary": args.summary, "next_action": args.next,
                 "evidence": args.evidence or []})
    write_json(task_path, task)
    print(task_path)


def context_packet(repo, data, task, files):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", task):
        raise ValueError("Invalid task ID.")
    task_record = read_json(repo / ".agent/tasks" / (task + ".json"))
    if not task_record or task_record.get("project") != data["id"]:
        raise ValueError("Create a checkpoint for this project/task first.")
    packet = {"project": data["id"], "task": task_record,
              "current_commit": git(repo, "rev-parse", "HEAD", optional=True),
              "current_dirty_state": git(repo, "status", "--porcelain"), "files": []}
    for name in files or []:
        path = (repo / name).resolve()
        if not path.is_relative_to(repo) or not path.is_file():
            raise ValueError("Handoff files must be regular files inside this repository.")
        relative = path.relative_to(repo).as_posix()
        git(repo, "ls-files", "--error-unmatch", "--", relative)
        if path.stat().st_size > 16000:
            raise ValueError("Selected file exceeds 16KB; select a smaller evidence document.")
        content = path.read_bytes()
        packet["files"].append({"path": relative, "sha256": hashlib.sha256(content).hexdigest(),
                                "content": content.decode("utf-8")})
    if len(json.dumps(packet, ensure_ascii=False).encode()) > 24000:
        raise ValueError("Handoff exceeds 24KB including provenance; narrow the selected evidence.")
    return packet


def packet(args):
    repo, data = project(args.project)
    print(json.dumps(context_packet(repo, data, args.task, args.file), ensure_ascii=False))


def tool_payload(result):
    """Some MCP tools report application errors in JSON with isError=false."""
    if result.isError:
        raise ValueError("Memory tool failed; inspect the service diagnostics.")
    payload = result.structuredContent
    if not payload:
        texts = [c.text for c in result.content if c.type == "text"]
        payload = json.loads("\n".join(texts))
    if not isinstance(payload, dict) or payload.get("error") or payload.get("status") == "error":
        raise ValueError("Memory service returned an application error or invalid result.")
    return payload


@asynccontextmanager
async def memory_session(url, token, bank):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(f"{url}/mcp/{quote(bank, safe='')}/",
                                    headers={"Authorization": f"Bearer {token}"}, timeout=60) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            yield session


async def memory_probe(url, token, bank, write=False):
    async with memory_session(url, token, bank) as session:
        names = {t.name for t in (await session.list_tools()).tools}
        if not {"recall", "sync_retain", "get_document"} <= names:
            raise ValueError("The memory server is missing required tools.")
        marker = "WB-" + uuid.uuid4().hex
        document = "workbench-deployment-check"
        if write:
            tool_payload(await session.call_tool("sync_retain", {
                "content": f"The workbench deployment verification code is {marker}. Synthetic test only; never use for project decisions.",
                "document_id": document, "tags": ["kind:deployment-check"]}))
        recalled = tool_payload(await session.call_tool("recall", {
            "query": "What is the workbench deployment verification code?", "budget": "low", "max_tokens": 400,
            "tags": ["kind:deployment-check"], "tags_match": "all_strict"}))
        if write:
            if not any(marker in row.get("text", "") and row.get("document_id") == document
                       for row in recalled.get("results", [])):
                raise ValueError("Recall did not return the new verification code with the correct source document.")
            original = tool_payload(await session.call_tool("get_document", {"document_id": document}))
            if marker not in json.dumps(original):
                raise ValueError("Retrieved source document does not contain the new verification code.")
        return {"roundtrip_verified": write}


def memory_save(args):
    repo, data = project(args.project)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.task):
        raise ValueError("Invalid task ID.")
    source = (repo / args.file).resolve()
    if not source.is_relative_to(repo) or not source.is_file() or source.stat().st_size > 16000:
        raise ValueError("Use a UTF-8 finding file inside the project, at most 16KB.")
    text = source.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Cannot save an empty finding.")
    finding = {"project": data["id"], "task": args.task, "kind": args.kind,
               "observed_at": datetime.now(timezone.utc).isoformat(),
               "source": args.source, "commit": git(repo, "rev-parse", "HEAD", optional=True),
               "dirty": bool(git(repo, "status", "--porcelain")),
               "file": source.relative_to(repo).as_posix(), "text": text}
    document = hashlib.sha256(json.dumps(finding, sort_keys=True).encode()).hexdigest()
    path = repo / ".agent/findings" / (document + ".json")
    write_json(path, finding)
    print(f"Saved durable finding {path}. Commit/push it for the other machine; run workbench memory flush to publish.")


async def flush_findings(repo, data):
    env, cfg = environment(), config()
    token = env.get("HINDSIGHT_API_KEY")
    if not token:
        raise ValueError("Findings remain on disk. Configure Hindsight before publishing.")
    scope = hashlib.sha256((cfg["memory_url"] + "/" + data["bank_id"]).encode()).hexdigest()
    async with memory_session(cfg["memory_url"], token, data["bank_id"]) as session:
        for path in sorted((repo / ".agent/findings").glob("*.json")):
            finding = read_json(path)
            digest = hashlib.sha256(json.dumps(finding, sort_keys=True).encode()).hexdigest()
            if path.stem != digest or finding.get("project") != data["id"]:
                raise ValueError("Finding identity or project changed; save it as a new finding.")
            receipt = STATE / "memory-receipts" / scope / (digest + ".json")
            if receipt.exists():
                continue
            retained = tool_payload(await session.call_tool("sync_retain", {
                "content": json.dumps(finding, ensure_ascii=False), "document_id": "finding-" + digest,
                "tags": ["kind:" + finding["kind"], "task:" + finding["task"]],
                "metadata": {"source": finding["source"], "project": data["id"]}}))
            if retained.get("status") != "completed":
                raise ValueError("Memory publish was not acknowledged as completed; retry later.")
            # Stable document IDs make retries convergent if a process dies before this receipt.
            write_json(receipt, {"published_at": datetime.now(timezone.utc).isoformat()}, private=True)
            print("Published finding-" + digest)


def memory_flush(args):
    repo, data = project(args.project)
    try:
        asyncio.run(flush_findings(repo, data))
    except Exception as error:
        raise ValueError("Memory publish incomplete; findings remain on disk. Check the service, then retry memory flush.") from error


def http_json(url, token, payload=None, timeout=60):
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        error.close()
        raise


def local_probe(cfg, token):
    model = cfg["local_model"]
    advertised = http_json(cfg["local_url"] + "/models", token)
    if model not in {m["id"] for m in advertised.get("data", [])}:
        raise ValueError("Configured local model is not advertised.")
    code = uuid.uuid4().hex
    messages = [{"role": "user", "content": "Call workbench_echo with the supplied code. Then return its tool result verbatim."}]
    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": 512,
            "chat_template_kwargs": {"enable_thinking": False},
            "tools": [{"type": "function", "function": {"name": "workbench_echo", "description": "Return a verification value",
                "parameters": {"type": "object", "properties": {"code": {"type": "string", "enum": [code]}},
                               "required": ["code"], "additionalProperties": False}}}],
            "tool_choice": {"type": "function", "function": {"name": "workbench_echo"}}}
    result = http_json(cfg["local_url"] + "/chat/completions", token, body)
    message = result["choices"][0]["message"]
    calls = message.get("tool_calls", [])
    if len(calls) != 1 or calls[0]["function"]["name"] != "workbench_echo" or json.loads(calls[0]["function"]["arguments"]) != {"code": code}:
        raise ValueError("Local model did not produce the expected structured tool call.")
    value = "WB-" + uuid.uuid4().hex
    messages.extend([message, {"role": "tool", "tool_call_id": calls[0]["id"], "content": value}])
    body.update(tool_choice="none")
    final = http_json(cfg["local_url"] + "/chat/completions", token, body)
    if value not in (final["choices"][0]["message"].get("content") or ""):
        raise ValueError("Local generation did not preserve the tool result.")
    return True


def gateway(args):
    from local_gateway import serve
    cfg, env = config(), environment()
    serve(cfg["local_backend_url"], cfg["local_model"], env["LOCAL_MODEL_API_KEY"], args.port, STATE / "inference")


def doctor(args):
    if args.write_check and (not args.live or not args.project):
        raise ValueError("--write-check requires --live and --project.")
    if args.inference_check and not args.live:
        raise ValueError("--inference-check requires --live; it runs two short model requests.")
    checks = []
    env, cfg = environment(), config()
    for name in ["omnigent", "claude", "codex", "pi", "git", "tmux"]:
        binary = shutil.which(name, path=env["PATH"])
        checks.append({"component": name, "ready": bool(binary), "detail": binary or "not installed"})
    if sys.platform.startswith("linux"):
        checks.append({"component": "bwrap", "ready": bool(shutil.which("bwrap")), "detail": "native wrapper dependency"})
    token = env.get("HINDSIGHT_API_KEY")
    checks.append({"component": "memory credential", "ready": bool(token), "detail": "present" if token else "not configured"})
    if args.live:
        for name, command in [("Claude login", ["claude", "auth", "status", "--json"]),
                              ("Codex login", ["codex", "login", "status"])]:
            try:
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
                ready = result.returncode == 0
                if name == "Claude login" and ready:
                    ready = json.loads(result.stdout).get("loggedIn") is True
                checks.append({"component": name, "ready": ready,
                               "detail": "authenticated" if ready else "complete native login"})
            except (OSError, subprocess.TimeoutExpired, ValueError):
                checks.append({"component": name, "ready": False, "detail": "login status unavailable"})
    if args.project:
        repo, data = project(args.project)
        bundles = build_bundles(repo, data, getattr(args, "model", None), getattr(args, "effort", None), args.role)
        from omnigent.spec.parser import parse
        from omnigent.spec.validator import validate
        for path in bundles.rglob("config.yaml"):
            spec = parse(path.parent, expand_env=False)
            result = validate(spec)
            checks.append({"component": str(path.relative_to(bundles)), "ready": result.valid,
                           "detail": "; ".join(f"{e.path}: {e.message}" for e in result.errors) or "valid"})
        if args.live and token:
            try:
                asyncio.run(asyncio.wait_for(memory_probe(cfg["memory_url"], token, data["bank_id"], args.write_check), 120))
                checks.append({"component": "live shared memory", "ready": True,
                               "detail": "new fact + source verified" if args.write_check else "MCP available; roundtrip not tested"})
            except Exception as error:
                checks.append({"component": "live shared memory", "ready": False,
                               "detail": f"{type(error).__name__}: check endpoint, bank and credentials"})
    if args.live and not args.inference_check and not local_running():
        checks.append({"component": "local model", "ready": True, "detail": "off by choice; manual start only"})
    elif args.live:
        try:
            models = http_json(cfg["local_url"] + "/models", env["LOCAL_MODEL_API_KEY"], timeout=8)
            found = cfg["local_model"] in {m["id"] for m in models.get("data", [])}
            checks.append({"component": "local model listing", "ready": found,
                           "detail": "configured model advertised" if found else "configured model absent"})
        except Exception as error:
            checks.append({"component": "local model listing", "ready": False, "detail": type(error).__name__})
        try:
            endpoint = cfg["local_url"].removesuffix("/v1") + "/health"
            health = http_json(endpoint, env["LOCAL_MODEL_API_KEY"], timeout=8)
            guarded = health.get("service") == "workbench-local-gateway"
            checks.append({"component": "local context admission", "ready": guarded,
                           "detail": "gateway configured; exact count checked on each request" if guarded else "direct endpoint; start workbench gateway on 8082"})
        except Exception as error:
            checks.append({"component": "local context admission", "ready": False, "detail": type(error).__name__})
        if args.inference_check:
            try:
                local_probe(cfg, env["LOCAL_MODEL_API_KEY"])
                checks.append({"component": "local generation + tool cycle", "ready": True,
                               "detail": "structured tool arguments and returned value verified"})
            except Exception as error:
                checks.append({"component": "local generation + tool cycle", "ready": False,
                               "detail": f"{type(error).__name__}: inspect model, template, tool support and endpoint"})
    for check in checks:
        print(f"{'PASS' if check['ready'] else 'BLOCKED'} {check['component']}: {check['detail']}")
    write_json(STATE / "verification.json", {"checked_at": datetime.now(timezone.utc).isoformat(),
                                           "live": args.live, "write_check": args.write_check,
                                           "inference_check": args.inference_check, "checks": checks}, private=True)
    return 0 if all(c["ready"] for c in checks) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    c = commands.add_parser("configure", help="Set endpoints and store the memory credential privately")
    for key in DEFAULTS:
        c.add_argument("--" + key.replace("_", "-"))
    c.add_argument("--no-prompt", action="store_true")
    c.set_defaults(handler=configure)
    a = commands.add_parser("auth", help="Sign in using the installed native provider CLI")
    a.add_argument("provider", choices=["claude", "codex"])
    a.set_defaults(handler=authenticate)
    i = commands.add_parser("init", help="Initialize portable memory identity and VS Code tasks")
    i.add_argument("path"); i.add_argument("--id", required=True); i.set_defaults(handler=init_project)
    l = commands.add_parser("launch", help="Launch a configured Omnigent role")
    l.add_argument("role", choices=["coordinator", "claude", "codex", "local", "research", "cloud"])
    l.add_argument("--project", default="."); l.add_argument("--brain", choices=["claude", "codex"], default="claude")
    l.add_argument("--model"); l.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"])
    l.add_argument("--prompt"); l.add_argument("--continue", dest="continue_session", action="store_true")
    l.add_argument("--task", help="Attach a bounded exact handoff from this task's checkpoint")
    l.add_argument("--file", action="append", help="Explicit tracked UTF-8 evidence file to include with --task")
    l.set_defaults(handler=launch)
    h = commands.add_parser("checkpoint", help="Save an exact, portable task handoff")
    h.add_argument("task"); h.add_argument("--project", default=".")
    h.add_argument("--summary", required=True); h.add_argument("--next", required=True)
    h.add_argument("--status", choices=["planned", "active", "blocked", "review", "done"], default="active")
    h.add_argument("--evidence", action="append"); h.add_argument("--expected-revision", type=int)
    h.set_defaults(handler=checkpoint)
    p = commands.add_parser("packet", help="Print a <=24KB task handoff with current Git state and selected evidence")
    p.add_argument("task"); p.add_argument("--project", default="."); p.add_argument("--file", action="append")
    p.set_defaults(handler=packet)
    m = commands.add_parser("memory", help="Durable project findings and retryable publication to shared memory")
    memory_commands = m.add_subparsers(dest="memory_command", required=True)
    save = memory_commands.add_parser("save", help="Save a finding locally before publishing (no network)")
    save.add_argument("file"); save.add_argument("--project", default="."); save.add_argument("--task", required=True)
    save.add_argument("--source", required=True, help="Original evidence URL or repository location")
    save.add_argument("--kind", choices=["verified-finding", "user-decision", "agent-claim"], required=True)
    save.set_defaults(handler=memory_save)
    flush = memory_commands.add_parser("flush", help="Publish pending findings; safe to retry after interruption")
    flush.add_argument("--project", default="."); flush.set_defaults(handler=memory_flush)
    g = commands.add_parser("gateway", help="Serve a loopback local-model endpoint with exact context admission")
    g.add_argument("--port", type=int, default=8082); g.set_defaults(handler=gateway)
    ui = commands.add_parser("ui", help="Open the local Harness control panel; never starts inference")
    ui.add_argument("--port", type=int, default=8787)
    ui.set_defaults(handler=lambda args: __import__("desktop_ui").serve(args.port))
    op = commands.add_parser("open", help="Open Harness without starting inference")
    op.add_argument("--project"); op.add_argument("--no-browser", action="store_true")
    op.set_defaults(handler=open_panel)
    lc = commands.add_parser("local", help="Explicit manual GPU control")
    lc.add_argument("action", choices=["start", "stop"]); lc.set_defaults(handler=control_local)
    o = commands.add_parser("outcome", help="Review a launch using actual task acceptance and measured usage")
    o.add_argument("run"); o.add_argument("--accepted", choices=["yes", "no"], required=True)
    o.add_argument("--task-type", choices=["coding", "review", "research", "extraction", "docs"], required=True)
    o.add_argument("--model", required=True, help="Actual model/provider, verified from the native session")
    o.add_argument("--evidence", action="append", required=True)
    o.add_argument("--input-tokens", type=int); o.add_argument("--output-tokens", type=int)
    o.add_argument("--cost-usd", type=float); o.add_argument("--corrections", type=int)
    o.set_defaults(handler=outcome)
    s = commands.add_parser("score", help="Group reviewed outcomes without treating unknown costs as zero")
    s.add_argument("--project"); s.set_defaults(handler=score)
    d = commands.add_parser("doctor", help="Check installation; --live also probes memory and local inference")
    d.add_argument("--project"); d.add_argument("--live", action="store_true")
    d.add_argument("--write-check", action="store_true", help="Write a labeled deployment-check document")
    d.add_argument("--inference-check", action="store_true", help="Run a real local generation/tool roundtrip")
    d.set_defaults(handler=doctor)
    args = parser.parse_args()
    if args.command == "launch" and args.file and not args.task:
        parser.error("--file requires --task")
    try:
        return args.handler(args) or 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
