"""Shared launcher core: reviewer identity, requested/observed settings, progress fields, freshness."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "subagents" / "scripts"
spec = importlib.util.spec_from_file_location("review_core_claude", SCRIPTS / "claude_cross_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
core = review.core

PAYLOAD = {"verdict": "clean", "coverage": [{"subject": subject, "status": "covered", "evidence": "Supplied plan"} for subject in ("plan.md", "R1")],
           "findings": [], "limitations": []}


def write_manifest(root, **overrides):
    (root / "plan.md").write_text("Plan evidence.\n", encoding="utf-8")
    manifest = {"repository": str(root), "phase": "plan", "run_id": "core", "selected_paths": ["plan.md"],
                "requirements": ["R1"], "verification_evidence": ["Planning only"], **overrides}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def run_main(argv):
    with mock.patch.object(sys, "argv", ["review", *argv]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return review.main()


class ProgressFieldTests(unittest.TestCase):
    def test_reviewer_fields_are_written_and_claude_names_still_mirrored(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = review.ReviewLog(Path(temporary), False)
            log.event("claude_started", reviewer_pid=123, reviewer_running=True)
            progress = json.loads((Path(temporary) / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual((progress["reviewer_pid"], progress["reviewer_running"]), (123, True))
            self.assertEqual((progress["claude_pid"], progress["claude_running"]), (123, True))
            log.output("", "", reviewer_running=False, reviewer_exit_code=7)
            progress = json.loads((Path(temporary) / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual((progress["reviewer_exit_code_hex"], progress["claude_exit_code_hex"]), ("0x00000007", "0x00000007"))

    def test_core_log_has_only_reviewer_fields_and_reads_either_spelling(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = core.ReviewLog(Path(temporary), False)
            log.event("reviewer_started", reviewer_pid=5, reviewer_running=True)
            progress = json.loads((Path(temporary) / "progress.json").read_text(encoding="utf-8"))
            self.assertFalse([key for key in progress if key.startswith("claude_")])
            self.assertEqual(core.progress_value(progress, "running"), True)
            self.assertEqual(core.progress_value({"claude_running": False}, "running"), False)
            self.assertEqual(core.progress_value({}, "pid", "none"), "none")


class ReportIdentityTests(unittest.TestCase):
    def review_report(self, root, usage=None):
        manifest = write_manifest(root)
        envelope = {"is_error": False, "subtype": "success", "structured_output": PAYLOAD}
        if usage is not None:
            envelope["modelUsage"] = usage
        process = mock.Mock(returncode=0)
        process.communicate.return_value = (json.dumps(envelope), "")
        runtime = {"requested_model": "sonnet", "executable": "/fixture/claude", "version": "2.1.0 (Claude Code)"}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(review, "resolve_claude", return_value=Path("claude")))
            stack.enter_context(mock.patch.object(review, "preflight", return_value=runtime))
            stack.enter_context(mock.patch.object(review.core, "start_review_process", return_value=process))
            stack.enter_context(mock.patch.object(review.core, "close_review_job"))
            code = run_main(["--manifest", str(manifest), "--output-dir", str(root / "reports"), "--effort", "high", "--model", "sonnet"])
        self.assertEqual(code, 0)
        directory = root / "reports" / "core" / "plan-1"
        return json.loads((directory / "report.json").read_text(encoding="utf-8")), (directory / "summary.md").read_text(encoding="utf-8"), directory

    def test_completed_claude_report_identifies_reviewer_and_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            report, summary, directory = self.review_report(Path(temporary), usage={"claude-sonnet-fixture": {"inputTokens": 1}})
            self.assertEqual(report["reviewer"], {"provider": "claude", "execution": "external", "host": "codex",
                                                  "executable": "/fixture/claude", "version": "2.1.0 (Claude Code)"})
            self.assertEqual(report["settings"], {"requested": {"model": "sonnet", "effort": "high"},
                                                  "observed": {"model": "claude-sonnet-fixture", "effort": "unknown"}})
            self.assertEqual(report["observed_settings"]["model_usage"], {"claude-sonnet-fixture": {"inputTokens": 1}})
            self.assertNotIn("effort", report["observed_settings"])
            self.assertNotIn("usage", json.dumps(report["settings"]))
            for line in ("# Claude cross-review: plan", "Reviewer: claude (external, host codex)",
                         "Requested: model sonnet, reasoning effort high", "Observed: model claude-sonnet-fixture, reasoning effort unknown"):
                self.assertIn(line, summary)
            metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual((metadata["reviewer"], metadata["settings"]), (report["reviewer"], report["settings"]))
            self.assertEqual((report["process"]["claude_exit_code"], report["process"]["reviewer_exit_code"]), (0, 0))

    def test_unreported_observed_values_read_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            report, summary, _ = self.review_report(Path(temporary))
            self.assertEqual(report["settings"]["observed"], {"model": "unknown", "effort": "unknown"})
            self.assertIn("Observed: model unknown, reasoning effort unknown", summary)

    def test_prepared_report_has_reviewer_identity_without_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = write_manifest(root)
            with mock.patch.object(review, "resolve_claude", side_effect=AssertionError("prepare resolved Claude")):
                self.assertEqual(run_main(["--manifest", str(manifest), "--output-dir", str(root / "reports"), "--prepare-only"]), 0)
            report = json.loads((root / "reports" / "core" / "plan-1" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["reviewer"], {"provider": "claude", "execution": "external", "host": "codex", "executable": None, "version": None})
            self.assertEqual(report["settings"]["requested"], {"model": "opus", "effort": "unknown"})


class FreshnessTests(unittest.TestCase):
    def check(self, report_path):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = review.check_current(report_path)
        return code, json.loads(output.getvalue())

    def test_check_current_works_for_new_and_pre_identity_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = write_manifest(root)
            self.assertEqual(run_main(["--manifest", str(manifest), "--output-dir", str(root / "reports"), "--prepare-only"]), 0)
            report_path = root / "reports" / "core" / "plan-1" / "report.json"
            code, result = self.check(report_path)
            self.assertEqual((code, result["current"]), (0, True))
            old = json.loads(report_path.read_text(encoding="utf-8"))
            for key in ("reviewer", "settings"):
                old.pop(key)
            legacy = root / "legacy-report.json"
            legacy.write_text(json.dumps(old), encoding="utf-8")
            code, result = self.check(legacy)
            self.assertEqual((code, result["current"]), (0, True))
            (root / "plan.md").write_text("Changed after capture.\n", encoding="utf-8")
            for path in (report_path, legacy):
                code, result = self.check(path)
                self.assertEqual((code, result["current"], result["source_changes"]["status"]), (3, False, "changed"))


class RetiredGuidanceTests(unittest.TestCase):
    def test_manifest_naming_the_retired_reference_blocks_with_the_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retired = root / "references" / "clanker-claude-cross-review.md"
            manifest = write_manifest(root, guidance_paths=[str(retired)])
            self.assertEqual(run_main(["--manifest", str(manifest), "--output-dir", str(root / "reports"), "--prepare-only"]), 2)
            report = json.loads((root / "reports" / "core" / "plan-1" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["execution_status"], "blocked")
            detail = " ".join(report["limitations"])
            self.assertIn(str(retired), detail)
            self.assertIn("references/clanker-cross-review.md", detail)

    def test_other_missing_guidance_has_no_replacement_hint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = write_manifest(root, guidance_paths=[str(root / "missing-role.md")])
            self.assertEqual(run_main(["--manifest", str(manifest), "--output-dir", str(root / "reports"), "--prepare-only"]), 2)
            report = json.loads((root / "reports" / "core" / "plan-1" / "report.json").read_text(encoding="utf-8"))
            self.assertNotIn("replaced", " ".join(report["limitations"]))


if __name__ == "__main__":
    unittest.main()
