#!/usr/bin/env python3
"""Run a read-only external cross-review and write `report.json`.

The caller writes a handoff file naming the gate, role file, criteria, base, and files to start
from; both reviewers get only its path. The core points the reviewer CLI at the handoff through a
provider adapter, with a wall-clock limit, validates the reviewer's findings, and writes an honest
report. Adapters live in `cross_review_<provider>.py` and supply CLI lookup, preflight, the
command, and event parsing.

Usage:
    cross_review.py --provider codex --phase plan|implementation|refactor --handoff handoff.md
                    --out DIR --model M --effort E [--repo DIR] [--cli PATH] [--timeout-minutes 45]
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from typing import Any

_SCRIPTS = str(pathlib.Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

DEFAULT_TIMEOUT_MINUTES = 45
PROVIDERS = ("codex",)
SEVERITIES = ("blocking", "major", "minor", "info", "proposal")
FINDING_FIELDS = ("id", "severity", "location", "summary", "remedy")

PHASES = ("plan", "implementation", "refactor")

OUTPUT_CONTRACT = (
    "Return only the JSON object defined by the output schema:\n"
    "- coverage: \"complete\" if you reviewed everything the handoff asks for, otherwise \"partial\" with the reason in "
    "limitations.\n"
    "- findings: each with an id unique in this review (F1, F2, ...), a severity, a location (path:line or "
    "artifact section), a one-paragraph summary of the problem and its failure scenario, and a suggested remedy.\n"
    "  Severities: {severities}.\n"
    "- limitations: anything you could not check.\n"
    "Return an empty findings list when you find nothing; do not invent findings.")

READ_ONLY_NOTE = (
    "This review is read-only. Do not edit files or start other agents. You may read other repository files for "
    "context; commands that write are denied, and a denial is a limitation, not a defect.")


class ReviewError(Exception):
    """A review that cannot produce findings. `status` is `failed` or `incomplete`."""

    def __init__(self, message: str, status: str = "failed"):
        super().__init__(message)
        self.status = status


def phase_severities(phase: str) -> list[str]:
    return ["proposal"] if phase == "refactor" else [s for s in SEVERITIES if s != "proposal"]


# --- Prompt -------------------------------------------------------------------------------------


def read_handoff(path: pathlib.Path) -> pathlib.Path:
    """The handoff must be a readable file; the reviewer reads it, the launcher only checks it."""
    try:
        with path.open(encoding="utf-8") as handle:
            handle.read(1)
    except (OSError, UnicodeDecodeError) as error:
        raise ReviewError(f"Handoff is not a readable file: {path} ({error})") from error
    return path.resolve()


def build_prompt(handoff: pathlib.Path, phase: str) -> str:
    return "\n\n".join([
        f"Read the handoff at {handoff} and follow it. Phase: {phase}.",
        READ_ONLY_NOTE,
        OUTPUT_CONTRACT.format(severities=", ".join(phase_severities(phase))),
        "Output schema:\n" + json.dumps(output_schema(phase), indent=2),
    ])


# --- Findings -----------------------------------------------------------------------------------


def output_schema(phase: str) -> dict[str, Any]:
    """Strict schema: every property required and no extra properties."""
    string = {"type": "string"}
    finding = {"type": "object", "additionalProperties": False, "required": list(FINDING_FIELDS),
               "properties": {**{name: string for name in FINDING_FIELDS},
                              "severity": {"type": "string", "enum": phase_severities(phase)}}}
    return {"type": "object", "additionalProperties": False, "required": ["coverage", "findings", "limitations"],
            "properties": {"coverage": {"type": "string", "enum": ["complete", "partial"]},
                           "findings": {"type": "array", "items": finding},
                           "limitations": {"type": "array", "items": string}}}


def validate_output(text: str, phase: str) -> dict[str, Any]:
    """Check reviewer output against the schema; any violation makes the review `incomplete`."""
    def invalid(reason: str) -> ReviewError:
        return ReviewError(f"Reviewer output failed validation: {reason}", status="incomplete")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise invalid("not JSON") from error
    if not isinstance(payload, dict) or set(payload) != {"coverage", "findings", "limitations"}:
        raise invalid("expected exactly coverage, findings, and limitations")
    if payload["coverage"] not in ("complete", "partial"):
        raise invalid("coverage must be complete or partial")
    limitations = payload["limitations"]
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        raise invalid("limitations must be a list of strings")
    findings = payload["findings"]
    if not isinstance(findings, list):
        raise invalid("findings must be a list")
    allowed, seen = phase_severities(phase), set()
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict) or set(finding) != set(FINDING_FIELDS):
            raise invalid(f"finding {index} must have exactly {', '.join(FINDING_FIELDS)}")
        if not all(isinstance(finding[name], str) and finding[name].strip() for name in FINDING_FIELDS):
            raise invalid(f"finding {index} has an empty or non-string field")
        if finding["severity"] not in allowed:
            raise invalid(f"finding {finding['id']} severity {finding['severity']} is not allowed in the {phase} phase")
        if finding["id"] in seen:
            raise invalid(f"duplicate finding id {finding['id']}")
        seen.add(finding["id"])
    return payload


def review_status(output: dict[str, Any]) -> str:
    if output["coverage"] != "complete":
        return "incomplete"
    return "changes_requested" if any(f["severity"] != "info" for f in output["findings"]) else "clean"


# --- Process ------------------------------------------------------------------------------------


def stop_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # Kill whatever is left in the group, including children that outlived the leader.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_process(command: list[str], cwd: pathlib.Path, stdin_text: str, timeout_seconds: float) -> tuple[str, str, int]:
    """Run the reviewer in its own process group; on timeout stop the whole group and raise."""
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", errors="replace", start_new_session=(os.name != "nt"))
    try:
        stdout, stderr = process.communicate(stdin_text, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        stop_process_tree(process)
        process.communicate()
        raise ReviewError(f"Review timed out after {timeout_seconds / 60:g} minutes; the reviewer process was stopped")
    except BaseException:
        stop_process_tree(process)
        raise
    return stdout, stderr, process.returncode


# --- Review -------------------------------------------------------------------------------------


def load_adapter(provider: str):
    if provider not in PROVIDERS:
        raise ReviewError(f"Unknown provider {provider}")
    return importlib.import_module(f"cross_review_{provider}")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run_review(provider: str, phase: str, handoff: pathlib.Path, out: pathlib.Path, model: str, effort: str,
               repo: pathlib.Path, cli: str | None = None,
               timeout_seconds: float = DEFAULT_TIMEOUT_MINUTES * 60) -> dict[str, Any]:
    """Run one review and write `out/report.json`. Always returns the report, whatever the status."""
    repo = repo.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started, clock = now(), time.monotonic()
    report: dict[str, Any] = {
        "status": "failed", "diagnostic": None, "provider": provider, "phase": phase, "handoff": str(handoff),
        "requested": {"model": model, "effort": effort}, "observed": {"model": "unknown", "effort": "unknown"},
        "usage": None, "started": started, "ended": None, "seconds": None,
        "coverage": None, "limitations": [], "findings": [],
    }
    try:
        if phase not in PHASES:
            raise ReviewError(f"Phase must be one of {', '.join(PHASES)}")
        handoff = read_handoff(handoff)
        report["handoff"] = str(handoff)
        adapter = load_adapter(provider)
        executable = adapter.find_cli(cli)
        adapter.preflight(executable, repo)
        prompt = build_prompt(handoff, phase)
        (out / "prompt.md").write_text(prompt, encoding="utf-8")
        schema_path, output_path = out / "schema.json", out / "last-message.json"
        schema_path.write_text(json.dumps(output_schema(phase), indent=2) + "\n", encoding="utf-8")
        output_path.unlink(missing_ok=True)
        command = adapter.command(executable, repo, model, effort, schema_path, output_path)
        stdout, stderr, returncode = run_process(command, repo, prompt, timeout_seconds)
        (out / "stdout.log").write_text(stdout, encoding="utf-8")
        (out / "stderr.log").write_text(stderr, encoding="utf-8")
        if returncode:
            tail = stderr.strip()[-500:] or stdout.strip()[-500:]
            raise ReviewError(f"{adapter.NAME} exited with code {returncode}; no retry. Last output: {tail}")
        result = adapter.read_result(stdout, output_path)
        report["observed"].update({k: v for k, v in result["observed"].items() if v})
        report["usage"] = result["usage"]
        output = validate_output(result["text"], phase)
        report.update(status=review_status(output), coverage=output["coverage"],
                      limitations=output["limitations"], findings=output["findings"])
    except ReviewError as error:
        report.update(status=error.status, diagnostic=str(error))
    except OSError as error:
        report.update(status="failed", diagnostic=f"{type(error).__name__}: {error}")
    report["ended"] = now()
    report["seconds"] = round(time.monotonic() - clock, 1)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def non_blank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be blank")
    return value.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a read-only external cross-review and write report.json.")
    parser.add_argument("--provider", required=True, choices=PROVIDERS)
    parser.add_argument("--phase", required=True, choices=PHASES)
    parser.add_argument("--handoff", required=True, type=pathlib.Path, help="The caller's handoff file for this round")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="Directory for report.json and the prompt")
    parser.add_argument("--model", required=True, type=non_blank, help="From the host's cross-review route")
    parser.add_argument("--effort", required=True, type=non_blank, help="From the host's cross-review route")
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--cli", help="Reviewer CLI path; defaults to the provider's CLI on PATH")
    parser.add_argument("--timeout-minutes", type=float, default=DEFAULT_TIMEOUT_MINUTES)
    args = parser.parse_args(argv)
    report = run_review(args.provider, args.phase, args.handoff, args.out, args.model, args.effort, args.repo, args.cli,
                        args.timeout_minutes * 60)
    print(f"{report['status']}: {args.out / 'report.json'}" + (f" ({report['diagnostic']})" if report["diagnostic"] else ""))
    return 0 if report["status"] in ("clean", "changes_requested") else 1


if __name__ == "__main__":
    # Run through the imported module so adapters raise the same ReviewError class this module catches.
    import cross_review
    raise SystemExit(cross_review.main())
