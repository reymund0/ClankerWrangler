#!/usr/bin/env python3
"""Run a read-only external cross-review and write `report.json`.

The core builds the evidence packet, runs the reviewer CLI through a provider adapter with a
wall-clock limit, validates the reviewer's findings, and writes an honest report. Adapters live
in `cross_review_<provider>.py` and supply CLI lookup, preflight, the command, and event parsing.

Usage:
    cross_review.py --provider codex --manifest manifest.json --out DIR --model M --effort E
                    [--repo DIR] [--cli PATH] [--timeout-minutes 45]

Manifest (paths are relative to the repository):
    {"phase": "plan" | "implementation" | "refactor",
     "base": "<revision>",            # required for implementation and refactor
     "paths": ["selected/file", "selected/dir"],
     "focus": "optional note for the reviewer"}
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import pathlib
import re
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

PHASE_CRITERIA = {
    "plan": (
        "Review the planning artifacts (proposal, design, specs, tasks) before any code exists. Missing code is "
        "expected and is not a defect. Look for requirements that contradict each other or the design, scenarios "
        "that cannot be verified, tasks that do not cover a requirement or verify their own result, and risks the "
        "plan does not address. Do not suggest extra mechanisms, safeguards, or configuration unless the plan "
        "fails without them."),
    "implementation": (
        "Review the code changes for correctness bugs, regressions in existing behavior, requirements the change "
        "was meant to cover but does not, and security problems (input handling, secrets, access control, trust "
        "boundaries). Report a defect only with a concrete failure scenario. Do not report style preferences."),
    "refactor": (
        "Propose refactors for the changed code and code directly related to it: duplicated logic, functions doing "
        "too much, complex conditionals, unclear names, magic values, dead code, and drift from local conventions. "
        "Return improvement proposals, not defects. Each proposal needs a location and a rationale (in summary) and "
        "the change to make (in remedy)."),
}

OUTPUT_CONTRACT = (
    "Return only the JSON object defined by the output schema:\n"
    "- coverage: \"complete\" if you reviewed all the selected evidence, otherwise \"partial\" with the reason in "
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


# --- Manifest and evidence packet ---------------------------------------------------------------


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewError(f"Manifest could not be read: {error}") from error
    if not isinstance(manifest, dict):
        raise ReviewError("Manifest must be a JSON object")
    phase = manifest.get("phase")
    if phase not in PHASE_CRITERIA:
        raise ReviewError(f"Manifest phase must be one of {', '.join(PHASE_CRITERIA)}")
    paths = manifest.get("paths", [])
    if not isinstance(paths, list) or not all(isinstance(p, str) and p.strip() for p in paths):
        raise ReviewError("Manifest paths must be a list of non-empty strings")
    base = manifest.get("base")
    if phase != "plan" and not (isinstance(base, str) and base.strip()):
        raise ReviewError(f"Manifest base is required for the {phase} phase")
    if phase == "plan" and not paths:
        raise ReviewError("Manifest paths are required for the plan phase")
    focus = manifest.get("focus", "")
    if not isinstance(focus, str):
        raise ReviewError("Manifest focus must be a string")
    return {"phase": phase, "base": base, "paths": paths, "focus": focus}


def git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", stdin=subprocess.DEVNULL)
    if result.returncode:
        raise ReviewError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def fenced(text: str, language: str = "") -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{text.rstrip(chr(10))}\n{fence}\n"


def file_section(repo: pathlib.Path, path: pathlib.Path) -> str:
    relative = path.relative_to(repo).as_posix()
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return f"### {relative}\n\n(binary file, {len(data)} bytes)\n\n"
    return f"### {relative}\n\n{fenced(text)}\n"


def selected_files(repo: pathlib.Path, paths: list[str]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for entry in paths:
        path = (repo / entry).resolve()
        if not path.is_relative_to(repo):
            raise ReviewError(f"Selected path is outside the repository: {entry}")
        if path.is_dir():
            files.extend(p for p in sorted(path.rglob("*")) if p.is_file() and ".git" not in p.relative_to(repo).parts)
        elif path.is_file():
            files.append(path)
        else:
            raise ReviewError(f"Selected path does not exist: {entry}")
    return list(dict.fromkeys(files))


def build_packet(repo: pathlib.Path, manifest: dict[str, Any]) -> str:
    """The evidence: selected paths, plus committed, staged, unstaged, and untracked work against the base."""
    parts = [f"# Evidence packet\n\nPhase: {manifest['phase']}\n"]
    base = manifest["base"]
    if base:
        parts.append(f"Base: {base}\n")
    parts.append("\n## Selected paths\n\n")
    files = selected_files(repo, manifest["paths"])
    if files:
        parts.extend(file_section(repo, path) for path in files)
    else:
        parts.append("(none)\n\n")
    if base:
        git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
        for title, args in (("Committed changes since base", ("diff", f"{base}...HEAD")),
                            ("Staged changes", ("diff", "--cached")),
                            ("Unstaged changes", ("diff",))):
            diff = git(repo, *args)
            parts.append(f"## {title}\n\n" + (fenced(diff, "diff") if diff.strip() else "(none)\n") + "\n")
        untracked = [line for line in git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if line]
        parts.append("## Untracked files\n\n")
        if untracked:
            parts.extend(file_section(repo, repo / name) for name in untracked)
        else:
            parts.append("(none)\n")
    return "".join(parts)


def build_prompt(manifest: dict[str, Any], packet: str) -> str:
    phase = manifest["phase"]
    sections = [f"You are an independent reviewer. Phase: {phase}.", PHASE_CRITERIA[phase]]
    if manifest["focus"]:
        sections.append("Caller focus: " + manifest["focus"])
    sections += [READ_ONLY_NOTE, OUTPUT_CONTRACT.format(severities=", ".join(phase_severities(phase))), packet]
    return "\n\n".join(sections)


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


def run_review(provider: str, manifest_path: pathlib.Path, out: pathlib.Path, model: str, effort: str,
               repo: pathlib.Path, cli: str | None = None,
               timeout_seconds: float = DEFAULT_TIMEOUT_MINUTES * 60) -> dict[str, Any]:
    """Run one review and write `out/report.json`. Always returns the report, whatever the status."""
    repo = repo.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started, clock = now(), time.monotonic()
    report: dict[str, Any] = {
        "status": "failed", "diagnostic": None, "provider": provider, "phase": None, "base": None, "paths": [],
        "requested": {"model": model, "effort": effort}, "observed": {"model": "unknown", "effort": "unknown"},
        "usage": None, "started": started, "ended": None, "seconds": None,
        "coverage": None, "limitations": [], "findings": [],
    }
    try:
        manifest = load_manifest(manifest_path)
        report.update(phase=manifest["phase"], base=manifest["base"], paths=manifest["paths"])
        adapter = load_adapter(provider)
        executable = adapter.find_cli(cli)
        adapter.preflight(executable, repo)
        packet = build_packet(repo, manifest)
        (out / "packet.md").write_text(packet, encoding="utf-8")
        schema_path, output_path = out / "schema.json", out / "last-message.json"
        schema_path.write_text(json.dumps(output_schema(manifest["phase"]), indent=2) + "\n", encoding="utf-8")
        output_path.unlink(missing_ok=True)
        command = adapter.command(executable, repo, model, effort, schema_path, output_path)
        stdout, stderr, returncode = run_process(command, repo, build_prompt(manifest, packet), timeout_seconds)
        (out / "stdout.log").write_text(stdout, encoding="utf-8")
        (out / "stderr.log").write_text(stderr, encoding="utf-8")
        if returncode:
            tail = stderr.strip()[-500:] or stdout.strip()[-500:]
            raise ReviewError(f"{adapter.NAME} exited with code {returncode}; no retry. Last output: {tail}")
        result = adapter.read_result(stdout, output_path)
        report["observed"].update({k: v for k, v in result["observed"].items() if v})
        report["usage"] = result["usage"]
        output = validate_output(result["text"], manifest["phase"])
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
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path, help="Directory for report.json and the packet")
    parser.add_argument("--model", required=True, type=non_blank, help="From the host's cross-review route")
    parser.add_argument("--effort", required=True, type=non_blank, help="From the host's cross-review route")
    parser.add_argument("--repo", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--cli", help="Reviewer CLI path; defaults to the provider's CLI on PATH")
    parser.add_argument("--timeout-minutes", type=float, default=DEFAULT_TIMEOUT_MINUTES)
    args = parser.parse_args(argv)
    report = run_review(args.provider, args.manifest, args.out, args.model, args.effort, args.repo, args.cli,
                        args.timeout_minutes * 60)
    print(f"{report['status']}: {args.out / 'report.json'}" + (f" ({report['diagnostic']})" if report["diagnostic"] else ""))
    return 0 if report["status"] in ("clean", "changes_requested") else 1


if __name__ == "__main__":
    # Run through the imported module so adapters raise the same ReviewError class this module catches.
    import cross_review
    raise SystemExit(cross_review.main())
