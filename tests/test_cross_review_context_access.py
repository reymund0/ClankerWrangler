"""Regression coverage for explicitly authorized context and live investigation scope."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "subagents/scripts/claude_cross_review.py"
spec = importlib.util.spec_from_file_location("cross_review_context_access_target", SOURCE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ContextAccessTests(unittest.TestCase):
    def setUp(self):
        ignored_temp_root = Path(__file__).resolve().parents[1] / ".clanker"
        ignored_temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="clanker-context-access-", dir=ignored_temp_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        previous_tempdir = tempfile.tempdir
        tempfile.tempdir = str(self.root)
        self.addCleanup(setattr, tempfile, "tempdir", previous_tempdir)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "app.py").write_text("value = 'base'\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout

    def manifest(self, **overrides):
        value = {
            "repository": str(self.repo),
            "phase": "implementation",
            "run_id": "context-access",
            "baseline": self.base,
            "selected_paths": ["app.py"],
            "context_paths": [],
            "guidance_paths": [],
            "requirements": ["R1"],
            "verification_evidence": ["Context access fixture"],
        }
        value.update(overrides)
        return value

    def snapshot(self, manifest):
        snapshot, files, fingerprint = review.collect_snapshot(
            self.repo, manifest["selected_paths"], manifest
        )
        self.addCleanup(lambda: shutil.rmtree(snapshot, ignore_errors=True))
        return snapshot, files, fingerprint

    def test_external_same_basename_files_get_distinct_packet_paths_and_keep_subjects(self):
        repository_file = self.repo / "notes.txt"
        repository_file.write_text("REPOSITORY_NOTES\n", encoding="utf-8")
        first = self.root / "first" / "notes.txt"
        second = self.root / "second" / "notes.txt"
        first.parent.mkdir()
        second.parent.mkdir()
        first.write_text("FIRST_EXTERNAL_CONTEXT\n", encoding="utf-8")
        second.write_text("SECOND_EXTERNAL_CONTEXT\n", encoding="utf-8")
        manifest = self.manifest(selected_paths=["app.py", "notes.txt", str(first), str(second)])

        snapshot, files, _ = self.snapshot(manifest)

        external = [item for item in files if item.get("path") in (str(first), str(second))]
        self.assertEqual([str(first), str(second)], [item["path"] for item in external])
        self.assertTrue(all(item["resolved_path"] == str(path.resolve()) for item, path in zip(external, (first, second))))
        packet_paths = [item["snapshot_path"] for item in external]
        repository_entry = next(item for item in files if item.get("path") == "notes.txt")
        all_paths = [repository_entry["snapshot_path"], *packet_paths]
        self.assertEqual(3, len(set(all_paths)))
        self.assertTrue(all(path.startswith("_clanker_packet/sources/external/") for path in packet_paths))
        self.assertEqual([first.read_bytes(), second.read_bytes()],
                         [(snapshot / path).read_bytes() for path in packet_paths])
        self.assertEqual(repository_file.read_bytes(), (snapshot / repository_entry["snapshot_path"]).read_bytes())

    @unittest.skipUnless(os.name == "nt", "reserved packet collision depends on native case-insensitive paths")
    def test_case_variant_reserved_sources_coexist_with_packet_metadata_and_diffs(self):
        references = (
            "_CLANKER_PACKET/evidence.json",
            "_CLANKER_PACKET/diffs/committed.diff",
        )
        originals = {}
        for index, reference in enumerate(references):
            source = self.repo / Path(reference)
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(f"ORIGINAL_RESERVED_SOURCE_{index}".encode("ascii") + b"\x00\xff")
            originals[reference] = source.read_bytes()
        manifest = self.manifest(selected_paths=["app.py", *references])

        snapshot, files, _ = self.snapshot(manifest)

        evidence = json.loads((snapshot / "_clanker_packet/evidence.json").read_text(encoding="utf-8"))
        by_subject = {item["path"]: item for item in evidence["files"]}
        for reference, original in originals.items():
            with self.subTest(path=reference):
                item = by_subject[reference]
                packet_copy = snapshot / item["snapshot_path"]
                self.assertEqual(original, packet_copy.read_bytes())
                self.assertEqual(review.sha256_bytes(original), item["sha256"])
                self.assertNotEqual("_clanker_packet/evidence.json", item["snapshot_path"])
                self.assertNotEqual("_clanker_packet/diffs/committed.diff", item["snapshot_path"])
                self.assertEqual(original, (self.repo / Path(reference)).read_bytes())

    def test_read_roots_and_required_context_are_validated_as_manifest_structure(self):
        context = self.repo / "context.md"
        context.write_text("Context required for acceptance.\n", encoding="utf-8")
        root_dir = self.root / "authorized-root"
        root_dir.mkdir()
        valid = self.manifest(context_paths=["context.md"], required_context_paths=["context.md"], read_roots=[str(root_dir)])
        review.validate_manifest(valid)

        cases = (
            ("relative read root", {"read_roots": ["authorized-root"]}),
            ("duplicate read root", {"read_roots": [str(root_dir), str(root_dir)]}),
            ("missing read root", {"read_roots": [str(self.root / "missing")] }),
            ("file read root", {"read_roots": [str(context)]}),
            ("required context outside context", {"required_context_paths": ["app.py"]}),
            ("duplicate required context", {"context_paths": ["context.md"], "required_context_paths": ["context.md", "context.md"]}),
        )
        for label, override in cases:
            with self.subTest(label=label), self.assertRaises(review.ReviewError):
                review.validate_manifest(self.manifest(**override))

    def test_selected_reference_exclusion_is_reported_as_out_of_scope(self):
        manifest = self.manifest(exclusions=[{"path": "app.py", "reason": "outside the requested review scope"}])
        snapshot, files, _ = self.snapshot(manifest)
        self.assertNotIn("app.py", review.required_subjects(manifest))
        self.assertFalse((snapshot / "app.py").exists())

    def test_selected_symlink_records_original_and_resolved_identity(self):
        source = self.root / "linked-source.txt"
        source.write_text("LINKED_SELECTED_CONTENT\n", encoding="utf-8")
        link = self.repo / "selected-link.txt"
        try:
            link.symlink_to(source)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        manifest = self.manifest(selected_paths=["selected-link.txt"])

        snapshot, files, _ = self.snapshot(manifest)

        item = next(entry for entry in files if entry.get("path") == "selected-link.txt")
        self.assertEqual("selected-link.txt", item["path"])
        self.assertEqual(str(source.resolve()), item["resolved_path"])
        self.assertEqual("selected-link.txt", review._repository_git_path(self.repo, str(link.absolute())))
        self.assertEqual(b"LINKED_SELECTED_CONTENT\n", (snapshot / item["snapshot_path"]).read_bytes())

    def test_absolute_dotdot_classifier_checks_link_metadata_before_normalizing(self):
        linked_parent = self.repo / "linked-parent"
        reference = str(linked_parent / ".." / "app.py")
        self.assertIn("..", Path(reference).parts)

        with mock.patch.object(Path, "is_symlink", autospec=True, side_effect=lambda candidate: candidate == linked_parent), mock.patch("os.readlink", return_value="external/nested"):
            self.assertIsNone(review._repository_git_path(self.repo, reference))
            links = review._source_links(Path(reference))

        self.assertEqual([{"path": str(linked_parent.absolute()), "target": "external/nested"}], links)
        self.assertEqual("app.py", review._repository_git_path(self.repo, str((self.repo / "app.py").absolute())))

    def test_absolute_dotdot_through_parent_symlink_captures_without_git_attribution(self):
        external = self.root / "external"
        nested = external / "nested"
        nested.mkdir(parents=True)
        source = external / "outside.py"
        source.write_text("external selected source\n", encoding="utf-8")
        linked_parent = self.repo / "linked-parent"
        try:
            linked_parent.symlink_to(nested, target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlink creation unavailable")
        reference = str(linked_parent / ".." / "outside.py")
        self.assertIn("..", Path(reference).parts)

        snapshot, files, _ = self.snapshot(self.manifest(selected_paths=["app.py", reference]))

        item = next(entry for entry in files if entry.get("path") == reference)
        self.assertEqual("included", item["state"])
        self.assertEqual(str(source.resolve()), item["resolved_path"])
        self.assertNotIn("git_path", item)
        self.assertTrue(any(entry["path"] == str(linked_parent.absolute()) for entry in item["source_links"]))
        self.assertEqual(b"external selected source\n", (snapshot / item["snapshot_path"]).read_bytes())
        git_entry = next(entry for entry in files if entry["path"] == "@git")
        self.assertEqual(["app.py"], git_entry["paths"])

    def test_invocation_uses_repository_and_declared_roots_with_normal_cli_configuration(self):
        external = self.root / "external" / "dependency.txt"
        external.parent.mkdir()
        external.write_text("Selected external dependency.\n", encoding="utf-8")
        extra_root = self.root / "additional-read-root"
        extra_root.mkdir()
        snapshot = self.root / "retained-packet"
        snapshot.mkdir()
        manifest = self.manifest(
            selected_paths=["app.py", str(external)],
            read_roots=[str(extra_root)],
            exclusions=[{"path": "out-of-scope/", "reason": "not part of this review"}],
        )
        payload = {
            "verdict": "clean",
            "coverage": [
                {"subject": subject, "status": "covered", "evidence": "fixture review"}
                for subject in review.required_subjects(manifest)
            ],
            "findings": [],
            "limitations": [],
            "consulted_paths": ["src/dependency.py"],
        }
        process = mock.Mock(returncode=0)
        process.communicate.return_value = (json.dumps({
            "is_error": False,
            "subtype": "success",
            "terminal_reason": "completed",
            "structured_output": payload,
        }), "")
        captured = {}

        def start(command, cwd, **streams):
            captured["command"] = command
            captured["cwd"] = cwd
            captured["streams"] = streams
            return process

        args = type("Args", (), {"model": None, "effort": None, "timeout_seconds": 1, "review_log": None})()
        with mock.patch.object(review, "start_review_process", side_effect=start), mock.patch.object(review, "close_review_job"):
            result = review.invoke(Path("claude"), snapshot, manifest, args)

        command = captured["command"]
        add_dirs = [Path(command[index + 1]) for index, value in enumerate(command[:-1]) if value == "--add-dir"]
        self.assertEqual(self.repo.resolve(), Path(captured["cwd"]).resolve())
        self.assertEqual([snapshot.resolve(), extra_root.resolve()], add_dirs)
        self.assertNotIn(external.parent.resolve(), add_dirs)
        for removed in ("--safe-mode", "--restricted", "--tools", "--allowedTools", "--disallowedTools", "--permission-prompts", "--strict-mcp-config", "--mcp-config", "--no-session-persistence", "--dangerously-skip-permissions", "--resume", "--continue"):
            self.assertNotIn(removed, command)
        self.assertEqual(["src/dependency.py"], result["consulted_paths"])
        prompt = process.communicate.call_args.args[0]
        self.assertIn("out-of-scope/", prompt)
        self.assertIn("outside findings scope, not filesystem controls", prompt)

    def test_source_comparison_reports_deletion_directory_link_and_external_changes(self):
        directory_file = self.repo / "directory-target"
        deleted_file = self.repo / "deleted-during-review.txt"
        link_target = self.root / "link-target.txt"
        replacement_target = self.root / "replacement-target.txt"
        external = self.root / "external-source.txt"
        directory_file.write_text("captured file\n", encoding="utf-8")
        deleted_file.write_text("captured then removed\n", encoding="utf-8")
        link_target.write_text("first link target\n", encoding="utf-8")
        replacement_target.write_text("replacement link target\n", encoding="utf-8")
        external.write_text("external captured version\n", encoding="utf-8")
        link = self.repo / "selected-link.txt"
        try:
            link.symlink_to(link_target)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        manifest = self.manifest(selected_paths=["app.py", "directory-target", "deleted-during-review.txt", "selected-link.txt", str(external)])

        _, files, _ = self.snapshot(manifest)

        directory_file.unlink()
        directory_file.mkdir()
        deleted_file.unlink()
        link.unlink()
        link.symlink_to(replacement_target)
        external.write_text("external changed during review\n", encoding="utf-8")
        changes = review.compare_source_changes(self.repo, files)

        self.assertEqual("unavailable", changes["status"])
        self.assertEqual("unattributed", changes["attribution"])
        by_path = {entry["path"]: entry for entry in changes["entries"]}
        self.assertEqual("removed", by_path["deleted-during-review.txt"]["status"])
        self.assertEqual("unavailable", by_path["directory-target"]["status"])
        self.assertEqual("changed", by_path["selected-link.txt"]["status"])
        self.assertEqual("changed", by_path[str(external)]["status"])

    def test_failed_git_comparison_is_reported_as_unavailable(self):
        manifest = self.manifest()
        _, files, _ = self.snapshot(manifest)
        with mock.patch.object(review, "_git_entry_fingerprint", side_effect=review.ReviewError("fixture git failure")):
            changes = review.compare_source_changes(self.repo, files)

        self.assertEqual("unavailable", changes["status"])
        self.assertTrue(any(entry["kind"] == "git" and entry["status"] == "unavailable" for entry in changes["entries"]))

    def test_optional_context_and_guidance_drift_are_not_freshness_eligible(self):
        optional_context = self.repo / "optional-context.md"
        optional_context.write_text("Captured optional context.\n", encoding="utf-8")
        guidance = self.root / "role-guidance.txt"
        guidance.write_text("Captured review guidance.\n", encoding="utf-8")
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        manifest_hash = review.sha256_file(manifest_path)

        for label, manifest_fields, source in (
            ("optional context", {"context_paths": ["optional-context.md"]}, optional_context),
            ("guidance", {"guidance_paths": [str(guidance)]}, guidance),
        ):
            with self.subTest(evidence=label):
                snapshot, files, _ = self.snapshot(self.manifest(**manifest_fields))
                evidence_kinds = {item["path"]: item.get("kind") for item in files}
                self.assertEqual("optional" if label == "optional context" else "guidance", evidence_kinds[str(source) if label == "guidance" else "optional-context.md"])
                report_path = self.root / f"{label.replace(' ', '-')}-report.json"
                initial_changes = review.compare_source_changes(self.repo, files)
                report_path.write_text(json.dumps({
                    "schema_version": 2,
                    "execution_status": "completed",
                    "verdict": "clean",
                    "source_changes": initial_changes,
                    "source_evidence": {
                        "repository": str(self.repo),
                        "read_scope": {"repository": str(self.repo), "packet": str(snapshot.resolve()), "additional_roots": []},
                        "files": files,
                        "manifest_path": str(manifest_path),
                        "manifest_sha256": manifest_hash,
                    },
                }), encoding="utf-8")
                original_report = report_path.read_bytes()
                with mock.patch("builtins.print") as emitted:
                    self.assertEqual(0, review.check_current(report_path))
                initial_query = json.loads(emitted.call_args.args[0])
                self.assertTrue(initial_query["current"])
                self.assertTrue(initial_query["eligible_for_parent_review"])
                self.assertEqual("current", initial_query["source_changes"]["status"])

                source.write_text("Changed after capture.\n", encoding="utf-8")
                with mock.patch("builtins.print") as emitted:
                    self.assertEqual(3, review.check_current(report_path))
                query = json.loads(emitted.call_args.args[0])
                self.assertFalse(query["current"])
                self.assertFalse(query["eligible_for_parent_review"])
                self.assertEqual("completed", query["execution_status"])
                self.assertEqual("changed", query["source_changes"]["status"])
                expected_subject = str(source) if label == "guidance" else "optional-context.md"
                changed = next(item for item in query["source_changes"]["entries"] if item["path"] == expected_subject)
                self.assertEqual("changed", changed["status"])
                self.assertEqual("optional" if label == "optional context" else "guidance", changed["kind"])
                self.assertEqual(original_report, report_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
