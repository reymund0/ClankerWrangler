"""Independent regression cases for scope isolation and review freshness."""
import importlib.util
import contextlib
import io
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
        ignored_temp_root = Path(__file__).resolve().parents[1] / ".clanker"
        ignored_temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="clanker-evidence-", dir=ignored_temp_root)
        self.addCleanup(self.temp.cleanup)
        previous_tempdir = tempfile.tempdir
        tempfile.tempdir = self.temp.name
        self.addCleanup(setattr, tempfile, "tempdir", previous_tempdir)
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

    def saved_v2_report(self, name, snapshot, files):
        manifest_path = Path(self.temp.name) / f"{name}-manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        manifest_hash = review.sha256_file(manifest_path)
        source_changes = review.compare_source_changes(self.repo, files, manifest_path, manifest_hash)
        self.assertEqual("current", source_changes["status"], source_changes)
        report = {
            "schema_version": 2,
            "execution_status": "prepared",
            "verdict": "incomplete",
            "source_changes": source_changes,
            "source_evidence": {
                "repository": str(self.repo),
                "read_scope": {"repository": str(self.repo), "packet": str(snapshot.resolve()), "additional_roots": []},
                "files": files,
                "manifest_path": str(manifest_path),
                "manifest_sha256": manifest_hash,
            },
        }
        report_path = Path(self.temp.name) / f"{name}-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report_path

    def current_query(self, report_path):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = review.check_current(report_path)
        return code, json.loads(output.getvalue())

    def assert_current_before_drift(self, report_path):
        code, query = self.current_query(report_path)
        self.assertEqual(0, code, query)
        self.assertTrue(query["current"])
        self.assertEqual("current", query["source_changes"]["status"])

    def assert_drift_entry(self, report_path, subject, kind, status="changed"):
        code, query = self.current_query(report_path)
        self.assertEqual(3, code, query)
        self.assertFalse(query["current"])
        self.assertEqual("changed" if status != "unavailable" else "unavailable", query["source_changes"]["status"])
        matching = [entry for entry in query["source_changes"]["entries"] if entry["path"] == subject and entry["kind"] == kind]
        self.assertEqual(1, len(matching), query["source_changes"])
        self.assertEqual(status, matching[0]["status"])

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
        evidence = json.loads((root / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))
        artifacts = evidence["git"]["diffs"]
        self.assertEqual({"committed", "staged", "unstaged"}, set(artifacts))
        combined_diff = []
        for kind, artifact in artifacts.items():
            self.assertTrue(artifact["path"].startswith("_clanker_packet/diffs/"), kind)
            self.assertTrue(artifact["path"].endswith(".diff"), kind)
            contents = (root / artifact["path"]).read_bytes()
            self.assertEqual(artifact["sha256"], review.sha256_bytes(contents), kind)
            self.assertEqual(artifact["bytes"], len(contents), kind)
            self.assertGreater(len(contents.splitlines()), 1, kind)
            combined_diff.append(contents.decode("utf-8"))
        readable_diff = "\n".join(combined_diff)
        self.assertIn("diff --git", readable_diff)
        self.assertNotIn("DO_NOT_SEND_UNRELATED_CONTENT", readable_diff)
        self.assertLessEqual(sum(item["bytes"] for item in artifacts.values()), 8 * review.MAX_OUTPUT_BYTES)

    def test_latin1_committed_staged_and_unstaged_hunks_are_utf8_and_preserve_source_bytes(self):
        source = self.repo / "latin1.txt"
        source.write_bytes(b"value = 'baseline'\n")
        self.git("add", "latin1.txt")
        self.git("commit", "-qm", "add Latin1 fixture")
        source.write_bytes(b"value = '\xe9'\n")
        self.git("add", "latin1.txt")
        self.git("commit", "-qm", "commit Latin1 hunk")
        source.write_bytes(b"value = '\xf1'\n")
        self.git("add", "latin1.txt")
        source.write_bytes(b"value = '\xe4'\n")
        expected_head = b"value = '\xe9'\n"
        expected_index = b"value = '\xf1'\n"
        expected_worktree = b"value = '\xe4'\n"

        root, _, _ = self.snapshot(["latin1.txt"])

        evidence = json.loads((root / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))
        artifacts = evidence["git"]["diffs"]
        for kind, escaped_byte in (("committed", b"\\xe9"), ("staged", b"\\xf1"), ("unstaged", b"\\xe4")):
            with self.subTest(diff=kind):
                metadata = artifacts[kind]
                artifact = root / metadata["path"]
                raw = artifact.read_bytes()
                self.assertEqual(metadata["sha256"], review.sha256_bytes(raw))
                self.assertEqual(metadata["bytes"], len(raw))
                artifact.read_text(encoding="utf-8")
                self.assertIn(escaped_byte, raw)
                self.assertNotIn(b"\xe9", raw)
                self.assertNotIn(b"\xf1", raw)
                self.assertNotIn(b"\xe4", raw)

        self.assertEqual(expected_worktree, source.read_bytes())
        git_bytes = lambda *args: subprocess.run(["git", *args], cwd=self.repo, capture_output=True, check=True).stdout
        self.assertEqual(expected_head, git_bytes("show", "HEAD:latin1.txt"))
        self.assertEqual(expected_index, git_bytes("show", ":latin1.txt"))

    def test_ignored_sensitive_named_and_binary_selected_files_enter_packet(self):
        (self.repo / "ignored.txt").write_text("DO_NOT_SEND_IGNORED\n")
        (self.repo / ".env").write_text("DO_NOT_SEND_ENV=example\n")
        certificate = "-----BEGIN CERTIFICATE-----\nSELECTED_PUBLIC_CERTIFICATE\n-----END CERTIFICATE-----\n"
        (self.repo / "key.pem").write_text(certificate)
        (self.repo / "credential-example.txt").write_text('api_key = "example-value-not-a-real-key"\n')
        (self.repo / "binary.dat").write_bytes(b"SELECTED_BINARY\x00\xff\x01")
        root, files, _ = self.snapshot(["app.py", "ignored.txt", ".env", "key.pem", "binary.dat"])
        for name in (
            "ignored.txt",
            ".env",
            "key.pem",
            "binary.dat",
        ):
            with self.subTest(path=name):
                item = next(entry for entry in files if entry.get("path") == name)
                self.assertEqual("included", item["state"])
                self.assertEqual((self.repo / name).read_bytes(), (root / item["snapshot_path"]).read_bytes())
        credential_root, credential_files, _ = self.snapshot(["credential-example.txt"])
        credential = next(entry for entry in credential_files if entry.get("path") == "credential-example.txt")
        self.assertEqual("included", credential["state"])
        self.assertIn(b"example-value-not-a-real-key", (credential_root / credential["snapshot_path"]).read_bytes())

    def test_deleted_source_diff_is_reviewable(self):
        (self.repo / "app.py").unlink()
        root, _, _ = self.snapshot(["app.py"])
        self.assertIn("value = 'base'", self.packet_text(root))
        evidence = json.loads((root / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))
        referenced = [root / item["path"] for item in evidence["git"]["diffs"].values()]
        self.assertTrue(any("-value = 'base'" in path.read_text(encoding="utf-8") for path in referenced))

    def test_new_file_after_snapshot_invalidates_fingerprint(self):
        snapshot, files, _ = self.snapshot(["app.py", "new.py"])
        report_path = self.saved_v2_report("new-file", snapshot, files)
        self.assert_current_before_drift(report_path)
        (self.repo / "new.py").write_text("changed = True\n")
        self.assert_drift_entry(report_path, "new.py", "required")

    def test_context_change_invalidates_fingerprint(self):
        (self.repo / "requirements.md").write_text("Original requirement\n")
        snapshot, files, _ = self.snapshot(["app.py"], context_paths=["requirements.md"])
        report_path = self.saved_v2_report("ordinary-context", snapshot, files)
        self.assert_current_before_drift(report_path)
        (self.repo / "requirements.md").write_text("Changed requirement\n")
        self.assert_drift_entry(report_path, "requirements.md", "optional")

    def test_invalid_baseline_cannot_be_silent_empty_diff(self):
        with self.assertRaises(review.ReviewError):
            self.snapshot(["app.py"], baseline="nonexistent-baseline")

    def test_pathspec_magic_is_not_a_file(self):
        with self.assertRaises(review.ReviewError):
            self.snapshot([":(glob)**"])

    def test_rename_preserves_old_and_new_evidence(self):
        self.git("mv", "app.py", "renamed.py")
        root, files, _ = self.snapshot(["app.py", "renamed.py"])
        packet = self.packet_text(root)
        self.assertIn("renamed.py", packet)
        self.assertIn("app.py", packet)
        self.assertIn("value = 'base'", packet)
        evidence = json.loads((root / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))
        diff_paths = [root / item["path"] for item in evidence["git"]["diffs"].values()]
        self.assertTrue(any("app.py" in path.read_text(encoding="utf-8") and "renamed.py" in path.read_text(encoding="utf-8") for path in diff_paths))

    def test_guidance_changes_are_reported_by_freshness_query(self):
        guidance = Path(self.temp.name) / "rules.md"
        guidance.write_text("Review carefully")
        root, files, _ = self.snapshot(["app.py"], guidance_paths=[str(guidance)])
        report_path = self.saved_v2_report("guidance", root, files)
        self.assertIn("Review carefully", self.packet_text(root))
        self.assert_current_before_drift(report_path)
        guidance.write_text("Changed guidance")
        self.assert_drift_entry(report_path, str(guidance), "guidance")

    def test_staged_index_only_change_is_reported_as_git_drift(self):
        root, files, _ = self.snapshot(["app.py"])
        report_path = self.saved_v2_report("staged-index", root, files)
        self.assert_current_before_drift(report_path)
        (self.repo / "app.py").write_text("indexed = True")
        self.git("add", "app.py")
        (self.repo / "app.py").write_text("value = 'base'\n")
        self.assert_drift_entry(report_path, "@git", "git")

    def test_rename_after_capture_is_reported_as_source_drift(self):
        root, files, _ = self.snapshot(["app.py"])
        report_path = self.saved_v2_report("rename-drift", root, files)
        self.assert_current_before_drift(report_path)

        self.git("mv", "app.py", "renamed.py")

        self.assert_drift_entry(report_path, "app.py", "required", status="removed")

    def test_credential_like_content_in_deleted_diff_remains_reviewable(self):
        (self.repo / "ordinary.txt").write_text("-----BEGIN PRIVATE KEY-----\nSELECTED_PRIVATE_LOOKING_FIXTURE")
        self.git("add", "ordinary.txt")
        self.git("commit", "-qm", "key fixture")
        (self.repo / "ordinary.txt").unlink()
        root, _, _ = self.snapshot(["ordinary.txt"])
        self.assertIn("SELECTED_PRIVATE_LOOKING_FIXTURE", self.packet_text(root))

    def test_oversized_diff_is_retained_with_warning_and_explicit_budget_blocks(self):
        (self.repo / "large.txt").write_text("x" * (review.MAX_OUTPUT_BYTES + 1))
        self.git("add", "large.txt")
        self.git("commit", "-qm", "large fixture")
        (self.repo / "large.txt").unlink()
        root, files, _ = self.snapshot(["large.txt"])
        self.assertIn("large.txt", self.packet_text(root))
        warnings = json.loads((root / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))["manifest"]["collection_warnings"]
        self.assertTrue(any("former 1 MB" in warning and "bytes" in warning for warning in warnings))
        with self.assertRaisesRegex(review.ReviewError, "max-file-bytes"):
            review.collect_snapshot(self.repo, ["large.txt"], {"phase": "implementation", "baseline": self.base}, max_file_bytes=review.MAX_OUTPUT_BYTES)

    def test_traversal_is_rejected_but_selected_link_is_captured(self):
        with self.assertRaises(review.ReviewError):
            self.snapshot(["../outside.txt"])
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_bytes(b"outside linked evidence\x00")
        try:
            (self.repo / "linked.txt").symlink_to(outside)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        root, files, _ = self.snapshot(["linked.txt"])
        item = next(entry for entry in files if entry.get("path") == "linked.txt")
        self.assertEqual(str(outside.resolve()), item["resolved_path"])
        self.assertEqual(outside.read_bytes(), (root / item["snapshot_path"]).read_bytes())

    def test_credential_like_content_is_included_in_plain_filename(self):
        (self.repo / "config.py").write_text('api_key = "example-value-not-a-real-key"')
        root, files, _ = self.snapshot(["config.py"])
        self.assertEqual(files[0]["state"], "included")
        self.assertIn("example-value-not-a-real-key", self.packet_text(root))

    def test_former_aggregate_packet_bound_is_warning_and_optional_budget_is_resource_error(self):
        payload = "x" * (8 * review.MAX_OUTPUT_BYTES + 1)
        (self.repo / "large-context.txt").write_text(payload, encoding="utf-8")
        root, files, _ = self.snapshot(["app.py", "large-context.txt"])
        self.assertEqual("included", next(item for item in files if item.get("path") == "large-context.txt")["state"])
        evidence = json.loads((root / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))
        self.assertTrue(any("former 8 MB" in warning and "bytes" in warning for warning in evidence["manifest"]["collection_warnings"]))
        with self.assertRaisesRegex(review.ReviewError, "max-packet-bytes"):
            review.collect_snapshot(self.repo, ["app.py", "large-context.txt"], {"phase": "implementation"}, max_packet_bytes=review.MAX_OUTPUT_BYTES)

    def test_plan_selected_file_does_not_require_git_ignore_check(self):
        not_repo = Path(self.temp.name) / "not-repo"
        not_repo.mkdir()
        (not_repo / "file.md").write_text("content")
        snapshot, files, _ = review.collect_snapshot(not_repo, ["file.md"], {"phase": "plan"})
        try:
            self.assertEqual("included", files[0]["state"])
            self.assertEqual("content", (snapshot / files[0]["snapshot_path"]).read_text(encoding="utf-8"))
        finally:
            review.cleanup_snapshot(snapshot)

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

    def test_legacy_git_fingerprint_remains_current_for_an_unchanged_repository(self):
        head = self.git("rev-parse", "HEAD").strip()
        merge_base = self.git("merge-base", self.base, head).strip()
        prefix = ("diff", "--no-ext-diff", "--no-textconv", "--no-color")
        legacy_git = {
            "head": head,
            "baseline": self.base,
            "merge_base": merge_base,
            "committed": self.git(*prefix, merge_base, head, "--", "app.py"),
            "staged": self.git(*prefix, "--cached", "--", "app.py"),
            "unstaged": self.git(*prefix, "--", "app.py"),
            "names": self.git(*prefix, "--name-status", "-M", merge_base, "--", "app.py"),
        }
        files = [
            {"path": "app.py", "state": "included", "sha256": review.sha256_file(self.repo / "app.py")},
            {"path": "@git", "state": "git", "baseline": self.base, "paths": ["app.py"],
             "sha256": review.sha256_bytes(json.dumps(legacy_git, sort_keys=True).encode())},
        ]
        report = self.repo.parent / "legacy-report.json"
        report.write_text(json.dumps({
            "execution_status": "completed",
            "source_evidence": {"repository": str(self.repo), "files": files,
                                "file_fingerprint": review.evidence_fingerprint(files)},
        }), encoding="utf-8")
        output = __import__("io").StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, review.check_current(report))
        self.assertTrue(json.loads(output.getvalue())["current"])
        saved_report = report.read_bytes()
        (self.repo / "app.py").write_text("value = 'changed after the legacy review'\n", encoding="utf-8")
        with contextlib.redirect_stdout(output := __import__("io").StringIO()):
            self.assertEqual(3, review.check_current(report))
        self.assertFalse(json.loads(output.getvalue())["current"])
        self.assertEqual(saved_report, report.read_bytes())

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
