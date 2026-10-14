#!/usr/bin/env python3
"""Run an advisory Claude Code review from an explicit evidence manifest.

This is the Claude reviewer adapter for the shared launcher in `cross_review_core.py`:
executable resolution, subscription preflight, command construction, and envelope parsing.
The launcher has no third-party dependencies. It captures selected evidence, checks
local prerequisites, and saves a validated report. Review instructions do not change
the user's ordinary Claude CLI permissions or guarantee that the checkout stays still.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any

_SCRIPTS = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import cross_review_core as core
# The shared names stay importable from this module for existing callers (model_discovery, tests).
from cross_review_core import *  # noqa: F401,F403
from cross_review_core import (  # noqa: F401
    _copy_evidence, _git_entry_fingerprint, _git_path_key, _packet_source_path, _reference_kind,
    _repository_git_path, _source_links,
)
from cross_review_core import (
    CONFIDENCES, MAX_OUTPUT_BYTES, SEVERITIES, VERDICTS, ReviewError, ReviewLog as CoreReviewLog,
    ReviewerAdapter, build_review_prompt, classify_cli_failure, cli_failure_excerpt, redact_text,
    run_review_process,
)


DEFAULT_REVIEW_MODEL = "opus"


class ReviewLog(CoreReviewLog):
    """Keeps mirroring reviewer progress under the existing `claude_` names."""

    legacy_prefix = "claude"


def diagnostic_for(stage: str, error: BaseException, *, category: str | None = None) -> dict[str, Any]:
    return core.diagnostic_for(stage, error, category=category, reviewer="Claude")


def validate_model_report(value: Any, phase: str) -> dict[str, Any]:
    return core.validate_model_report(value, phase, "Claude")


def native_candidates() -> list[pathlib.Path]:
    candidates: list[pathlib.Path] = []
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(pathlib.Path(local).parent / ".local" / "bin" / "claude.exe")
        candidates.append(pathlib.Path.home() / ".local" / "bin" / "claude.exe")
    else:
        candidates.append(pathlib.Path.home() / ".local" / "bin" / "claude")
    return candidates


def resolve_claude(explicit: str | None) -> pathlib.Path:
    candidates: list[pathlib.Path] = []
    if explicit:
        supplied = pathlib.Path(explicit)
        if not supplied.is_absolute():
            raise ReviewError("--claude-exe must be an absolute executable path")
        candidates.append(supplied)
    else:
        found = shutil.which("claude")
        if found:
            candidates.append(pathlib.Path(found))
        candidates.extend(native_candidates())
    for candidate in candidates:
        if is_safe_executable(candidate):
            return candidate.resolve()
    if explicit:
        raise ReviewError("Claude executable is missing or is an unsupported launch shim")
    raise ReviewError("Claude executable was not found on PATH or at the native installation path")


def run_local(command: list[str], timeout: int = 20, *, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    return core.run_local(command, timeout, cwd=cwd, label="Claude")


def configured_review_model(explicit: str | None, config_directory: str | None = None,
                            repository: pathlib.Path | None = None) -> str | None:
    config = pathlib.Path(config_directory or os.environ.get("CLAUDE_CONFIG_DIR", str(pathlib.Path.home() / ".claude")))
    settings_files = [config / "settings.json"]
    if repository is not None:
        settings_files.extend((repository / ".claude" / "settings.json", repository / ".claude" / "settings.local.json"))
    conflicts = []
    for settings_file in dict.fromkeys(path.resolve() for path in settings_files):
        if not settings_file.exists():
            continue
        settings = load_json(settings_file)
        conflicts.extend(f"{settings_file.name}:{key}" for key in ("apiKeyHelper", "anthropicApiKey", "apiKey", "baseUrl", "baseURL", "apiProvider") if settings.get(key))
        environment = settings.get("env", {})
        if not isinstance(environment, dict):
            raise ReviewError(f"Claude settings env must be an object: {settings_file.name}")
        conflicts.extend(f"{settings_file.name}:env.{key}" for key, value in environment.items() if value and provider_override(key))
    if conflicts:
        raise ReviewError("Claude settings contain provider/credential overrides: " + ", ".join(conflicts))
    model = DEFAULT_REVIEW_MODEL if explicit is None else explicit
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise ReviewError("Configured Claude model is invalid")
    return model


def provider_override(name: str) -> bool:
    return (name.startswith("ANTHROPIC_") and name not in MODEL_ENVIRONMENT_KEYS) or name in {
        "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
        "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR",
    }


def preflight(executable: pathlib.Path, requested_model: str | None, requested_effort: str | None,
              repository: pathlib.Path | None = None) -> dict[str, Any]:
    version = run_local([str(executable), "--version"], cwd=repository)
    if version.returncode:
        raise ReviewError("Claude --version failed; verify the executable is runnable", exit_code=version.returncode,
                          diagnostic_category=classify_cli_failure(version.stdout + "\n" + version.stderr))
    help_result = run_local([str(executable), "--help"], cwd=repository)
    help_text = help_result.stdout + help_result.stderr
    required_controls = ["--add-dir", "--output-format", "--json-schema"]
    if requested_model:
        required_controls.append("--model")
    if requested_effort is not None:
        required_controls.append("--effort")
    absent = [control for control in required_controls if control not in help_text]
    if help_result.returncode or absent:
        raise ReviewError("Claude lacks required review controls: " + ", ".join(absent or ["--help failed"]),
                          exit_code=help_result.returncode or None)
    if requested_effort is not None:
        effort_help = re.search(r"--effort\b[^\n]*(?:\n(?!\s*--)[^\n]*)*", help_text)
        levels = re.search(r"\(([a-z]+(?:,\s*[a-z]+)+)\)", effort_help.group(0)) if effort_help else None
        supported_efforts = {item.strip() for item in levels.group(1).split(",")} if levels else set()
        if requested_effort not in supported_efforts:
            raise ReviewError("Requested Claude effort is unsupported or its supported values cannot be verified from --help")
    overrides = sorted(name for name, value in os.environ.items() if value and provider_override(name))
    if overrides:
        raise ReviewError("Provider or API credential override detected: " + ", ".join(overrides))
    auth = run_local([str(executable), "auth", "status", "--json"], cwd=repository)
    if auth.returncode:
        raise ReviewError("Claude subscription authentication status failed", diagnostic_category="authentication", exit_code=auth.returncode)
    try:
        auth_data = json.loads(auth.stdout)
    except json.JSONDecodeError as error:
        raise ReviewError("Claude subscription authentication status is unavailable") from error
    if not isinstance(auth_data, dict) or not auth_data.get("loggedIn"):
        raise ReviewError("Claude subscription login is required; run the official Claude login flow")
    if auth_data.get("authMethod") != "claude.ai" or auth_data.get("apiProvider") != "firstParty" or auth_data.get("subscriptionType") not in {"pro", "max", "team", "enterprise"}:
        raise ReviewError("Claude authentication is not verified as first-party subscription mode")
    requested_model = configured_review_model(requested_model, auth_data.get("configDirectory"), repository)
    if requested_model and "--model" not in help_text:
        raise ReviewError("Requested Claude model is unsupported by this CLI")
    return {
        "executable": str(executable),
        "version": redact_text(version.stdout.strip() or version.stderr.strip()),
        "authentication": {"logged_in": True, "method": "claude.ai", "provider": "firstParty", "subscription_type": auth_data.get("subscriptionType")},
        "requested_model": requested_model,
        "requested_effort": requested_effort,
    }


def invoke(executable: pathlib.Path, snapshot: pathlib.Path, manifest: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    string = {"type": "string", "minLength": 1}
    finding = {key: string for key in ("id", "location", "scenario", "evidence", "suggested_remedy")}
    finding.update(severity={"enum": sorted(SEVERITIES)}, confidence={"enum": sorted(CONFIDENCES)})
    schema = {"type": "object", "required": ["verdict", "coverage", "findings", "limitations"], "properties": {
        "phase": {"enum": [manifest["phase"]]}, "verdict": {"enum": sorted(VERDICTS)},
        "coverage": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["subject", "status", "evidence"], "properties": {"subject": string, "status": {"enum": ["covered", "partial", "unreviewed"]}, "evidence": string}}},
        "findings": {"type": "array", "items": {"type": "object", "required": list(finding), "properties": finding}},
        "limitations": {"type": "array", "items": string}, "consulted_paths": {"type": "array", "items": string}}}
    prompt, repository, read_roots, packet_path = build_review_prompt(snapshot, manifest)
    command = [str(executable)]
    for directory in [packet_path, *read_roots]:
        command.extend(["--add-dir", str(directory)])
    command.extend(["--output-format", "json", "--json-schema", json.dumps(schema, separators=(",", ":"))])
    if args.model:
        command.extend(["--model", args.model])
    if args.effort:
        command.extend(["--effort", args.effort])
    command.append("-p")
    stdout, stderr, returncode = run_review_process(command, repository, prompt, args, label="Claude", started_event="claude_started")
    if returncode:
        output = stdout + "\n" + stderr
        category = classify_cli_failure(output)
        excerpt = cli_failure_excerpt(output)
        detail = "recognized diagnostic: " + excerpt if excerpt else "no recognized diagnostic; inspect local --debug capture"
        raise ReviewError(f"Claude review exited with code {returncode}; {detail}", diagnostic_category=category, exit_code=returncode)
    if len(stdout.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ReviewError("Claude output exceeded the bounded output limit")
    try:
        outer = json.loads(stdout)
        if not isinstance(outer, dict) or outer.get("is_error") is not False or outer.get("subtype") != "success" or outer.get("terminal_reason") not in {None, "completed"} or not isinstance(outer.get("subagent_stats", {}), dict):
            raise ReviewError("Claude returned an incomplete or restricted execution envelope")
        if outer.get("subagent_stats", {}).get("spawned", 0):
            raise ReviewError("Claude reported nested reviewer delegation; this assignment does not permit nested orchestration",
                              diagnostic_category="process")
        denials = outer.get("permission_denials")
        payload = outer.get("structured_output")
        payload = json.loads(payload) if isinstance(payload, str) else payload
    except (json.JSONDecodeError, KeyError) as error:
        raise ReviewError("Claude review returned malformed JSON") from error
    validated = validate_model_report(payload, manifest["phase"])
    if denials:
        validated["limitations"].append("Claude reported denied investigation permissions; required coverage determines review completeness.")
    if isinstance(outer, dict):
        validated["observed_settings"] = {"model_usage": outer.get("modelUsage"), "turns": outer.get("num_turns"), "terminal_reason": outer.get("terminal_reason")}
    else:
        validated["observed_settings"] = {}
    return validated


class ClaudeAdapter(ReviewerAdapter):
    provider = "claude"
    host = "codex"
    label = "Claude"
    description = "Run an advisory Claude Code review from a JSON manifest."
    resolution_stage = "claude_resolution"
    prepare_help = "Prepare and report the local evidence packet without resolving or launching Claude"

    def new_log(self, directory: pathlib.Path, debug: bool) -> ReviewLog:
        return ReviewLog(directory, debug)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--claude-exe")
        parser.add_argument("--model", default=DEFAULT_REVIEW_MODEL, help="Review model override (default: opus)")
        parser.add_argument("--effort", help="Explicit review effort selected from scope/risk or user override; no default")

    def validate_arguments(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        if not args.effort or not args.effort.strip():
            parser.error("--effort is required for review execution; select it from scope/risk or a user override")

    # Look the module-level functions up at call time so they stay individually replaceable.
    def resolve_executable(self, args: argparse.Namespace) -> pathlib.Path:
        return resolve_claude(args.claude_exe)

    def preflight(self, executable: pathlib.Path, args: argparse.Namespace, repository: pathlib.Path) -> dict[str, Any]:
        return preflight(executable, args.model, args.effort, repository)

    def invoke(self, executable: pathlib.Path, snapshot: pathlib.Path, manifest: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
        return invoke(executable, snapshot, manifest, args)

    def observed(self, observed_settings: dict[str, Any]) -> dict[str, str | None]:
        usage = observed_settings.get("model_usage")
        models = sorted(usage) if isinstance(usage, dict) else []
        return {"model": ", ".join(models) or None, "effort": None}


def main(argv: list[str] | None = None) -> int:
    return core.main(ClaudeAdapter(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
