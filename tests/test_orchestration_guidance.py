"""Static checks for the harness-neutral coordinator, host references, and worker definition."""

from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUBAGENTS = ROOT / "subagents"
sys.path.insert(0, str(SUBAGENTS / "scripts"))
import routing_policy as policy


def flat(text):
    """Collapse line wrapping so assertions do not depend on where lines break."""
    return " ".join(text.split())


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise AssertionError(f"{path} has no frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, text[match.end():]


class WorkerDefinitionTests(unittest.TestCase):
    def test_worker_is_generic_and_cannot_delegate(self):
        fields, body = frontmatter(SUBAGENTS / "claude" / "clanker-orchestration-worker.md")
        self.assertEqual(set(fields), {"name", "description", "disallowedTools"})
        self.assertEqual(fields["name"], "clanker-orchestration-worker")
        self.assertEqual(fields["disallowedTools"], "Agent")
        self.assertTrue(fields["description"].startswith("Clanker Orchestration Nation assignments only"))
        for forbidden in ("model", "effort", "tools"):
            self.assertNotIn(forbidden, fields)
        self.assertIn("<!-- clanker-orchestration-nation: managed worker definition -->", body)
        for boundary in ("supplied instruction path", "Do not delegate", "shared run log", "reply contract"):
            self.assertIn(boundary, body)


class HostConfigurationTests(unittest.TestCase):
    def test_shipped_host_files_validate_and_match_the_policy(self):
        bundle = policy.load_bundle()
        for host, interaction, launcher in (("codex", "claude-review", "scripts/claude_cross_review.py"),
                                            ("claude", "codex-review", "scripts/codex_cross_review.py")):
            config = policy.load_host_config(SUBAGENTS / "hosts" / host / "host.json", bundle)
            self.assertEqual((config["host"], config["external_review"]),
                             (host, {"interaction": interaction, "launcher": launcher}))
            self.assertEqual(config["preferences_file"], policy.HOST_PREFERENCE_FILES[host])
            self.assertTrue((SUBAGENTS / launcher).exists(), launcher)

    def test_claude_host_blocks_a_missing_worker_and_runs_the_reviewer_in_the_background(self):
        claude = flat((SUBAGENTS / "hosts" / "claude" / "host.md").read_text(encoding="utf-8"))
        for fragment in ("If the installed definition itself is absent, block Claude-native dispatch",
                         "do not substitute another agent type",
                         "compare any project, `--agents`, or managed definition against `subagents/claude/clanker-orchestration-worker.md`",
                         "as a background command (the Bash tool's `run_in_background`)", "collect its receipt when it completes",
                         "Never run it in the foreground", "2 minutes by default (10 minutes at most)", "2700-second default"):
            self.assertIn(fragment, claude, fragment)
        shared = flat((SUBAGENTS / "clanker-cross-review.md").read_text(encoding="utf-8"))
        self.assertIn("never foreground a review that can outlast the host's command timeout", shared)

    def test_host_references_cover_their_procedures(self):
        codex = (SUBAGENTS / "hosts" / "codex" / "host.md").read_text(encoding="utf-8")
        for fragment in ("native Codex collaboration tools", "empty history fork", "Limit concurrent assignments to three",
                         "scripts/claude_cross_review.py", "subscription login", "reasoning-effort"):
            self.assertIn(flat(fragment), flat(codex), fragment)
        claude = (SUBAGENTS / "hosts" / "claude" / "host.md").read_text(encoding="utf-8")
        for fragment in ("Agent tool", "subagent_type: clanker-orchestration-worker", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
                         "CLAUDE_CODE_EFFORT_LEVEL", "agent.spawn", "byte-identical", "`--agents`", ".claude/agents/clanker-orchestration-worker.md",
                         "Never translate an exact ID", "ChatGPT", "OPENAI_API_KEY", "unknown unless the runtime reports"):
            self.assertIn(flat(fragment), flat(claude), fragment)


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.text = (SUBAGENTS / "clanker-orchestration-nation.md").read_text(encoding="utf-8")

    def test_coordinator_names_no_harness_and_requires_host_files(self):
        stripped = self.text.replace("Claude Design", "")
        self.assertIsNone(re.search(r"Codex|Claude", stripped), "coordinator must stay harness-neutral")
        for fragment in ("references/host.md", "routing/host.json", "dispatch no worker", "Do not infer the host", "clanker-cross-review.md"):
            self.assertIn(fragment, flat(self.text), fragment)

    def test_moved_dispatch_text_lives_in_the_codex_host_reference(self):
        moved = (
            "Prefer an empty history fork with a focused assignment",
            "A full-history fork inherits parent settings and must not be",
            "Reuse a suitable idle",
            "After a capacity rejection, do not repeat the same",
        )
        host = (SUBAGENTS / "hosts" / "codex" / "host.md").read_text(encoding="utf-8")
        for fragment in moved:
            self.assertIn(flat(fragment), flat(host), fragment)
            self.assertNotIn(flat(fragment), flat(self.text), fragment)

    def test_run_log_procedure_records_settings_and_route_outcomes(self):
        for fragment in ("Model: haiku · Reasoning: Adaptive/straightforward → medium · Observed: unknown", "route-outcome table",
                         "`first-pass`", "`revised`", "`rerouted`", "`blocked`", "orchestration host and its preference source",
                         "never retyped from memory"):
            self.assertIn(flat(fragment), flat(self.text), fragment)

    def test_shared_cross_review_reference_replaces_the_claude_only_one(self):
        self.assertFalse((SUBAGENTS / "clanker-claude-cross-review.md").exists())
        shared = SUBAGENTS / "clanker-cross-review.md"
        fields, body = frontmatter(shared)
        self.assertEqual(fields["name"], "clanker-cross-review")
        self.assertIn("routing/host.json", body)
        self.assertIsNone(re.search(r"\bCodex\b|\bClaude\b", body.replace("`clanker-claude-cross-review.md`", "")))


if __name__ == "__main__":
    unittest.main()
