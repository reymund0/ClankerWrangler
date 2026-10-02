"""CLI-level regression coverage for local cross-review preparation and readiness."""
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


SOURCE = Path(__file__).resolve().parents[1] / "subagents/scripts/claude_cross_review.py"
spec = importlib.util.spec_from_file_location("cross_review_readiness_target", SOURCE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clanker-readiness-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.repo / "app.py").write_text("value = 'base'\n", encoding="utf-8")
        (self.repo / "deleted.txt").write_text("reviewable deleted content\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.output = self.root / "reports"
        self.reservations = self.root / "reservations"

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout

    def manifest(self, **overrides):
        value = {
            "repository": str(self.repo),
            "phase": "implementation",
            "run_id": "readiness",
            "baseline": self.base,
            "selected_paths": ["app.py"],
            "context_paths": [],
            "guidance_paths": [],
            "requirements": ["R1"],
            "verification_evidence": ["Tests were not run by this reviewer."],
        }
        value.update(overrides)
        return value

    def invoke_main(self, manifest, *options, patches=()):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        argv = ["claude_cross_review.py", "--manifest", str(manifest_path), "--output-dir", str(self.output), *options]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, "argv", argv))
            stack.enter_context(mock.patch.object(review, "reservation_root", return_value=self.reservations))
            for patcher in patches:
                stack.enter_context(patcher)
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            code = review.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def emitted_report(self, output):
        result = json.loads(output.strip().splitlines()[-1])
        return result, json.loads(Path(result["report"]).read_text(encoding="utf-8"))

    @staticmethod
    def clean_static_review(_executable, _snapshot, _manifest, _args):
        return {
            "verdict": "clean",
            "coverage": [
                {"subject": "app.py", "status": "covered", "evidence": "app.py"},
                {"subject": "R1", "status": "covered", "evidence": "app.py"},
            ],
            "findings": [],
            "limitations": [],
            "observed_settings": {},
        }

    def test_prepare_only_accepts_legacy_manifest_and_is_never_review_eligible(self):
        no_claude = [
            mock.patch.object(review, "resolve_claude", side_effect=AssertionError("prepare resolved Claude")),
            mock.patch.object(review, "preflight", side_effect=AssertionError("prepare ran preflight")),
            mock.patch.object(review, "invoke", side_effect=AssertionError("prepare invoked a model")),
        ]
        first_code, first_stdout, _ = self.invoke_main(self.manifest(), "--prepare-only", patches=no_claude)
        second_code, second_stdout, _ = self.invoke_main(self.manifest(), "--prepare-only", patches=no_claude)
        self.assertEqual((0, 0), (first_code, second_code))
        first_result, first = self.emitted_report(first_stdout)
        second_result, second = self.emitted_report(second_stdout)
        self.assertNotEqual(first_result["report"], second_result["report"])
        self.assertEqual("prepared", first["execution_status"])
        self.assertEqual("incomplete", first["verdict"])
        self.assertEqual("ready", first["readiness"]["status"])
        self.assertIn("counts", first["readiness"])
        self.assertIn("warnings", first["readiness"])
        self.assertFalse(first.get("runtime"))
        self.assertIsNone(first.get("diagnostic"))
        self.assertEqual("prepared", second["execution_status"])
        self.assertFalse(list(self.reservations.glob("*")) if self.reservations.exists() else [])

        freshness = io.StringIO()
        with contextlib.redirect_stdout(freshness):
            self.assertEqual(0, review.check_current(Path(first_result["report"])))
        self.assertFalse(json.loads(freshness.getvalue())["eligible_for_parent_review"])
        (self.repo / "app.py").write_text("value = 'changed after preparation'\n", encoding="utf-8")
        stale = io.StringIO()
        with contextlib.redirect_stdout(stale):
            self.assertEqual(3, review.check_current(Path(first_result["report"])))
        self.assertFalse(json.loads(stale.getvalue())["current"])

    def test_readiness_packet_byte_count_matches_snapshot_with_guidance_and_metadata(self):
        guidance = self.root / "review-guidance.md"
        guidance.write_text("Check compatibility and keep parent acceptance separate.\n", encoding="utf-8")
        captured = {}
        cleanup = review.cleanup_snapshot

        def capture_snapshot_bytes(snapshot):
            packet_files = [path for path in snapshot.rglob("*") if path.is_file()]
            captured["snapshot"] = snapshot
            captured["bytes"] = sum(path.stat().st_size for path in packet_files)
            captured["paths"] = {path.relative_to(snapshot).as_posix() for path in packet_files}
            cleanup(snapshot)

        code, stdout, _ = self.invoke_main(
            self.manifest(guidance_paths=[str(guidance)]),
            "--prepare-only",
            patches=[
                mock.patch.object(review, "resolve_claude", side_effect=AssertionError("prepare resolved Claude")),
                mock.patch.object(review, "preflight", side_effect=AssertionError("prepare ran preflight")),
                mock.patch.object(review, "invoke", side_effect=AssertionError("prepare invoked Claude")),
                mock.patch.object(review, "cleanup_snapshot", side_effect=capture_snapshot_bytes),
            ],
        )
        self.assertEqual(0, code)
        _, report = self.emitted_report(stdout)
        counts = report["readiness"]["counts"]
        self.assertEqual(1, counts["guidance"])
        self.assertEqual(captured["bytes"], counts["packet_bytes"])
        self.assertIn("_clanker_packet/evidence.json", captured["paths"])
        self.assertTrue(any(path.startswith("_clanker_packet/guidance/") for path in captured["paths"]))
        self.assertFalse(captured["snapshot"].exists())

    def test_static_mapping_and_parent_checks_are_reported_separately(self):
        browser_check = {
            "subject": "Rendered settings page at 1440x900",
            "owner": "parent",
            "status": "pending",
            "evidence": "Browser acceptance remains with the coordinator.",
        }
        manifest = self.manifest(requirement_paths={"R1": ["app.py"]}, parent_checks=[browser_check])
        seen = {}
        def inspect_manifest(executable, snapshot, passed_manifest, args):
            seen.update(passed_manifest)
            self.assertEqual(["app.py", "R1"], review.required_subjects(passed_manifest))
            return self.clean_static_review(executable, snapshot, passed_manifest, args)

        code, stdout, _ = self.invoke_main(
            manifest,
            "--effort", "medium",
            patches=[
                mock.patch.object(review, "resolve_claude", return_value=Path("claude")),
                mock.patch.object(review, "preflight", return_value={"requested_model": "opus"}),
                mock.patch.object(review, "invoke", side_effect=inspect_manifest),
            ],
        )
        self.assertEqual(0, code)
        result, report = self.emitted_report(stdout)
        self.assertEqual("completed", report["execution_status"])
        self.assertEqual("clean", report["verdict"])
        self.assertEqual([browser_check], report["parent_checks"])
        self.assertEqual([browser_check], report["source_evidence"]["parent_checks"])
        self.assertEqual({"R1": ["app.py"]}, report["source_evidence"]["requirement_paths"])
        self.assertNotIn(browser_check["subject"], [item["subject"] for item in report["coverage"]])
        self.assertEqual("pending", seen["parent_checks"][0]["status"])
        self.assertEqual("parent", seen["parent_checks"][0]["owner"])

    def test_invalid_requirement_mappings_stop_before_claude(self):
        cases = {
            "unknown requirement": (self.manifest(), {"R2": ["app.py"]}),
            "unmapped requirement": (self.manifest(requirements=["R1", "R2"]), {"R1": ["app.py"]}),
            "path outside selected evidence": (self.manifest(), {"R1": ["other.txt"]}),
            "empty evidence list": (self.manifest(), {"R1": []}),
        }
        for name, (manifest, mapping) in cases.items():
            with self.subTest(name=name):
                code, stdout, stderr = self.invoke_main(
                    {**manifest, "requirement_paths": mapping},
                    "--effort", "medium",
                    patches=[
                        mock.patch.object(review, "resolve_claude", side_effect=AssertionError("invalid map resolved Claude")),
                        mock.patch.object(review, "preflight", side_effect=AssertionError("invalid map ran preflight")),
                        mock.patch.object(review, "invoke", side_effect=AssertionError("invalid map launched review")),
                    ],
                )
                self.assertEqual(2, code)
                self.assertNotIn("Traceback", stdout + stderr)

    def test_filtered_and_missing_required_evidence_block_before_preflight(self):
        (self.repo / ".env").write_text("PRIVATE_READINESS_MARKER=never-send-this\n", encoding="utf-8")
        (self.repo / "ignored.txt").write_text("IGNORED_READINESS_MARKER=never-send-this\n", encoding="utf-8")
        manifest = self.manifest(selected_paths=[".env", "ignored.txt", "never-existed.txt"])
        preflight = mock.Mock(side_effect=AssertionError("incomplete evidence reached Claude preflight"))
        invoke = mock.Mock(side_effect=AssertionError("incomplete evidence reached Claude"))
        code, stdout, stderr = self.invoke_main(
            manifest,
            "--effort", "medium",
            patches=[
                mock.patch.object(review, "resolve_claude", side_effect=AssertionError("incomplete evidence resolved Claude")),
                mock.patch.object(review, "preflight", preflight),
                mock.patch.object(review, "invoke", invoke),
            ],
        )
        self.assertEqual(2, code)
        _, report = self.emitted_report(stdout)
        self.assertEqual("blocked", report["execution_status"])
        self.assertEqual("blocked", report["readiness"]["status"])
        self.assertEqual("evidence_preparation", report["diagnostic"]["stage"])
        self.assertIn("coverage", report["diagnostic"]["category"])
        self.assertIn(".env", json.dumps(report["source_evidence"]))
        self.assertIn("never-existed.txt", json.dumps(report["source_evidence"]))
        self.assertNotIn("PRIVATE_READINESS_MARKER", json.dumps(report))
        self.assertNotIn("IGNORED_READINESS_MARKER", json.dumps(report))
        self.assertNotIn("Traceback", stdout + stderr)
        preflight.assert_not_called()
        invoke.assert_not_called()

    def test_deleted_and_renamed_files_remain_preparable_from_scoped_diffs(self):
        self.git("mv", "app.py", "renamed.py")
        (self.repo / "deleted.txt").unlink()
        manifest = self.manifest(selected_paths=["app.py", "renamed.py", "./deleted.txt"])
        code, stdout, _ = self.invoke_main(
            manifest,
            "--prepare-only",
            patches=[
                mock.patch.object(review, "resolve_claude", side_effect=AssertionError("prepare resolved Claude")),
                mock.patch.object(review, "preflight", side_effect=AssertionError("prepare ran preflight")),
                mock.patch.object(review, "invoke", side_effect=AssertionError("prepare invoked Claude")),
            ],
        )
        self.assertEqual(0, code)
        result, report = self.emitted_report(stdout)
        self.assertEqual("prepared", report["execution_status"])
        self.assertEqual("ready", report["readiness"]["status"])
        source_files = report["source_evidence"]["files"]
        self.assertTrue(any(item.get("path") == "./deleted.txt" and item["state"] == "missing" for item in source_files))

    def test_deleted_binary_file_blocks_preparation_before_claude(self):
        binary = self.repo / "ordinary.dat"
        binary.write_bytes(b"PRIVATE_BINARY_MARKER\x00payload")
        self.git("add", "ordinary.dat")
        self.git("commit", "-qm", "add binary fixture")
        binary.unlink()
        code, stdout, _ = self.invoke_main(
            self.manifest(selected_paths=["ordinary.dat"]),
            "--prepare-only",
            patches=[
                mock.patch.object(review, "resolve_claude", side_effect=AssertionError("binary deletion resolved Claude")),
                mock.patch.object(review, "preflight", side_effect=AssertionError("binary deletion ran preflight")),
                mock.patch.object(review, "invoke", side_effect=AssertionError("binary deletion launched Claude")),
            ],
        )
        self.assertEqual(2, code)
        _, report = self.emitted_report(stdout)
        self.assertEqual("blocked", report["execution_status"])
        self.assertEqual("evidence_preparation", report["diagnostic"]["stage"])
        self.assertEqual("evidence", report["diagnostic"]["category"])
        self.assertNotIn("PRIVATE_BINARY_MARKER", json.dumps(report))

    def test_reservation_filesystem_denial_is_reported_before_claude(self):
        reservation_file = self.root / "not-a-directory"
        reservation_file.write_text("block reservation directory creation", encoding="utf-8")
        code, stdout, _ = self.invoke_main(
            self.manifest(),
            "--prepare-only",
            patches=[
                mock.patch.object(review, "reservation_root", return_value=reservation_file),
                mock.patch.object(review, "resolve_claude", side_effect=AssertionError("filesystem failure resolved Claude")),
                mock.patch.object(review, "preflight", side_effect=AssertionError("filesystem failure ran preflight")),
                mock.patch.object(review, "invoke", side_effect=AssertionError("filesystem failure launched Claude")),
            ],
        )
        self.assertEqual(2, code)
        _, report = self.emitted_report(stdout)
        self.assertEqual("blocked", report["execution_status"])
        self.assertEqual("filesystem_preparation", report["diagnostic"]["stage"])
        self.assertEqual("filesystem", report["diagnostic"]["category"])
        self.assertTrue(report["diagnostic"]["action"])

    def test_process_diagnostics_keep_fixed_metadata_and_drop_cli_payload(self):
        cases = (
            ("Permission denied token=PRIVATE_PERMISSION", "permission"),
            ("Invalid API key token=PRIVATE_AUTH", "authentication"),
            ("Usage limit reached password=PRIVATE_USAGE", "usage"),
            ("Model not found api_key=PRIVATE_MODEL", "model"),
            ("Opaque runtime failure credential=PRIVATE_UNKNOWN", "unknown"),
        )
        for message, category in cases:
            with self.subTest(category=category):
                process = mock.Mock(returncode=17)
                process.communicate.return_value = (message, "stderr password=PRIVATE_STDERR")
                code, stdout, _ = self.invoke_main(
                    self.manifest(),
                    "--effort", "medium",
                    patches=[
                        mock.patch.object(review, "resolve_claude", return_value=Path("claude")),
                        mock.patch.object(review, "preflight", return_value={"requested_model": "opus"}),
                        mock.patch.object(review, "start_review_process", return_value=process),
                        mock.patch.object(review, "close_review_job"),
                    ],
                )
                self.assertEqual(2, code)
                _, report = self.emitted_report(stdout)
                self.assertEqual("review_execution", report["diagnostic"]["stage"])
                self.assertEqual(category, report["diagnostic"]["category"])
                self.assertTrue(report["diagnostic"]["action"])
                self.assertEqual(17, report["diagnostic"]["exit_code"])
                serialized = json.dumps(report)
                for marker in ("PRIVATE_PERMISSION", "PRIVATE_AUTH", "PRIVATE_USAGE", "PRIVATE_MODEL", "PRIVATE_UNKNOWN", "PRIVATE_STDERR"):
                    self.assertNotIn(marker, serialized)

    def test_unknown_cli_launch_error_records_type_without_exception_text(self):
        code, stdout, _ = self.invoke_main(
            self.manifest(),
            "--effort", "medium",
            patches=[
                mock.patch.object(review, "resolve_claude", return_value=Path("claude")),
                mock.patch.object(review, "preflight", return_value={"requested_model": "opus"}),
                mock.patch.object(review, "start_review_process", side_effect=OSError("credential=PRIVATE_LAUNCH_ERROR")),
            ],
        )
        self.assertEqual(2, code)
        _, report = self.emitted_report(stdout)
        self.assertEqual("review_execution", report["diagnostic"]["stage"])
        self.assertEqual("unknown", report["diagnostic"]["category"])
        self.assertEqual("OSError", report["diagnostic"]["exception_type"])
        self.assertTrue(report["diagnostic"]["action"])
        self.assertNotIn("PRIVATE_LAUNCH_ERROR", json.dumps(report))

    def test_report_directory_denial_stops_before_claude(self):
        code, stdout, stderr = self.invoke_main(
            self.manifest(),
            "--effort", "medium",
            patches=[
                mock.patch.object(review, "report_directory", side_effect=PermissionError("private report path detail")),
                mock.patch.object(review, "resolve_claude", side_effect=AssertionError("report denial resolved Claude")),
                mock.patch.object(review, "preflight", side_effect=AssertionError("report denial ran preflight")),
                mock.patch.object(review, "invoke", side_effect=AssertionError("report denial launched Claude")),
            ],
        )
        self.assertEqual(2, code)
        self.assertNotIn("private report path detail", stdout + stderr)
        self.assertNotIn("Traceback", stdout + stderr)


if __name__ == "__main__":
    unittest.main()
