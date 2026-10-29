"""Real HTTP boundary checks with a deterministic llama.cpp stand-in, no paid models."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError

import local_gateway as gateway
import workbench as w


@contextmanager
def running(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class GatewayChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.counted = []
        self.generated = []
        self.hold = False
        self.incomplete_stream = False
        self.entered = threading.Event()
        self.release = threading.Event()
        test = self
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def send(self, data, content_type="application/json"):
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(data if isinstance(data, bytes) else json.dumps(data).encode())
            def do_GET(self):
                self.send({"data": [{"id": "local-test"}]})
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path.endswith("/input_tokens"):
                    test.counted.append(body)
                    count = len(json.dumps(body["messages"])) + len(json.dumps(body.get("tools", [])))
                    self.send({"input_tokens": count})
                    return
                test.generated.append(body)
                if test.hold:
                    test.entered.set()
                    test.release.wait(5)
                usage = {"prompt_tokens": 90, "completion_tokens": 10, "total_tokens": 100,
                         "private_backend_field": "SHOULD NEVER BE LOGGED"}
                if body.get("stream"):
                    self.send(b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n' +
                              b'data: ' + json.dumps({"choices": [], "usage": usage}).encode() +
                              (b'\n\n' if test.incomplete_stream else b'\n\ndata: [DONE]\n\n'), "text/event-stream")
                elif isinstance(body.get("tool_choice"), dict):
                    code = body["tools"][0]["function"]["parameters"]["properties"]["code"]["enum"][0]
                    self.send({"choices": [{"message": {"role": "assistant", "content": None,
                        "tool_calls": [{"id": "call1", "type": "function", "function": {
                            "name": "workbench_echo", "arguments": json.dumps({"code": code})}}]}}], "usage": usage})
                else:
                    content = body["messages"][-1]["content"]
                    self.send({"choices": [{"message": {"role": "assistant", "content": content}}], "usage": usage})
        self.backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)

    def tearDown(self):
        self.backend.server_close()
        self.tmp.cleanup()

    @contextmanager
    def endpoints(self):
        with running(self.backend) as backend:
            with running(gateway.make_server(backend + "/v1", "local-test", "test-token", 0, Path(self.tmp.name))) as local:
                yield local

    def body(self):
        return {"model": "local-test", "messages": [{"role": "system", "content": "PRIVATE PROMPT"},
                {"role": "user", "content": "hello"}], "max_tokens": 100000}

    def test_complete_request_is_counted_output_capped_and_oversize_never_reaches_inference(self):
        with self.endpoints() as url:
            body = self.body()
            body["tools"] = [{"type": "function", "function": {"name": "probe", "parameters": {"type": "object"}}}]
            w.http_json(url + "/v1/chat/completions", "test-token", body)
            self.assertEqual(self.counted[0]["tools"], body["tools"])
            self.assertEqual(self.counted[0]["messages"], body["messages"])
            self.assertEqual(self.generated[0]["max_tokens"], gateway.OUTPUT_LIMIT)
            self.assertEqual(self.generated[0]["n_predict"], gateway.OUTPUT_LIMIT)
            body["tools"][0]["function"]["description"] = "x" * gateway.INPUT_LIMIT
            with self.assertRaises(HTTPError) as error:
                w.http_json(url + "/v1/chat/completions", "test-token", body)
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(len(self.generated), 1)
            body["messages"][1]["content"] = [{"type": "image_url", "image_url": {"url": "private"}}]
            with self.assertRaises(HTTPError) as error:
                w.http_json(url + "/v1/chat/completions", "test-token", body)
            self.assertEqual(error.exception.code, 400)
        logs = "".join(p.read_text() for p in Path(self.tmp.name).glob("*.json"))
        self.assertNotIn("PRIVATE", logs)
        self.assertNotIn("test-token", logs)
        self.assertNotIn("SHOULD NEVER", logs)

    def test_tool_cycle_and_stream_forwarding_work_over_real_http(self):
        from urllib.request import Request, urlopen
        with self.endpoints() as url:
            self.assertTrue(w.local_probe({"local_url": url + "/v1", "local_model": "local-test"}, "test-token"))
            self.assertEqual(len(self.generated), 2)
            body = self.body() | {"stream": True}
            request = Request(url + "/v1/chat/completions", data=json.dumps(body).encode(),
                              headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"})
            with urlopen(request, timeout=5) as response:
                streamed = response.read()
            self.assertIn(b"hello", streamed)
            self.assertIn(b"[DONE]", streamed)
            self.assertTrue(self.generated[-1]["stream_options"]["include_usage"])
        records = [json.loads(p.read_text()) for p in Path(self.tmp.name).glob("*.json")]
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r["completed"] and r["usage"]["total_tokens"] == 100 for r in records))

    def test_text_content_parts_are_counted_and_forwarded_without_changes(self):
        with self.endpoints() as url:
            body = self.body()
            body["messages"][1]["content"] = [{"type": "text", "text": "hello"}]
            w.http_json(url + "/v1/chat/completions", "test-token", body)
            self.assertEqual(self.counted[0]["messages"], body["messages"])
            self.assertEqual(self.generated[0]["messages"], body["messages"])
            for part in [{"type": "image_url", "image_url": {"url": "private"}},
                         {"type": "text", "text": 7}]:
                body["messages"][1]["content"].append(part)
                with self.assertRaises(HTTPError):
                    w.http_json(url + "/v1/chat/completions", "test-token", body)
                body["messages"][1]["content"].pop()
            self.assertEqual(len(self.generated), 1)

    def test_auth_and_concurrency_are_enforced_before_backend_work(self):
        with self.endpoints() as url:
            with self.assertRaises(HTTPError) as error:
                w.http_json(url + "/v1/models", "wrong-token")
            self.assertEqual(error.exception.code, 401)
            self.hold = True
            failures = []
            def generate():
                try:
                    w.http_json(url + "/v1/chat/completions", "test-token", self.body())
                except Exception as error:
                    failures.append(error)
            thread = threading.Thread(target=generate)
            thread.start()
            try:
                self.assertTrue(self.entered.wait(3))
                with self.assertRaises(HTTPError) as error:
                    w.http_json(url + "/v1/chat/completions", "test-token", self.body())
                self.assertEqual(error.exception.code, 429)
            finally:
                self.release.set()
                thread.join(timeout=5)
            self.assertEqual(failures, [])
            self.assertEqual(len(self.counted), 1)

    def test_tokenizer_failure_fails_closed_without_guessing(self):
        from unittest.mock import patch
        with self.endpoints() as url:
            with patch.object(gateway, "http_json", return_value={"wrong_field": 1}):
                with self.assertRaises(HTTPError) as error:
                    w.http_json(url + "/v1/chat/completions", "test-token", self.body())
                self.assertEqual(error.exception.code, 400)
            self.assertEqual(self.generated, [])

    def test_stream_disconnect_is_not_recorded_as_completed(self):
        from urllib.request import Request, urlopen
        self.incomplete_stream = True
        with self.endpoints() as url:
            request = Request(url + "/v1/chat/completions", data=json.dumps(self.body() | {"stream": True}).encode(),
                              headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"})
            with urlopen(request, timeout=5) as response:
                self.assertNotIn(b"[DONE]", response.read())
        records = [json.loads(p.read_text()) for p in Path(self.tmp.name).glob("*.json")]
        self.assertFalse(records[0]["completed"])
        self.assertEqual(records[0]["http_status"], 502)


if __name__ == "__main__":
    unittest.main()
