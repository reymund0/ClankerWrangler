"""Cooperative review reservations protect scope without blocking unrelated work."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("review_reservations", Path(__file__).parents[1] / "subagents/scripts/claude_cross_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReservationTests(unittest.TestCase):
    def test_overlap_external_guidance_missing_files_and_independent_reviews(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            source = repo / "code.py"
            source.write_text("pass")
            guidance = root / "guidance.md"
            guidance.write_text("Guidance")
            manifest_path = root / "manifest.json"
            manifest_path.write_text("{}")
            manifest = {"selected_paths": ["code.py", "deleted.py"], "guidance_paths": [str(guidance)]}
            with mock.patch.object(review, "reservation_root", return_value=root / "registry"):
                first = review.reserve_review(repo, manifest, manifest_path, root / "report")
                second = review.reserve_review(repo, manifest, manifest_path, root / "report2")
                self.assertEqual(json.loads(first.read_text())["files"][0]["sha256"], review.sha256_file(source))
                for path in [source, repo, guidance, repo / "deleted.py", manifest_path]:
                    self.assertFalse(review.check_write_reservations([str(path)])["allowed"])
                self.assertTrue(review.check_write_reservations([str(repo / "other.py")])["allowed"])
                first.unlink()
                self.assertFalse(review.check_write_reservations([str(source)])["allowed"])
                second.unlink()
                self.assertTrue(review.check_write_reservations([str(source)])["allowed"])

    def test_malformed_reservation_and_relative_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(review, "reservation_root", return_value=root):
                with self.assertRaises(review.ReviewError):
                    review.check_write_reservations(["relative.py"])
                (root / "broken.json").write_text('{"files": [null]}')
                with self.assertRaises(review.ReviewError):
                    review.check_write_reservations([str(root / "file")])

    def test_cleanup_on_success_failure_timeout_interrupt_and_snapshot_failure(self):
        for outcome in [None, review.ReviewError("Claude review timed out"), review.ReviewError("Claude exited"), KeyboardInterrupt(), "snapshot", "stale"]:
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest_path = root / "manifest.json"
                manifest_path.write_text(json.dumps({"repository": str(root), "phase": "plan", "run_id": "test", "selected_paths": ["code.py"], "requirements": ["works"], "verification_evidence": ["unrun"]}))
                registry = root / "registry"
                def invoke(*args):
                    self.assertEqual(len(list(registry.glob("*.json"))), 1)
                    if isinstance(outcome, BaseException):
                        raise outcome
                    return {"verdict": "clean", "coverage": [{"subject": s, "status": "covered", "evidence": "checked"} for s in ["code.py", "works"]], "findings": [], "limitations": []}
                with mock.patch.object(review, "reservation_root", return_value=registry), mock.patch.object(review, "resolve_claude", return_value=Path("claude")), mock.patch.object(review, "preflight", return_value={"requested_model": "claude-opus-5"}), mock.patch.object(review, "collect_snapshot", return_value=(root / "snapshot", [], "fp"), side_effect=review.ReviewError("snapshot failed") if outcome == "snapshot" else None), mock.patch.object(review, "invoke", side_effect=invoke), mock.patch.object(review, "current_fingerprint", return_value="changed" if outcome == "stale" else "fp"), mock.patch.object(review, "cleanup_snapshot"), mock.patch("sys.argv", ["review", "--manifest", str(manifest_path), "--output-dir", str(root / "reports"), "--effort", "high"]), contextlib.redirect_stdout(io.StringIO()):
                    code = review.main()
                self.assertEqual(code, 0 if outcome is None else 3 if outcome == "stale" else 2)
                if outcome == "stale":
                    report = json.loads((root / "reports/test/plan-1/report.json").read_text())
                    self.assertEqual(report["execution_status"], "stale")
                    self.assertIn("Review completed, but inputs changed", report["limitations"][-1])
                self.assertEqual(list(registry.glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
