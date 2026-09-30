"""Independent regression cases for scope isolation and review freshness."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "subagents/scripts/claude_cross_review.py"
spec = importlib.util.spec_from_file_location("cross_review_evidence_target", SOURCE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clanker-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "app.py").write_text("value = 'base'\n")
        (self.repo / "unrelated.txt").write_text("base unrelated\n")
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        r = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def snapshot(self, paths, **extra):
        manifest = dict(repository=str(self.repo), phase="implementation", run_id="fixture", baseline=self.base,
                        selected_paths=paths, context_paths=[], requirements=["Preserve expected values"], verification_evidence=[])
        manifest.update(extra)
        result = review.collect_snapshot(self.repo, paths, manifest)
        self.addCleanup(lambda: shutil.rmtree(result[0]) if result[0].exists() else None)
        return result

    def packet_text(self, root):
        return "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*") if p.is_file())

    def test_only_selected_changes_enter_packet(self):
        (self.repo / "app.py").write_text("value = 'committed'\n")
        self.git("add", "app.py")
        self.git("commit", "-qm", "feature")
        (self.repo / "app.py").write_text("value = 'staged'\n")
        self.git("add", "app.py")
        (self.repo / "app.py").write_text("value = 'unstaged'\n")
        (self.repo / "new.py").write_text("new_value = 42\n")
        (self.repo / "unrelated.txt").write_text("DO_NOT_SEND_UNRELATED_CONTENT\n")
        root, _, _ = self.snapshot(["app.py", "new.py"])
        packet = self.packet_text(root)
        for expected in ("committed", "staged", "unstaged", "new_value = 42"):
            self.assertIn(expected, packet)
        self.assertNotIn("DO_NOT_SEND_UNRELATED_CONTENT", packet)
        self.assertFalse((root / "unrelated.txt").exists())

    def test_ignored_and_sensitive_files_do_not_enter_packet(self):
        (self.repo / "ignored.txt").write_text("DO_NOT_SEND_IGNORED\n")
        (self.repo / ".env").write_text("DO_NOT_SEND_ENV=example\n")
        (self.repo / "key.pem").write_text("-----BEGIN PRIVATE KEY-----\nDO_NOT_SEND_PRIVATE_KEY\n")
        (self.repo / "binary.dat").write_bytes(b"DO_NOT_SEND_BINARY\x00\x01")
        root, files, _ = self.snapshot(["app.py", "ignored.txt", ".env", "key.pem", "binary.dat"])
        packet = self.packet_text(root)
        for marker in ("DO_NOT_SEND_IGNORED", "DO_NOT_SEND_ENV", "DO_NOT_SEND_PRIVATE_KEY", "DO_NOT_SEND_BINARY"):
            self.assertNotIn(marker, packet)
        self.assertTrue(any(entry.get("state") == "excluded" for entry in files))

    def test_deleted_source_diff_is_reviewable(self):
        (self.repo / "app.py").unlink()
        root, _, _ = self.snapshot(["app.py"])
        self.assertIn("value = 'base'", self.packet_text(root))

    def test_new_file_after_snapshot_invalidates_fingerprint(self):
        _, files, before = self.snapshot(["app.py", "new.py"])
        self.assertEqual(review.current_fingerprint(self.repo, files), before)
        (self.repo / "new.py").write_text("changed = True\n")
        self.assertNotEqual(review.current_fingerprint(self.repo, files), before)

    def test_context_change_invalidates_fingerprint(self):
        (self.repo / "requirements.md").write_text("Original requirement\n")
        _, files, before = self.snapshot(["app.py"], context_paths=["requirements.md"])
        (self.repo / "requirements.md").write_text("Changed requirement\n")
        self.assertNotEqual(review.current_fingerprint(self.repo, files), before)

    def test_invalid_baseline_cannot_be_silent_empty_diff(self):
        with self.assertRaises(review.ReviewError):
            self.snapshot(["app.py"], baseline="nonexistent-baseline")

    def test_pathspec_magic_is_not_a_file(self):
        with self.assertRaises(review.ReviewError):
            self.snapshot([":(glob)**"])

    def test_rename_preserves_old_and_new_evidence(self):
        self.git("mv", "app.py", "renamed.py")
        root, files, before = self.snapshot(["app.py", "renamed.py"])
        packet = self.packet_text(root)
        self.assertIn("renamed.py", packet)
        self.assertIn("app.py", packet)
        self.assertIn("value = 'base'", packet)
        self.assertEqual(review.current_fingerprint(self.repo, files), before)

    def test_guidance_is_copied_and_fingerprinted(self):
        guidance = Path(self.temp.name) / "rules.md"
        guidance.write_text("Review carefully")
        root, files, before = self.snapshot(["app.py"], guidance_paths=[str(guidance)])
        self.assertIn("Review carefully", self.packet_text(root))
        self.assertEqual(review.current_fingerprint(self.repo, files), before)
        guidance.write_text("Changed guidance")
        self.assertNotEqual(review.current_fingerprint(self.repo, files), before)

    def test_baseline_index_changes_invalidate_review(self):
        _, files, before = self.snapshot(["app.py"])
        (self.repo / "app.py").write_text("indexed = True")
        self.git("add", "app.py")
        (self.repo / "app.py").write_text("value = 'base'\n")
        self.assertNotEqual(review.current_fingerprint(self.repo, files), before)

    def test_private_key_in_deleted_diff_is_blocked(self):
        (self.repo / "ordinary.txt").write_text("-----BEGIN PRIVATE KEY-----\nprivate data")
        self.git("add", "ordinary.txt")
        self.git("commit", "-qm", "key fixture")
        (self.repo / "ordinary.txt").unlink()
        with self.assertRaises(review.ReviewError):
            self.snapshot(["ordinary.txt"])

    def test_oversized_diff_is_blocked(self):
        (self.repo / "large.txt").write_text("x" * (review.MAX_OUTPUT_BYTES + 1))
        self.git("add", "large.txt")
        self.git("commit", "-qm", "large fixture")
        (self.repo / "large.txt").unlink()
        with self.assertRaises(review.ReviewError):
            self.snapshot(["large.txt"])

    def test_traversal_and_linked_evidence_rejected(self):
        with self.assertRaises(review.ReviewError):
            self.snapshot(["../outside.txt"])
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("outside")
        try:
            (self.repo / "linked.txt").symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(review.ReviewError):
            self.snapshot(["linked.txt"])

    def test_credential_content_is_excluded_in_plain_filename(self):
        (self.repo / "config.py").write_text('api_key = "example-value-not-a-real-key"')
        root, files, _ = self.snapshot(["config.py"])
        self.assertEqual(files[0]["state"], "excluded")
        self.assertNotIn("example-value-not-a-real-key", self.packet_text(root))

    def test_metadata_counts_toward_packet_bound(self):
        with self.assertRaisesRegex(review.ReviewError, "size bound"):
            self.snapshot(["app.py"], verification_evidence=["x" * (8 * review.MAX_OUTPUT_BYTES)])

    def test_plan_cannot_ignore_failed_git_ignore_check(self):
        not_repo = Path(self.temp.name) / "not-repo"
        not_repo.mkdir()
        (not_repo / "file.md").write_text("content")
        with self.assertRaisesRegex(review.ReviewError, "ignore status"):
            review.collect_snapshot(not_repo, ["file.md"], {"phase": "plan"})

    def test_unique_attempts_and_no_report_overwrite(self):
        output = Path(self.temp.name) / "reports"
        first = review.report_directory(output, "fixture", "plan")
        second = review.report_directory(output, "fixture", "plan")
        self.assertNotEqual(first, second)
        report = {"phase": "plan", "execution_status": "failed", "verdict": "incomplete"}
        path = review.write_report(first, report)
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            review.write_report(first, {**report, "verdict": "clean"})
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue((first / "metadata.json").is_file())
        with self.assertRaises(OSError):
            review.write_report(output / "missing", report)

    def test_output_symlink_cannot_escape_report_root(self):
        output = Path(self.temp.name) / "reports"
        outside = Path(self.temp.name) / "outside"
        output.mkdir(); outside.mkdir()
        try:
            (output / "fixture").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlink creation unavailable")
        with self.assertRaises(review.ReviewError):
            review.report_directory(output, "fixture", "plan")
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
