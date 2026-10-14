"""Codex review launcher against a fake `codex` executable; no real Codex or model call is made."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from test_cross_review_process import process_exited

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
spec = importlib.util.spec_from_file_location("review_codex", ROOT / "subagents" / "scripts" / "codex_cross_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
core = review.core
claude_spec = importlib.util.spec_from_file_location("review_codex_claude", ROOT / "subagents" / "scripts" / "claude_cross_review.py")
claude = importlib.util.module_from_spec(claude_spec)
claude_spec.loader.exec_module(claude)

FAKE_CODEX = textwrap.dedent('''\
    #!{python}
    import json, os, subprocess, sys, time
    scenario = json.load(open(os.environ["FAKE_CODEX_SCENARIO"]))
    argv = sys.argv[1:]
    with open(os.environ["FAKE_CODEX_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps({{"argv": argv, "cwd": os.getcwd()}}) + "\\n")
    if argv == ["--version"]:
        print(scenario.get("version", "codex-cli 0.162.1"))
    elif argv == ["exec", "--help"]:
        print(scenario["help"])
    elif argv[:2] == ["doctor", "--json"]:
        print(scenario["doctor"] if isinstance(scenario["doctor"], str) else json.dumps(scenario["doctor"]))
    elif argv == ["debug", "models"]:
        print(json.dumps(scenario["models"]))
    elif argv[:1] == ["exec"]:
        prompt = sys.stdin.read()
        open(os.environ["FAKE_CODEX_PROMPT"], "w", encoding="utf-8").write(prompt)
        review = scenario["review"]
        if review.get("child_pid_file"):
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            open(review["child_pid_file"], "w").write(str(child.pid))
        if review.get("sleep"):
            time.sleep(review["sleep"])
        output = argv[argv.index("-o") + 1]
        if review.get("last_message") is not None:
            text = review["last_message"] if isinstance(review["last_message"], str) else json.dumps(review["last_message"])
            open(output, "w", encoding="utf-8").write(text)
        for event in review["events"]:
            print(event if isinstance(event, str) else json.dumps(event), flush=True)
        sys.stderr.write(review.get("stderr", ""))
        sys.exit(review.get("exit_code", 0))
    else:
        sys.stderr.write("unexpected invocation: " + " ".join(argv))
        sys.exit(64)
''')

HELP = "\n".join(("-c, --config <key=value>", "--disable <FEATURE>", "-s, --sandbox <SANDBOX_MODE>",
                  "[possible values: read-only, workspace-write, danger-full-access]", "--cd", "-m, --model <MODEL>",
                  "--ephemeral", "--output-schema <FILE>", "--json", "-o, --output-last-message <FILE>"))
EVENTS = [
    {"type": "thread.started", "thread_id": "thread-fixture"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "i1", "type": "command_execution", "command": "ls", "aggregated_output": "plan.md", "exit_code": 0, "status": "completed"}},
    {"type": "item.completed", "item": {"id": "i2", "type": "agent_message", "text": "done"}},
    {"type": "turn.completed", "usage": {"input_tokens": 3, "cached_input_tokens": 0, "cache_write_input_tokens": 0, "output_tokens": 2, "reasoning_output_tokens": 1}},
]
PAYLOAD = {"phase": "plan", "verdict": "clean", "findings": [], "limitations": [], "consulted_paths": [],
           "coverage": [{"subject": "plan.md", "status": "covered", "evidence": "Read the plan"},
                        {"subject": "R1", "status": "covered", "evidence": "Plan states R1"}]}
CLEAN_ENVIRONMENT = {name: "" for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE", "CODEX_API_KEY")}


def tree_state(root):
    return {str(path.relative_to(root)): (path.read_bytes() if path.is_file() else None) for path in sorted(root.rglob("*"))}


@unittest.skipIf(os.name == "nt", "the fake executable uses a shebang")
class CodexLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="clanker-codex-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / "plan.md").write_text("Plan evidence.\n", encoding="utf-8")
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "config.toml").write_text('model = "ambient-default"\nmodel_reasoning_effort = "low"\n', encoding="utf-8")
        self.fake = self.root / "bin" / "codex"
        self.fake.parent.mkdir()
        self.fake.write_text(FAKE_CODEX.format(python=sys.executable), encoding="utf-8")
        self.fake.chmod(0o755)
        self.log = self.root / "invocations.jsonl"
        self.prompt = self.root / "prompt.txt"
        self.scenario_path = self.root / "scenario.json"
        self.scenario = {"help": HELP, "doctor": json.loads((FIXTURES / "codex_doctor.json").read_text(encoding="utf-8")),
                         "models": json.loads((FIXTURES / "codex_models.json").read_text(encoding="utf-8")),
                         "review": {"events": EVENTS, "last_message": PAYLOAD}}
        self.environment = {**CLEAN_ENVIRONMENT, "FAKE_CODEX_SCENARIO": str(self.scenario_path), "FAKE_CODEX_LOG": str(self.log),
                            "FAKE_CODEX_PROMPT": str(self.prompt), "CODEX_HOME": str(self.codex_home)}

    def write_manifest(self, **overrides):
        manifest = {"repository": str(self.repo), "phase": "plan", "run_id": "codex", "selected_paths": ["plan.md"],
                    "requirements": ["R1"], "verification_evidence": ["Planning only"], **overrides}
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def run_review(self, *extra, manifest=None, model="gpt-6.1-sol", effort="high", environment=None, exe=True, timeout=None):
        self.scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        manifest = manifest or self.write_manifest()
        argv = ["codex_cross_review.py", "--manifest", str(manifest), "--output-dir", str(self.root / "reports")]
        if exe:
            argv += ["--codex-exe", str(self.fake)]
        if model is not None:
            argv += ["--model", model]
        if effort is not None:
            argv += ["--effort", effort]
        if timeout:
            argv += ["--timeout-seconds", str(timeout)]
        argv += list(extra)
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.dict(os.environ, {**self.environment, **(environment or {})}), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = review.main()
        return code, output.getvalue(), errors.getvalue()

    def report(self, run_id="codex", attempt="plan-1"):
        return json.loads((self.root / "reports" / run_id / attempt / "report.json").read_text(encoding="utf-8"))

    def invocations(self):
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()] if self.log.exists() else []

    def review_calls(self):
        return [item["argv"] for item in self.invocations() if item["argv"][:1] == ["exec"] and "--help" not in item["argv"]]

    def assert_no_model_call(self):
        self.assertEqual(self.review_calls(), [])

    # --- success and command contract -------------------------------------------------------
    def test_plan_review_succeeds_with_the_exact_command_and_unchanged_codex_home(self):
        before = tree_state(self.codex_home)
        code, stdout, stderr = self.run_review()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout.strip().splitlines()[-1])["execution_status"], "completed")
        directory = self.root / "reports" / "codex" / "plan-1"
        schema = directory / "packet" / "_clanker_packet" / "review-schema.json"
        expected = ["exec", "--ephemeral", "-s", "read-only", "-C", str(self.repo), "-m", "gpt-6.1-sol",
                    "-c", 'model_reasoning_effort="high"', "--disable", "multi_agent", "--output-schema", str(schema),
                    "-o", str(directory / "last-message.json"), "--json"]
        self.assertEqual(self.review_calls(), [expected])
        self.assertEqual([item["argv"] for item in self.invocations()][:4],
                         [["--version"], ["exec", "--help"], ["doctor", "--json", "-c", 'model_reasoning_effort="high"'], ["debug", "models"]])
        self.assertEqual(len(self.invocations()), 5)
        flat = " ".join(argument for item in self.invocations() for argument in item["argv"])
        for forbidden in ("login", "--dangerously", "--approve-for-me", "--ignore-user-config", "--ignore-rules", "--add-dir",
                          "--enable", "workspace-write", "danger-full-access", "--oss", "--profile", " -p "):
            self.assertNotIn(forbidden, flat)
        self.assertTrue(all(item["cwd"] == str(self.repo) or Path(item["cwd"]).resolve() == self.repo for item in self.invocations()))
        self.assertEqual(tree_state(self.codex_home), before)
        self.assertIn(str(directory / "packet"), self.prompt.read_text(encoding="utf-8"))
        report = self.report()
        self.assertEqual((report["execution_status"], report["verdict"], report["phase"]), ("completed", "clean", "plan"))
        self.assertEqual(report["reviewer"], {"provider": "codex", "execution": "external", "host": "claude",
                                              "executable": str(self.fake.resolve()), "version": "codex-cli 0.162.1"})
        self.assertEqual(report["settings"], {"requested": {"model": "gpt-6.1-sol", "effort": "high"},
                                              "observed": {"model": "unknown", "effort": "unknown"}})
        self.assertEqual(report["runtime"]["authentication"], {"logged_in": True, "method": "chatgpt", "provider": "openai"})
        self.assertEqual(report["observed_settings"], {"turns": 1, "terminal_reason": "completed", "thread_id": "thread-fixture"})
        self.assertNotIn("usage", json.dumps(report).lower().replace("usage_", ""))
        summary = (directory / "summary.md").read_text(encoding="utf-8")
        for line in ("# Codex cross-review: plan", "Reviewer: codex (external, host claude)",
                     "Requested: model gpt-6.1-sol, reasoning effort high", "Observed: model unknown, reasoning effort unknown"):
            self.assertIn(line, summary)
        progress = json.loads((directory / "progress.json").read_text(encoding="utf-8"))
        self.assertFalse([key for key in progress if key.startswith("claude_")])
        self.assertEqual((progress["reviewer_running"], progress["reviewer_exit_code"]), (False, 0))

    def test_schema_is_strict_everywhere(self):
        schema = review.review_schema("plan")

        def check(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node["additionalProperties"], False)
                    self.assertEqual(sorted(node["required"]), sorted(node["properties"]))
                self.assertNotIn("null", json.dumps(node.get("type", "")))
                for key in ("minLength", "minItems", "default", "format", "pattern"):
                    self.assertNotIn(key, node)
                for value in node.values():
                    check(value)
            elif isinstance(node, list):
                for value in node:
                    check(value)
        check(schema)
        self.assertEqual(schema["properties"]["phase"]["enum"], ["plan"])

    def test_implementation_review_with_git_baseline(self):
        for command in (["init", "-q"], ["config", "user.name", "Fixture"], ["config", "user.email", "fixture@example.invalid"]):
            subprocess.run(["git", *command], cwd=self.repo, check=True, capture_output=True)
        (self.repo / "app.py").write_text("value = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.repo, check=True, capture_output=True)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, capture_output=True, text=True).stdout.strip()
        (self.repo / "app.py").write_text("value = 2\n", encoding="utf-8")
        manifest = self.write_manifest(phase="implementation", baseline=base, selected_paths=["app.py"])
        payload = {**PAYLOAD, "phase": "implementation", "coverage": [
            {"subject": "app.py", "status": "covered", "evidence": "Read the diff"}, {"subject": "R1", "status": "covered", "evidence": "Met"}]}
        self.scenario["review"]["last_message"] = payload
        code, _out, err = self.run_review(manifest=manifest)
        self.assertEqual(code, 0, err)
        report = self.report(attempt="implementation-1")
        self.assertEqual((report["phase"], report["verdict"], report["execution_status"]), ("implementation", "clean", "completed"))
        self.assertTrue(any(item["path"] == "@git" for item in report["source_evidence"]["files"]))

    def test_schema_valid_empty_optional_lists_match_the_shared_validator(self):
        self.assertEqual(self.run_review()[0], 0)
        report = self.report()
        expected = core.validate_model_report(PAYLOAD, "plan", "Claude")
        for key in ("verdict", "coverage", "findings", "limitations", "consulted_paths"):
            self.assertEqual(report[key], expected[key])
        findings = {**PAYLOAD, "verdict": "changes_requested", "findings": [{
            "id": "F1", "severity": "major", "location": "plan.md:1", "scenario": "S", "evidence": "E", "confidence": "confirmed", "suggested_remedy": "R"}]}
        self.scenario["review"]["last_message"] = findings
        manifest = self.write_manifest(run_id="findings")
        self.assertEqual(self.run_review(manifest=manifest)[0], 0)
        self.assertEqual(self.report("findings")["findings"][0]["id"], "F1")

    def test_ambient_codex_defaults_do_not_change_the_requested_model_and_effort(self):
        before = (self.codex_home / "config.toml").read_bytes()
        self.assertEqual(self.run_review(model="gpt-6-luna", effort="xhigh")[0], 0)
        call = self.review_calls()[0]
        self.assertEqual(call[call.index("-m") + 1], "gpt-6-luna")
        self.assertIn('model_reasoning_effort="xhigh"', call)
        self.assertEqual((self.codex_home / "config.toml").read_bytes(), before)
        self.assertEqual(self.report()["settings"]["requested"], {"model": "gpt-6-luna", "effort": "xhigh"})

    # --- argument and evidence gates -----------------------------------------------------------
    def test_missing_or_blank_model_or_effort_stops_before_preflight(self):
        for kwargs in ({"effort": None}, {"model": None}, {"effort": "  "}, {"model": " "}, {"effort": " high"}):
            with self.subTest(kwargs=kwargs), mock.patch.object(review, "preflight") as preflight, self.assertRaises(SystemExit) as caught:
                self.run_review(**kwargs)
            self.assertEqual(caught.exception.code, 2)
            preflight.assert_not_called()
        self.assertEqual(self.invocations(), [])

    def test_prepare_only_and_freshness_need_no_model_effort_or_codex(self):
        manifest = self.write_manifest()
        with mock.patch.object(review, "resolve_codex", side_effect=AssertionError("prepare resolved Codex")):
            code, _out, err = self.run_review("--prepare-only", manifest=manifest, model=None, effort=None, exe=False)
        self.assertEqual(code, 0, err)
        report = self.report()
        self.assertEqual((report["execution_status"], report["reviewer"]["executable"]), ("prepared", None))
        self.assertEqual(report["settings"]["requested"], {"model": "unknown", "effort": "unknown"})
        with mock.patch.object(sys, "argv", ["codex_cross_review.py", "--check-current", str(self.root / "reports" / "codex" / "plan-1" / "report.json")]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(), 0)
        self.assertEqual(self.invocations(), [])

    def test_missing_required_evidence_blocks_before_any_codex_call(self):
        manifest = self.write_manifest(selected_paths=["plan.md", "missing.md"])
        code, _out, _err = self.run_review(manifest=manifest)
        self.assertEqual(code, 2)
        report = self.report()
        self.assertEqual((report["execution_status"], report["readiness"]["status"]), ("blocked", "blocked"))
        self.assertEqual(self.invocations(), [])

    # --- preflight -------------------------------------------------------------------------------
    def assert_blocked(self, category, fragment=None, environment=None, **kwargs):
        code, stdout, stderr = self.run_review(environment=environment, **kwargs)
        self.assertEqual(code, 2, stderr)
        report = self.report()
        self.assertEqual(report["execution_status"], "blocked", report["limitations"])
        self.assertEqual(report["diagnostic"]["category"], category)
        if fragment:
            self.assertIn(fragment, " ".join(report["limitations"]))
        self.assert_no_model_call()
        return report, stdout + stderr

    def doctor_with(self, check, **details):
        self.scenario["doctor"]["checks"][check]["details"].update(details)

    def test_api_key_and_base_url_environment_block_without_printing_values(self):
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE", "CODEX_API_KEY"):
            with self.subTest(name=name):
                self.setUp()
                report, console = self.assert_blocked("authentication", name, environment={name: "SECRET-VALUE-123"})
                self.assertNotIn("SECRET-VALUE-123", json.dumps(report) + console)

    def test_persistent_alternate_provider_and_stored_api_key_block(self):
        cases = (("config.load", {"model provider": "azure"}, "non-default model provider"),
                 ("auth.credentials", {"stored API key": "true"}, "stored API key"),
                 ("auth.credentials", {"stored auth mode": "apikey"}, "not logged in with ChatGPT"),
                 ("auth.credentials", {"stored auth mode": "none"}, "not logged in with ChatGPT"))
        for check, details, fragment in cases:
            with self.subTest(details=details):
                self.setUp()
                self.doctor_with(check, **details)
                self.assert_blocked("authentication", fragment)

    def test_missing_renamed_or_failing_doctor_fields_fail_closed(self):
        def drop(check, key):
            del self.scenario["doctor"]["checks"][check]["details"][key]

        mutations = (
            lambda: drop("auth.credentials", "stored auth mode"),
            lambda: drop("auth.credentials", "stored API key"),
            lambda: drop("config.load", "model provider"),
            lambda: self.scenario["doctor"]["checks"].pop("auth.credentials"),
            lambda: self.scenario["doctor"]["checks"].pop("config.load"),
            lambda: self.scenario["doctor"]["checks"]["auth.credentials"].update(status="error"),
            lambda: self.scenario["doctor"]["checks"]["config.load"].update(status="warning"),
            lambda: self.scenario["doctor"].update(checks=[]),
            lambda: self.scenario.update(doctor="not json"),
            lambda: self.scenario.update(doctor="[]"),
            lambda: self.scenario["doctor"]["checks"]["auth.credentials"]["details"].update({"stored auth mode ": "chatgpt"}) or drop("auth.credentials", "stored auth mode"),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                self.setUp()
                mutate()
                self.assert_blocked("authentication")

    def reachability(self):
        return self.scenario["doctor"]["checks"].setdefault("network.provider_reachability", {"details": {}})

    def test_inference_url_must_be_chatgpt_and_reachability_status_is_ignored(self):
        self.assertEqual(self.run_review()[0], 0)
        self.setUp()
        self.reachability().update(status="error")  # Offline or failing reachability does not change the host verdict.
        self.reachability()["details"]["ChatGPT inference URL"] = "https://chatgpt.com/backend-api/<redacted> connect failed (required)"
        self.assertEqual(self.run_review()[0], 0)
        cases = (
            ("ChatGPT inference URL", "https://example.invalid/backend-api/<redacted> connect failed (required)"),
            ("ChatGPT inference URL", "http://chatgpt.com/backend-api/<redacted> reachable (HTTP 405)"),
            ("ChatGPT inference URL", "https://chatgpt.com.evil.example/backend-api/ reachable"),
            ("ChatGPT inference URL", "https://user@chatgpt.com:8443/backend-api/ reachable"),
            ("ChatGPT inference URL", ""),
            ("openai API inference URL", "https://example.invalid/v1/<redacted> reachable (HTTP 404)"),
        )
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.setUp()
                self.reachability()["details"][key] = value
                self.assert_blocked("authentication", "non-ChatGPT inference endpoint")

    def test_openai_inference_key_or_missing_reachability_details_fail_closed(self):
        self.setUp()
        self.reachability()["details"]["openai API inference URL"] = "https://example.invalid/v1/<redacted> reachable (HTTP 404)"
        self.assert_blocked("authentication", "non-ChatGPT inference endpoint")
        mutations = (
            lambda: self.scenario["doctor"]["checks"].pop("network.provider_reachability"),
            lambda: self.scenario["doctor"]["checks"]["network.provider_reachability"].pop("details"),
            lambda: self.scenario["doctor"]["checks"]["network.provider_reachability"].update(details=[]),
            lambda: self.scenario["doctor"]["checks"]["network.provider_reachability"]["details"].update({"reachability mode": "API key"}),
            lambda: self.scenario["doctor"]["checks"]["network.provider_reachability"]["details"].pop("reachability mode"),
            lambda: self.scenario["doctor"]["checks"]["network.provider_reachability"]["details"].pop("ChatGPT inference URL"),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                self.setUp()
                mutate()
                self.assert_blocked("authentication", "inference")

    def test_non_inference_urls_are_ignored(self):
        self.reachability()["details"]["desktop assets CDN"] = "https://cdn.example.invalid/assets reachable"
        self.assertEqual(self.run_review()[0], 0)

    def test_missing_exec_control_blocks_with_usage_category(self):
        self.scenario["help"] = HELP.replace("--disable <FEATURE>", "")
        report, _ = self.assert_blocked("usage", "--disable")
        self.assertEqual([item["argv"] for item in self.invocations()], [["--version"], ["exec", "--help"]])

    def test_unadvertised_effort_or_model_blocks_with_the_requested_pair(self):
        self.assert_blocked("usage", "gpt-5.5 does not advertise reasoning effort high", model="gpt-5.5", effort="high")
        self.setUp()
        self.assert_blocked("model", "does not advertise the requested model gpt-nope", model="gpt-nope", effort="low")
        self.setUp()
        self.assert_blocked("usage", "not a valid reasoning effort", effort='high"; evil')

    def test_not_logged_in_preflight_never_starts_a_login_flow(self):
        self.doctor_with("auth.credentials", **{"stored auth mode": "none", "stored ChatGPT tokens": "false"})
        self.assert_blocked("authentication")
        self.assertFalse([item for item in self.invocations() if "login" in item["argv"]])

    def test_config_override_arguments_are_detected(self):
        self.assertEqual(review.config_override_conflicts(["-c", 'model_provider="x"', "-c", "foo.api_key=1", "-c", "model_providers.x.base_url=1"]),
                         ["model_provider", "foo.api_key", "model_providers.x.base_url"])
        self.assertEqual(review.config_override_conflicts(review.config_arguments("high")), [])
        self.scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        with mock.patch.dict(os.environ, self.environment), mock.patch.object(review, "config_arguments", return_value=["-c", 'model_provider="other"']):
            with self.assertRaisesRegex(review.ReviewError, "override detected: model_provider"):
                review.preflight(self.fake, "gpt-6.1-sol", "high", self.repo)
        self.assert_no_model_call()

    def test_executable_resolution_is_explicit_safe_and_never_finds_the_real_cli(self):
        with self.assertRaisesRegex(review.ReviewError, "absolute"):
            review.resolve_codex("codex")
        shim = self.root / "codex.cmd"
        shim.write_text("@echo off\n", encoding="utf-8")
        with self.assertRaisesRegex(review.ReviewError, "unsupported launch shim"):
            review.resolve_codex(str(shim))
        self.assertEqual(review.resolve_codex(str(self.fake)), self.fake.resolve())
        with mock.patch.object(review.shutil, "which", return_value=str(self.fake)):
            self.assertEqual(review.resolve_codex(None), self.fake.resolve())
        with mock.patch.object(review.shutil, "which", return_value=None), mock.patch.object(review, "native_candidates", return_value=[]):
            with self.assertRaisesRegex(review.ReviewError, "not found"):
                review.resolve_codex(None)

    # --- envelope handling ---------------------------------------------------------------------
    def assert_failed(self, fragment, status="failed", category=None):
        code, _out, stderr = self.run_review()
        self.assertEqual(code, 2, stderr)
        report = self.report()
        self.assertEqual(report["execution_status"], status, report["limitations"])
        self.assertEqual(report["verdict"], "incomplete")
        self.assertIn(fragment, " ".join(report["limitations"]))
        if category:
            self.assertEqual(report["diagnostic"]["category"], category)
        return report

    def test_malformed_or_missing_output_fails_without_a_clean_verdict(self):
        cases = (("not json", "malformed JSON"), ("[]", "must be a JSON object"), (None, "wrote no final message"),
                 ({**PAYLOAD, "verdict": "approved"}, "invalid verdict"), ({**PAYLOAD, "coverage": []}, "invalid verdict, coverage"),
                 ({**PAYLOAD, "phase": "implementation"}, "phase does not match"))
        for message, fragment in cases:
            with self.subTest(fragment=fragment):
                self.setUp()
                self.scenario["review"]["last_message"] = message
                self.assert_failed(fragment)

    def test_malformed_event_stream_or_missing_completion_fails(self):
        self.scenario["review"]["events"] = ["{not json"]
        self.assert_failed("malformed event output")
        self.setUp()
        self.scenario["review"]["events"] = EVENTS[:-1]
        self.assert_failed("no completed turn")
        self.setUp()
        self.scenario["review"]["events"] = [*EVENTS[:-1], {"type": "turn.failed", "error": {"message": "stream broke"}}]
        self.assert_failed("incomplete or failed execution envelope")

    def test_usage_limit_is_a_failed_attempt_with_a_usage_diagnostic_and_no_retry(self):
        self.scenario["review"].update(exit_code=1, events=[{"type": "error", "message": "You've hit your usage limit"}], last_message=None,
                                       stderr="ERROR: You've hit your usage limit. Try again later.\n")
        report = self.assert_failed("usage limit", status="failed", category="usage")
        self.assertEqual(len(self.review_calls()), 1)
        self.assertEqual(report["diagnostic"]["stage"], "review_execution")
        self.setUp()
        self.scenario["review"].update(events=[{"type": "turn.failed", "error": {"message": "usage limit reached"}}])
        self.assert_failed("usage limit", status="failed", category="usage")

    def test_nested_agent_events_fail_the_attempt_with_a_process_diagnostic(self):
        for item in ({"id": "x", "type": "collab_tool_call", "tool": "spawn_agent", "status": "completed"},
                     {"id": "x", "type": "mcp_tool_call", "tool": "spawn_agent", "status": "completed"}):
            with self.subTest(item=item):
                self.setUp()
                self.scenario["review"]["events"] = [*EVENTS[:-1], {"type": "item.completed", "item": item}, EVENTS[-1]]
                self.assert_failed("nested reviewer delegation", category="process")
        call = self.review_calls()[0]
        self.assertEqual(call[call.index("--disable") + 1], "multi_agent")

    def test_denials_and_unrecognized_items_are_limitations_not_failures(self):
        events = [*EVENTS[:-1],
                  {"type": "item.completed", "item": {"id": "d", "type": "command_execution", "command": "cat > /tmp/x", "aggregated_output": "Operation not permitted", "exit_code": 1, "status": "failed"}},
                  {"type": "item.completed", "item": {"id": "u", "type": "web_search", "query": "q"}},
                  {"type": "item.completed", "item": {"id": "f", "type": "file_change", "status": "failed", "changes": []}},
                  EVENTS[-1]]
        self.scenario["review"]["events"] = events
        self.assertEqual(self.run_review()[0], 0)
        limitations = " ".join(self.report()["limitations"])
        for fragment in ("denied investigation commands", "unrecognized event item type: web_search", "attempted a file change"):
            self.assertIn(fragment, limitations)
        self.assertEqual(self.report()["verdict"], "clean")

    def test_error_event_before_a_completed_turn_is_a_limitation_not_a_failure(self):
        error = {"type": "error", "message": "Reconnecting... 1/5"}
        self.scenario["review"]["events"] = [EVENTS[0], EVENTS[1], error, *EVENTS[2:]]
        self.assertEqual(self.run_review()[0], 0)
        report = self.report()
        self.assertEqual((report["execution_status"], report["verdict"]), ("completed", "clean"))
        self.assertIn("error events during the review", " ".join(report["limitations"]))
        self.assertNotIn("Reconnecting", json.dumps(report))

    def test_error_event_without_a_completed_turn_still_fails(self):
        self.scenario["review"]["events"] = [EVENTS[0], EVENTS[1], {"type": "error", "message": "stream disconnected before completion"}]
        self.assert_failed("incomplete or failed execution envelope")

    def test_stream_larger_than_one_result_completes_with_debug_capture(self):
        big = "x" * 200_000
        items = [{"type": "item.completed", "item": {"id": f"b{index}", "type": "command_execution", "command": "cat", "aggregated_output": big,
                                                     "exit_code": 0, "status": "completed"}} for index in range(6)]
        self.scenario["review"]["events"] = [*EVENTS[:2], *items, *EVENTS[2:]]
        for flags in ((), ("--debug",)):
            with self.subTest(flags=flags):
                self.setUp()
                self.scenario["review"]["events"] = [*EVENTS[:2], *items, *EVENTS[2:]]
                self.assertEqual(self.run_review(*flags)[0], 0)
                self.assertEqual(self.report()["verdict"], "clean")
        capture = self.root / "reports" / "codex" / "plan-1" / "stdout.log"
        self.assertGreater(capture.stat().st_size, 1_000_000)

    def test_completed_file_change_fails_the_attempt(self):
        change = {"type": "item.completed", "item": {"id": "f", "type": "file_change", "status": "completed", "changes": []}}
        self.scenario["review"]["events"] = [*EVENTS[:-1], change, EVENTS[-1]]
        self.assert_failed("file change during an advisory review", category="process")

    def test_reported_model_becomes_the_observed_model_and_unreported_effort_stays_unknown(self):
        self.scenario["review"]["events"] = [{"type": "thread.started", "thread_id": "t", "model": "gpt-6.1-sol"}, *EVENTS[1:]]
        self.assertEqual(self.run_review()[0], 0)
        self.assertEqual(self.report()["settings"]["observed"], {"model": "gpt-6.1-sol", "effort": "unknown"})

    def test_incomplete_required_coverage_yields_an_incomplete_verdict(self):
        self.scenario["review"]["last_message"] = {**PAYLOAD, "coverage": [{"subject": "plan.md", "status": "covered", "evidence": "Read"}]}
        self.assertEqual(self.run_review()[0], 0)
        report = self.report()
        self.assertEqual(report["verdict"], "incomplete")
        self.assertIn("Required review coverage incomplete: R1", " ".join(report["limitations"]))

    # --- containment ---------------------------------------------------------------------------
    def test_timeout_terminates_the_owned_process_tree(self):
        child_file = self.root / "child.pid"
        self.scenario["review"].update(sleep=30, child_pid_file=str(child_file))
        code, _out, _err = self.run_review(timeout=2)
        self.assertEqual(code, 2)
        report = self.report()
        self.assertEqual((report["execution_status"], report["verdict"]), ("timed_out", "incomplete"))
        events = [json.loads(line) for line in (self.root / "reports" / "codex" / "plan-1" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        requested = next(item for item in events if item["event"] == "termination_requested")
        self.assertEqual(requested["termination_reason"], "timeout")
        self.assertTrue(process_exited(requested["reviewer_pid"]))
        self.assertTrue(process_exited(int(child_file.read_text(encoding="utf-8"))))

    def test_interruption_terminates_the_owned_process_tree(self):
        child_file = self.root / "child.pid"
        self.scenario["review"].update(sleep=30, child_pid_file=str(child_file))

        def interrupt(process, prompt, timeout, log):
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.communicate(prompt, timeout=2)  # Deliver the prompt so the fake starts its child.
            raise KeyboardInterrupt

        with mock.patch.object(core, "communicate_review", side_effect=interrupt):
            code, _out, _err = self.run_review()
        self.assertEqual(code, 2)
        self.assertEqual(self.report()["execution_status"], "interrupted")
        self.assertTrue(process_exited(int(child_file.read_text(encoding="utf-8"))))

    # --- freshness and shared run directories --------------------------------------------------
    def test_changed_source_is_reported_by_check_current_without_erasing_the_verdict(self):
        self.assertEqual(self.run_review()[0], 0)
        path = self.root / "reports" / "codex" / "plan-1" / "report.json"

        def check():
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = core.check_current(path)
            return code, json.loads(output.getvalue())

        code, result = check()
        self.assertEqual((code, result["current"], result["eligible_for_parent_review"]), (0, True, True))
        (self.repo / "plan.md").write_text("Changed after capture.\n", encoding="utf-8")
        code, result = check()
        self.assertEqual((code, result["current"], result["source_changes"]["status"]), (3, False, "changed"))
        self.assertEqual(self.report()["verdict"], "clean")

    def test_claude_and_codex_attempts_in_one_run_have_distinct_identified_reports(self):
        manifest = self.write_manifest(run_id="shared")
        with mock.patch.object(sys, "argv", ["claude_cross_review.py", "--manifest", str(manifest), "--output-dir", str(self.root / "reports"), "--prepare-only"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(claude.main(), 0)
        self.assertEqual(self.run_review(manifest=manifest)[0], 0)
        first, second = self.report("shared", "plan-1"), self.report("shared", "plan-2")
        self.assertEqual((first["reviewer"]["provider"], second["reviewer"]["provider"]), ("claude", "codex"))
        self.assertEqual((first["reviewer"]["host"], second["reviewer"]["host"]), ("codex", "claude"))
        for attempt in ("plan-1", "plan-2"):
            with mock.patch.object(sys, "argv", ["x", "--check-current", str(self.root / "reports" / "shared" / attempt / "report.json")]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(review.main(), 0)


if __name__ == "__main__":
    unittest.main()
