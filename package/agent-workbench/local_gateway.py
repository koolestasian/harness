"""Loopback-only llama.cpp admission control. Python stdlib; no inference framework."""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid

from workbench import http_json, write_json

CONTEXT = 36864
INPUT_LIMIT = 24576
OUTPUT_LIMIT = 8192
MARGIN = 1024


def admit(body, upstream, model, token):
    if not isinstance(body, dict) or body.get("model") != model or not isinstance(body.get("messages"), list) or not body["messages"]:
        raise ValueError("Use the configured model and a nonempty chat messages array.")
    # The MVP counts text + tools exactly; image/audio admission needs a separate measured profile.
    for message in body["messages"]:
        if not isinstance(message, dict):
            raise ValueError("Messages must be objects.")
        content = message.get("content", "")
        text_parts = isinstance(content, list) and all(
            isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
            for part in content)
        if not isinstance(content, (str, type(None))) and not text_parts:
            raise ValueError("This 36k profile accepts text and tool messages only.")
    output = min(OUTPUT_LIMIT, *(body.get(k, OUTPUT_LIMIT) for k in ["max_tokens", "max_completion_tokens", "n_predict"]))
    if type(output) is not int or output < 1:
        raise ValueError("Output budget must be a positive integer.")
    body = dict(body, max_tokens=output, n_predict=output)
    body.pop("max_completion_tokens", None)
    if body.get("stream"):
        body["stream_options"] = {"include_usage": True}
    # Same server parses the complete request: system prompt, history, tool schemas and template.
    counted = http_json(upstream + "/chat/completions/input_tokens", token, body, timeout=30)
    count = counted.get("input_tokens")
    if type(count) is not int or count < 1:
        raise ValueError("llama.cpp did not return an exact input token count; upgrade the server.")
    if count > INPUT_LIMIT or count + output + MARGIN > CONTEXT:
        raise ValueError(f"Context budget exceeded ({count} input tokens). Checkpoint; start a fresh bounded task. No history was discarded.")
    return body, count


def make_server(upstream, model, token, port, traces):
    parsed = urlsplit(upstream)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.path.rstrip("/") != "/v1":
        raise ValueError("Gateway upstream must be a loopback HTTP llama.cpp /v1 endpoint; tunnel remote inference first.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port == port:
        raise ValueError("Use distinct gateway/backend ports without URL credentials or query strings.")
    slot = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No raw prompts, paths, credentials or tool results in access logs.

        def setup(self):
            super().setup()
            self.connection.settimeout(60)

        def reply(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                self.reply(401, {"error": {"message": "Local gateway authentication required."}})
                return False
            return True

        def do_GET(self):
            if not self.authorized():
                return
            if self.path == "/health":
                self.reply(200, {"service": "workbench-local-gateway", "input_limit": INPUT_LIMIT,
                                 "output_limit": OUTPUT_LIMIT, "context_window": CONTEXT,
                                 "backend_verified": False})
            elif self.path == "/v1/models":
                try:
                    self.reply(200, http_json(upstream + "/models", token, timeout=10))
                except Exception:
                    self.reply(502, {"error": {"message": "Local backend unavailable."}})
            else:
                self.reply(404, {"error": {"message": "Unknown route."}})

        def do_POST(self):
            if not self.authorized():
                return
            if self.path != "/v1/chat/completions":
                self.reply(404, {"error": {"message": "Only chat completions are supported."}})
                return
            if not slot.acquire(blocking=False):
                self.reply(429, {"error": {"message": "One local generation is already active; wait for its result."}})
                return
            started = time.monotonic()
            record = {"request_id": uuid.uuid4().hex, "model": model, "input_tokens": None,
                      "usage": None, "http_status": None, "completed": False}
            response_started = False
            slot_held = True
            def finish():
                nonlocal slot_held
                record["elapsed_seconds"] = round(time.monotonic() - started, 3)
                try:
                    write_json(Path(traces) / (record["request_id"] + ".json"), record, private=True)
                finally:
                    slot_held = False
                    slot.release()
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 4 * 1024 * 1024 or self.headers.get("Transfer-Encoding"):
                    raise ValueError("Use a JSON request with Content-Length between 1 byte and 4MB.")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete request body.")
                body, count = admit(json.loads(raw), upstream, model, token)
                record["input_tokens"] = count
                request = Request(upstream + "/chat/completions", data=json.dumps(body).encode(),
                                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
                with urlopen(request, timeout=300) as response:
                    record["http_status"] = response.status
                    if body.get("stream"):
                        self.send_response(response.status)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        response_started = True
                        for line in response:
                            if line.strip() == b"data: [DONE]":
                                record["completed"] = True
                                finish()  # Release before the client can dispatch its next tool turn.
                                line += b"\n"
                            elif line.startswith(b"data: "):
                                event = json.loads(line[6:])
                                if event.get("usage"):
                                    record["usage"] = self.usage(event["usage"])
                            self.wfile.write(line)
                            self.wfile.flush()
                            if record["completed"]:
                                break
                        if not record["completed"]:
                            raise OSError("Backend stream ended without a completion marker.")
                    else:
                        result = json.load(response)
                        record["usage"] = self.usage(result.get("usage", {}))
                        record["completed"] = True
                        finish()
                        response_started = True
                        self.reply(response.status, result)
            except (ValueError, TypeError, KeyError) as error:
                record.update(http_status=400, completed=False)
                if slot_held:
                    finish()
                if not response_started:
                    self.reply(400, {"error": {"message": str(error), "type": "workbench_admission_error"}})
            except Exception as error:
                status = error.code if isinstance(error, HTTPError) else 502
                if isinstance(error, HTTPError):
                    error.close()
                record.update(http_status=status, completed=False, error_type=type(error).__name__)
                if slot_held:
                    finish()
                if not response_started:
                    self.reply(status, {"error": {"message": "Local backend/counting failed. No automatic retry; inspect llama.cpp and run doctor --inference-check."}})
            finally:
                if slot_held:
                    finish()

        @staticmethod
        def usage(value):
            # Allowlisted measured counters only; never persist arbitrary backend response fields.
            return {k: v for k, v in value.items() if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                    and type(v) is int and v >= 0} or None

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(upstream, model, token, port, traces):
    with make_server(upstream, model, token, port, traces) as server:
        print(f"Local gateway: http://127.0.0.1:{port}/v1; {INPUT_LIMIT} input / {OUTPUT_LIMIT} output tokens; one active request.", flush=True)
        server.serve_forever()
