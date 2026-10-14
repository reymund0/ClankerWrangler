"""Exercise both real installers only against temporary agent destinations."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
NAME = "clanker-orchestration-nation"
RETIRED = ("clanker-ux-designer", "clanker-documentation-writer", "clanker-product-engineer")
OLD_REVIEW_REFERENCE = "clanker-claude-cross-review"
WORKER = "clanker-orchestration-worker"
# Same marker with different letter case: the installer must treat this file as unmanaged and back it up.
WORKER_CASE_VARIANT = "<!-- CLANKER-ORCHESTRATION-NATION: MANAGED WORKER DEFINITION -->\nuser agent with a case-differing marker\n"
SCRIPTS = ("claude_cross_review.py", "codex_cross_review.py", "cross_review_core.py", "model_discovery.py", "routing_editor.py", "routing_policy.py")


class InstallerTests(unittest.TestCase):
    def link_directory(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("Directory links unavailable")
            creation = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                      capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if creation.returncode:
                self.skipTest("Symlink/junction creation unavailable")

    def assert_host_install(self, source_repo, base, bundle, host):
        """Each root gets its own host reference and configuration, the shared reviewer reference, and (Claude only) the worker."""
        source = source_repo / "subagents"
        self.assertEqual((bundle / "references/host.md").read_bytes(), (source / "hosts" / host / "host.md").read_bytes())
        self.assertEqual((bundle / "routing/host.json").read_bytes(), (source / "hosts" / host / "host.json").read_bytes())
        other = "codex" if host == "claude" else "claude"
        self.assertNotEqual((bundle / "references/host.md").read_bytes(), (source / "hosts" / other / "host.md").read_bytes())
        self.assertEqual((bundle / "references/clanker-cross-review.md").read_bytes(), (source / "clanker-cross-review.md").read_bytes())
        self.assertFalse((bundle / "references" / (OLD_REVIEW_REFERENCE + ".md")).exists())
        if host == "claude":
            worker = base / "agents" / (WORKER + ".md")
            self.assertEqual(worker.read_bytes(), (source / "claude" / (WORKER + ".md")).read_bytes())
            self.assertEqual([path.name for path in (base / "agents").iterdir()], [worker.name])
        else:
            self.assertFalse((base / "agents").exists())

    def assert_installed_launchers(self, root, bundle, host):
        """Run the installed helpers: imports resolve, the snapshot host comes from routing/host.json, retired guidance is explained."""
        scripts = bundle / "scripts"
        home = root / "snapshot-home"  # No preference files: this only checks host selection, not the fixture preferences.
        for launcher in ("claude_cross_review.py", "codex_cross_review.py"):
            result = subprocess.run([sys.executable, "-B", str(scripts / launcher), "--help"], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
        preferences = {"claude": "orchestration-routing-claude.json", "codex": "orchestration-routing.json"}
        other = "codex" if host == "claude" else "claude"
        policy = [sys.executable, "-B", str(scripts / "routing_policy.py"), "snapshot"]
        output = root / ("snapshot-" + host + ".json")
        output.unlink(missing_ok=True)
        made = subprocess.run([*policy, "--global", str(home / ".clanker" / preferences[host]), "--output", str(output)], cwd=root, capture_output=True, text=True, timeout=30)
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual(json.loads(made.stdout)["host"], host)
        for arguments in (["--host", other, "--global", str(home / ".clanker" / preferences[host])], ["--global", str(home / ".clanker" / preferences[other])]):
            rejected = subprocess.run([*policy, *arguments], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(rejected.returncode, 2, rejected.stdout)
        repository = root / "launcher-repo"
        repository.mkdir(exist_ok=True)
        (repository / "plan.md").write_text("Plan.\n", encoding="utf-8")
        retired = bundle / "references" / (OLD_REVIEW_REFERENCE + ".md")
        manifest = root / "retired-manifest.json"
        manifest.write_text(json.dumps({"repository": str(repository), "phase": "plan", "run_id": "retired-" + host, "selected_paths": ["plan.md"],
                                        "requirements": ["R1"], "verification_evidence": ["Planning only"], "guidance_paths": [str(retired)]}), encoding="utf-8")
        prepared = subprocess.run([sys.executable, "-B", str(scripts / "claude_cross_review.py"), "--manifest", str(manifest),
                                   "--output-dir", str(root / "launcher-reports"), "--prepare-only"], cwd=root, capture_output=True, text=True, timeout=30)
        self.assertEqual(prepared.returncode, 2, prepared.stdout)
        report = json.loads(next((root / "launcher-reports" / ("retired-" + host)).glob("plan-*/report.json")).read_text(encoding="utf-8"))
        detail = " ".join(report["limitations"])
        self.assertEqual(report["execution_status"], "blocked")
        self.assertIn(str(retired), detail)
        self.assertIn("references/clanker-cross-review.md", detail)
        shutil.rmtree(root / "launcher-reports")

    def exercise(self, shell, built, scenario=None, linked_agent_roots=False, worker_text="user agent without marker"):
        with tempfile.TemporaryDirectory(prefix="clanker installers ") as temp:
            root = Path(temp)
            source_repo = root / "source"
            source_repo.mkdir()
            for filename in ("wrangle.ps1", "wrangle.sh", "global_rules.md"):
                shutil.copy2(REPO / filename, source_repo / filename)
            shutil.copytree(REPO / "skills", source_repo / "skills")
            shutil.copytree(REPO / "subagents", source_repo / "subagents", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            shutil.copytree(REPO / "routing-editor/scripts", source_repo / "routing-editor/scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            project_preference = source_repo / ".clanker/orchestration-routing.json"
            project_preference.parent.mkdir()
            project_bytes = b'{"schema_version":1,"adaptive_profiles":{"codex:custom":{"tiers":{"straightforward":"low","involved":"high","demanding":"xhigh"},"default_ceiling":"xhigh"}}}\n'
            project_preference.write_bytes(project_bytes)
            if built:
                build = source_repo / "routing-editor/dist"
                (build / "assets").mkdir(parents=True)
                (build / "index.html").write_text("<!doctype html><title>Fixture editor</title>")
                (build / "compatibility.json").write_text('{"schema_version":1,"policy_version":"7"}')
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
            legacy_bytes = b'{"schema_version":1,"adaptive_profiles":{"codex:custom":{"tiers":{"mechanical":"low","routine":"medium","complex":"high","exceptional":"xhigh"},"default_ceiling":"xhigh"}}}\n'
            preference.write_bytes(legacy_bytes)
            claude_preference = preference.with_name("orchestration-routing-claude.json")
            claude_bytes = b'{"schema_version":1,"interactions":{"implementation":{"model":"haiku"}}}\n'
            claude_preference.write_bytes(claude_bytes)
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
                # Git Bash consumes environment paths as POSIX text, not Python's
                # backslash-separated Windows strings.
                env.update(CLAUDE_ROOT=claude.as_posix(), CODEX_ROOT=codex.as_posix(),
                           WINDSURF_MEMORIES_ROOT=windsurf.as_posix(), HOME=isolated_home.as_posix())
                command = [binary, str(source_repo / "wrangle.sh")]

            def run(expected=0):
                result = subprocess.run(command, cwd=source_repo, env=env, capture_output=True, text=True, timeout=90)
                if expected:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(sentinel.exists(), "Installer invoked Claude")
                if linked_agent_roots:
                    for base in (claude, codex):
                        self.assertTrue(base.is_symlink() or bool(getattr(base.lstat(), "st_file_attributes", 0) & 0x400),
                                        "Installer replaced the owner-selected linked root")
                        target_bundle = root / (base.name + "-target") / "skills" / NAME / "SKILL.md"
                        self.assertTrue(target_bundle.is_file())
                        self.assertEqual(target_bundle.read_bytes(), (base / "skills" / NAME / "SKILL.md").read_bytes())
                self.assertEqual(project_preference.read_bytes(), project_bytes)
                self.assertEqual(preference.read_bytes(), legacy_bytes)
                self.assertEqual(claude_preference.read_bytes(), claude_bytes)
                self.assertEqual(sorted(path.name for path in preference.parent.iterdir()), [claude_preference.name, preference.name])
                if expected:
                    return result
                self.assertEqual((windsurf / "global_rules.md").read_bytes(), (source_repo / "global_rules.md").read_bytes())
                for base, rules, host in ((claude, "CLAUDE.md", "claude"), (codex, "AGENTS.md", "codex")):
                    bundle = base / "skills" / NAME
                    self.assertEqual((bundle / "SKILL.md").read_bytes(), (source_repo / "subagents" / (NAME + ".md")).read_bytes())
                    for script_name in SCRIPTS:
                        self.assertEqual((bundle / "scripts" / script_name).read_bytes(),
                                         (source_repo / ("routing-editor/scripts" if script_name in ("routing_editor.py", "model_discovery.py") else "subagents/scripts") / script_name).read_bytes())
                    self.assertEqual(sorted(f.name for f in (bundle / "scripts").iterdir()), sorted(SCRIPTS))
                    self.assert_host_install(source_repo, base, bundle, host)
                    self.assert_installed_launchers(root, bundle, host)
                    help_result = subprocess.run([sys.executable, "-B", str(bundle / "scripts/routing_editor.py"), "--help"],
                                                 cwd=root, capture_output=True, text=True, timeout=10)
                    self.assertEqual(help_result.returncode, 0, help_result.stderr)
                    self.assertIn("--global-config-dir", help_result.stdout)
                    self.assertNotIn("--project", help_result.stdout)
                    for source in (source_repo / "subagents" / "routing").rglob("*"):
                        if source.is_file():
                            destination = bundle / "routing" / source.relative_to(source_repo / "subagents" / "routing")
                            self.assertEqual(destination.read_bytes(), source.read_bytes())
                    for source in (source_repo / "subagents").glob("*.md"):
                        if source.stem == NAME:
                            continue
                        self.assertEqual((bundle / "references" / source.name).read_bytes(), source.read_bytes())
                        self.assertFalse((base / "skills" / source.stem / "SKILL.md").exists())
                    references = bundle / "references"
                    self.assertEqual(len(list((source_repo / "subagents").glob("*.md"))), 11)
                    for name in RETIRED:
                        self.assertFalse((references / (name + ".md")).exists())
                        self.assertFalse((base / "skills" / name).exists())
                    self.assertEqual(list(bundle.rglob("SKILL.md")), [bundle / "SKILL.md"])
                    self.assertEqual((base / rules).read_bytes(), (source_repo / "global_rules.md").read_bytes())
                self.assertIn("allow_implicit_invocation: true", (codex / "skills" / NAME / "agents/openai.yaml").read_text(encoding="utf-8-sig"))
                self.assertEqual(preference.read_bytes(), legacy_bytes)

            if linked_agent_roots:
                for base in (claude, codex):
                    target = root / (base.name + "-target")
                    target.mkdir()
                    self.link_directory(base, target)

            run()  # Fresh install.
            for base in (claude, codex):
                for name in RETIRED:
                    reference = base / "skills" / NAME / "references" / (name + ".md")
                    reference.write_bytes(("custom reference " + name).encode())
                    standalone = base / "skills" / name
                    standalone.mkdir()
                    (standalone / "custom.txt").write_text("custom standalone " + name)
                    backup = base / "backups/orchestration-nation"
                    backup.mkdir(parents=True, exist_ok=True)
                    (backup / (name + ".md")).write_text("earlier reference")
                    (backup / name).mkdir()
                    (backup / name / "custom.txt").write_text("earlier standalone")
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
                backups = base / "backups/orchestration-nation"
                (base / "skills" / NAME / "references" / (OLD_REVIEW_REFERENCE + ".md")).write_text("custom old reference")
                (backups / (OLD_REVIEW_REFERENCE + ".md")).write_text("earlier old reference")
            worker = claude / "agents" / (WORKER + ".md")
            self.assertIn("managed worker definition", worker.read_text(encoding="utf-8"))
            worker.write_text(worker_text)
            (claude / "backups/orchestration-nation" / (WORKER + ".md")).write_text("earlier worker backup")

            if scenario == "retained_link":
                old = claude / "skills/clanker-backend-developer"
                target = root / "retained-link-target"
                old.rename(target)
                self.link_directory(old, target)

            if scenario and scenario != "retained_link":
                references = claude / "skills" / NAME / "references"
                reference = references / (RETIRED[0] + ".md")
                standalone = claude / "skills" / RETIRED[0]
                outside = root / "outside"
                outside.mkdir()
                (outside / "sentinel").write_text("outside unchanged")
                saved_reference = reference.read_bytes()
                saved_script = (source_repo / ("wrangle.ps1" if shell == "powershell" else "wrangle.sh")).read_text()
                linked = None

                if scenario in ("references_parent", "standalone_link", "backup_parent", "backup_directory", "skills_parent", "agents_link"):
                    if scenario == "references_parent":
                        original = references.with_name("references-original")
                        references.rename(original)
                        linked = references
                    elif scenario == "standalone_link":
                        original = standalone.with_name(standalone.name + "-original")
                        standalone.rename(original)
                        linked = standalone
                    elif scenario == "backup_parent":
                        linked = claude / "backups"
                        original = claude / "backups-original"
                        linked.rename(original)
                    elif scenario == "backup_directory":
                        linked = claude / "backups/orchestration-nation"
                        original = claude / "backups/orchestration-nation-original"
                        linked.rename(original)
                    elif scenario == "agents_link":
                        linked = claude / "agents"
                        original = claude / "agents-original"
                        linked.rename(original)
                    else:
                        linked = claude / "skills"
                        original = claude / "skills-original"
                        linked.rename(original)
                    self.link_directory(linked, outside)
                elif scenario == "reference_link":
                    original = reference.with_name(reference.name + ".original")
                    reference.rename(original)
                    linked = reference
                    outside_reference = outside / "retired-reference.md"
                    outside_reference.write_bytes(saved_reference)
                    try:
                        linked.symlink_to(outside_reference)
                    except OSError:
                        self.skipTest("File symlink creation unavailable")
                elif scenario in ("old_reference_link", "old_reference_directory"):
                    linked = references / (OLD_REVIEW_REFERENCE + ".md")
                    original = linked.with_name(linked.name + ".original")
                    linked.rename(original)
                    if scenario == "old_reference_link":
                        outside_old = outside / "old-reference.md"
                        outside_old.write_bytes(original.read_bytes())
                        try:
                            linked.symlink_to(outside_old)
                        except OSError:
                            self.skipTest("File symlink creation unavailable")
                    else:
                        linked.mkdir()
                elif scenario in ("worker_backup_link", "worker_backup_file"):
                    # Only the unmarked worker needs a backup: remove every retired entry first.
                    for name in RETIRED:
                        (references / (name + ".md")).unlink()
                        shutil.rmtree(claude / "skills" / name)
                    (references / (OLD_REVIEW_REFERENCE + ".md")).unlink()
                    linked = claude / "backups/orchestration-nation"
                    original = claude / "backups/orchestration-nation-original"
                    linked.rename(original)
                    if scenario == "worker_backup_link":
                        self.link_directory(linked, outside)
                    else:
                        linked.write_text("not a directory")
                elif scenario == "worker_link":
                    linked = claude / "agents" / (WORKER + ".md")
                    original = linked.with_name(linked.name + ".original")
                    linked.rename(original)
                    outside_worker = outside / "worker.md"
                    outside_worker.write_bytes(original.read_bytes())
                    try:
                        linked.symlink_to(outside_worker)
                    except OSError:
                        self.skipTest("File symlink creation unavailable")
                elif scenario == "worker_directory":
                    linked = claude / "agents" / (WORKER + ".md")
                    original = linked.with_name(linked.name + ".original")
                    linked.rename(original)
                    linked.mkdir()
                elif scenario == "reference_directory":
                    reference.unlink()
                    reference.mkdir()
                elif scenario == "standalone_file":
                    (standalone / "custom.txt").unlink()
                    standalone.rmdir()
                    standalone.write_text("unexpected file")
                elif scenario == "move_failure":
                    later_sources = {
                        path: path.read_bytes()
                        for name in RETIRED[1:]
                        for path in (references / (name + ".md"), claude / "skills" / name / "custom.txt")
                    }
                    backup_root = claude / "backups/orchestration-nation"
                    expected_backups = {
                        path.relative_to(backup_root): path.read_bytes()
                        for path in backup_root.rglob("*") if path.is_file()
                    }
                    expected_backups[Path(RETIRED[0] + "-2.md")] = saved_reference
                    expected_backups[Path(RETIRED[0] + "-2/custom.txt")] = (standalone / "custom.txt").read_bytes()
                    script = source_repo / ("wrangle.ps1" if shell == "powershell" else "wrangle.sh")
                    if shell == "powershell":
                        injection = '''function Move-Item {
    [CmdletBinding()] param([string]$LiteralPath, [string]$Destination)
    if ($LiteralPath.EndsWith("clanker-documentation-writer.md")) { throw "Injected retirement move failure: $LiteralPath" }
    Microsoft.PowerShell.Management\\Move-Item -LiteralPath $LiteralPath -Destination $Destination -ErrorAction Stop
}
'''
                        script.write_text(saved_script.replace("function Copy-SafeFile", injection + "\nfunction Copy-SafeFile", 1))
                    else:
                        injection = '''mv() {
    case "$*" in *clanker-documentation-writer.md*) echo "Injected retirement move failure: $*" >&2; return 1 ;; esac
    command mv "$@"
}
'''
                        script.write_text(saved_script.replace("set -euo pipefail\n", "set -euo pipefail\n" + injection, 1))

                (codex / "skills" / NAME / "SKILL.md").write_text("later root unchanged")
                later_steps = (claude / "CLAUDE.md", codex / "AGENTS.md", windsurf / "global_rules.md")
                for path in later_steps:
                    path.write_text("later step unchanged")
                if scenario not in ("skills_parent", "move_failure"):
                    (claude / "skills" / NAME / "SKILL.md").write_text("before preflight")
                elif scenario == "move_failure":
                    (claude / "skills" / NAME / "SKILL.md").write_text("before bundle writes")
                result = run(expected=1)
                self.assertEqual((codex / "skills" / NAME / "SKILL.md").read_text(), "later root unchanged")
                for path in later_steps:
                    self.assertEqual(path.read_text(), "later step unchanged")
                self.assertEqual((outside / "sentinel").read_text(), "outside unchanged")
                if scenario in ("references_parent", "standalone_link", "backup_parent", "backup_directory", "skills_parent", "agents_link"):
                    self.assertEqual(list(outside.iterdir()), [outside / "sentinel"])
                elif scenario == "old_reference_link":
                    self.assertEqual(outside_old.read_bytes(), original.read_bytes())
                    self.assertEqual(set(outside.iterdir()), {outside / "sentinel", outside_old})
                elif scenario == "old_reference_directory":
                    self.assertEqual(list(linked.iterdir()), [])
                elif scenario == "worker_backup_link":
                    self.assertEqual(list(outside.iterdir()), [outside / "sentinel"])
                elif scenario == "worker_backup_file":
                    self.assertEqual(linked.read_text(), "not a directory")
                elif scenario == "worker_link":
                    self.assertEqual(outside_worker.read_bytes(), original.read_bytes())
                    self.assertEqual(set(outside.iterdir()), {outside / "sentinel", outside_worker})
                    self.assertEqual(original.read_text(encoding="utf-8"), worker_text)
                elif scenario == "worker_directory":
                    self.assertEqual(list(linked.iterdir()), [])
                elif scenario == "reference_link":
                    self.assertEqual(outside_reference.read_bytes(), saved_reference)
                    self.assertEqual(set(outside.iterdir()), {outside / "sentinel", outside_reference})
                if scenario not in ("skills_parent", "move_failure"):
                    self.assertEqual((claude / "skills" / NAME / "SKILL.md").read_text(), "before preflight")
                if scenario == "move_failure":
                    self.assertIn("Injected retirement move failure", result.stdout + result.stderr)
                    self.assertFalse(reference.exists())
                    self.assertFalse(standalone.exists())
                    for path, content in later_sources.items():
                        self.assertEqual(path.read_bytes(), content)
                    actual_backups = {
                        path.relative_to(backup_root): path.read_bytes()
                        for path in backup_root.rglob("*") if path.is_file()
                    }
                    self.assertEqual(actual_backups, expected_backups)
                    self.assertEqual((claude / "skills" / NAME / "SKILL.md").read_bytes(),
                                     (source_repo / "subagents" / (NAME + ".md")).read_bytes())
                    self.assertEqual((claude / "backups/orchestration-nation" / (RETIRED[0] + "-2.md")).read_bytes(), saved_reference)
                    (source_repo / ("wrangle.ps1" if shell == "powershell" else "wrangle.sh")).write_text(saved_script)
                elif linked:
                    if linked.is_symlink() or linked.is_file():
                        linked.unlink()
                    else:
                        linked.rmdir()  # Removes the fixture junction, not its target.
                    original.rename(linked)
                    if scenario.startswith("worker_backup"):
                        for name in RETIRED:  # Put back the entries removed to isolate the worker preflight.
                            (references / (name + ".md")).write_bytes(("custom reference " + name).encode())
                            (claude / "skills" / name).mkdir()
                            (claude / "skills" / name / "custom.txt").write_text("custom standalone " + name)
                        (references / (OLD_REVIEW_REFERENCE + ".md")).write_text("custom old reference")
                elif scenario == "reference_directory":
                    reference.rmdir()
                    reference.write_bytes(saved_reference)
                elif scenario == "standalone_file":
                    standalone.unlink()
                    standalone.mkdir()
                    (standalone / "custom.txt").write_text("custom standalone " + RETIRED[0])

            run()  # Upgrade and collision backup.
            run()  # Repeat without extra backups.
            for base in (claude, codex):
                self.assertEqual((base / "skills/unrelated/SKILL.md").read_text(), "untouched")
                self.assertEqual((base / "skills" / NAME / "references/user-note.txt").read_text(), "keep note")
                retired_backups = base / "backups/orchestration-nation"
                self.assertEqual((retired_backups / (OLD_REVIEW_REFERENCE + ".md")).read_text(), "earlier old reference")
                self.assertEqual((retired_backups / (OLD_REVIEW_REFERENCE + "-2.md")).read_text(), "custom old reference")
                self.assertFalse((retired_backups / (OLD_REVIEW_REFERENCE + "-3.md")).exists())
                if base == claude:
                    self.assertEqual((retired_backups / (WORKER + ".md")).read_text(), "earlier worker backup")
                    self.assertEqual((retired_backups / (WORKER + "-2.md")).read_text(), worker_text)
                    self.assertFalse((retired_backups / (WORKER + "-3.md")).exists())
                else:
                    self.assertEqual([path.name for path in retired_backups.glob(WORKER + "*")], [])
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
                for name in RETIRED:
                    self.assertEqual((backup / (name + ".md")).read_text(), "earlier reference")
                    self.assertEqual((backup / (name + "-2.md")).read_text(), "custom reference " + name)
                    self.assertEqual((backup / name / "custom.txt").read_text(), "earlier standalone")
                    self.assertEqual((backup / (name + "-2") / "custom.txt").read_text(), "custom standalone " + name)
                    self.assertFalse((backup / (name + "-3.md")).exists())
                    self.assertFalse((backup / (name + "-3")).exists())

    def test_powershell_retirement_failures_and_recovery(self):
        for scenario in ("references_parent", "standalone_link", "backup_parent", "skills_parent", "reference_directory", "standalone_file", "move_failure"):
            with self.subTest(scenario=scenario):
                self.exercise("powershell", built=False, scenario=scenario)

    def test_bash_retirement_failures_and_recovery(self):
        for scenario in ("references_parent", "standalone_link", "backup_parent", "skills_parent", "reference_directory", "standalone_file", "move_failure"):
            with self.subTest(scenario=scenario):
                self.exercise("bash", built=False, scenario=scenario)

    def test_powershell_retained_standalone_link(self):
        self.exercise("powershell", built=False, scenario="retained_link")

    def test_bash_retained_standalone_link(self):
        self.exercise("bash", built=False, scenario="retained_link")

    def test_powershell_linked_agent_roots(self):
        for scenario in (None, "references_parent", "backup_parent", "standalone_link", "backup_directory"):
            with self.subTest(scenario=scenario):
                self.exercise("powershell", built=False, scenario=scenario, linked_agent_roots=True)

    def test_bash_linked_agent_roots(self):
        for scenario in (None, "references_parent", "backup_parent", "standalone_link", "backup_directory"):
            with self.subTest(scenario=scenario):
                self.exercise("bash", built=False, scenario=scenario, linked_agent_roots=True)

    def test_powershell_linked_retired_reference(self):
        self.exercise("powershell", built=False, scenario="reference_link")

    def test_bash_linked_retired_reference(self):
        self.exercise("bash", built=False, scenario="reference_link")

    def test_powershell_worker_definition_failures(self):
        for scenario in ("agents_link", "worker_link", "worker_directory"):
            with self.subTest(scenario=scenario):
                self.exercise("powershell", built=False, scenario=scenario)

    def test_bash_worker_definition_failures(self):
        for scenario in ("agents_link", "worker_link", "worker_directory"):
            with self.subTest(scenario=scenario):
                self.exercise("bash", built=False, scenario=scenario)

    def test_powershell_old_reference_and_worker_backup_failures(self):
        for scenario in ("old_reference_link", "old_reference_directory", "worker_backup_link", "worker_backup_file"):
            with self.subTest(scenario=scenario):
                self.exercise("powershell", built=False, scenario=scenario)

    def test_bash_old_reference_and_worker_backup_failures(self):
        for scenario in ("old_reference_link", "old_reference_directory", "worker_backup_link", "worker_backup_file"):
            with self.subTest(scenario=scenario):
                self.exercise("bash", built=False, scenario=scenario)

    def test_powershell_worker_marker_is_case_sensitive(self):
        self.exercise("powershell", built=False, worker_text=WORKER_CASE_VARIANT)

    def test_bash_worker_marker_is_case_sensitive(self):
        self.exercise("bash", built=False, worker_text=WORKER_CASE_VARIANT)

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
