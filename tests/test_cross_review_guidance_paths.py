"""Regression coverage for native path identity in local review preparation."""
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
spec = importlib.util.spec_from_file_location("cross_review_guidance_paths_target", SOURCE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class GuidancePathReadinessTests(unittest.TestCase):
    def setUp(self):
        ignored_temp_root = Path(__file__).resolve().parents[1] / ".clanker"
        ignored_temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="clanker-guidance-paths-", dir=ignored_temp_root)
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
        self.output = self.root / "reports"
        self.reservations = self.root / "reservations"
        self.no_claude = [
            mock.patch.object(review, "resolve_claude", side_effect=AssertionError("prepare resolved Claude")),
            mock.patch.object(review, "preflight", side_effect=AssertionError("prepare ran preflight")),
            mock.patch.object(review, "invoke", side_effect=AssertionError("prepare invoked Claude")),
        ]

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout

    def manifest(self, **overrides):
        value = {
            "repository": str(self.repo),
            "phase": "implementation",
            "run_id": "guidance-paths",
            "baseline": self.base,
            "selected_paths": ["app.py"],
            "context_paths": [],
            "guidance_paths": [],
            "requirements": ["R1"],
            "verification_evidence": ["Preparation does not run tests."],
        }
        value.update(overrides)
        return value

    def invoke_prepare(self, manifest, *, patches=()):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        argv = ["claude_cross_review.py", "--manifest", str(manifest_path), "--output-dir", str(self.output), "--prepare-only"]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, "argv", argv))
            stack.enter_context(mock.patch.object(review, "reservation_root", return_value=self.reservations))
            for patcher in [*self.no_claude, *patches]:
                stack.enter_context(patcher)
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            code = review.main()
        lines = stdout.getvalue().strip().splitlines()
        result = json.loads(lines[-1]) if lines else {}
        report = json.loads(Path(result["report"]).read_text(encoding="utf-8")) if result.get("report") else {}
        return code, result, report, stdout.getvalue() + stderr.getvalue()

    @staticmethod
    def forward_slashes(path):
        return str(path).replace("\\", "/")

    @unittest.skipUnless(sys.platform == "win32", "forward/native separator mismatch is specific to Windows")
    def test_forward_slash_guidance_prepares_on_windows(self):
        guidance = self.root / "role.md"
        guidance.write_text("Review compatibility.\n", encoding="utf-8")
        native_guidance = self.root / "native-role.md"
        native_guidance.write_text("Keep the supplied context in scope.\n", encoding="utf-8")
        raw_path = self.forward_slashes(guidance)
        self.assertIn("/", raw_path)
        self.assertNotEqual(raw_path, str(Path(raw_path)))

        guidance_paths = [raw_path, str(native_guidance)]
        code, _, report, output = self.invoke_prepare(self.manifest(guidance_paths=guidance_paths))

        self.assertEqual(0, code, output)
        self.assertEqual("ready", report["readiness"]["status"])
        self.assertEqual(guidance_paths, [item["path"] for item in report["source_evidence"]["guidance"]])
        self.assertEqual(["app.py", "R1"], review.required_subjects(self.manifest(guidance_paths=guidance_paths)))

    @unittest.skipUnless(sys.platform == "win32", "forward/native separator mismatch is specific to Windows")
    def test_mapped_guidance_prepares_and_preserves_original_mapping_and_subjects(self):
        guidance = self.root / "mapped-role.md"
        guidance.write_text("Use the established fixture contract.\n", encoding="utf-8")
        raw_path = self.forward_slashes(guidance)
        mapping = {"R1": [raw_path]}
        manifest = self.manifest(guidance_paths=[raw_path], requirement_paths=mapping)

        code, _, report, output = self.invoke_prepare(manifest)

        self.assertEqual(0, code, output)
        self.assertEqual("ready", report["readiness"]["status"])
        self.assertEqual(mapping, report["source_evidence"]["requirement_paths"])
        self.assertEqual(["app.py", "R1"], review.required_subjects(manifest))
        self.assertNotIn(raw_path, review.required_subjects(manifest))

    def test_formerly_filtered_mapped_evidence_is_usable_but_missing_mapping_blocks(self):
        guidance = self.root / "role.md"
        guidance.write_text("Review compatibility.\n", encoding="utf-8")
        (self.repo / ".env").write_text("PRIVATE_GUIDANCE_PATH_MARKER=value\n", encoding="utf-8")
        cases = (
            ("selected formerly filtered", {"selected_paths": ["app.py", ".env"]}, ".env", 0),
            ("context formerly filtered", {"context_paths": [".env"]}, ".env", 0),
            ("missing selected", {"selected_paths": ["app.py", "missing.py"]}, "missing.py", 2),
        )
        for name, scope, mapped_path, expected_code in cases:
            with self.subTest(name=name):
                manifest = self.manifest(
                    **scope,
                    guidance_paths=[str(guidance)],
                    requirement_paths={"R1": [mapped_path]},
                )
                code, _, report, output = self.invoke_prepare(manifest)
                self.assertEqual(expected_code, code, output)
                if expected_code == 0:
                    self.assertEqual("ready", report["readiness"]["status"])
                    evidence = report["source_evidence"]["files"]
                    self.assertEqual("included", next(item for item in evidence if item.get("path") == mapped_path)["state"])
                else:
                    self.assertEqual("blocked", report["readiness"]["status"])
                    self.assertTrue(any(item.get("path") == mapped_path for item in report["readiness"]["blockers"]))
                self.assertNotIn("PRIVATE_GUIDANCE_PATH_MARKER", json.dumps(report))

    def test_unrelated_same_basename_guidance_does_not_satisfy_manifest_path(self):
        guidance = self.root / "role.md"
        guidance.write_text("Review compatibility.\n", encoding="utf-8")
        unrelated = self.root / "elsewhere" / "role.md"
        unrelated.parent.mkdir()
        unrelated.write_text("Unrelated guidance.\n", encoding="utf-8")
        collect = review.collect_snapshot

        def capture_unrelated(repository, selected_paths, passed_manifest, **kwargs):
            snapshot, files, fingerprint = collect(repository, selected_paths, passed_manifest, **kwargs)
            guidance_item = next(item for item in files if item.get("kind") == "guidance")
            guidance_item["path"] = str(unrelated)
            guidance_item["resolved_path"] = str(unrelated.resolve())
            return snapshot, files, fingerprint

        code, _, report, output = self.invoke_prepare(
            self.manifest(guidance_paths=[str(guidance)]),
            patches=[mock.patch.object(review, "collect_snapshot", side_effect=capture_unrelated)],
        )

        self.assertEqual(2, code, output)
        self.assertEqual("blocked", report["readiness"]["status"])
        self.assertTrue(any(item["subject"] == str(guidance) for item in report["readiness"]["blockers"]))

    def test_empty_guidance_capture_blocks_and_missing_guidance_file_blocks(self):
        guidance = self.root / "role.md"
        guidance.write_text("Review compatibility.\n", encoding="utf-8")
        collect = review.collect_snapshot

        def omit_guidance(repository, selected_paths, passed_manifest, **kwargs):
            snapshot, files, fingerprint = collect(repository, selected_paths, passed_manifest, **kwargs)
            files[:] = [item for item in files if item.get("kind") != "guidance"]
            return snapshot, files, fingerprint

        with self.subTest("empty capture"):
            code, _, report, output = self.invoke_prepare(
                self.manifest(guidance_paths=[str(guidance)]),
                patches=[mock.patch.object(review, "collect_snapshot", side_effect=omit_guidance)],
            )
            self.assertEqual(2, code, output)
            self.assertEqual("blocked", report["readiness"]["status"])
            self.assertTrue(any(item["subject"] == str(guidance) for item in report["readiness"]["blockers"]))

        with self.subTest("missing source"):
            missing = self.root / "missing-role.md"
            code, _, report, output = self.invoke_prepare(self.manifest(guidance_paths=[str(missing)]))
            self.assertEqual(2, code, output)
            self.assertEqual("blocked", report["execution_status"])
            self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
