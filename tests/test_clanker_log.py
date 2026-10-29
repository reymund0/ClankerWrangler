"""Tests for the run log helper (`clanker_log.py`) and the routes template it reads."""

import contextlib
import csv
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "subagents" / "scripts"))

import clanker_log  # noqa: E402

TEMPLATE = ROOT / "subagents" / "hosts" / "claude" / "routes.jsonc"


class LogTestCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = pathlib.Path(temp.name)

    def start(self, chat="implementation", routes=TEMPLATE, change="demo"):
        return clanker_log.start(self.repo, chat, "claude", change, routes, "opus/high")

    def event(self, run, **event):
        self.assertEqual(clanker_log.main(["event", "--repo", str(self.repo), "--run", run, json.dumps(event)]), 0)

    def state(self, run):
        return clanker_log.replay(clanker_log.read_events(clanker_log.log_path(self.repo, run)))

    def rows(self, name):
        with (self.repo / ".clanker" / name).open(newline="") as handle:
            return list(csv.DictReader(handle))


class RoutesTests(LogTestCase):
    def test_template_parses_with_comment_lines_dropped(self):
        routes = clanker_log.read_routes(TEMPLATE, "claude", clanker_log.ROLES)
        self.assertEqual(set(routes), set(clanker_log.ROLES))
        self.assertIn("//", TEMPLATE.read_text())

    def test_invalid_routes_block_with_file_and_key(self):
        path = self.repo / "routes.jsonc"
        cases = [("{not json", "not valid JSON"),
                 ('{"host": "codex", "roles": {}}', "`host`"),
                 ('{"host": "claude", "roles": {"cross-review": {"model": "m", "effort": "e"}}}', "`roles.reviewer`"),
                 ('{"host": "claude", "roles": {"reviewer": {"model": "", "effort": "e"}, '
                  '"cross-review": {"model": "m", "effort": "e"}}}', "`roles.reviewer`")]
        for text, message in cases:
            path.write_text(text)
            with self.assertRaisesRegex(clanker_log.LogError, message):
                self.start(chat="design", routes=path)
        self.assertFalse((self.repo / ".clanker" / "runs").exists() and any((self.repo / ".clanker" / "runs").iterdir()))

    def test_design_chat_needs_only_review_routes(self):
        path = self.repo / "routes.jsonc"
        path.write_text('{"host": "claude", "roles": {"reviewer": {"model": "s", "effort": "high"}, '
                        '"cross-review": {"model": "g", "effort": "high"}}}')
        run = self.start(chat="design", routes=path)
        self.assertEqual(set(self.state(run)["routes"]), {"reviewer", "cross-review"})

    def test_resume_keeps_routes_recorded_at_start(self):
        path = self.repo / "routes.jsonc"
        path.write_text(TEMPLATE.read_text())
        run = self.start(routes=path)
        path.write_text(TEMPLATE.read_text().replace('"haiku"', '"opus"'))
        self.assertEqual(self.state(run)["routes"]["implementor"]["model"], "haiku")


class RunLogTests(LogTestCase):
    def test_append_never_rewrites_earlier_lines(self):
        run = self.start()
        path = clanker_log.log_path(self.repo, run)
        self.assertRegex(run, r"^\d{8}-\d{6}-demo$")
        first = path.read_text()
        self.event(run, type="round-start", gate="code", round=1)
        self.assertTrue(path.read_text().startswith(first))
        self.assertEqual([json.loads(line)["type"] for line in path.read_text().splitlines()], ["start", "round-start"])

    def test_event_rejects_unknown_type_and_unstarted_run(self):
        run = self.start()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(clanker_log.main(["event", "--repo", str(self.repo), "--run", run, '{"type": "note"}']), 1)
            self.assertEqual(clanker_log.main(["event", "--repo", str(self.repo), "--run", "missing",
                                               '{"type": "usage", "role": "reviewer"}']), 1)
        self.assertFalse(clanker_log.log_path(self.repo, "missing").exists())

    def test_replay_after_clean_round(self):
        run = self.start()
        self.event(run, type="round-start", gate="code", round=1)
        self.event(run, type="round-end", gate="code", round=1, native="clean", cross="clean")
        state = self.state(run)
        self.assertEqual((state["gate"], state["round"], state["round_open"]), ("code", 1, False))
        self.assertEqual((state["open_findings"], state["pending_decisions"]), ([], []))

    def test_replay_with_pending_user_decision(self):
        run = self.start()
        self.event(run, type="round-start", gate="code", round=1)
        self.event(run, type="finding", gate="code", round=1, id="N1", source="both", severity="major", summary="S")
        self.event(run, type="triage", gate="code", round=1, id="N1", triage="user-decision", reason="adds a cache")
        self.event(run, type="round-end", gate="code", round=1, native="changes_requested", cross="changes_requested")
        state = self.state(run)
        self.assertEqual([f["id"] for f in state["pending_decisions"]], ["N1"])
        self.event(run, type="user-decision", gate="code", round=1, id="N1", decision="take")
        state = self.state(run)
        self.assertEqual(state["pending_decisions"], [])
        self.assertEqual([f["id"] for f in state["open_findings"]], ["N1"])

    def test_fresh_code_gate_after_functional_cycle(self):
        run = self.start()
        for gate, number in (("code", 1), ("code", 2), ("functional", 1), ("code", 3), ("functional", 2)):
            self.event(run, type="round-start", gate=gate, round=number)
            self.event(run, type="round-end", gate=gate, round=number, native="clean", cross="clean")
        self.event(run, type="round-start", gate="code", round=4)
        state = self.state(run)
        self.assertEqual((state["rounds"]["code"], state["gate_rounds"], state["functional_cycles"]), (4, 1, 1))


class FinalRowsTests(LogTestCase):
    def test_finish_creates_headers_and_appends_final_rows(self):
        run = self.start()
        self.event(run, type="round-start", gate="code", round=1)
        self.event(run, type="finding", gate="code", round=1, id="N1", source="cross", severity="minor",
                   summary='Has "quotes", commas')
        self.event(run, type="triage", gate="code", round=1, id="N1", triage="accept")
        self.event(run, type="fixed", gate="code", round=1, id="N1", by="orchestrator")
        self.event(run, type="finding", gate="code", round=1, id="N2", source="native", severity="info", summary="S")
        self.event(run, type="triage", gate="code", round=1, id="N2", triage="reject", reason="Not reproducible")
        self.event(run, type="usage", role="reviewer", tokens=1200, model="sonnet", effort="high")
        self.event(run, type="usage", role="cross-review", seconds=124.3)
        clanker_log.finish(self.repo, run, "done", "note")
        [row] = self.rows("runs.csv")
        self.assertEqual(list(row), list(clanker_log.RUNS_COLUMNS))
        self.assertEqual((row["outcome"], row["code_rounds"], row["small_fixes_by_orchestrator"]), ("done", "1", "1"))
        self.assertEqual(row["reviewer_model"], "sonnet/high")
        self.assertEqual(row["implementor_model"], "haiku/medium (req)")
        self.assertEqual((row["cross_review_seconds"], row["cross_review_tokens"]), ("124.3", ""))
        findings = self.rows("findings.csv")
        self.assertEqual(list(findings[0]), list(clanker_log.FINDINGS_COLUMNS))
        self.assertEqual([(f["id"], f["triage"], f["fixed_by"], f["reason"]) for f in findings],
                         [("N1", "accept", "orchestrator", ""), ("N2", "reject", "", "Not reproducible")])
        self.assertEqual(findings[0]["summary"], 'Has "quotes", commas')
        second = self.start(change="other")
        clanker_log.finish(self.repo, second, "small-job-declined")
        self.assertEqual([r["run"] for r in self.rows("runs.csv")], [run, second])
        with self.assertRaisesRegex(clanker_log.LogError, "already ended"):
            clanker_log.finish(self.repo, second, "done")

    def test_mismatched_header_is_refused(self):
        (self.repo / ".clanker").mkdir()
        (self.repo / ".clanker" / "runs.csv").write_text("run,old\n")
        run = self.start()
        with self.assertRaisesRegex(clanker_log.LogError, "header"):
            clanker_log.finish(self.repo, run, "done")


if __name__ == "__main__":
    unittest.main()
