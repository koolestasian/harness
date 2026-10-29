import argparse
import asyncio
from contextlib import asynccontextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import workbench as w


class WorkbenchChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.state_patch = patch.object(w, "STATE", self.root / "state")
        self.state_patch.start()

    def tearDown(self):
        self.state_patch.stop()
        self.tmp.cleanup()

    def initialize(self, identifier="personal/test-project"):
        w.init_project(argparse.Namespace(path=str(self.repo), id=identifier))
        return w.read_json(self.repo / ".agent/PROJECT.json")

    def test_project_identity_is_portable_and_never_silently_changed(self):
        first = self.initialize()
        second = self.initialize()
        self.assertEqual(first["bank_id"], second["bank_id"])
        with self.assertRaises(ValueError):
            self.initialize("other/project")
        self.assertNotIn(str(self.repo), json.dumps(first))
        second["bank_id"] = "project-another-bank"
        w.write_json(self.repo / ".agent/PROJECT.json", second)
        with self.assertRaises(ValueError):
            w.project(self.repo)

    def test_generated_specs_pass_real_omnigent_parser_and_validator(self):
        from omnigent.spec.parser import parse
        from omnigent.spec.validator import validate
        data = self.initialize()
        base = w.build_bundles(self.repo, data)
        specs = list(base.rglob("config.yaml"))
        self.assertEqual(len(specs), 7)
        self.assertFalse((base / "coordinator/agents/local").exists())
        for path in specs:
            spec = parse(path.parent, expand_env=False)
            validation = validate(spec)
            self.assertTrue(validation.valid, [(e.path, e.message) for e in validation.errors])
            if path.parent == base / "local":
                self.assertEqual(spec.mcp_servers, [])
            else:
                self.assertEqual(spec.mcp_servers[0].tools, ["recall", "sync_retain", "get_document"])
        local = parse(base / "local", expand_env=False)
        self.assertEqual(local.executor.context_window, 36864)
        self.assertEqual(local.executor.auth.name, "workbench-local")

    def test_local_provider_reaches_pi_chat_endpoint_in_real_spawn_builder(self):
        from omnigent.spec.parser import parse
        from omnigent.runtime.workflow import _build_pi_spawn_env
        data = self.initialize()
        base = w.build_bundles(self.repo, data)
        provider_file = w.STATE / "omnigent/config.yaml"
        self.assertEqual(provider_file.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("$LOCAL_MODEL_API_KEY", provider_file.read_text())
        with patch.dict(os.environ, {"OMNIGENT_CONFIG_HOME": str(w.STATE / "omnigent")}):
            os.environ.pop("LOCAL_MODEL_API_KEY", None)
            spawn = _build_pi_spawn_env(parse(base / "local", expand_env=False), cwd=self.repo)
        self.assertEqual(json.loads(spawn["HARNESS_PI_GATEWAY_BASE_URLS"])["openai"], w.DEFAULTS["local_url"])
        self.assertEqual(spawn["HARNESS_PI_GATEWAY_OPENAI_WIRE_API"], "chat")

    def test_existing_editor_tasks_and_native_instructions_are_preserved(self):
        path = self.repo / ".vscode/tasks.json"
        path.parent.mkdir()
        path.write_text('{"existing": true}')
        (self.repo / "AGENTS.md").write_text("Existing repository instructions")
        self.initialize()
        self.assertEqual(path.read_text(), '{"existing": true}')
        self.assertEqual((self.repo / "AGENTS.md").read_text(), "Existing repository instructions")

    def test_checkpoint_retains_dirty_state_and_rejects_old_revision_or_path_escape(self):
        self.initialize()
        args = argparse.Namespace(project=str(self.repo), task="auth-fix", summary="Investigated",
                                  next="Reproduce", status="active", evidence=["docs/repro.md"],
                                  expected_revision=0)
        w.checkpoint(args)
        record = w.read_json(self.repo / ".agent/tasks/auth-fix.json")
        self.assertEqual(record["revision"], 1)
        self.assertIsNone(record["commit"])
        self.assertTrue(record["working_tree_status"])
        with self.assertRaises(ValueError):
            w.checkpoint(args)
        args.task = "../../escape"
        with self.assertRaises(ValueError):
            w.checkpoint(args)

    def test_secret_storage_and_endpoint_validation(self):
        args = argparse.Namespace(**{k:None for k in w.DEFAULTS}, no_prompt=True)
        with patch.dict(os.environ, {"HINDSIGHT_API_KEY": "test-secret-never-shipped"}):
            w.configure(args)
        path = w.STATE / "secrets.json"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("test-secret", (w.STATE / "config.json").read_text())
        for url in ["http://public.example.com", "https://user:password@example.com", "https://x.example/?token=a"]:
            with self.assertRaises(ValueError):
                w.valid_url(url, local=True)
        self.assertEqual(w.valid_url("http://100.70.80.90:8081/v1", local=True), "http://100.70.80.90:8081/v1")

    def test_packet_keeps_exact_state_and_evidence_and_rejects_oversize_or_escape(self):
        data = self.initialize()
        args = argparse.Namespace(project=str(self.repo), task="auth-fix", summary="Unresolved",
                                  next="Reproduce", status="active", evidence=[], expected_revision=0)
        w.checkpoint(args)
        source = self.repo / "evidence.md"
        source.write_text("Exact command and revision")
        subprocess.run(["git", "-C", str(self.repo), "add", "evidence.md"], check=True)
        packet = w.context_packet(self.repo, data, "auth-fix", ["evidence.md"])
        self.assertEqual(packet["files"][0]["content"], source.read_text())
        self.assertEqual(packet["task"]["revision"], 1)
        self.assertTrue(packet["current_dirty_state"])
        source.write_text("x" * 16001)
        with self.assertRaises(ValueError):
            w.context_packet(self.repo, data, "auth-fix", ["evidence.md"])
        outside = self.root / "outside.md"
        outside.write_text("Do not include")
        (self.repo / "link.md").symlink_to(outside)
        with self.assertRaises(ValueError):
            w.context_packet(self.repo, data, "auth-fix", ["link.md"])

    def test_memory_roundtrip_requires_new_fact_and_correct_source_not_just_success(self):
        class Session:
            wrong = None
            async def list_tools(self):
                return SimpleNamespace(tools=[SimpleNamespace(name=n) for n in ["recall", "sync_retain", "get_document"]])
            async def call_tool(self, name, arguments):
                if name == "sync_retain":
                    self.content = arguments["content"]
                    data = {"status": "completed"}
                elif name == "get_document":
                    data = {"content": self.content if self.wrong != "source-content" else "old fact"}
                else:
                    data = {"results": [{"text": self.content if self.wrong != "stale" else "old fact",
                                         "document_id": "wrong" if self.wrong == "source-id" else "workbench-deployment-check"}]}
                    if self.wrong == "application-error":
                        data = {"error": "bank unavailable", "results": []}
                return SimpleNamespace(isError=False, structuredContent=data, content=[])
        session = Session()
        @asynccontextmanager
        async def connection(*args):
            yield session
        with patch.object(w, "memory_session", connection):
            self.assertTrue(asyncio.run(w.memory_probe("url", "token", "bank", True))["roundtrip_verified"])
            for wrong in ["stale", "source-id", "source-content", "application-error"]:
                session.wrong = wrong
                with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                    asyncio.run(w.memory_probe("url", "token", "bank", True))

    def test_memory_publish_survives_outage_and_retries_the_same_document(self):
        data = self.initialize()
        (self.repo / "finding.md").write_text("Verified fix; evidence: test command, exit 0")
        w.memory_save(argparse.Namespace(project=str(self.repo), file="finding.md", task="auth-fix",
                     kind="verified-finding", source="docs/repro.md"))
        paths = list((self.repo / ".agent/findings").glob("*.json"))
        self.assertEqual(len(paths), 1)
        documents = []
        fail = [True]
        class Session:
            async def call_tool(self, name, arguments):
                documents.append(arguments["document_id"])
                return SimpleNamespace(isError=False, structuredContent={"status": "error" if fail[0] else "completed"}, content=[])
        @asynccontextmanager
        async def connection(*args):
            yield Session()
        with patch.object(w, "memory_session", connection), patch.dict(os.environ, {"HINDSIGHT_API_KEY": "test"}):
            with self.assertRaises(ValueError):
                asyncio.run(w.flush_findings(self.repo, data))
            self.assertTrue(paths[0].exists())
            self.assertEqual(list((w.STATE / "memory-receipts").rglob("*.json")), [])
            fail[0] = False
            asyncio.run(w.flush_findings(self.repo, data))
            asyncio.run(w.flush_findings(self.repo, data))
        self.assertEqual(documents[0], documents[1])
        self.assertEqual(len(documents), 2)

    def test_launch_records_exit_and_requires_review_before_counting_acceptance(self):
        self.initialize()
        args = argparse.Namespace(project=str(self.repo), role="codex", brain="claude", prompt="PRIVATE PROMPT",
                                  task=None, file=None, continue_session=False)
        with patch.dict(os.environ, {"HINDSIGHT_API_KEY": "PRIVATE TOKEN"}), patch.object(w.subprocess, "call", return_value=1):
            self.assertEqual(w.launch(args), 1)
        path = next((w.STATE / "runs").glob("*.json"))
        record = w.read_json(path)
        self.assertEqual(record["exit_code"], 1)
        self.assertIsNone(record["accepted"])
        self.assertNotIn("PRIVATE", path.read_text())
        args = argparse.Namespace(run=record["run_id"], accepted="no", task_type="coding", model="observed-model",
                                  evidence=["tests/repro.log"], input_tokens=None, output_tokens=None, cost_usd=None, corrections=1)
        w.outcome(args)
        with redirect_stdout(io.StringIO()) as stream:
            w.score(argparse.Namespace(project=str(self.repo)))
        summary = json.loads(stream.getvalue())[0]
        self.assertEqual(summary["accepted"], 0)
        self.assertIsNone(summary["cost_per_accepted_usd"])
        record = w.read_json(path)
        record["cost_usd"] = 2
        w.write_json(path, record)
        second = dict(record, run_id="a" * 32, accepted=True, cost_usd=3)
        w.write_json(w.STATE / "runs" / (second["run_id"] + ".json"), second)
        with redirect_stdout(io.StringIO()) as stream:
            w.score(argparse.Namespace(project=str(self.repo)))
        summary = json.loads(stream.getvalue())[0]
        self.assertEqual(summary["cost_per_accepted_usd"], 5)
        self.assertEqual(summary["attempts"], 2)
        args.cost_usd = float("nan")
        with self.assertRaises(ValueError):
            w.outcome(args)


if __name__ == "__main__":
    unittest.main()
