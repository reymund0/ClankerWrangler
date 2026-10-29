"""Codex CLI adapter for `cross_review.py`, used by Claude-hosted runs.

Preflight only checks that the CLI exists and is logged in; it never logs in, switches billing, or
changes Codex settings. The review runs `codex exec` in the read-only sandbox with delegated agents
disabled, and the model and reasoning effort are passed on every invocation.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
from typing import Any

from cross_review import ReviewError

NAME = "Codex"


def find_cli(explicit: str | None) -> str:
    path = explicit or shutil.which("codex")
    if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
        raise ReviewError("Codex CLI not found; install the Codex CLI or pass --cli")
    return path


def preflight(cli: str, repo: pathlib.Path) -> None:
    """Fail with the missing prerequisite; `codex login status` only reads the stored login."""
    try:
        result = subprocess.run([cli, "login", "status"], cwd=repo, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReviewError(f"Codex login status could not be checked: {error}") from error
    output = (result.stdout + result.stderr).lower()
    if result.returncode or "not logged in" in output:
        raise ReviewError("Codex CLI is not logged in; run `codex login` yourself, then retry")


def command(cli: str, repo: pathlib.Path, model: str, effort: str, schema_path: pathlib.Path,
            output_path: pathlib.Path) -> list[str]:
    """The review command; the prompt goes on standard input."""
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", effort):
        raise ReviewError(f"Codex reasoning effort {effort!r} is not a valid effort name")
    return [cli, "exec", "--ephemeral", "--sandbox", "read-only", "--cd", str(repo),
            "--model", model, "--config", f'model_reasoning_effort="{effort}"',
            "--disable", "multi_agent", "--disable", "multi_agent_v2",
            "--output-schema", str(schema_path), "--output-last-message", str(output_path), "--json", "-"]


def read_result(stdout: str, output_path: pathlib.Path) -> dict[str, Any]:
    """Read the JSONL event stream for completion, model, and usage, then the final message."""
    completed, failures, model = False, [], None
    usage: dict[str, int] = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if isinstance(event.get("model"), str) and event["model"]:
            model = event["model"]
        kind = event.get("type")
        if kind == "turn.completed":
            completed = True
            for key, value in (event.get("usage") or {}).items():
                if isinstance(value, int):
                    usage[key] = usage.get(key, 0) + value
        elif kind in ("turn.failed", "error"):
            error = event.get("error")
            failures.append(str(event.get("message") or (error.get("message") if isinstance(error, dict) else error) or kind))
    if not completed:
        detail = "; ".join(failures) or "no completed turn was reported"
        raise ReviewError(f"Codex did not complete the review; no retry. {detail}")
    try:
        text = output_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReviewError("Codex wrote no final message", status="incomplete") from error
    return {"text": text, "observed": {"model": model, "effort": None}, "usage": usage or None}
