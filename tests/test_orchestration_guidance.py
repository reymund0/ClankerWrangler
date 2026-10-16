"""Static checks for the harness-neutral coordinator, host references, and worker definition."""

from __future__ import annotations

import csv
from pathlib import Path
import re
import subprocess
import sys
import tempfile
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
        for boundary in ("supplied instruction path", "Do not delegate", "shared run log", "reply contract",
                         "restated ownership and stated revisions supersede your earlier brief"):
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

    def test_host_references_describe_thread_continuation_mechanics(self):
        claude = flat((SUBAGENTS / "hosts" / "claude" / "host.md").read_text(encoding="utf-8"))
        for fragment in ("find the worker with `ListAgents`", "send the continued assignment with `SendMessage`",
                         "keeps the model and effort it was started with", "Limit concurrent assignments to three",
                         "After a capacity rejection, do not repeat the same spawn", "message.model",
                         "compact_boundary", "subagents/agent-<id>.jsonl", "record `unknown`"):
            self.assertIn(fragment, claude, fragment)
        self.assertNotIn("start a new worker rather than assuming", claude)
        codex = flat((SUBAGENTS / "hosts" / "codex" / "host.md").read_text(encoding="utf-8"))
        for fragment in ("keeps the model and effort it was started with", "Limit concurrent assignments to three",
                         "Never copy requested settings into the observed fields"):
            self.assertIn(fragment, codex, fragment)

    def test_dispatch_procedure_resolves_once_per_workstream(self):
        usage = flat((SUBAGENTS / "routing" / "usage.md").read_text(encoding="utf-8"))
        for fragment in ("Resolve routes once per workstream, when its thread starts",
                         "Make no new resolver request for a follow-up",
                         "refers to the workstream's resolver JSON and still states the readable settings line"):
            self.assertIn(fragment, usage, fragment)


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
            "After a capacity rejection, do not repeat the same",
        )
        host = (SUBAGENTS / "hosts" / "codex" / "host.md").read_text(encoding="utf-8")
        for fragment in moved:
            self.assertIn(flat(fragment), flat(host), fragment)
            self.assertNotIn(flat(fragment), flat(self.text), fragment)
        # Reuse policy lives in the coordinator; the host reference keeps only the continuation mechanics.
        self.assertNotIn("Reuse a suitable idle", flat(host))
        self.assertIn("send the continued assignment to the workstream's idle worker through the collaboration tools", flat(host))
        self.assertIn("Reuse threads only through workstreams and reviewer rechecks", flat(self.text))

    def test_delegation_threshold(self):
        for fragment in ("fixes it has already diagnosed that it can finish in a few calls",
                         "plus its own git, OpenSpec, and log work", "logs a one-line reason",
                         "straightforward work leans to the parent and involved or demanding work to a workstream"):
            self.assertIn(fragment, flat(self.text), fragment)

    def test_workstreams_own_code_areas_and_keep_one_thread(self):
        for fragment in ("Group build work into workstreams by code area", "recorded as its file ownership",
                         "one lead role plus optional extra role checklists", "workstreams never own overlapping files",
                         "write the contract between them before dispatch", "each side is substantial enough",
                         "Each workstream has at most one thread at a time", "restates the ownership",
                         "states every spec, design, or scope revision"):
            self.assertIn(fragment, flat(self.text), fragment)

    def test_workstream_route_is_fixed_at_thread_start(self):
        for fragment in ("Resolve a workstream's route once, when its thread starts",
                         "from its lead role and the hardest tier expected in its area",
                         "Continued assignments keep the thread's model and effort",
                         "never changes a workstream's route on its own", "requires an explicit user choice",
                         "continue it, take the fix over under the delegation threshold, or ask the user"):
            self.assertIn(fragment, flat(self.text), fragment)
        self.assertNotIn("escalat", self.text.lower())

    def test_workstream_retirement(self):
        for fragment in ("Retire a thread once parent verification passes and no follow-up is pending",
                         "as `blocked` when its unfinished work is abandoned", "the run ends blocked or interrupted",
                         "A thread waiting on a user decision stays active",
                         "Leave context compaction to the host default and record it when observed",
                         "continue the retired thread if the host can still reach it", "parent-written summary"):
            self.assertIn(fragment, flat(self.text), fragment)

    def test_reviewer_recheck_and_acceptance_outside_the_parent(self):
        for fragment in ("A native reviewer performs its own single automatic recheck in the same thread",
                         "the finding IDs, the fix diff, and a request to check the changed lines for regressions",
                         "Start a fresh native review", "External cross-review rechecks keep their fresh-session behavior",
                         "run in a worker that owns the browser state", "unless the user explicitly directs the parent",
                         "The parent keeps the evidence states"):
            self.assertIn(fragment, flat(self.text), fragment)

    def test_run_log_procedure_records_settings_and_route_outcomes(self):
        for fragment in ("Model: haiku · Reasoning: Adaptive/straightforward → medium · Observed: unknown",
                         ".clanker/orchestration-ledger.csv`", "A `retire` row records the workstream's outcome",
                         "`first-pass`", "`revised`", "`rerouted`", "`blocked`", "`defect_source`",
                         "`assign-new`", "`assign-continued`", "`parent-kept`", "`followup_kind`",
                         "or write `unknown`", "orchestration host and its preference source", "never retyped from memory",
                         "from the host clock at write time", "never estimate, reconstruct, or copy a time"):
            self.assertIn(flat(fragment), flat(self.text), fragment)
        self.assertNotIn("route-outcome table", flat(self.text))

    def test_documented_ledger_append_quotes_values_into_fourteen_columns(self):
        script = re.search(r"python3 -c '([^']*)' <repo>/\.clanker/orchestration-ledger\.csv", self.text).group(1)
        detail = 'Fix R1-2, then "recheck"'
        values = ["run-1", "api", "assign-continued", "agent-1", "clanker-backend-developer",
                  "haiku/high/involved", detail, "defect", "native review", "", "", "", ""]
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "orchestration-ledger.csv"
            for _ in range(2):
                subprocess.run([sys.executable, "-c", script, str(ledger), *values], check=True)
            with ledger.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ["time", "run", "workstream", "event", "thread", "lead_role", "route", "detail",
                                   "followup_kind", "defect_source", "observed_model", "observed_effort",
                                   "final_context", "outcome"])
        self.assertEqual(len(rows), 3, "the header is written only when the file is created")
        for row in rows[1:]:
            self.assertEqual(len(row), 14)
            self.assertEqual(row[1:], values)
            self.assertRegex(row[0], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_readme_names_workstreams_and_the_same_log_paths(self):
        readme = flat((ROOT / "README.md").read_text(encoding="utf-8"))
        for fragment in ("groups build work into workstreams by code area", ".clanker/YYYY-MM-DD-orchestration-nation.md",
                         ".clanker/orchestration-ledger.csv"):
            self.assertIn(fragment, readme, fragment)
        for path in ("YYYY-MM-DD-orchestration-nation.md", ".clanker/orchestration-ledger.csv"):
            self.assertIn(path, self.text, path)

    def test_shared_cross_review_reference_replaces_the_claude_only_one(self):
        self.assertFalse((SUBAGENTS / "clanker-claude-cross-review.md").exists())
        shared = SUBAGENTS / "clanker-cross-review.md"
        fields, body = frontmatter(shared)
        self.assertEqual(fields["name"], "clanker-cross-review")
        self.assertIn("routing/host.json", body)
        self.assertIsNone(re.search(r"\bCodex\b|\bClaude\b", body.replace("`clanker-claude-cross-review.md`", "")))


if __name__ == "__main__":
    unittest.main()
