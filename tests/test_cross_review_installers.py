"""Exercise both real installers only against temporary agent destinations."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
NAME = "clanker-orchestration-nation"


class InstallerTests(unittest.TestCase):
    def exercise(self, shell):
        with tempfile.TemporaryDirectory(prefix="clanker installers ") as temp:
            root = Path(temp)
            claude, codex, windsurf = [root / name for name in ("claude", "codex", "windsurf")]
            sentinel = root / "unexpected-claude-call"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            (fake_bin / "claude").write_text("#!/bin/sh\ntouch \"" + sentinel.as_posix() + "\"\nexit 1\n")
            (fake_bin / "claude").chmod(0o755)
            (fake_bin / "claude.cmd").write_text('@echo off\necho called > "' + str(sentinel) + '"\nexit /b 1\n')
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            env.update(CLAUDE_ROOT=str(claude), CODEX_ROOT=str(codex), WINDSURF_MEMORIES_ROOT=str(windsurf))
            if shell == "powershell":
                binary = shutil.which("powershell") or shutil.which("pwsh")
                if not binary:
                    self.skipTest("PowerShell unavailable")
                command = [binary, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(REPO / "wrangle.ps1"),
                           "-ClaudeRoot", str(claude), "-CodexRoot", str(codex), "-WindsurfMemoriesRoot", str(windsurf)]
            else:
                binary = str(Path("C:/Program Files/Git/bin/bash.exe")) if os.name == "nt" else shutil.which("bash")
                if not binary or not Path(binary).is_file():
                    self.skipTest("Bash unavailable")
                command = [binary, str(REPO / "wrangle.sh")]

            def run():
                result = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(sentinel.exists(), "Installer invoked Claude")
                self.assertEqual((windsurf / "global_rules.md").read_bytes(), (REPO / "global_rules.md").read_bytes())
                for base, rules in ((claude, "CLAUDE.md"), (codex, "AGENTS.md")):
                    bundle = base / "skills" / NAME
                    self.assertEqual((bundle / "SKILL.md").read_bytes(), (REPO / "subagents" / (NAME + ".md")).read_bytes())
                    self.assertEqual((bundle / "scripts/claude_cross_review.py").read_bytes(),
                                     (REPO / "subagents/scripts/claude_cross_review.py").read_bytes())
                    self.assertEqual(sorted(f.name for f in (bundle / "scripts").iterdir()), ["claude_cross_review.py"])
                    for source in (REPO / "subagents").glob("*.md"):
                        if source.stem == NAME:
                            continue
                        self.assertEqual((bundle / "references" / source.name).read_bytes(), source.read_bytes())
                        self.assertFalse((base / "skills" / source.stem / "SKILL.md").exists())
                    self.assertEqual(list(bundle.rglob("SKILL.md")), [bundle / "SKILL.md"])
                    self.assertEqual((base / rules).read_bytes(), (REPO / "global_rules.md").read_bytes())
                self.assertIn("allow_implicit_invocation: true", (codex / "skills" / NAME / "agents/openai.yaml").read_text(encoding="utf-8-sig"))

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
            run()  # Upgrade and collision backup.
            run()  # Repeat without extra backups.
            for base in (claude, codex):
                self.assertEqual((base / "skills/unrelated/SKILL.md").read_text(), "untouched")
                self.assertEqual((base / "skills" / NAME / "references/user-note.txt").read_text(), "keep note")
                backup = base / "backups/orchestration-nation"
                self.assertEqual((backup / "clanker-backend-developer-2/custom.txt").read_text(), "preserve custom")
                self.assertEqual((backup / "clanker-backend-developer/previous.txt").read_text(), "existing backup")
                self.assertFalse((backup / "clanker-backend-developer-3").exists())

    def test_powershell_fresh_upgrade_repeat(self):
        self.exercise("powershell")

    def test_bash_fresh_upgrade_repeat(self):
        self.exercise("bash")


if __name__ == "__main__":
    unittest.main()
