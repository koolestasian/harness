"""HTTP control boundary and manual-only GPU routing. No real inference."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import desktop_ui as ui
import workbench as w


class PanelChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.state_patch = patch.object(w, "STATE", self.state)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)

    def test_usage_preserves_zero_remaining_and_shared_account_windows(self):
        raw = {"rateLimitsByLimitId": {"codex": {"primary": {"usedPercent": 100, "windowDurationMins": 300, "resetsAt": 123}}}}
        async def limits():
            return raw
        with patch.object(ui, "codex_limits", limits), patch.object(ui, "claude_usage", return_value=None), patch.object(w, "environment", return_value={"OPENROUTER_API_KEY": "private-test"}), patch.object(w, "http_json", return_value={"data": {"limit": 10, "usage": 10, "limit_remaining": 0}}):
            snapshot = ui.usage_snapshot()
        self.assertEqual(snapshot["codex"]["windows"][0]["used"], 100)
        self.assertEqual(snapshot["cloud"]["remaining"], 0)
        self.assertNotIn("private-test", json.dumps(snapshot))
        self.assertEqual(snapshot["claude"]["status"], "expired")

    def test_usage_failure_is_unknown_not_zero(self):
        async def unavailable():
            raise OSError("not installed")
        with patch.object(ui, "codex_limits", unavailable), patch.object(ui, "claude_usage", side_effect=OSError("offline")), patch.object(w, "environment", return_value={}):
            snapshot = ui.usage_snapshot()
        self.assertEqual(snapshot["codex"], {"status": "unavailable", "windows": []})
        self.assertEqual(snapshot["claude"], {"status": "unavailable"})
        self.assertNotIn("remaining", snapshot["cloud"])

    def test_claude_usage_reads_plan_windows_without_exposing_or_refreshing_sign_in(self):
        home = self.state / "home"
        (home / ".claude").mkdir(parents=True)
        credentials = home / ".claude/.credentials.json"
        credentials.write_text(json.dumps({"claudeAiOauth": {"accessToken": "private-claude-token", "expiresAt": (ui.time.time() + 3600) * 1000}}))
        reply = {"five_hour": {"utilization": 56.0, "resets_at": "2026-10-29T12:10:00+00:00"},
                 "seven_day": {"utilization": 16.0, "resets_at": "2026-11-02T20:00:00+00:00"},
                 "seven_day_opus": None, "extra_usage": {"is_enabled": False}}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a): return json.dumps(reply).encode()
        with patch.object(ui.Path, "home", return_value=home), patch.object(ui, "urlopen", return_value=Response()) as call:
            windows = ui.claude_usage()
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/api/oauth/usage")
        self.assertIsNone(request.data)
        self.assertEqual([(x["minutes"], x["used"]) for x in windows], [(300, 56.0), (10080, 16.0)])
        self.assertNotIn("private-claude-token", json.dumps(windows))
        expired = json.dumps({"claudeAiOauth": {"accessToken": "old", "expiresAt": 1000}})
        credentials.write_text(expired)
        with patch.object(ui.Path, "home", return_value=home), patch.object(ui, "urlopen") as call:
            self.assertIsNone(ui.claude_usage())
            call.assert_not_called()
        self.assertEqual(credentials.read_text(), expired)

    def test_claude_offers_current_models_with_full_effort_ladder(self):
        models = ui.task_models("claude")
        self.assertEqual([m["id"] for m in models], ["claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"])
        self.assertTrue(all(m["efforts"] == ["low", "medium", "high", "xhigh", "max"] for m in models))

    def test_local_library_lists_complete_models_once(self):
        models = self.state / "models"
        (models / ".partial").mkdir(parents=True)
        (models / "Small-Q4_K_M.gguf").write_bytes(b"x" * 10)
        (models / "Big-Q8_0-00001-of-00002.gguf").write_bytes(b"x" * 5)
        (models / "Big-Q8_0-00002-of-00002.gguf").write_bytes(b"x" * 7)
        (models / "Half-IQ3_S-00001-of-00002.gguf").write_bytes(b"x")
        (models / "mmproj-F16.gguf").write_bytes(b"x")
        (models / ".partial/New-Q4_0.gguf.part").write_bytes(b"x")
        with patch.object(ui, "MODELS", models):
            found = {m["name"]: m for m in ui.local_models()}
        self.assertEqual(set(found), {"Small-Q4_K_M", "Big-Q8_0"})
        self.assertEqual(found["Big-Q8_0"]["size"], 12)
        self.assertEqual(found["Big-Q8_0"]["quant"], "Q8_0")
        self.assertTrue(found["Big-Q8_0"]["id"].endswith("-00001-of-00002.gguf"))
        self.assertEqual(found["Small-Q4_K_M"]["fit"], "fits")

    def test_repository_files_group_splits_and_reject_invalid_names_before_network(self):
        tree = [{"type": "directory", "path": "Q8_0"},
                {"type": "file", "path": "Q8_0/M-Q8_0-00002-of-00002.gguf", "size": 8e9},
                {"type": "file", "path": "Q8_0/M-Q8_0-00001-of-00002.gguf", "size": 9e9},
                {"type": "file", "path": "M-Q4_K_M.gguf", "size": 4e9},
                {"type": "file", "path": "M-IQ2_XS-00001-of-00003.gguf", "size": 1e9},
                {"type": "file", "path": "mmproj-M-F16.gguf", "size": 1e9},
                {"type": "file", "path": "README.md", "size": 10}]
        with patch.object(ui, "MODELS", self.state), patch.object(ui, "hugging_face", return_value=tree) as fetch:
            files = ui.repo_files("owner/M-GGUF")
            for invalid in ("../etc", "owner/../x", "https://evil.example/x", None):
                with self.assertRaises(ValueError):
                    ui.repo_files(invalid)
        fetch.assert_called_once_with("/api/models/owner/M-GGUF/tree/main?recursive=true")
        self.assertEqual([(f["quant"], f["size"], f["fit"]) for f in files], [("Q4_K_M", 4e9, "fits"), ("Q8_0", 17e9, "too_large")])
        self.assertEqual(files[1]["paths"], ["Q8_0/M-Q8_0-00001-of-00002.gguf", "Q8_0/M-Q8_0-00002-of-00002.gguf"])

    def test_download_fetches_only_listed_files_into_models_without_touching_gpu(self):
        models = self.state / "models"
        entry = {"file": "a/M-Q4_0-00001-of-00002.gguf", "name": "M-Q4_0", "quant": "Q4_0", "size": 7, "downloaded": False,
                 "paths": ["a/M-Q4_0-00001-of-00002.gguf", "a/M-Q4_0-00002-of-00002.gguf"], "sizes": [4, 3]}
        bodies = iter([b"abcd", b"efg"])
        class Response:
            status = 200
            def __init__(self): self.data = [next(bodies), b""]
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a): return self.data.pop(0)
        panel = ui.Panel()
        with patch.object(ui, "MODELS", models), patch.object(ui, "repo_files", return_value=[entry]), patch.object(
                ui, "urlopen", side_effect=lambda *a, **k: Response()) as fetch, patch.object(ui, "systemctl") as ctl, patch.object(
                ui.threading, "Thread", side_effect=lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})()):
            with self.assertRaisesRegex(ValueError, "no longer listed"):
                panel.start_download({"repo": "owner/m", "file": "../../outside.gguf"})
            fetch.assert_not_called()
            panel.start_download({"repo": "owner/m", "file": entry["file"]})
            ctl.assert_not_called()
        self.assertEqual(panel.download["state"], "done")
        self.assertEqual([c.args[0].full_url for c in fetch.call_args_list],
                         ["https://huggingface.co/owner/m/resolve/main/a/M-Q4_0-00001-of-00002.gguf",
                          "https://huggingface.co/owner/m/resolve/main/a/M-Q4_0-00002-of-00002.gguf"])
        self.assertEqual((models / "M-Q4_0-00001-of-00002.gguf").read_bytes(), b"abcd")
        self.assertEqual((models / "M-Q4_0-00002-of-00002.gguf").read_bytes(), b"efg")
        self.assertEqual(list((models / ".partial").iterdir()), [])

    def test_interrupted_download_keeps_progress_and_resumes_with_range(self):
        models = self.state / "models"
        (models / ".partial").mkdir(parents=True)
        (models / ".partial/M-Q4_0.gguf.part").write_bytes(b"ab")
        entry = {"file": "M-Q4_0.gguf", "name": "M-Q4_0", "quant": "Q4_0", "size": 5, "downloaded": False,
                 "paths": ["M-Q4_0.gguf"], "sizes": [5]}
        class Response:
            status = 206
            def __init__(self): self.data = [b"cde", b""]
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a): return self.data.pop(0)
        panel = ui.Panel()
        with patch.object(ui, "MODELS", models), patch.object(ui, "repo_files", return_value=[entry]), patch.object(
                ui, "urlopen", return_value=Response()) as fetch, patch.object(
                ui.threading, "Thread", side_effect=lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})()):
            panel.start_download({"repo": "owner/m", "file": "M-Q4_0.gguf"})
        self.assertEqual(fetch.call_args.args[0].get_header("Range"), "bytes=2-")
        self.assertEqual((models / "M-Q4_0.gguf").read_bytes(), b"abcde")

    def test_cancelled_download_removes_partial_files(self):
        models = self.state / "models"
        entry = {"file": "M.gguf", "name": "M", "quant": "", "size": 8, "downloaded": False, "paths": ["M.gguf"], "sizes": [8]}
        panel = ui.Panel()
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a):
                panel.download_cancel.set()
                return b"abcd"
        with patch.object(ui, "MODELS", models), patch.object(ui, "repo_files", return_value=[entry]), patch.object(
                ui, "urlopen", return_value=Response()), patch.object(
                ui.threading, "Thread", side_effect=lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})()):
            panel.start_download({"repo": "owner/m", "file": "M.gguf"})
        self.assertEqual(panel.download["state"], "cancelled")
        self.assertFalse((models / "M.gguf").exists())
        self.assertEqual(list((models / ".partial").iterdir()), [])

    def test_cloud_provider_resolves_private_key_and_local_never_enters_team(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-private-key"}):
            cfg = w.DEFAULTS | {"cloud_model": "vendor/test-model"}
            w.write_json(w.STATE / "config.json", cfg)
            providers = w.provider_config(cfg)
            self.assertEqual(providers["providers"]["workbench-cloud"]["openai"]["api_key"], "test-private-key")
            repo = self.state / "repo"
            repo.mkdir()
            data = {"id": "personal/ui-test", "bank_id": "test"}
            base = w.build_bundles(repo, data)
            from omnigent.spec.parser import parse
            from omnigent.spec.validator import validate
            self.assertTrue(validate(parse(base / "cloud", expand_env=False)).valid)
            self.assertTrue(validate(parse(base / "coordinator", expand_env=False)).valid)
            self.assertTrue((base / "coordinator/agents/cloud").exists())
            self.assertFalse((base / "coordinator/agents/local").exists())

    def test_new_job_has_bounded_redacted_title_without_launching_a_worker(self):
        panel = ui.Panel()
        prompt = "Fix test-private-key " + "x" * 200 + "\nFull task body"
        with patch.object(w, "project", return_value=(self.state, {})), patch.object(
            w, "environment", return_value={"API_KEY": "test-private-key"}
        ), patch.object(ui.threading, "Thread") as worker:
            result = panel.start_job({"role": "codex", "project": str(self.state), "prompt": prompt})
        job = panel.jobs[result["id"]]
        self.assertEqual(len(job["title"]), 120)
        self.assertIn("[hidden]", job["title"])
        self.assertNotIn("test-private-key", job["title"])
        self.assertNotIn("Full task body", job["title"])
        panel._update_job(job, state="done")
        saved = w.read_json(w.STATE / "desktop-jobs" / (job["id"] + ".json"))
        self.assertEqual(saved["title"], job["title"])
        worker.assert_called_once()

    def test_model_and_effort_reach_worker_and_generated_executor(self):
        panel = ui.Panel()
        with patch.object(w, "project", return_value=(self.state, {})), patch.object(ui.threading, "Thread") as worker:
            result = panel.start_job({"role": "codex", "project": str(self.state), "prompt": "Check", "model": "test-model", "effort": "high"})
        args = worker.call_args.kwargs["args"][1]
        self.assertEqual(args[-4:], ["--model", "test-model", "--effort", "high"])
        self.assertEqual(panel.jobs[result["id"]]["requested_effort"], "high")
        from omnigent.spec.parser import parse
        from omnigent.spec.validator import validate
        base = w.build_bundles(self.state, {"id": "personal/selection", "bank_id": "test"}, "test-model", "high", "codex")
        spec = parse(base / "codex", expand_env=False)
        self.assertTrue(validate(spec).valid)
        self.assertEqual(spec.executor.model, "test-model")
        self.assertEqual(spec.executor.reasoning_effort, "high")
        self.assertIsNone(parse(base / "claude", expand_env=False).executor.reasoning_effort)

    def test_local_selection_is_validated_and_never_starts_gpu(self):
        panel = ui.Panel()
        with patch.object(w, "local_running", return_value=False), patch.object(ui, "local_models", return_value=[{"id": "/models/test.gguf"}]), patch.object(ui, "systemctl") as ctl:
            with self.assertRaises(ValueError):
                panel.select_local({"model": "/other/file.gguf"})
            panel.select_local({"model": "/models/test.gguf"})
            self.assertEqual(w.config()["local_model_file"], "/models/test.gguf")
            ctl.assert_not_called()
        with patch.object(w, "local_running", return_value=True):
            with self.assertRaisesRegex(ValueError, "Stop"):
                panel.select_local({"model": "/models/test.gguf"})

    def test_stop_forces_gpu_release_without_start_or_enable(self):
        with patch.object(ui, "systemctl") as call:
            ui.local_control("stop")
        calls = [args.args for args in call.call_args_list]
        self.assertIn(("kill", "--signal=SIGKILL", "workbench-model.service"), calls)
        self.assertTrue(all("start" not in args and "enable" not in args for args in calls))

    def test_secrets_and_request_boundary_over_real_http(self):
        panel = ui.Panel()
        server = ui.make_server(0, panel)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        with patch.object(w, "local_running", return_value=False), patch.object(ui, "systemctl") as ctl:
            html = urlopen(base).read().decode()
            token = re.search("const token='([^']+)'", html).group(1)
            body = json.dumps({"provider": "openrouter", "key": "secret-test-123", "model": "vendor/model"}).encode()
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + "/api/provider", data=body, headers={"Content-Type": "application/json"}))
            self.assertEqual(error.exception.code, 403)
            result = urlopen(Request(base + "/api/provider", data=body, headers={"Content-Type": "application/json", "X-Harness-Token": token})).read()
            self.assertNotIn(b"secret-test", result)
            state = urlopen(base + "/api/status").read()
            self.assertNotIn(b"secret-test", state)
            self.assertEqual(json.loads(state)["local"], "off")
            self.assertEqual((w.STATE / "secrets.json").stat().st_mode & 0o777, 0o600)
            ctl.assert_not_called()
            with self.assertRaises(HTTPError):
                urlopen(Request(base + "/api/local", data=b'{"action":"start"}', headers={"X-Harness-Token": token, "Origin": "https://evil.example"}))
            ctl.assert_not_called()

    def test_off_local_launch_is_rejected_before_any_subprocess_launch(self):
        with patch.object(w, "project", return_value=(Path('/tmp'), {})), patch.object(w, "local_running", return_value=False), patch.object(w.subprocess, "call") as launch:
            with self.assertRaisesRegex(ValueError, "Local model is off"):
                w.launch(type("Args", (), {"project": "/tmp", "role": "local"})())
            launch.assert_not_called()

    def test_unavailable_local_and_hosted_tasks_explain_what_to_do_first(self):
        panel = ui.Panel()
        with patch.object(w, "project", return_value=(self.state, {})), patch.object(
            w, "local_running", return_value=False
        ), patch.object(w, "cloud_ready", return_value=False), patch.object(ui.threading, "Thread") as worker:
            with self.assertRaises(ValueError) as local:
                panel.start_job({"role": "local", "project": str(self.state), "prompt": "Hello"})
            with self.assertRaises(ValueError) as hosted:
                panel.start_job({"role": "cloud", "project": str(self.state), "prompt": "Hello"})
            worker.assert_not_called()
        self.assertEqual(str(local.exception), "The local model is off. Start it in System first.")
        self.assertEqual(str(hosted.exception), "Connect a hosted model in Connections first.")

    def test_stop_reconciles_native_turn_start_before_reporting_stopped(self):
        panel = ui.Panel()
        job = {"id": "test", "state": "running", "url": "http://127.0.0.1:6767/c/" + "a" * 32}
        panel.jobs["test"] = job
        replies = iter([{}, {"status": "idle"}, {}, {"status": "running", "active_response_id": "turn"}, {}, {"status": "idle"}])
        with patch.object(w, "http_json", side_effect=lambda *a, **k: next(replies)) as http, patch.object(ui.time, "monotonic", side_effect=[0, 0, 0, 1, 4, 4]), patch.object(ui.time, "sleep"):
            panel.stop_job("test")
        self.assertEqual(job["state"], "stopped")
        self.assertEqual(http.call_count, 6)

    def test_persisted_reply_recovers_missing_cli_text_without_reading_tool_output(self):
        items = {"data": [{"type": "function_call_output", "output": "untrusted tool text"},
                          {"type": "message", "role": "assistant", "status": "completed",
                           "content": [{"type": "output_text", "text": "Complete final answer"}]}]}
        with patch.object(w, "http_json", return_value=items):
            self.assertEqual(ui.session_answer("http://127.0.0.1:6767/c/" + "a" * 32), "Complete final answer")
        with patch.object(w, "http_json") as call:
            self.assertEqual(ui.session_answer("https://external.example/c/" + "a" * 32), "")
            call.assert_not_called()

    def test_vscode_open_starts_only_control_panel(self):
        with patch.object(w.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()) as run, patch.object(w.subprocess, "Popen") as browser:
            w.open_panel(type("Args", (), {"project": None, "no_browser": True})())
        self.assertEqual(run.call_args.args[0], ["systemctl", "--user", "start", "workbench-ui.service"])
        browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
