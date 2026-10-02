"""Saved preferences -> shared preview/CLI -> bounded Claude invocation arguments."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "routing-editor/scripts"))
import routing_editor as editor
import routing_policy as policy
spec = importlib.util.spec_from_file_location("routing_review_fixture", ROOT / "subagents/scripts/claude_cross_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class RoutingIntegrationTests(unittest.TestCase):
    def test_editor_rejects_removed_project_option_before_startup(self):
        command = [sys.executable, "-B", str(ROOT / "routing-editor/scripts/routing_editor.py")]
        result = subprocess.run(command + ["--project", "unused"], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments: --project", result.stderr)
        self.assertNotIn("Open the local editor:", result.stdout)

    def test_saved_preview_snapshot_cli_and_claude_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            store = editor.PreferenceStore(global_config_dir=root / "global")
            global_doc = {"schema_version": 1, "interactions": {"claude-review": {"model": "claude-opus-5", "reasoning": {"mode": "fixed", "effort": "low"}}}}
            ignored = project / ".clanker" / "orchestration-routing.json"
            ignored.parent.mkdir()
            ignored.write_bytes(b"malformed ignored project preferences")
            store.save("global", global_doc, "missing")
            request = {"interaction": "claude-review", "tier": "involved", "risk_flags": ["security"], "reason": "Review authorization contract", "session_override": {"reasoning": {"mode": "fixed", "effort": "high"}}}
            preview = store.preview("global", global_doc, request)["decision"]
            snapshot_path = root / "run-1.json"
            command = [sys.executable, "-B", str(ROOT / "subagents/scripts/routing_policy.py")]
            created = subprocess.run(command + ["snapshot", "--global", str(store.target("global")[1]), "--output", str(snapshot_path)], capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(json.loads(snapshot_path.read_text())["policy_version"], "4")
            self.assertEqual(ignored.read_bytes(), b"malformed ignored project preferences")
            def resolve():
                result = subprocess.run(command + ["resolve", "--snapshot", str(snapshot_path)], input=json.dumps(request), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            decision = resolve()
            for key in ("model", "effort", "proposed_effort", "tier", "provenance", "capability_status", "launcher_allowed"):
                self.assertEqual(decision[key], preview[key], key)
            self.assertEqual(decision["effort"], "high")
            self.assertTrue(decision["launcher_allowed"])
            self.assertFalse(decision["dispatch_allowed"])
            # Existing run remains byte-for-byte independent of live configuration.
            store.save("global", {"schema_version": 1}, store.read("global")["revision"])
            self.assertEqual(resolve(), decision)
            overwritten = subprocess.run(command + ["snapshot", "--global", str(store.target("global")[1]), "--output", str(snapshot_path)], capture_output=True, text=True)
            self.assertNotEqual(overwritten.returncode, 0)

            subprocess.run(["git", "init", "-q"], cwd=project, check=True, capture_output=True)
            (project / "plan.md").write_text("Bounded fixture plan for routing integration.", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"repository": str(project), "phase": "plan", "run_id": "routing", "selected_paths": ["plan.md"], "requirements": ["R1"], "verification_evidence": ["Deterministic fixture only"]}), encoding="utf-8")
            payload = {"verdict": "clean", "coverage": [{"subject": subject, "status": "covered", "evidence": "Fixture plan read"} for subject in ("plan.md", "R1")], "findings": [], "limitations": []}
            process = mock.Mock(returncode=0)
            process.communicate.return_value = (json.dumps({"is_error": False, "subtype": "success", "structured_output": payload}), "")
            argv = ["review", "--manifest", str(manifest), "--output-dir", str(root / "reports"), "--model", decision["model"], "--effort", decision["effort"]]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "resolve_claude", return_value=Path("claude")), mock.patch.object(review, "preflight", side_effect=lambda executable, model, effort: {"requested_model": model}) as preflight, mock.patch.object(review, "reservation_root", return_value=root / "reservations"), mock.patch.object(review, "start_review_process", return_value=process) as launch, mock.patch.object(review, "close_review_job"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(review.main(), 0)
            self.assertEqual(preflight.call_args.args[1:], (decision["model"], decision["effort"]))
            actual = launch.call_args.args[0]
            self.assertEqual(actual[actual.index("--model") + 1], decision["model"])
            self.assertEqual(actual[actual.index("--effort") + 1], decision["effort"])
            self.assertNotIn("--fallback-model", actual)
            report = json.loads((root / "reports/routing/plan-1/report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["requested_settings"]["model"], decision["model"])
            self.assertEqual(report["requested_settings"]["effort"], decision["effort"])
            self.assertNotIn("effort", report["observed_settings"])

    def test_saved_native_agent_preview_cli_and_frozen_global_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            store = editor.PreferenceStore(global_config_dir=root / "global")
            global_doc = {"schema_version": 1, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra", "reasoning": {"mode": "fixed", "effort": "medium"}}}}
            global_doc["interactions"] = {"implementation": {"specialists": {"clanker-backend-developer": {"model": "gpt-5.6-luna"}}}}
            ignored = project / ".clanker" / "orchestration-routing.json"
            ignored.parent.mkdir()
            ignored.write_bytes(b"malformed ignored project preferences")
            store.save("global", global_doc, "missing")
            request = {"interaction": "implementation", "role": "clanker-backend-developer", "tier": "straightforward", "reason": "Saved global exception", "capabilities": {"provider": "codex", "source": "fixture", "models": {"gpt-5.6-luna": ["medium"]}}}
            reloaded = editor.PreferenceStore(global_config_dir=root / "global")
            baseline = reloaded.configuration()["effective"]["agents"]["clanker-backend-developer"]
            self.assertEqual(baseline["route"], global_doc["agents"]["clanker-backend-developer"])
            self.assertEqual(baseline["provenance"]["model"], "global.agents.clanker-backend-developer.model")
            preview = reloaded.preview("global", global_doc, request)["decision"]
            self.assertEqual((preview["model"], preview["effort"]), ("gpt-5.6-luna", "medium"))
            self.assertEqual(preview["provenance"]["model"], "global.interactions.implementation.specialists.clanker-backend-developer.model")
            snapshot_path = root / "run-native-agent.json"
            command = [sys.executable, "-B", str(ROOT / "subagents/scripts/routing_policy.py")]
            created = subprocess.run(command + ["snapshot", "--global", str(store.target("global")[1]), "--output", str(snapshot_path)], capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(json.loads(snapshot_path.read_text())["policy_version"], "4")
            self.assertEqual(ignored.read_bytes(), b"malformed ignored project preferences")
            resolved = subprocess.run(command + ["resolve", "--snapshot", str(snapshot_path)], input=json.dumps(request), capture_output=True, text=True)
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            cli_decision = json.loads(resolved.stdout)
            for key in ("model", "reasoning", "effort", "proposed_effort", "tier", "provenance", "capability_status", "dispatch_allowed"):
                self.assertEqual(cli_decision[key], preview[key], key)
            store.save("global", {"schema_version": 1}, store.read("global")["revision"])
            frozen = subprocess.run(command + ["resolve", "--snapshot", str(snapshot_path)], input=json.dumps(request), capture_output=True, text=True)
            self.assertEqual(frozen.returncode, 0, frozen.stderr)
            self.assertEqual(json.loads(frozen.stdout), cli_decision)

    def test_native_unavailable_pair_has_no_dispatch_permission(self):
        snapshot = policy.snapshot_from_documents({"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna", "reasoning": {"mode": "fixed", "effort": "max"}}}})
        result = policy.resolve(snapshot, {"interaction": "implementation", "tier": "straightforward", "reason": "Explicit worker selection", "capabilities": {"provider": "codex", "source": "Fixture active tool metadata", "models": {"gpt-5.6-luna": ["medium"]}}})
        self.assertEqual((result["model"], result["effort"]), ("gpt-5.6-luna", "max"))
        self.assertEqual(result["capability_status"], "unsupported")
        self.assertFalse(result["dispatch_allowed"])


if __name__ == "__main__":
    unittest.main()
