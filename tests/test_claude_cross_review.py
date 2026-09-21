import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

MODULE = pathlib.Path(__file__).parents[1] / "subagents" / "scripts" / "claude_cross_review.py"
spec = importlib.util.spec_from_file_location("claude_cross_review", MODULE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ClaudeCrossReviewTests(unittest.TestCase):
    def setUp(self):
        self.close_job = mock.patch.object(review, "close_review_job").start()
        self.addCleanup(mock.patch.stopall)

    def test_snapshot_is_explicit_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            (repository / "included.txt").write_text("known", encoding="utf-8")
            (repository / "secret.token").write_text("hidden", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repository, capture_output=True, check=True)
            snapshot, files, fingerprint = review.collect_snapshot(
                repository, ["included.txt", "secret.token", "deleted.txt"], {"context_paths": []}
            )
            self.addCleanup(lambda: __import__("shutil").rmtree(snapshot, ignore_errors=True))
            self.assertEqual("included", files[0]["state"])
            self.assertEqual("excluded", files[1]["state"])
            self.assertEqual("missing", files[2]["state"])
            self.assertEqual("known", (snapshot / "included.txt").read_text(encoding="utf-8"))
            self.assertEqual(fingerprint, review.current_fingerprint(repository, files))
            (repository / "included.txt").write_text("changed", encoding="utf-8")
            self.assertNotEqual(fingerprint, review.current_fingerprint(repository, files))

    def test_preflight_requires_subscription_and_never_returns_identity(self):
        help_text = " ".join(("--safe-mode", "--restricted", "--tools", "--allowedTools", "--disallowedTools", "--permission-prompts", "--strict-mcp-config", "--mcp-config", "--no-session-persistence", "--output-format", "--json-schema", "--max-turns", "--model", "--effort")) + " (low, medium, high, xhigh, max)"
        responses = [
            subprocess.CompletedProcess([], 0, "2.1.278", ""),
            subprocess.CompletedProcess([], 0, help_text, ""),
            subprocess.CompletedProcess([], 0, json.dumps({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "pro", "email": "private@example.test"}), ""),
        ]
        with mock.patch.object(review, "run_local", side_effect=responses):
            result = review.preflight(pathlib.Path("C:/Claude/claude.exe"), "sonnet", "high")
        self.assertTrue(result["authentication"]["logged_in"])
        self.assertNotIn("email", json.dumps(result))

    def test_model_report_rejects_incomplete_finding(self):
        value = {"verdict": "changes_requested", "coverage": [{"subject": "R1", "status": "covered"}], "findings": [{"id": "F1", "severity": "blocking"}]}
        with self.assertRaises(review.ReviewError):
            review.validate_model_report(value, "implementation")

    def test_check_current_reports_stale_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            source = repository / "file.txt"
            source.write_text("a", encoding="utf-8")
            files = [{"path": "file.txt", "state": "included", "sha256": review.sha256_file(source)}]
            report = repository / "report.json"
            report.write_text(json.dumps({"execution_status": "completed", "source_evidence": {"repository": str(repository), "files": files, "fingerprint": review.evidence_fingerprint(files)}}), encoding="utf-8")
            self.assertEqual(0, review.check_current(report))
            source.write_text("b", encoding="utf-8")
            self.assertEqual(3, review.check_current(report))

    def test_missing_file_becoming_present_is_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            files = [{"path": "later.txt", "state": "missing"}]
            original = review.evidence_fingerprint(files)
            (repository / "later.txt").write_text("now present", encoding="utf-8")
            self.assertNotEqual(original, review.current_fingerprint(repository, files))

    def test_snapshot_excludes_ignored_and_private_key_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            (repository / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            (repository / "ignored.txt").write_text("ignore me", encoding="utf-8")
            (repository / "key.txt").write_text("-----BEGIN PRIVATE KEY-----", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repository, capture_output=True, check=True)
            snapshot, files, _ = review.collect_snapshot(repository, ["ignored.txt", "key.txt"], {"context_paths": []})
            self.addCleanup(lambda: __import__("shutil").rmtree(snapshot, ignore_errors=True))
            self.assertEqual(["excluded", "excluded"], [item["state"] for item in files])

    def test_preflight_blocks_provider_override_without_leaking_value(self):
        help_text = " ".join(("--safe-mode", "--restricted", "--tools", "--allowedTools", "--disallowedTools", "--permission-prompts", "--strict-mcp-config", "--mcp-config", "--no-session-persistence", "--output-format", "--json-schema"))
        responses = [subprocess.CompletedProcess([], 0, "2", ""), subprocess.CompletedProcess([], 0, help_text, "")]
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "do-not-leak"}, clear=True), mock.patch.object(review, "run_local", side_effect=responses):
            with self.assertRaisesRegex(review.ReviewError, "ANTHROPIC_API_KEY") as raised:
                review.preflight(pathlib.Path("C:/Claude/claude.exe"), None, None)
        self.assertNotIn("do-not-leak", str(raised.exception))

    def test_model_report_rejects_spoofed_clean_and_duplicate_findings(self):
        coverage = [{"subject": "R1", "status": "covered", "evidence": "file.py"}]
        blocking = {"id": "F1", "severity": "blocking", "location": "file.py", "scenario": "bad", "evidence": "line 1", "confidence": "confirmed", "suggested_remedy": "fix"}
        with self.assertRaises(review.ReviewError):
            review.validate_model_report({"verdict": "clean", "coverage": coverage, "findings": [blocking]}, "implementation")
        duplicate = dict(blocking)
        duplicate["severity"] = "minor"
        with self.assertRaises(review.ReviewError):
            review.validate_model_report({"verdict": "changes_requested", "coverage": coverage, "findings": [blocking, duplicate]}, "implementation")

    def test_model_report_requires_coverage_evidence_and_consistent_subjects(self):
        with self.assertRaises(review.ReviewError):
            review.validate_model_report({"verdict": "clean", "coverage": [{"subject": "R1", "status": "covered", "evidence": ""}], "findings": []}, "plan")
        with self.assertRaises(review.ReviewError):
            review.validate_model_report({"verdict": "clean", "coverage": [{"subject": "R1", "status": "covered", "evidence": "a"}, {"subject": "R1", "status": "partial", "evidence": "b"}], "findings": []}, "plan")

    def test_cleanup_rejects_unowned_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(review.ReviewError):
                review.cleanup_snapshot(pathlib.Path(temporary))

    def test_validate_manifest_rejects_malformed_optional_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = {"repository": temporary, "phase": "plan", "run_id": "run", "selected_paths": ["file.py"], "context_paths": "not-a-list"}
            with self.assertRaises(review.ReviewError):
                review.validate_manifest(manifest)

    def test_review_model_defaults_to_opus_and_still_blocks_helpers(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = pathlib.Path(temporary)
            (config / "settings.json").write_text(json.dumps({"model": "configured-model"}), encoding="utf-8")
            with mock.patch.dict("os.environ", {"ANTHROPIC_MODEL": "ambient-model"}):
                self.assertEqual("claude-opus-5", review.configured_review_model(None, str(config)))
                self.assertEqual("explicit", review.configured_review_model("explicit", str(config)))
            self.assertEqual(json.loads((config / "settings.json").read_text(encoding="utf-8")), {"model": "configured-model"})
            with self.assertRaises(review.ReviewError):
                review.configured_review_model("", str(config))
            self.assertEqual("explicit", review.configured_review_model("explicit", str(config)))
            (config / "settings.json").write_text(json.dumps({"apiKeyHelper": "private-helper"}), encoding="utf-8")
            with self.assertRaisesRegex(review.ReviewError, "apiKeyHelper") as raised:
                review.configured_review_model(None, str(config))
            self.assertNotIn("private-helper", str(raised.exception))

    def test_invoke_rejects_zero_exit_error_envelope(self):
        envelope = {"is_error": True, "subtype": "success", "terminal_reason": "completed", "structured_output": {"verdict": "clean", "coverage": [{"subject": "R", "status": "covered", "evidence": "x"}], "findings": []}}
        process = mock.Mock(returncode=0)
        process._review_job = None
        process.communicate.return_value = (json.dumps(envelope), "")
        args = types.SimpleNamespace(max_turns=1, model=None, effort=None, timeout_seconds=1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process):
            with self.assertRaisesRegex(review.ReviewError, "envelope"):
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "implementation"}, args)

    def test_invoke_timeout_terminates_owned_process(self):
        process = mock.Mock()
        process._review_job = None
        process.communicate.side_effect = [subprocess.TimeoutExpired([], 1), ("", "")]
        args = types.SimpleNamespace(max_turns=1, model=None, effort=None, timeout_seconds=1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process), mock.patch.object(review, "terminate") as terminate:
            with self.assertRaisesRegex(review.ReviewError, "timed out"):
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)
        terminate.assert_called_once_with(process)

    def test_invoke_interrupt_terminates_owned_process(self):
        process = mock.Mock()
        process._review_job = None
        process.communicate.side_effect = [KeyboardInterrupt(), ("", "")]
        args = types.SimpleNamespace(max_turns=1, model=None, effort=None, timeout_seconds=1)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process), mock.patch.object(review, "terminate") as terminate:
            with self.assertRaises(KeyboardInterrupt):
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)
        terminate.assert_called_once_with(process)

    def test_preflight_blocks_missing_controls_and_unknown_auth(self):
        controls = "--safe-mode"
        responses = [subprocess.CompletedProcess([], 0, "2", ""), subprocess.CompletedProcess([], 0, controls, "")]
        with mock.patch.object(review, "run_local", side_effect=responses):
            with self.assertRaisesRegex(review.ReviewError, "lacks required"):
                review.preflight(pathlib.Path("C:/Claude/claude.exe"), None, None)
        full_help = " ".join(("--safe-mode", "--restricted", "--tools", "--allowedTools", "--disallowedTools", "--permission-prompts", "--strict-mcp-config", "--mcp-config", "--no-session-persistence", "--output-format", "--json-schema"))
        responses = [subprocess.CompletedProcess([], 0, "2", ""), subprocess.CompletedProcess([], 0, full_help, ""), subprocess.CompletedProcess([], 0, "{}", "")]
        with mock.patch.object(review, "run_local", side_effect=responses):
            with self.assertRaisesRegex(review.ReviewError, "login"):
                review.preflight(pathlib.Path("C:/Claude/claude.exe"), None, None)

    def test_executable_resolution_rejects_shim_and_accepts_absolute_native_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            shim = root / "claude.cmd"
            shim.write_text("echo no", encoding="utf-8")
            with self.assertRaises(review.ReviewError):
                review.resolve_claude(str(shim))
            executable = root / "claude.exe"
            executable.write_bytes(b"fixture")
            self.assertEqual(executable.resolve(), review.resolve_claude(str(executable)))

    def test_invoke_rejects_nonzero_and_truncated_output(self):
        args = types.SimpleNamespace(max_turns=1, model=None, effort=None, timeout_seconds=1)
        nonzero = mock.Mock(returncode=9)
        nonzero._review_job = None
        nonzero.communicate.return_value = ("token=private", "")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=nonzero):
            with self.assertRaisesRegex(review.ReviewError, "code 9") as raised:
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)
        self.assertNotIn("private", str(raised.exception))
        oversized = mock.Mock(returncode=0)
        oversized._review_job = None
        oversized.communicate.return_value = ("x" * (review.MAX_OUTPUT_BYTES + 1), "")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=oversized):
            with self.assertRaisesRegex(review.ReviewError, "bounded output"):
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)

    def test_cleanup_failure_is_visible(self):
        snapshot = pathlib.Path(tempfile.mkdtemp(prefix="claude-cross-review-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(snapshot, ignore_errors=True))
        with mock.patch.object(review.shutil, "rmtree", side_effect=OSError("locked")):
            with self.assertRaisesRegex(review.ReviewError, "cleanup failed"):
                review.cleanup_snapshot(snapshot)

    def test_main_uses_runtime_model_and_marks_manifest_change_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = root / "manifest.json"
            manifest = {"repository": str(root), "phase": "implementation", "run_id": "run", "baseline": "base", "selected_paths": ["file.py"], "context_paths": [], "guidance_paths": [], "requirements": ["R1"], "verification_evidence": ["tests unrun"]}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            snapshot = pathlib.Path(tempfile.mkdtemp(prefix="claude-cross-review-"))
            files = [{"path": "file.py", "state": "included", "sha256": "x"}]
            captured = {}
            def invoke_side_effect(_exe, _snapshot, _manifest, args):
                self.assertEqual("configured", args.model)
                manifest_path.write_text(json.dumps({**manifest, "prompt": "changed"}), encoding="utf-8")
                return {"verdict": "clean", "coverage": [{"subject": "file.py", "status": "covered", "evidence": "file.py"}, {"subject": "R1", "status": "covered", "evidence": "R1"}], "findings": [], "limitations": [], "observed_settings": {}}
            def writer(_directory, report):
                captured.update(report)
                return root / "report.json"
            argv = ["runner", "--manifest", str(manifest_path), "--output-dir", str(root / "out"), "--effort", "medium"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "resolve_claude", return_value=pathlib.Path("claude.exe")), mock.patch.object(review, "preflight", return_value={"requested_model": "configured"}), mock.patch.object(review, "collect_snapshot", return_value=(snapshot, files, "fingerprint")), mock.patch.object(review, "current_fingerprint", return_value="fingerprint"), mock.patch.object(review, "invoke", side_effect=invoke_side_effect), mock.patch.object(review, "write_report", side_effect=writer), mock.patch.object(review, "cleanup_snapshot"):
                self.assertEqual(3, review.main())
            self.assertEqual("stale", captured["execution_status"])
            self.assertEqual("incomplete", captured["verdict"])

    def test_main_marks_excluded_scope_and_incomplete_coverage_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = root / "manifest.json"
            manifest = {"repository": str(root), "phase": "implementation", "run_id": "run", "baseline": "base", "selected_paths": ["file.py"], "context_paths": [], "guidance_paths": [], "requirements": ["R1"], "verification_evidence": ["unrun"]}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            snapshot = pathlib.Path(tempfile.mkdtemp(prefix="claude-cross-review-"))
            captured = {}
            result = {"verdict": "clean", "coverage": [{"subject": "file.py", "status": "partial", "evidence": "partial"}], "findings": [], "limitations": [], "observed_settings": {}}
            argv = ["runner", "--manifest", str(manifest_path), "--output-dir", str(root / "out"), "--effort", "medium"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "resolve_claude", return_value=pathlib.Path("claude.exe")), mock.patch.object(review, "preflight", return_value={"requested_model": None}), mock.patch.object(review, "collect_snapshot", return_value=(snapshot, [{"path": "file.py", "state": "excluded", "reason": "binary"}], "fp")), mock.patch.object(review, "current_fingerprint", return_value="fp"), mock.patch.object(review, "invoke", return_value=result), mock.patch.object(review, "write_report", side_effect=lambda _d, report: captured.update(report) or root / "report.json"), mock.patch.object(review, "cleanup_snapshot"):
                self.assertEqual(0, review.main())
            self.assertEqual("completed", captured["execution_status"])
            self.assertEqual("incomplete", captured["verdict"])

    def test_invoke_rejects_denied_read_and_usage_exhaustion_envelopes(self):
        args = types.SimpleNamespace(max_turns=1, model=None, effort=None, timeout_seconds=1)
        for envelope in (
            {"subtype": "success", "terminal_reason": "completed", "permission_denials": ["Read file.py"]},
            {"subtype": "error", "terminal_reason": "usage_limit"},
        ):
            envelope["structured_output"] = {"verdict": "clean", "coverage": [{"subject": "R", "status": "covered", "evidence": "x"}], "findings": []}
            process = mock.Mock(returncode=0)
            process._review_job = None
            process.communicate.return_value = (json.dumps(envelope), "")
            with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process):
                with self.subTest(envelope=envelope):
                    with self.assertRaisesRegex(review.ReviewError, "incomplete or restricted"):
                        review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)

    def test_resolution_uses_native_executable_with_spaces_when_path_is_stale(self):
        with tempfile.TemporaryDirectory(prefix="claude native ") as temporary:
            executable = pathlib.Path(temporary) / "claude.exe"
            executable.write_bytes(b"fixture")
            with mock.patch.object(review.shutil, "which", return_value=None), mock.patch.object(review, "native_candidates", return_value=[executable]):
                self.assertEqual(executable.resolve(), review.resolve_claude(None))


if __name__ == "__main__":
    unittest.main()
