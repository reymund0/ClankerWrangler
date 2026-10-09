import importlib.util
import io
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
        ignored_temp_root = pathlib.Path(__file__).resolve().parents[1] / ".clanker"
        ignored_temp_root.mkdir(parents=True, exist_ok=True)
        previous_tempdir = tempfile.tempdir
        tempfile.tempdir = str(ignored_temp_root)
        self.addCleanup(setattr, tempfile, "tempdir", previous_tempdir)
        self.close_job = mock.patch.object(review, "close_review_job").start()
        self.addCleanup(mock.patch.stopall)

    def test_snapshot_is_explicit_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            (repository / "included.txt").write_text("known", encoding="utf-8")
            (repository / "secret.token").write_text("hidden", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repository, capture_output=True, check=True)
            snapshot, files, fingerprint = review.collect_snapshot(
                repository, ["included.txt", "secret.token", "deleted.txt"],
                {"selected_paths": ["included.txt", "secret.token", "deleted.txt"], "context_paths": []},
            )
            self.addCleanup(lambda: __import__("shutil").rmtree(snapshot, ignore_errors=True))
            self.assertEqual("included", files[0]["state"])
            self.assertEqual("included", files[1]["state"])
            self.assertEqual("missing", files[2]["state"])
            self.assertEqual("known", (snapshot / "included.txt").read_text(encoding="utf-8"))
            self.assertEqual(fingerprint, review.current_fingerprint(repository, files))
            (repository / "included.txt").write_text("changed", encoding="utf-8")
            changes = review.compare_source_changes(repository, files)
            self.assertEqual("changed", changes["status"])
            entry = next(item for item in changes["entries"] if item["path"] == "included.txt")
            self.assertEqual(("changed", "required"), (entry["status"], entry["kind"]))

    def test_preflight_requires_subscription_and_never_returns_identity(self):
        help_text = "--output-format --json-schema --add-dir --model --effort (low, medium, high, xhigh, max)"
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
            files = [{"path": "file.txt", "resolved_path": str(source.resolve()), "state": "included", "kind": "selected", "sha256": review.sha256_file(source)}]
            report = repository / "report.json"
            report.write_text(json.dumps({"schema_version": 2, "execution_status": "completed", "verdict": "clean", "source_changes": {"status": "current", "attribution": "unattributed", "entries": []}, "source_evidence": {"repository": str(repository), "read_scope": {"repository": str(repository), "packet": str(repository / "packet"), "additional_roots": []}, "files": files, "fingerprint": review.evidence_fingerprint(files)}}), encoding="utf-8")
            original_report = report.read_bytes()
            with mock.patch("builtins.print") as emitted:
                self.assertEqual(0, review.check_current(report))
            current = json.loads(emitted.call_args.args[0])
            self.assertTrue(current["current"])
            self.assertTrue(current["eligible_for_parent_review"])
            self.assertEqual("completed", current["execution_status"])
            self.assertEqual(original_report, report.read_bytes())
            source.write_text("b", encoding="utf-8")
            with mock.patch("builtins.print") as emitted:
                self.assertEqual(3, review.check_current(report))
            stale = json.loads(emitted.call_args.args[0])
            self.assertFalse(stale["current"])
            self.assertEqual("completed", stale["execution_status"])
            self.assertEqual(original_report, report.read_bytes())

    def test_missing_file_becoming_present_is_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            path = repository / "later.txt"
            files = [{"path": "later.txt", "state": "missing", "kind": "required", "resolved_path": str(path.resolve())}]
            self.assertEqual("current", review.compare_source_changes(repository, files)["status"])
            path.write_text("now present", encoding="utf-8")
            changes = review.compare_source_changes(repository, files)
            self.assertEqual("changed", changes["status"])
            self.assertEqual([{"path": "later.txt", "status": "changed", "kind": "required", "reason": "previously unavailable source is now present", "resolved_path": str(path.resolve())}], changes["entries"])

    def test_snapshot_includes_ignored_and_credential_like_selected_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            (repository / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            (repository / "ignored.txt").write_text("ignore me", encoding="utf-8")
            (repository / "key.txt").write_text("-----BEGIN PRIVATE KEY-----", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repository, capture_output=True, check=True)
            snapshot, files, _ = review.collect_snapshot(repository, ["ignored.txt", "key.txt"], {"context_paths": []})
            self.addCleanup(lambda: __import__("shutil").rmtree(snapshot, ignore_errors=True))
            self.assertEqual(["included", "included"], [item["state"] for item in files])
            self.assertEqual("ignore me", (snapshot / files[0]["snapshot_path"]).read_text(encoding="utf-8"))
            self.assertEqual("-----BEGIN PRIVATE KEY-----", (snapshot / files[1]["snapshot_path"]).read_text(encoding="utf-8"))

    def test_preflight_blocks_provider_override_without_leaking_value(self):
        help_text = "--output-format --json-schema --add-dir"
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
                self.assertEqual("opus", review.configured_review_model(None, str(config)))
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

    def test_preflight_does_not_require_removed_controls_and_still_checks_auth(self):
        controls = "--output-format --json-schema --model --effort --add-dir"
        responses = [subprocess.CompletedProcess([], 0, "2", ""), subprocess.CompletedProcess([], 0, controls, ""), subprocess.CompletedProcess([], 0, "{}", "")]
        with mock.patch.object(review, "run_local", side_effect=responses):
            with self.assertRaisesRegex(review.ReviewError, "login"):
                review.preflight(pathlib.Path("C:/Claude/claude.exe"), None, None)
        full_help = "--output-format --json-schema --model --effort --add-dir"
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

    def test_main_keeps_captured_verdict_when_manifest_changes_during_review(self):
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
                return {"verdict": "clean", "coverage": [{"subject": "file.py", "status": "covered", "evidence": "file.py"}, {"subject": "R1", "status": "covered", "evidence": "R1"}], "findings": [], "limitations": [], "consulted_paths": ["src/dependency.py"], "observed_settings": {}}
            def writer(_directory, report):
                captured.update(report)
                return root / "report.json"
            argv = ["runner", "--manifest", str(manifest_path), "--output-dir", str(root / "out"), "--effort", "medium"]
            changes = {"status": "changed", "attribution": "unattributed", "entries": [{"path": str(manifest_path), "status": "changed", "kind": "manifest", "reason": "manifest changed"}]}
            with mock.patch.object(sys, "argv", argv), mock.patch.object(review, "reservation_root", return_value=root / "reservations"), mock.patch.object(review, "resolve_claude", return_value=pathlib.Path("claude.exe")), mock.patch.object(review, "preflight", return_value={"requested_model": "configured"}), mock.patch.object(review, "collect_snapshot", return_value=(snapshot, files, "fingerprint")), mock.patch.object(review, "invoke", side_effect=invoke_side_effect), mock.patch.object(review, "compare_source_changes", return_value=changes), mock.patch.object(review, "write_report", side_effect=writer), mock.patch.object(review, "cleanup_snapshot"):
                self.assertEqual(0, review.main())
            self.assertEqual("completed", captured["execution_status"])
            self.assertEqual("clean", captured["verdict"])
            self.assertEqual(2, captured["schema_version"])
            self.assertEqual(changes, captured["source_changes"])
            self.assertEqual(["src/dependency.py"], captured["consulted_paths"])
            self.assertFalse(any(item["path"] == "src/dependency.py" for item in captured["source_changes"]["entries"]))

    def test_manifest_rejects_excluded_required_context_before_preflight(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = root / "manifest.json"
            manifest = {"repository": str(root), "phase": "implementation", "run_id": "run", "baseline": "base", "selected_paths": ["file.py"], "context_paths": ["file.py"], "required_context_paths": ["file.py"], "exclusions": [{"path": "file.py", "reason": "out of review scope"}], "guidance_paths": [], "requirements": ["R1"], "verification_evidence": ["unrun"]}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            snapshot = pathlib.Path(tempfile.mkdtemp(prefix="claude-cross-review-"))
            argv = ["runner", "--manifest", str(manifest_path), "--output-dir", str(root / "out"), "--effort", "medium"]
            error_output = io.StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch.object(sys, "stderr", error_output), mock.patch.object(review, "reservation_root", return_value=root / "reservations"), mock.patch.object(review, "resolve_claude", side_effect=AssertionError("invalid manifest resolved Claude")), mock.patch.object(review, "preflight") as preflight, mock.patch.object(review, "collect_snapshot", side_effect=AssertionError("invalid manifest collected evidence")), mock.patch.object(review, "invoke") as invoke:
                self.assertEqual(2, review.main())
            self.assertIn("Required or mapped evidence is excluded", error_output.getvalue())
            self.assertFalse((root / "out").exists())
            preflight.assert_not_called()
            invoke.assert_not_called()

    def test_invoke_keeps_valid_denied_optional_read_and_rejects_usage_exhaustion(self):
        args = types.SimpleNamespace(max_turns=1, model=None, effort=None, timeout_seconds=1)
        denied = {"is_error": False, "subtype": "success", "terminal_reason": "completed", "permission_denials": ["Read file.py"], "structured_output": {"verdict": "clean", "coverage": [{"subject": "R", "status": "covered", "evidence": "x"}], "findings": []}}
        process = mock.Mock(returncode=0)
        process._review_job = None
        process.communicate.return_value = (json.dumps(denied), "")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process):
            result = review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)
        self.assertTrue(any("denied" in item.lower() for item in result["limitations"]))

        exhausted = {"is_error": True, "subtype": "error", "terminal_reason": "usage_limit", "structured_output": denied["structured_output"]}
        process = mock.Mock(returncode=0)
        process._review_job = None
        process.communicate.return_value = (json.dumps(exhausted), "")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process):
            with self.assertRaises(review.ReviewError):
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)

        spawned = {"is_error": False, "subtype": "success", "terminal_reason": "completed", "subagent_stats": {"spawned": 1}, "structured_output": denied["structured_output"]}
        process = mock.Mock(returncode=0)
        process._review_job = None
        process.communicate.return_value = (json.dumps(spawned), "")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(review, "start_review_process", return_value=process):
            with self.assertRaisesRegex(review.ReviewError, "nested reviewer delegation"):
                review.invoke(pathlib.Path("claude.exe"), pathlib.Path(temporary), {"phase": "plan"}, args)

    def test_main_reports_nested_spawn_as_failed_process_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repository = root / "repo"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repository, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repository, capture_output=True, check=True)
            (repository / "file.py").write_text("value = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "file.py"], cwd=repository, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repository, capture_output=True, check=True)
            baseline = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, capture_output=True, text=True, check=True).stdout.strip()
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({
                "repository": str(repository),
                "phase": "implementation",
                "run_id": "nested-spawn",
                "baseline": baseline,
                "selected_paths": ["file.py"],
                "context_paths": [],
                "guidance_paths": [],
                "requirements": ["R1"],
                "verification_evidence": ["Mocked process envelope only."],
            }), encoding="utf-8")
            envelope = {
                "is_error": False,
                "subtype": "success",
                "terminal_reason": "completed",
                "subagent_stats": {"spawned": 1},
                "structured_output": {"verdict": "clean", "coverage": [], "findings": [], "limitations": []},
            }
            process = mock.Mock(returncode=0)
            process._review_job = None
            process.communicate.return_value = (json.dumps(envelope), "")
            argv = ["runner", "--manifest", str(manifest_path), "--output-dir", str(root / "reports"), "--effort", "medium"]
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch.object(sys, "stdout", stdout), mock.patch.object(sys, "stderr", stderr), mock.patch.object(review, "reservation_root", return_value=root / "reservations"), mock.patch.object(review, "resolve_claude", return_value=pathlib.Path("claude.exe")), mock.patch.object(review, "preflight", return_value={"requested_model": "opus"}), mock.patch.object(review, "start_review_process", return_value=process):
                self.assertEqual(2, review.main())

            summary = json.loads(stdout.getvalue().strip().splitlines()[-1])
            report = json.loads(pathlib.Path(summary["report"]).read_text(encoding="utf-8"))
            self.assertEqual("failed", report["execution_status"])
            self.assertEqual("incomplete", report["verdict"])
            self.assertEqual("process", report["diagnostic"]["category"])
            self.assertIn("nested reviewer delegation", report["diagnostic"]["detail"])
            self.assertEqual(2, summary["launcher_exit_code"])

    def test_resolution_uses_native_executable_with_spaces_when_path_is_stale(self):
        with tempfile.TemporaryDirectory(prefix="claude native ") as temporary:
            executable = pathlib.Path(temporary) / "claude.exe"
            executable.write_bytes(b"fixture")
            with mock.patch.object(review.shutil, "which", return_value=None), mock.patch.object(review, "native_candidates", return_value=[executable]):
                self.assertEqual(executable.resolve(), review.resolve_claude(None))


if __name__ == "__main__":
    unittest.main()
