"""Tests for the rewritten cross-review launcher (`cross_review.py`) and its Codex adapter.

Failure modes kept from the old launcher tests (test_cross_review_*.py, test_codex_cross_review.py):

1. Malformed or schema-invalid reviewer output yields `incomplete`, never `clean`, and no findings
   are invented (old: test_malformed_or_missing_output_fails_without_a_clean_verdict).
2. A review that outlives the time limit is stopped with its whole process tree and reported as
   `failed` with a timeout diagnostic (old: test_timeout_terminates_the_owned_process_tree).
3. Model and effort are required, passed explicitly on the reviewer command line, and recorded as
   requested; observed values the CLI does not report read `unknown`
   (old: test_missing_or_blank_model_or_effort_stops_before_preflight,
   test_reported_model_becomes_the_observed_model_and_unreported_effort_stays_unknown).
4. Preflight fails with the missing prerequisite (CLI absent, not logged in) before any review
   call, and never starts a login flow (old: test_not_logged_in_preflight_never_starts_a_login_flow).
5. The reviewer is pointed at the caller's handoff, and a missing or unreadable handoff fails before
   any review call instead of producing a review of nothing
   (old: test_missing_required_evidence_blocks_before_any_codex_call,
   test_invalid_baseline_cannot_be_silent_empty_diff).
6. A reviewer that exits nonzero or never completes its turn (for example a usage limit) is
   `failed` with a diagnostic and is not retried
   (old: test_usage_limit_is_a_failed_attempt_with_a_usage_diagnostic_and_no_retry).
"""

import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "subagents" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cross_review  # noqa: E402
import cross_review_claude  # noqa: E402

FAKE_CODEX = textwrap.dedent('''\
    #!{python}
    import json, os, subprocess, sys, time
    scenario = json.load(open(os.environ["FAKE_CODEX_SCENARIO"]))
    argv = sys.argv[1:]
    with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
        log.write(json.dumps(argv) + "\\n")
    if argv[:2] == ["login", "status"]:
        print(scenario.get("login", "Logged in using ChatGPT"))
        sys.exit(scenario.get("login_exit", 0))
    sys.stdin.read()
    if scenario.get("child_pid_file"):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        open(scenario["child_pid_file"], "w").write(str(child.pid))
    time.sleep(scenario.get("sleep", 0))
    if "last_message" in scenario:
        text = scenario["last_message"]
        open(argv[argv.index("--output-last-message") + 1], "w").write(text if isinstance(text, str) else json.dumps(text))
    for event in scenario.get("events", []):
        print(json.dumps(event))
    sys.stderr.write(scenario.get("stderr", ""))
    sys.exit(scenario.get("exit_code", 0))
''')

FAKE_CLAUDE = textwrap.dedent('''\
    #!{python}
    import json, os, sys
    scenario = json.load(open(os.environ["FAKE_CODEX_SCENARIO"]))
    argv = sys.argv[1:]
    with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
        log.write(json.dumps(argv) + "\\n")
    if argv[:2] == ["auth", "status"]:
        print(json.dumps({{"loggedIn": scenario.get("logged_in", True), "authMethod": "claude.ai"}}))
        sys.exit(0)
    sys.stdin.read()
    envelope = {{"type": "result", "subtype": "success", "is_error": False, "result": "",
                "usage": {{"input_tokens": 50, "output_tokens": 10, "service_tier": "standard"}},
                "modelUsage": {{"claude-opus-test": {{}}}}}}
    envelope.update(scenario.get("envelope", {{}}))
    print(json.dumps(envelope))
    sys.exit(scenario.get("exit_code", 0))
''')

COMPLETED = [{"type": "thread.started", "thread_id": "t1"},
             {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20}}]
CLEAN = {"coverage": "complete", "findings": [], "limitations": []}


def finding(id_="F1", severity="major"):
    return {"id": id_, "severity": severity, "location": "design.md:10", "summary": "Breaks X.", "remedy": "Do Y."}


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class ReviewTestCase(unittest.TestCase):
    provider, fake_cli = "codex", FAKE_CODEX

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "T")
        (self.repo / "design.md").write_text("# Design\n")
        (self.repo / "app.py").write_text("x = 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "base")
        self.cli = self.root / self.provider
        self.cli.write_text(self.fake_cli.format(python=sys.executable))
        self.cli.chmod(0o755)
        self.log = self.root / "calls.jsonl"
        self.scenario_path = self.root / "scenario.json"
        self.out = self.root / "out"
        env = mock.patch.dict(os.environ, {"FAKE_CODEX_LOG": str(self.log), "FAKE_CODEX_SCENARIO": str(self.scenario_path)})
        env.start()
        self.addCleanup(env.stop)

        self.handoff = self.repo / ".clanker" / "handoff.md"
        self.handoff.parent.mkdir()
        self.handoff.write_text("# Review handoff\nGate: plan\nStart from: design.md\n")

    def review(self, scenario, phase="plan", handoff=None, timeout_seconds=60):
        self.scenario_path.write_text(json.dumps(scenario))
        report = cross_review.run_review(self.provider, phase, handoff or self.handoff, self.out, "gpt-test", "high",
                                         self.repo, str(self.cli), timeout_seconds)
        self.assertEqual(json.loads((self.out / "report.json").read_text()), report)
        return report

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def exec_calls(self):
        return [argv for argv in self.calls() if argv[:1] == ["exec"]]


class HandoffTests(ReviewTestCase):
    def test_prompt_points_at_the_handoff_with_schema_and_no_file_contents(self):
        # Failure mode 5.
        (self.repo / "design.md").write_text("SECRET DESIGN CONTENT\n")
        report = self.review({"last_message": CLEAN, "events": COMPLETED}, phase="refactor")
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["handoff"], str(self.handoff))
        prompt = (self.out / "prompt.md").read_text()
        self.assertIn(f"Read the handoff at {self.handoff}", prompt)
        self.assertIn('"enum": [\n', prompt)
        self.assertIn('"proposal"', prompt)
        self.assertNotIn("SECRET DESIGN CONTENT", prompt)
        self.assertNotIn("Gate: plan", prompt)

    def test_unreadable_handoff_fails_before_any_review_call(self):
        # Failure mode 5.
        for handoff in (self.root / "missing.md", self.repo):
            report = self.review({"last_message": CLEAN, "events": COMPLETED}, handoff=handoff)
            self.assertEqual(report["status"], "failed")
            self.assertIn("Handoff is not a readable file", report["diagnostic"])
        self.assertEqual(self.calls(), [])


class ValidationTests(unittest.TestCase):
    def assert_incomplete(self, text, phase="implementation"):
        with self.assertRaises(cross_review.ReviewError) as caught:
            cross_review.validate_output(text, phase)
        self.assertEqual(caught.exception.status, "incomplete")

    def test_invalid_output_is_incomplete(self):
        # Failure mode 1.
        self.assert_incomplete("not json")
        self.assert_incomplete(json.dumps({"findings": []}))
        self.assert_incomplete(json.dumps({**CLEAN, "verdict": "clean"}))
        self.assert_incomplete(json.dumps({**CLEAN, "findings": [finding(), finding()]}))
        self.assert_incomplete(json.dumps({**CLEAN, "findings": [{**finding(), "remedy": ""}]}))
        self.assert_incomplete(json.dumps({**CLEAN, "findings": [finding(severity="critical")]}))
        self.assert_incomplete(json.dumps({**CLEAN, "findings": [finding(severity="major")]}), phase="refactor")
        self.assert_incomplete(json.dumps({**CLEAN, "findings": [finding(severity="proposal")]}), phase="plan")

    def test_status_follows_coverage_and_severity(self):
        status = lambda payload, phase="implementation": cross_review.review_status(
            cross_review.validate_output(json.dumps(payload), phase))
        self.assertEqual(status(CLEAN), "clean")
        self.assertEqual(status({**CLEAN, "findings": [finding(severity="info")]}), "clean")
        self.assertEqual(status({**CLEAN, "findings": [finding(severity="minor")]}), "changes_requested")
        self.assertEqual(status({**CLEAN, "findings": [finding(severity="proposal")]}, "refactor"), "changes_requested")
        self.assertEqual(status({**CLEAN, "coverage": "partial"}), "incomplete")

    def test_schema_is_strict_and_phase_specific(self):
        schema = cross_review.output_schema("refactor")
        item = schema["properties"]["findings"]["items"]
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(item["additionalProperties"])
        self.assertEqual(sorted(item["required"]), sorted(item["properties"]))
        self.assertEqual(item["properties"]["severity"]["enum"], ["proposal"])


class CodexReviewTests(ReviewTestCase):
    def test_plan_review_passes_settings_explicitly_and_reports_usage(self):
        # Failure mode 3.
        report = self.review({"last_message": {**CLEAN, "findings": [finding()]},
                              "events": [{"type": "session.configured", "model": "gpt-test"}, *COMPLETED]})
        self.assertEqual(report["status"], "changes_requested")
        self.assertEqual(report["findings"], [finding()])
        self.assertEqual(report["requested"], {"model": "gpt-test", "effort": "high"})
        self.assertEqual(report["observed"], {"model": "gpt-test", "effort": "unknown"})
        self.assertEqual(report["usage"], {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20})
        [argv] = self.exec_calls()
        for flags in (["--sandbox", "read-only"], ["--model", "gpt-test"], ["--config", 'model_reasoning_effort="high"'],
                      ["--disable", "multi_agent"], ["--cd", str(self.repo)]):
            self.assertIn(flags, [argv[i:i + 2] for i in range(len(argv))])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)

    def test_unreported_observed_settings_read_unknown(self):
        # Failure mode 3.
        report = self.review({"last_message": CLEAN, "events": COMPLETED})
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["observed"], {"model": "unknown", "effort": "unknown"})

    def test_blank_model_or_effort_stops_before_preflight(self):
        # Failure mode 3.
        for flag in ("--model", "--effort"):
            args = {"--model": "gpt-test", "--effort": "high", flag: "  "}
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                cross_review.main(["--provider", "codex", "--phase", "plan", "--handoff", str(self.handoff), "--out", str(self.out),
                                   "--cli", str(self.cli), "--repo", str(self.repo), *sum(args.items(), ())])
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.out / "report.json").exists())

    def test_malformed_output_is_incomplete_without_findings(self):
        # Failure mode 1.
        report = self.review({"last_message": "{\"findings\": [", "events": COMPLETED})
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["findings"], [])
        self.assertIn("failed validation", report["diagnostic"])
        self.assertIsNotNone(report["usage"])

    def test_missing_final_message_does_not_reuse_a_stale_one(self):
        # Failure mode 1.
        self.out.mkdir()
        (self.out / "last-message.json").write_text(json.dumps(CLEAN))
        report = self.review({"events": COMPLETED})
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("no final message", report["diagnostic"])

    def test_not_logged_in_fails_before_review_and_never_logs_in(self):
        # Failure mode 4.
        report = self.review({"login": "Not logged in", "login_exit": 1, "last_message": CLEAN, "events": COMPLETED})
        self.assertEqual(report["status"], "failed")
        self.assertIn("not logged in", report["diagnostic"])
        self.assertEqual(self.calls(), [["login", "status"]])

    def test_missing_cli_fails_naming_the_prerequisite(self):
        # Failure mode 4.
        self.scenario_path.write_text("{}")
        report = cross_review.run_review("codex", "plan", self.handoff, self.out, "gpt-test", "high", self.repo,
                                         str(self.root / "absent"))
        self.assertEqual(report["status"], "failed")
        self.assertIn("Codex CLI not found", report["diagnostic"])

    def test_nonzero_exit_fails_with_diagnostic_and_no_retry(self):
        # Failure mode 6.
        report = self.review({"exit_code": 1, "stderr": "You've hit your usage limit.", "events": []})
        self.assertEqual(report["status"], "failed")
        self.assertIn("usage limit", report["diagnostic"])
        self.assertEqual(len(self.exec_calls()), 1)

    def test_no_completed_turn_fails(self):
        # Failure mode 6.
        report = self.review({"last_message": CLEAN,
                              "events": [{"type": "turn.failed", "error": {"message": "stream disconnected"}}]})
        self.assertEqual(report["status"], "failed")
        self.assertIn("stream disconnected", report["diagnostic"])

    @unittest.skipIf(os.name == "nt", "process groups are POSIX-only")
    def test_timeout_stops_the_reviewer_process_tree(self):
        # Failure mode 2.
        pid_file = self.root / "child.pid"
        report = self.review({"sleep": 60, "child_pid_file": str(pid_file), "last_message": CLEAN, "events": COMPLETED},
                             timeout_seconds=2)
        self.assertEqual(report["status"], "failed")
        self.assertIn("timed out", report["diagnostic"])
        self.assertLess(report["seconds"], 30)
        child = int(pid_file.read_text())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            self.fail("reviewer child process is still running")



class ClaudeReviewTests(ReviewTestCase):
    provider, fake_cli = "claude", FAKE_CLAUDE

    def test_review_passes_settings_and_read_only_tools_and_reports_usage(self):
        # Failure mode 3.
        report = self.review({"envelope": {"structured_output": {**CLEAN, "findings": [finding()]}}})
        self.assertEqual(report["status"], "changes_requested")
        self.assertEqual(report["observed"], {"model": "claude-opus-test", "effort": "unknown"})
        self.assertEqual(report["usage"], {"input_tokens": 50, "output_tokens": 10})
        [argv] = [argv for argv in self.calls() if "-p" in argv]
        pairs = [argv[i:i + 2] for i in range(len(argv))]
        for flags in (["--model", "gpt-test"], ["--effort", "high"], ["--tools", "Read,Grep,Glob,Bash"],
                      ["--permission-mode", "dontAsk"], ["--output-format", "json"]):
            self.assertIn(flags, pairs)
        self.assertIn(str(cross_review_claude.skills_directory()), argv[argv.index("--add-dir") + 1:])
        self.assertNotIn("Edit", argv[argv.index("--tools") + 1])
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_not_logged_in_fails_before_review_and_never_logs_in(self):
        # Failure mode 4.
        report = self.review({"logged_in": False})
        self.assertEqual(report["status"], "failed")
        self.assertIn("not logged in", report["diagnostic"])
        self.assertEqual(self.calls(), [["auth", "status", "--json"]])

    def test_error_envelope_fails_with_its_message(self):
        # Failure mode 6.
        report = self.review({"envelope": {"is_error": True, "result": "API Error: usage limit reached"}, "exit_code": 1})
        self.assertEqual(report["status"], "failed")
        self.assertIn("usage limit", report["diagnostic"])

    def test_missing_or_invalid_structured_output_is_incomplete(self):
        # Failure mode 1.
        for envelope in ({}, {"structured_output": {"findings": "none"}}):
            report = self.review({"envelope": envelope})
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
