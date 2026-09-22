"""Exercise both real installers only against temporary agent destinations."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
NAME = "clanker-orchestration-nation"


class InstallerTests(unittest.TestCase):
    def exercise(self, shell, built):
        with tempfile.TemporaryDirectory(prefix="clanker installers ") as temp:
            root = Path(temp)
            source_repo = root / "source"
            source_repo.mkdir()
            for filename in ("wrangle.ps1", "wrangle.sh", "global_rules.md"):
                shutil.copy2(REPO / filename, source_repo / filename)
            shutil.copytree(REPO / "skills", source_repo / "skills")
            shutil.copytree(REPO / "subagents", source_repo / "subagents", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            project_preference = source_repo / ".clanker/orchestration-routing.json"
            project_preference.parent.mkdir()
            project_preference.write_bytes(b'{"schema_version":1}\n')
            if built:
                build = source_repo / "routing-editor/dist"
                (build / "assets").mkdir(parents=True)
                (build / "index.html").write_text("<!doctype html><title>Fixture editor</title>")
                (build / "compatibility.json").write_text('{"schema_version":1,"policy_version":"2"}')
                (build / "assets/app.js").write_text("// fixture build")
            claude, codex, windsurf = [root / name for name in ("claude", "codex", "windsurf")]
            sentinel = root / "unexpected-claude-call"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            (fake_bin / "claude").write_text("#!/bin/sh\ntouch \"" + sentinel.as_posix() + "\"\nexit 1\n")
            (fake_bin / "claude").chmod(0o755)
            (fake_bin / "claude.cmd").write_text('@echo off\necho called > "' + str(sentinel) + '"\nexit /b 1\n')
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            isolated_home = root / "isolated-home"
            preference = isolated_home / ".clanker" / "orchestration-routing.json"
            preference.parent.mkdir(parents=True)
            preference.write_bytes(b'{"schema_version": 1, "sentinel": "preserve"}\n')
            env.update(CLAUDE_ROOT=str(claude), CODEX_ROOT=str(codex), WINDSURF_MEMORIES_ROOT=str(windsurf),
                       HOME=str(isolated_home), USERPROFILE=str(isolated_home))
            if shell == "powershell":
                binary = shutil.which("powershell") or shutil.which("pwsh")
                if not binary:
                    self.skipTest("PowerShell unavailable")
                command = [binary, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(source_repo / "wrangle.ps1"),
                           "-ClaudeRoot", str(claude), "-CodexRoot", str(codex), "-WindsurfMemoriesRoot", str(windsurf)]
            else:
                binary = str(Path("C:/Program Files/Git/bin/bash.exe")) if os.name == "nt" else shutil.which("bash")
                if not binary or not Path(binary).is_file():
                    self.skipTest("Bash unavailable")
                command = [binary, str(source_repo / "wrangle.sh")]

            def run():
                result = subprocess.run(command, cwd=source_repo, env=env, capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(sentinel.exists(), "Installer invoked Claude")
                self.assertEqual(project_preference.read_bytes(), b'{"schema_version":1}\n')
                self.assertEqual((windsurf / "global_rules.md").read_bytes(), (source_repo / "global_rules.md").read_bytes())
                for base, rules in ((claude, "CLAUDE.md"), (codex, "AGENTS.md")):
                    bundle = base / "skills" / NAME
                    self.assertEqual((bundle / "SKILL.md").read_bytes(), (source_repo / "subagents" / (NAME + ".md")).read_bytes())
                    for script_name in ("claude_cross_review.py", "routing_policy.py", "routing_editor.py", "model_discovery.py"):
                        self.assertEqual((bundle / "scripts" / script_name).read_bytes(),
                                         (source_repo / "subagents/scripts" / script_name).read_bytes())
                    self.assertEqual(sorted(f.name for f in (bundle / "scripts").iterdir()),
                                     ["claude_cross_review.py", "model_discovery.py", "routing_editor.py", "routing_policy.py"])
                    help_result = subprocess.run([sys.executable, "-B", str(bundle / "scripts/routing_editor.py"), "--help"],
                                                 cwd=root, capture_output=True, text=True, timeout=10)
                    self.assertEqual(help_result.returncode, 0, help_result.stderr)
                    self.assertIn("--global-config-dir", help_result.stdout)
                    for source in (source_repo / "subagents" / "routing").rglob("*"):
                        if source.is_file():
                            destination = bundle / "routing" / source.relative_to(source_repo / "subagents" / "routing")
                            self.assertEqual(destination.read_bytes(), source.read_bytes())
                    for source in (source_repo / "subagents").glob("*.md"):
                        if source.stem == NAME:
                            continue
                        self.assertEqual((bundle / "references" / source.name).read_bytes(), source.read_bytes())
                        self.assertFalse((base / "skills" / source.stem / "SKILL.md").exists())
                    self.assertEqual(list(bundle.rglob("SKILL.md")), [bundle / "SKILL.md"])
                    self.assertEqual((base / rules).read_bytes(), (source_repo / "global_rules.md").read_bytes())
                self.assertIn("allow_implicit_invocation: true", (codex / "skills" / NAME / "agents/openai.yaml").read_text(encoding="utf-8-sig"))
                self.assertEqual(preference.read_bytes(), b'{"schema_version": 1, "sentinel": "preserve"}\n')

            run()  # Fresh install.
            for base in (claude, codex):
                custom = base / "skills/unrelated/SKILL.md"
                custom.parent.mkdir(parents=True)
                custom.write_text("untouched")
                old = base / "skills/clanker-backend-developer"
                old.mkdir()
                (old / "SKILL.md").write_text("legacy")
                (old / "custom.txt").write_text("preserve custom")
                backup = base / "backups/orchestration-nation/clanker-backend-developer"
                backup.mkdir(parents=True)
                (backup / "previous.txt").write_text("existing backup")
                (base / "skills" / NAME / "references/user-note.txt").write_text("keep note")
                editor = base / "skills" / NAME / "editor"
                editor.mkdir(parents=True, exist_ok=True)
                (editor / "index.html").write_text("stale")
                (editor / "compatibility.json").write_text("stale")
                (editor / "assets").mkdir(exist_ok=True)
                (editor / "assets" / "stale.js").write_text("stale")
                (editor / "user-note.txt").write_text("keep note")
            run()  # Upgrade and collision backup.
            run()  # Repeat without extra backups.
            for base in (claude, codex):
                self.assertEqual((base / "skills/unrelated/SKILL.md").read_text(), "untouched")
                self.assertEqual((base / "skills" / NAME / "references/user-note.txt").read_text(), "keep note")
                editor = base / "skills" / NAME / "editor"
                self.assertEqual((editor / "user-note.txt").read_text(), "keep note")
                if (source_repo / "routing-editor" / "dist").is_dir():
                    self.assertEqual((editor / "compatibility.json").read_bytes(), (source_repo / "routing-editor/dist/compatibility.json").read_bytes())
                    self.assertEqual((editor / "assets/app.js").read_bytes(), (source_repo / "routing-editor/dist/assets/app.js").read_bytes())
                    self.assertFalse((editor / "assets/stale.js").exists())
                else:
                    self.assertFalse((editor / "index.html").exists())
                    self.assertFalse((editor / "compatibility.json").exists())
                    self.assertFalse((editor / "assets").exists())
                backup = base / "backups/orchestration-nation"
                self.assertEqual((backup / "clanker-backend-developer-2/custom.txt").read_text(), "preserve custom")
                self.assertEqual((backup / "clanker-backend-developer/previous.txt").read_text(), "existing backup")
                self.assertFalse((backup / "clanker-backend-developer-3").exists())

    def test_powershell_fresh_upgrade_repeat(self):
        self.exercise("powershell", built=False)

    def test_powershell_built_editor(self):
        self.exercise("powershell", built=True)

    def test_bash_fresh_upgrade_repeat(self):
        self.exercise("bash", built=False)

    def test_bash_built_editor(self):
        self.exercise("bash", built=True)


if __name__ == "__main__":
    unittest.main()
