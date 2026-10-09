import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

from test_cross_review_process import process_exited


MODULE = pathlib.Path(__file__).parents[1] / "subagents/scripts/claude_cross_review.py"
spec = importlib.util.spec_from_file_location("cross_review_diagnostics", MODULE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="clanker-diagnostics-")
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.args = types.SimpleNamespace(model="opus", effort="medium", timeout_seconds=3)
        self.real_start = review.start_review_process

    def invoke_fixture(self, code, *, debug=False, timeout=3):
        self.args.review_log = review.ReviewLog(self.root, debug)
        self.args.timeout_seconds = timeout

        def start(_command, snapshot, **streams):
            return self.real_start([sys.executable, "-u", "-c", code], snapshot, **streams)

        with mock.patch.object(review, "start_review_process", side_effect=start), mock.patch.object(review, "HEARTBEAT_SECONDS", 0.1):
            return review.invoke(pathlib.Path(sys.executable), self.root, {"phase": "plan"}, self.args)

    def events(self):
        return [json.loads(line) for line in (self.root / "events.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_silent_review_heartbeats_do_not_resend_input_or_claim_output(self):
        log = review.ReviewLog(self.root, False)
        code = "import sys,time; value=sys.stdin.read(); time.sleep(0.35); print(len(value))"
        process = self.real_start([sys.executable, "-u", "-c", code], self.root)
        try:
            log.event("claude_started", claude_pid=process.pid, claude_running=True)
            with mock.patch.object(review, "HEARTBEAT_SECONDS", 0.1):
                stdout, stderr = review.communicate_review(process, "single prompt", 3, log)
            self.assertEqual("13", stdout.strip())
            self.assertEqual("", stderr)
            heartbeats = [item for item in self.events() if item["event"] == "process_progress"]
            self.assertGreaterEqual(len(heartbeats), 2)
            self.assertTrue(all(item["claude_running"] for item in heartbeats))
            self.assertTrue(all(item["stdout_bytes"] == item["stderr_bytes"] == 0 for item in heartbeats))
            self.assertTrue(all(item["last_output_at"] is None for item in heartbeats))
            self.assertGreater(heartbeats[-1]["elapsed_seconds"], heartbeats[0]["elapsed_seconds"])
            self.assertFalse((self.root / "stdout.log").exists())
        finally:
            review.terminate(process)
            process.communicate(timeout=2)

    def test_debug_streams_are_persisted_before_exit_without_entering_safe_logs(self):
        code = ("import sys,time; sys.stdin.read(); "
                "print('PRIVATE_STDOUT'); print('permission denied token=PRIVATE_STDERR', file=sys.stderr); "
                "time.sleep(0.35); sys.exit(7)")
        with self.assertRaises(review.ReviewError) as caught:
            self.invoke_fixture(code, debug=True)
        self.assertEqual(7, caught.exception.exit_code)
        diagnostic = review.diagnostic_for("review_execution", caught.exception)
        self.assertIn("permission denied", diagnostic["detail"])
        safe = (self.root / "events.jsonl").read_text(encoding="utf-8") + json.dumps(diagnostic)
        self.assertNotIn("PRIVATE_", safe)
        self.assertIn("PRIVATE_STDOUT", (self.root / "stdout.log").read_text(encoding="utf-8"))
        self.assertIn("PRIVATE_STDERR", (self.root / "stderr.log").read_text(encoding="utf-8"))
        self.assertEqual("stdout.log\nstderr.log\n", (self.root / ".gitignore").read_text(encoding="utf-8"))
        live = [item for item in self.events() if item["event"] == "process_progress" and item["claude_running"]]
        self.assertTrue(any(item["stdout_bytes"] > 0 and item["stderr_bytes"] > 0 and item["last_output_at"] for item in live))
        final = json.loads((self.root / "progress.json").read_text(encoding="utf-8"))
        self.assertFalse(final["claude_running"])
        self.assertEqual("0x00000007", final["claude_exit_code_hex"])
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        ignored = subprocess.run(["git", "check-ignore", "stdout.log", "stderr.log"], cwd=self.root, check=True, capture_output=True, text=True)
        self.assertEqual({"stdout.log", "stderr.log"}, set(ignored.stdout.splitlines()))

    def test_timeout_records_reason_and_partial_capture_then_stops_process(self):
        code = "import sys,time; sys.stdin.read(); print('PRIVATE_PARTIAL'); time.sleep(60)"
        with self.assertRaisesRegex(review.ReviewError, "timed out"):
            self.invoke_fixture(code, debug=True, timeout=1)
        events = self.events()
        requested = next(item for item in events if item["event"] == "termination_requested")
        self.assertEqual("timeout", requested["termination_reason"])
        self.assertTrue(process_exited(requested["claude_pid"]))
        self.assertIn("PRIVATE_PARTIAL", (self.root / "stdout.log").read_text(encoding="utf-8"))
        final = events[-1]
        self.assertFalse(final["claude_running"])
        self.assertIsInstance(final["claude_exit_code"], int)
        self.assertIn("claude_exit_code_hex", final)
        self.assertNotIn("PRIVATE_PARTIAL", json.dumps(events))

    def test_debug_capture_preserves_success_validation(self):
        envelope = {"is_error": False, "subtype": "success", "terminal_reason": "completed",
            "structured_output": {"verdict": "clean", "coverage": [{"subject": "R1", "status": "covered", "evidence": "Fixture"}],
                "findings": [], "limitations": []}}
        code = "import sys; sys.stdin.read(); print(" + repr(json.dumps(envelope)) + ")"
        result = self.invoke_fixture(code, debug=True)
        self.assertEqual("clean", result["verdict"])
        self.assertEqual(envelope, json.loads((self.root / "stdout.log").read_text(encoding="utf-8")))

    def test_debug_capture_still_rejects_oversized_results(self):
        code = "import sys; sys.stdin.read(); print('x' * " + str(review.MAX_OUTPUT_BYTES + 1) + ")"
        with self.assertRaisesRegex(review.ReviewError, "bounded output"):
            self.invoke_fixture(code, debug=True)
        self.assertGreater((self.root / "stdout.log").stat().st_size, review.MAX_OUTPUT_BYTES)

    def test_debug_diagnostic_sample_includes_tail_with_bounded_read(self):
        capture = self.root / "sample.log"
        capture.write_bytes(b"x" * (3 * review.MAX_OUTPUT_BYTES) + b"permission denied")
        sample = review.read_capture(capture, tail=True)
        self.assertLessEqual(len(sample), 2 * review.MAX_OUTPUT_BYTES + 1)
        self.assertEqual("permission", review.classify_cli_failure(sample))

    def test_interrupt_still_terminates_when_diagnostic_write_fails(self):
        log = review.ReviewLog(self.root, False)
        self.args.review_log = log
        process = mock.Mock(pid=123, returncode=None)
        process.communicate.side_effect = KeyboardInterrupt()
        original_event = log.event

        def event(name, **fields):
            if name == "termination_requested":
                raise OSError(5, "private disk error")
            original_event(name, **fields)

        with mock.patch.object(review, "start_review_process", return_value=process), mock.patch.object(review, "close_review_job"), mock.patch.object(review, "terminate") as terminate, mock.patch.object(log, "event", side_effect=event):
            with self.assertRaises(OSError):
                review.invoke(pathlib.Path("claude"), self.root, {"phase": "plan"}, self.args)
        terminate.assert_called_once_with(process)

    def test_os_error_numbers_survive_without_exception_payload(self):
        original = OSError(13, "credential=PRIVATE_ERROR")
        original.winerror = 5
        try:
            raise review.ReviewError("Local Claude preflight failed") from original
        except review.ReviewError as error:
            diagnostic = review.diagnostic_for("subscription_preflight", error)
        self.assertEqual(13, diagnostic["errno"])
        self.assertEqual(5, diagnostic["winerror"])
        self.assertNotIn("PRIVATE_ERROR", json.dumps(diagnostic))

    @unittest.skipUnless(os.name == "nt", "kill-on-close review containment is a Windows job guarantee")
    def test_hard_stopped_launcher_leaves_capture_and_early_log_paths(self):
        repo = self.root / "repo"
        repo.mkdir()
        (repo / "plan.md").write_text("Review this plan.", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True, check=True)
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"repository": str(repo), "phase": "plan", "run_id": "hard-stop",
            "selected_paths": ["plan.md"], "requirements": ["R1"], "verification_evidence": ["Fixture only."]}), encoding="utf-8")
        fixture = "import sys,time; sys.stdin.read(); print('PRIVATE_BEFORE_STOP'); time.sleep(60)"
        wrapper = ("import importlib.util,pathlib,sys; "
            "spec=importlib.util.spec_from_file_location('fixture_review',sys.argv[1]); "
            "review=importlib.util.module_from_spec(spec); spec.loader.exec_module(review); "
            "start=review.start_review_process; "
            "review.start_review_process=lambda command,snapshot,**streams: start([sys.executable,'-u','-c'," + repr(fixture) + "],snapshot,**streams); "
            "review.resolve_claude=lambda _: pathlib.Path(sys.executable); "
            "review.preflight=lambda *args: {'requested_model':'opus'}; "
            "reservation_path=pathlib.Path(sys.argv[2]); review.reservation_root=lambda: reservation_path; "
            "sys.argv=['review',*sys.argv[3:]]; sys.exit(review.main())")
        launcher = subprocess.Popen([sys.executable, "-u", "-c", wrapper, str(MODULE), str(self.root / "reservations"),
            "--manifest", str(manifest), "--output-dir", str(self.root / "reports"), "--effort", "medium", "--debug"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        attempt = self.root / "reports/hard-stop/plan-1"
        capture = attempt / "stdout.log"
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and (not capture.exists() or capture.stat().st_size == 0):
                self.assertIsNone(launcher.poll(), "fixture launcher exited before capture")
                time.sleep(0.05)
            self.assertTrue(capture.exists() and capture.stat().st_size > 0)
        finally:
            launcher.kill()
            stdout, stderr = launcher.communicate(timeout=5)
        self.assertEqual("", stdout)
        startup = json.loads(stderr.splitlines()[0])
        self.assertEqual(str(attempt), startup["report_directory"])
        self.assertNotIn("PRIVATE_BEFORE_STOP", stderr)
        self.assertFalse((attempt / "report.json").exists())
        self.assertIn("PRIVATE_BEFORE_STOP", capture.read_text(encoding="utf-8"))
        events = [json.loads(line) for line in (attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        child_pid = next(item["claude_pid"] for item in events if item["event"] == "claude_started")
        self.assertTrue(process_exited(child_pid))
        self.assertTrue((attempt / "progress.json").exists())


if __name__ == "__main__":
    unittest.main()
