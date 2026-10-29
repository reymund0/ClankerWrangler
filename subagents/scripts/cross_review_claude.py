"""Claude Code CLI adapter for `cross_review.py`, used by Codex-hosted runs.

Preflight only checks that the CLI exists and is logged in; it never logs in, switches billing, or
changes Claude settings. The review runs `claude -p` with only read tools and read-only git commands
allowed, no agent tool, and every other permission request denied. The model and effort are passed
on every invocation, and the installed skills directory is added so the reviewer can read the role
file and criteria the handoff names.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
from typing import Any

from cross_review import ReviewError

NAME = "Claude"
TOOLS = "Read,Grep,Glob,Bash"
READ_ONLY_GIT = ",".join(f"Bash(git {command}:*)" for command in
                         ("diff", "status", "log", "show", "ls-files", "merge-base", "rev-parse"))


def skills_directory() -> pathlib.Path:
    return pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR", pathlib.Path.home() / ".claude")) / "skills"


def find_cli(explicit: str | None) -> str:
    path = explicit or shutil.which("claude")
    if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
        raise ReviewError("Claude Code CLI not found; install Claude Code or pass --cli")
    return path


def preflight(cli: str, repo: pathlib.Path) -> None:
    """Fail with the missing prerequisite; `claude auth status` only reads the stored login."""
    try:
        result = subprocess.run([cli, "auth", "status", "--json"], cwd=repo, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=60)
        status = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise ReviewError(f"Claude login status could not be checked: {error}") from error
    if result.returncode or not isinstance(status, dict) or not status.get("loggedIn"):
        raise ReviewError("Claude Code CLI is not logged in; run `claude auth login` yourself, then retry")


def command(cli: str, repo: pathlib.Path, model: str, effort: str, schema_path: pathlib.Path,
            output_path: pathlib.Path) -> list[str]:
    """The review command; the prompt goes on standard input and the result comes back on stdout."""
    return [cli, "-p", "--output-format", "json", "--json-schema", schema_path.read_text(encoding="utf-8"),
            "--model", model, "--effort", effort, "--tools", TOOLS, "--allowedTools", READ_ONLY_GIT,
            "--permission-mode", "dontAsk", "--no-session-persistence", "--add-dir", str(skills_directory())]


def read_result(stdout: str, output_path: pathlib.Path) -> dict[str, Any]:
    """Read the JSON result envelope for completion, model, usage, and the structured output."""
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ReviewError("Claude returned no readable result; no retry") from error
    if not isinstance(envelope, dict) or envelope.get("is_error") or envelope.get("subtype") != "success":
        detail = envelope.get("result") or envelope.get("terminal_reason") if isinstance(envelope, dict) else None
        raise ReviewError(f"Claude did not complete the review; no retry. {detail or 'no detail reported'}")
    output = envelope.get("structured_output")
    if output is None:
        raise ReviewError("Claude returned no structured output", status="incomplete")
    models = sorted(envelope.get("modelUsage") or {})
    usage = {key: value for key, value in (envelope.get("usage") or {}).items() if isinstance(value, int)}
    return {"text": output if isinstance(output, str) else json.dumps(output),
            "observed": {"model": ", ".join(models) or None, "effort": None}, "usage": usage or None}
