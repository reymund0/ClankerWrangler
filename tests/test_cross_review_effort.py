"""Explicit effort must survive dispatch and reporting without a silent default."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("review_effort", Path(__file__).parents[1] / "subagents/scripts/claude_cross_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class EffortTests(unittest.TestCase):
    def test_missing_or_blank_effort_stops_before_preflight(self):
        for option in ([], ["--effort", ""], ["--effort", "   "]):
            with self.subTest(option=option), mock.patch.object(sys, "argv", ["review", "--manifest", "unused.json", "--output-dir", "unused", *option]), mock.patch.object(review, "preflight") as preflight, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    review.main()
                self.assertEqual(caught.exception.code, 2)
                preflight.assert_not_called()

    def test_freshness_check_needs_no_effort(self):
        with mock.patch.object(sys, "argv", ["review", "--check-current", "report.json"]), mock.patch.object(review, "check_current", return_value=0) as check:
            self.assertEqual(review.main(), 0)
            check.assert_called_once_with(Path("report.json"))

    def test_selected_effort_reaches_preflight_command_and_saved_report(self):
        for effort in ("low", "medium", "high", "xhigh", "max"):
            with self.subTest(effort=effort), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest = root / "manifest.json"
                manifest.write_text(json.dumps({"repository": str(root), "phase": "plan", "run_id": "effort", "selected_paths": ["plan.md"], "requirements": ["R1"], "verification_evidence": ["Planning only"]}), encoding="utf-8")
                payload = {"verdict": "clean", "coverage": [{"subject": subject, "status": "covered", "evidence": "Supplied plan"} for subject in ("plan.md", "R1")], "findings": [], "limitations": []}
                process = mock.Mock(returncode=0)
                process.communicate.return_value = (json.dumps({"is_error": False, "subtype": "success", "structured_output": payload}), "")
                argv = ["review", "--manifest", str(manifest), "--output-dir", str(root / "reports"), "--effort", effort]
                with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "resolve_claude", return_value=Path("claude")), mock.patch.object(review, "preflight", return_value={"requested_model": None}) as preflight, mock.patch.object(review, "collect_snapshot", return_value=(root / "snapshot", [], "fp")), mock.patch.object(review, "current_fingerprint", return_value="fp"), mock.patch.object(review, "cleanup_snapshot"), mock.patch.object(review, "start_review_process", return_value=process) as launch, mock.patch.object(review, "close_review_job"), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(review.main(), 0)
                self.assertEqual(preflight.call_args.args[2], effort)
                command = launch.call_args.args[0]
                self.assertEqual(command[command.index("--effort") + 1], effort)
                report = json.loads((root / "reports/effort/plan-1/report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["requested_settings"]["effort"], effort)
                self.assertNotIn("effort", report["observed_settings"])

    def test_default_and_override_model_reach_dispatch_and_report(self):
        for extra, expected in (([], "claude-opus-5"), (["--model", "sonnet"], "sonnet")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest = root / "manifest.json"
                manifest.write_text(json.dumps({"repository": str(root), "phase": "plan", "run_id": "model", "selected_paths": ["plan.md"], "requirements": ["R1"], "verification_evidence": ["Planning only"]}), encoding="utf-8")
                payload = {"verdict": "clean", "coverage": [{"subject": subject, "status": "covered", "evidence": "Supplied plan"} for subject in ("plan.md", "R1")], "findings": [], "limitations": []}
                process = mock.Mock(returncode=0)
                process.communicate.return_value = (json.dumps({"is_error": False, "subtype": "success", "structured_output": payload}), "")
                argv = ["review", "--manifest", str(manifest), "--output-dir", str(root / "reports"), "--effort", "medium", *extra]
                with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "resolve_claude", return_value=Path("claude")), mock.patch.object(review, "preflight", side_effect=lambda executable, model, effort: {"requested_model": model}) as preflight, mock.patch.object(review, "collect_snapshot", return_value=(root / "snapshot", [], "fp")), mock.patch.object(review, "current_fingerprint", return_value="fp"), mock.patch.object(review, "cleanup_snapshot"), mock.patch.object(review, "start_review_process", return_value=process) as launch, mock.patch.object(review, "close_review_job"), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(review.main(), 0)
                self.assertEqual(preflight.call_args.args[1], expected)
                command = launch.call_args.args[0]
                self.assertEqual(command[command.index("--model") + 1], expected)
                self.assertEqual(command[command.index("--effort") + 1], "medium")
                self.assertNotIn("--fallback-model", command)
                report = json.loads((root / "reports/model/plan-1/report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["requested_settings"]["model"], expected)
                self.assertIsNone(report["observed_settings"]["model_usage"])

    def test_real_preflight_validates_advertised_effort_without_model_call(self):
        controls = " ".join(("--safe-mode", "--restricted", "--tools", "--allowedTools", "--disallowedTools", "--permission-prompts", "--strict-mcp-config", "--mcp-config", "--no-session-persistence", "--output-format", "--json-schema"))
        help_text = controls + "\n  --effort <level>  Effort level for the session\n      (low, medium, high, xhigh, max)\n  --environment <id> Other option"
        for effort, help_output, accepted in (("medium", help_text, True), ("xhigh", help_text, True), ("unavailable", help_text, False), (" high ", help_text, False), ("high", controls + " --effort", False)):
            with self.subTest(effort=effort, accepted=accepted), mock.patch.dict("os.environ", {name: "ambient-override" for name in review.MODEL_ENVIRONMENT_KEYS}, clear=True), mock.patch.object(review, "configured_review_model", return_value=None), mock.patch.object(review, "run_local", side_effect=[subprocess.CompletedProcess([], 0, "2.1.278", ""), subprocess.CompletedProcess([], 0, help_output, ""), subprocess.CompletedProcess([], 0, json.dumps({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "pro"}), "")]) as local:
                if accepted:
                    result = review.preflight(Path("claude"), None, effort)
                    self.assertEqual(result["requested_effort"], effort)
                else:
                    with self.assertRaisesRegex(review.ReviewError, "unsupported"):
                        review.preflight(Path("claude"), None, effort)
                    self.assertEqual(local.call_count, 2)
                for call in local.call_args_list:
                    self.assertNotIn("-p", call.args[0])

    def test_model_mapping_environment_is_ignored_without_changing_parent(self):
        model_environment = {name: "ambient-override" for name in review.MODEL_ENVIRONMENT_KEYS}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {**model_environment, "CLANKER_FIXTURE_ENV": "preserved"}):
            root = Path(temporary)
            (root / "settings.json").write_text(json.dumps({"env": model_environment}), encoding="utf-8")
            self.assertEqual(review.configured_review_model(None, str(root)), "claude-opus-5")
            for name in model_environment:
                self.assertFalse(review.provider_override(name))
            self.assertTrue(review.provider_override("ANTHROPIC_API_KEY"))
            self.assertTrue(review.provider_override("ANTHROPIC_BASE_URL"))
            code = "import os,json; print(json.dumps({k:v for k,v in os.environ.items() if k.startswith('ANTHROPIC_') or k=='CLANKER_FIXTURE_ENV'}))"
            process = review.start_review_process([sys.executable, "-c", code], root)
            try:
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stderr)
                actual = json.loads(stdout)
                self.assertEqual(actual["CLANKER_FIXTURE_ENV"], "preserved")
                for name in model_environment:
                    self.assertNotIn(name, actual)
                    self.assertEqual(os.environ[name], "ambient-override")
            finally:
                review.terminate(process)

    def test_shared_profiles_are_explicit_fingerprinted_packet_guidance(self):
        repo = Path(__file__).resolve().parents[1]
        profiles = [repo / "subagents" / name for name in ("clanker-architect.md", "clanker-data-engineer.md")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
            (root / "plan.md").write_text("Review the proposed data contract.", encoding="utf-8")
            manifest = {"phase": "plan", "guidance_paths": [str(p) for p in profiles]}
            snapshot, files, fingerprint = review.collect_snapshot(root, ["plan.md"], manifest)
            try:
                self.assertEqual(review.current_fingerprint(root, files), fingerprint)
                guidance = [item for item in files if item["state"] == "guidance"]
                self.assertEqual([item["path"] for item in guidance], [str(p) for p in profiles])
                for source, entry in zip(profiles, guidance):
                    self.assertEqual((snapshot / entry["snapshot_path"]).read_bytes(), source.read_bytes())
                    self.assertEqual(entry["sha256"], review.sha256_file(source))
            finally:
                review.cleanup_snapshot(snapshot)
            with self.assertRaises(review.ReviewError):
                review.collect_snapshot(root, ["plan.md"], {"guidance_paths": [str(root / "missing-role.md")]})

    def test_unsupported_effort_preflight_has_no_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"repository": str(root), "phase": "plan", "run_id": "effort", "selected_paths": ["plan.md"], "requirements": ["R1"], "verification_evidence": ["Planning only"]}), encoding="utf-8")
            argv = ["review", "--manifest", str(manifest), "--output-dir", str(root / "reports"), "--effort", "unavailable"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "resolve_claude", return_value=Path("claude")), mock.patch.object(review, "preflight", side_effect=review.ReviewError("Requested Claude effort is unsupported by this CLI")) as preflight, mock.patch.object(review, "invoke") as invoke, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(review.main(), 2)
            preflight.assert_called_once()
            invoke.assert_not_called()
            report = json.loads((root / "reports/effort/plan-1/report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["requested_settings"]["effort"], "unavailable")
            self.assertEqual(report["execution_status"], "blocked")


if __name__ == "__main__":
    unittest.main()
