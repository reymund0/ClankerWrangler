#!/usr/bin/env python3
"""Run an advisory Codex CLI review from an explicit evidence manifest.

This is the Codex reviewer adapter for the shared launcher in `cross_review_core.py`:
executable resolution, ChatGPT-login preflight, command construction, and JSONL/last-message
envelope parsing. It never logs in, switches billing, edits persistent Codex settings, or
bypasses approvals or the sandbox. The model and reasoning effort are required, are applied to
this invocation only, and have no default or fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import sys
from typing import Any
from urllib.parse import urlsplit

_SCRIPTS = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import cross_review_core as core
from cross_review_core import (
    CONFIDENCES, MAX_OUTPUT_BYTES, SEVERITIES, VERDICTS, ReviewError, ReviewerAdapter, build_review_prompt,
    classify_cli_failure, cli_failure_excerpt, is_safe_executable, redact_text, run_review_process,
)


# Controls the invocation uses; each must be listed by `codex exec --help`.
REQUIRED_EXEC_CONTROLS = ("--ephemeral", "--sandbox", "--cd", "--model", "--config", "--disable",
                          "--output-schema", "--output-last-message", "--json", "read-only")
# Environment names that would change the credential source or provider; names only, never values.
OVERRIDE_ENVIRONMENT = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE", "CODEX_API_KEY")
# `-c` keys that select another provider or credential source.
OVERRIDE_CONFIG_KEYS = ("model_provider", "model_providers", "openai_base_url", "chatgpt_base_url",
                        "preferred_auth_method", "api_key", "experimental_bearer_token")
MAX_EVENT_STREAM_BYTES = 16 * MAX_OUTPUT_BYTES
BENIGN_ITEM_TYPES = {"agent_message", "reasoning", "command_execution", "todo_list"}
DELEGATION_TOKENS = ("collab", "spawn", "subagent", "sub_agent", "multi_agent")
DENIAL_PHRASES = ("permission denied", "operation not permitted", "read-only file system", "sandbox denied")
NATIVE_CANDIDATES = ("/opt/homebrew/bin/codex", "/usr/local/bin/codex")


def native_candidates() -> list[pathlib.Path]:
    candidates: list[pathlib.Path] = []
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(pathlib.Path(local) / "Programs" / "codex" / "codex.exe")
        candidates.append(pathlib.Path.home() / ".local" / "bin" / "codex.exe")
    else:
        candidates.append(pathlib.Path.home() / ".local" / "bin" / "codex")
        candidates.extend(pathlib.Path(path) for path in NATIVE_CANDIDATES)
    return candidates


def resolve_codex(explicit: str | None) -> pathlib.Path:
    candidates: list[pathlib.Path] = []
    if explicit:
        supplied = pathlib.Path(explicit)
        if not supplied.is_absolute():
            raise ReviewError("--codex-exe must be an absolute executable path")
        candidates.append(supplied)
    else:
        found = shutil.which("codex")
        if found:
            candidates.append(pathlib.Path(found))
        candidates.extend(native_candidates())
    for candidate in candidates:
        if is_safe_executable(candidate):
            return candidate.resolve()
    if explicit:
        raise ReviewError("Codex executable is missing or is an unsupported launch shim")
    raise ReviewError("Codex executable was not found on PATH or at a documented installation path")


def run_local(command: list[str], timeout: int = 20, *, cwd: pathlib.Path | None = None) -> Any:
    return core.run_local(command, timeout, cwd=cwd, label="Codex")


def config_arguments(effort: str) -> list[str]:
    """Per-invocation configuration shared by preflight (`doctor`) and the review command."""
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", effort):
        raise ReviewError("Requested Codex effort is not a valid reasoning effort name", diagnostic_category="usage")
    return ["-c", f'model_reasoning_effort="{effort}"']


def config_override_conflicts(arguments: list[str]) -> list[str]:
    conflicts = []
    for index, value in enumerate(arguments):
        if value in {"-c", "--config"} and index + 1 < len(arguments):
            key = arguments[index + 1].split("=", 1)[0].strip().lower()
            if any(key == name or key.startswith(name + ".") or key.endswith("api_key") for name in OVERRIDE_CONFIG_KEYS):
                conflicts.append(key)
    return conflicts


def _parse_json_output(result: Any, what: str, category: str) -> dict[str, Any]:
    try:
        value = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise ReviewError(f"Codex {what} output could not be read as JSON", diagnostic_category=category) from error
    if not isinstance(value, dict):
        raise ReviewError(f"Codex {what} output is not a JSON object", diagnostic_category=category)
    return value


def _doctor_details(report: dict[str, Any], check: str) -> dict[str, Any]:
    checks = report.get("checks")
    entry = checks.get(check) if isinstance(checks, dict) else None
    details = entry.get("details") if isinstance(entry, dict) else None
    if not isinstance(entry, dict) or entry.get("status") != "ok" or not isinstance(details, dict):
        raise ReviewError(f"Codex doctor did not report a passing {check} check; ChatGPT login and provider cannot be verified",
                          diagnostic_category="authentication")
    return details


def verify_doctor(result: Any) -> None:
    """Require ChatGPT login, no stored API key, and the default provider from the effective configuration."""
    report = _parse_json_output(result, "doctor", "authentication")
    auth = _doctor_details(report, "auth.credentials")
    if auth.get("stored auth mode") != "chatgpt":
        raise ReviewError("Codex is not logged in with ChatGPT; the login flow must be run by the user", diagnostic_category="authentication")
    if str(auth.get("stored API key")).lower() != "false":
        raise ReviewError("Codex reports a stored API key credential; ChatGPT login is required for review", diagnostic_category="authentication")
    config = _doctor_details(report, "config.load")
    if config.get("model provider") != "openai":
        raise ReviewError("Codex effective configuration selects a non-default model provider", diagnostic_category="authentication")
    verify_provider_urls(report)


def verify_provider_urls(report: dict[str, Any]) -> None:
    """Require every effective inference endpoint to be ChatGPT's. Reachability status is not part of the verdict."""
    checks = report.get("checks")
    entry = checks.get("network.provider_reachability") if isinstance(checks, dict) else None
    details = entry.get("details") if isinstance(entry, dict) else None
    if not isinstance(details, dict) or details.get("reachability mode") != "ChatGPT auth":
        raise ReviewError("Codex doctor did not report ChatGPT-auth provider reachability; the inference endpoint cannot be verified",
                          diagnostic_category="authentication")
    urls = {key: value for key, value in details.items() if isinstance(key, str) and key.endswith("inference URL")}
    if not urls:
        raise ReviewError("Codex doctor reported no inference URL; the inference endpoint cannot be verified", diagnostic_category="authentication")
    for key, value in urls.items():
        parsed = urlsplit(value.split()[0]) if isinstance(value, str) and value.split() else None
        try:
            port = parsed.port if parsed else None
        except ValueError:
            port = -1
        if parsed is None or parsed.scheme != "https" or parsed.hostname != "chatgpt.com" or port not in (None, 443):
            raise ReviewError("Codex effective configuration uses a non-ChatGPT inference endpoint", diagnostic_category="authentication")


def verify_model_pair(result: Any, model: str, effort: str) -> None:
    if result.returncode:
        raise ReviewError("Codex model metadata is unavailable", exit_code=result.returncode, diagnostic_category="model")
    catalog = _parse_json_output(result, "model metadata", "model")
    models = catalog.get("models")
    if not isinstance(models, list):
        raise ReviewError("Codex model metadata has no models list", diagnostic_category="model")
    entry = next((item for item in models if isinstance(item, dict) and item.get("slug") == model), None)
    if entry is None:
        raise ReviewError(f"Codex does not advertise the requested model {model}", diagnostic_category="model")
    levels = entry.get("supported_reasoning_levels")
    efforts = {item.get("effort") for item in levels if isinstance(item, dict)} if isinstance(levels, list) else set()
    if effort not in efforts:
        raise ReviewError(f"Codex model {model} does not advertise reasoning effort {effort}; unsupported combination", diagnostic_category="usage")


def preflight(executable: pathlib.Path, requested_model: str | None, requested_effort: str | None,
              repository: pathlib.Path | None = None) -> dict[str, Any]:
    """Check every prerequisite without a model call, login, or configuration change."""
    if not requested_model or not requested_effort:
        raise ReviewError("Codex review requires an explicit model and reasoning effort", diagnostic_category="usage")
    config = config_arguments(requested_effort)
    version = run_local([str(executable), "--version"], cwd=repository)
    if version.returncode:
        raise ReviewError("Codex --version failed; verify the executable is runnable", exit_code=version.returncode,
                          diagnostic_category=classify_cli_failure(version.stdout + "\n" + version.stderr))
    help_result = run_local([str(executable), "exec", "--help"], cwd=repository)
    help_text = help_result.stdout + help_result.stderr
    absent = [control for control in REQUIRED_EXEC_CONTROLS if control not in help_text]
    if help_result.returncode or absent:
        raise ReviewError("Codex lacks required review controls: " + ", ".join(absent or ["exec --help failed"]),
                          exit_code=help_result.returncode or None, diagnostic_category="usage")
    verify_doctor(run_local([str(executable), "doctor", "--json", *config], 60, cwd=repository))
    overrides = [name for name in OVERRIDE_ENVIRONMENT if os.environ.get(name)]
    overrides += config_override_conflicts(config)
    if overrides:
        raise ReviewError("Provider or API credential override detected: " + ", ".join(overrides), diagnostic_category="authentication")
    verify_model_pair(run_local([str(executable), "debug", "models"], cwd=repository), requested_model, requested_effort)
    return {
        "executable": str(executable),
        "version": redact_text(version.stdout.strip() or version.stderr.strip()),
        "authentication": {"logged_in": True, "method": "chatgpt", "provider": "openai"},
        "requested_model": requested_model,
        "requested_effort": requested_effort,
    }


def review_schema(phase: str) -> dict[str, Any]:
    """Strict output schema: every property required, no extra properties, and no nulls."""
    string = {"type": "string"}
    finding = {"type": "object", "additionalProperties": False,
               "required": ["id", "severity", "location", "scenario", "evidence", "confidence", "suggested_remedy"],
               "properties": {"id": string, "location": string, "scenario": string, "evidence": string, "suggested_remedy": string,
                              "severity": {"type": "string", "enum": sorted(SEVERITIES)},
                              "confidence": {"type": "string", "enum": sorted(CONFIDENCES)}}}
    coverage = {"type": "object", "additionalProperties": False, "required": ["subject", "status", "evidence"],
                "properties": {"subject": string, "evidence": string,
                               "status": {"type": "string", "enum": ["covered", "partial", "unreviewed"]}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["phase", "verdict", "coverage", "findings", "limitations", "consulted_paths"],
            "properties": {"phase": {"type": "string", "enum": [phase]}, "verdict": {"type": "string", "enum": sorted(VERDICTS)},
                           "coverage": {"type": "array", "items": coverage}, "findings": {"type": "array", "items": finding},
                           "limitations": {"type": "array", "items": string}, "consulted_paths": {"type": "array", "items": string}}}


PROMPT_NOTE = (
    "\nThis review runs in a read-only sandbox with ephemeral state and no approval prompts. Commands that write files, "
    "including temporary files, are denied; treat a denial as a limitation, not a defect. "
    "Return exactly the object defined by the supplied output schema: include phase and consulted_paths (empty arrays when there "
    "is nothing to list) and do not add other fields such as observed_settings.")


def review_command(executable: pathlib.Path, repository: pathlib.Path, model: str, effort: str,
                   schema_path: pathlib.Path, last_message_path: pathlib.Path) -> list[str]:
    """The complete review argument vector; the prompt is supplied on standard input."""
    return [str(executable), "exec", "--ephemeral", "-s", "read-only", "-C", str(repository), "-m", model,
            *config_arguments(effort), "--disable", "multi_agent", "--output-schema", str(schema_path),
            "-o", str(last_message_path), "--json"]


def _is_delegation(item: dict[str, Any]) -> bool:
    kind = str(item.get("type", "")).lower()
    tool = str(item.get("tool", "")).lower()
    return any(token in kind or token in tool for token in DELEGATION_TOKENS)


def parse_events(stdout: str) -> dict[str, Any]:
    """Summarize the JSONL stream: completion, failures, spawned agents, limitations, observed model."""
    summary: dict[str, Any] = {"turns_completed": 0, "failures": [], "errors": [], "limitations": [], "model": None, "thread_id": None}
    unrecognized: set[str] = set()
    denied = False
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ReviewError("Codex review returned malformed event output") from error
        if not isinstance(event, dict):
            raise ReviewError("Codex review returned malformed event output")
        kind = event.get("type")
        if isinstance(event.get("model"), str) and event["model"]:
            summary["model"] = event["model"]
        if kind == "thread.started" and isinstance(event.get("thread_id"), str):
            summary["thread_id"] = event["thread_id"]
        elif kind == "turn.completed":
            summary["turns_completed"] += 1
        elif kind in {"turn.failed", "error"}:
            error = event.get("error")
            message = event.get("message") or (error.get("message") if isinstance(error, dict) else error)
            summary["failures" if kind == "turn.failed" else "errors"].append((kind, str(message or "")))
        item = event.get("item")
        if kind in {"item.started", "item.updated", "item.completed"} and isinstance(item, dict):
            if _is_delegation(item):
                raise ReviewError("Codex reported nested reviewer delegation; this assignment does not permit nested orchestration",
                                  diagnostic_category="process")
            item_type = str(item.get("type", ""))
            if item_type == "file_change":
                if kind == "item.completed" and item.get("status") == "completed":
                    raise ReviewError("Codex reported a file change during an advisory review", diagnostic_category="process")
                summary["limitations"].append("Codex attempted a file change, which the advisory read-only review does not permit.")
            elif item_type not in BENIGN_ITEM_TYPES:
                unrecognized.add(item_type or "unknown")
            elif item_type == "command_execution" and kind == "item.completed":
                output = str(item.get("aggregated_output", "")).lower()
                if item.get("status") == "declined" or (item.get("status") == "failed" and any(phrase in output for phrase in DENIAL_PHRASES)):
                    denied = True
    if summary["errors"] and summary["turns_completed"]:
        # An error event the turn recovered from does not fail the attempt; without a completed turn it does.
        summary["limitations"].append("Codex reported error events during the review; required coverage determines review completeness.")
    if denied:
        summary["limitations"].append("Codex reported denied investigation commands; required coverage determines review completeness.")
    for item_type in sorted(unrecognized):
        summary["limitations"].append(f"Codex reported an unrecognized event item type: {item_type}")
    summary["limitations"] = list(dict.fromkeys(summary["limitations"]))
    return summary


def invoke(executable: pathlib.Path, snapshot: pathlib.Path, manifest: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    prompt, repository, _read_roots, packet_path = build_review_prompt(snapshot, manifest)
    schema_path = packet_path / "_clanker_packet" / "review-schema.json"
    schema_path.write_text(json.dumps(review_schema(manifest["phase"]), indent=2) + "\n", encoding="utf-8")
    log = getattr(args, "review_log", None)
    last_message = (log.directory if log is not None else packet_path) / "last-message.json"
    command = review_command(executable, repository, args.model, args.effort, schema_path, last_message)
    stdout, stderr, returncode = run_review_process(command, repository, prompt + PROMPT_NOTE, args, label="Codex", started_event="codex_started",
                                                    capture_limit=MAX_EVENT_STREAM_BYTES)
    if returncode:
        output = stdout + "\n" + stderr
        category = classify_cli_failure(output)
        excerpt = cli_failure_excerpt(output)
        detail = "recognized diagnostic: " + excerpt if excerpt else "no recognized diagnostic; inspect local --debug capture"
        raise ReviewError(f"Codex review exited with code {returncode}; {detail}", diagnostic_category=category, exit_code=returncode)
    if len(stdout.encode("utf-8")) > MAX_EVENT_STREAM_BYTES:
        raise ReviewError("Codex output exceeded the bounded output limit")
    events = parse_events(stdout)
    if events["failures"] or not events["turns_completed"]:
        messages = "\n".join(message for _kind, message in [*events["failures"], *events["errors"]])
        excerpt = cli_failure_excerpt(messages)
        category = classify_cli_failure(messages)
        detail = "recognized diagnostic: " + excerpt if excerpt else "no completed turn was reported"
        raise ReviewError(f"Codex returned an incomplete or failed execution envelope; {detail}", diagnostic_category=category)
    try:
        raw = last_message.read_bytes()
    except OSError as error:
        raise ReviewError("Codex review wrote no final message") from error
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ReviewError("Codex output exceeded the bounded output limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ReviewError("Codex review returned malformed JSON") from error
    validated = core.validate_model_report(payload, manifest["phase"], "Codex")
    validated["limitations"].extend(item for item in events["limitations"] if item not in validated["limitations"])
    observed: dict[str, Any] = {"turns": events["turns_completed"], "terminal_reason": "completed", "thread_id": events["thread_id"]}
    if events["model"]:
        observed["model"] = events["model"]
    validated["observed_settings"] = observed
    return validated


class CodexAdapter(ReviewerAdapter):
    provider = "codex"
    host = "claude"
    label = "Codex"
    description = "Run an advisory Codex CLI review from a JSON manifest."
    resolution_stage = "codex_resolution"
    prepare_help = "Prepare and report the local evidence packet without resolving or launching Codex"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--codex-exe")
        parser.add_argument("--model", help="Explicit review model resolved from the codex-review route; no default")
        parser.add_argument("--effort", help="Explicit reasoning effort resolved from the codex-review route; no default")

    def validate_arguments(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        for name in ("model", "effort"):
            value = getattr(args, name)
            if not value or not value.strip() or value != value.strip():
                parser.error(f"--{name} is required for review execution; resolve it from the codex-review route")

    # Look the module-level functions up at call time so they stay individually replaceable.
    def resolve_executable(self, args: argparse.Namespace) -> pathlib.Path:
        return resolve_codex(args.codex_exe)

    def preflight(self, executable: pathlib.Path, args: argparse.Namespace, repository: pathlib.Path) -> dict[str, Any]:
        return preflight(executable, args.model, args.effort, repository)

    def invoke(self, executable: pathlib.Path, snapshot: pathlib.Path, manifest: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
        return invoke(executable, snapshot, manifest, args)

    def observed(self, observed_settings: dict[str, Any]) -> dict[str, str | None]:
        return {"model": observed_settings.get("model"), "effort": observed_settings.get("effort")}

    def execution_status(self, stage: str, error: str, diagnostic: dict[str, Any]) -> str:
        # A usage or rate limit reached during the review is a failed attempt; before it, a blocked prerequisite.
        if stage == "review_execution" and diagnostic["category"] == "usage":
            return "failed"
        return super().execution_status(stage, error, diagnostic)


def main(argv: list[str] | None = None) -> int:
    return core.main(CodexAdapter(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
