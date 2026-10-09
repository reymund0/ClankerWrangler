#!/usr/bin/env python3
"""Run an advisory Claude Code review from an explicit evidence manifest.

The launcher has no third-party dependencies. It captures selected evidence, checks
local prerequisites, and saves a validated report. Review instructions do not change
the user's ordinary Claude CLI permissions or guarantee that the checkout stays still.
"""

from __future__ import annotations

import argparse
import codecs
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 2700
DEFAULT_REVIEW_MODEL = "opus"
MODEL_ENVIRONMENT_KEYS = {
    "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}
MAX_OUTPUT_BYTES = 1_000_000
HEARTBEAT_SECONDS = 30
FORMER_FILE_INPUT_BYTES = 1_000_000
FORMER_PACKET_INPUT_BYTES = 8 * MAX_OUTPUT_BYTES
SPLIT_WARNING_BYTES = 2 * MAX_OUTPUT_BYTES
SPLIT_WARNING_SUBJECTS = 40
PHASES = {"plan", "implementation"}
STATUSES = {"prepared", "completed", "blocked", "failed", "timed_out", "interrupted", "stale"}
VERDICTS = {"clean", "changes_requested", "incomplete"}
SEVERITIES = {"blocking", "major", "minor", "info"}
CONFIDENCES = {"confirmed", "plausible"}


class ReviewError(Exception):
    """An expected, sanitized failure that should become a report."""

    def __init__(self, message: str, *, diagnostic_category: str | None = None, exit_code: int | None = None, exception_type: str | None = None):
        super().__init__(message)
        self.diagnostic_category = diagnostic_category
        self.exit_code = exit_code
        self.exception_type = exception_type


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


class ReviewLog:
    """Persist content-free progress before the final report is available."""

    def __init__(self, directory: pathlib.Path, debug: bool):
        self.directory = directory
        self.started = time.monotonic()
        self.paths = {"events": str(directory / "events.jsonl"), "progress": str(directory / "progress.json")}
        if debug:
            self.paths.update(stdout=str(directory / "stdout.log"), stderr=str(directory / "stderr.log"))
            (directory / ".gitignore").write_text("stdout.log\nstderr.log\n", encoding="utf-8")
        (directory / "events.jsonl").touch(exist_ok=False)
        self.progress: dict[str, Any] = {"launcher_pid": os.getpid(), "claude_pid": None,
            "claude_running": False, "stdout_bytes": 0, "stderr_bytes": 0, "last_output_at": None,
            "logs": self.paths}
        self.event("started", stage="filesystem_preparation")

    def event(self, event: str, **fields: Any) -> None:
        timestamp = utc_now()
        self.progress.update(fields, updated_at=timestamp, elapsed_seconds=round(time.monotonic() - self.started, 3))
        record = {"event": event, **self.progress}
        # Each append is closed/flushed immediately, including before model launch.
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, sort_keys=True) + "\n")
        pending = self.directory / "progress.pending"
        pending.write_text(json.dumps(self.progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pending.replace(self.directory / "progress.json")

    def output(self, stdout: str | bytes | None, stderr: str | bytes | None, **fields: Any) -> None:
        counts = {}
        for name, value in (("stdout", stdout), ("stderr", stderr)):
            if name in self.paths:
                path = pathlib.Path(self.paths[name])
                counts[name + "_bytes"] = path.stat().st_size if path.exists() else 0
            else:
                counts[name + "_bytes"] = len(value.encode("utf-8") if isinstance(value, str) else value or b"")
        if any(counts[key] > self.progress[key] for key in counts):
            fields["last_output_at"] = utc_now()
        if isinstance(fields.get("claude_exit_code"), int):
            fields["claude_exit_code_hex"] = f"0x{fields['claude_exit_code'] & 0xFFFFFFFF:08X}"
        self.event("process_progress", **counts, **fields)


def read_capture(path: pathlib.Path, *, tail: bool = False) -> str:
    """Read a bounded result or diagnostic sample from an opt-in raw capture."""
    with path.open("rb") as source:
        first = source.read(MAX_OUTPUT_BYTES + 1)
        if tail and len(first) > MAX_OUTPUT_BYTES:
            source.seek(max(0, path.stat().st_size - MAX_OUTPUT_BYTES))
            first = first[:MAX_OUTPUT_BYTES] + b"\n" + source.read(MAX_OUTPUT_BYTES)
    return first.decode("utf-8", errors="replace")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReviewError("Cannot read valid JSON input") from error
    if not isinstance(value, dict):
        raise ReviewError("JSON input must contain an object")
    return value

def safe_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", value):
        raise ReviewError(f"{label} must use only letters, numbers, dot, underscore, or dash")
    return value


def finite_positive(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def raw_reference(root: pathlib.Path, reference: str) -> pathlib.Path:
    if not isinstance(reference, str) or not reference.strip() or reference in {".", ".."}:
        raise ReviewError("Path must name an evidence file")
    candidate = pathlib.Path(reference)
    if not candidate.is_absolute() and (".." in candidate.parts or any(char in reference for char in (":", "*", "?", "\x00"))):
        raise ReviewError("Path is not a safe repository-relative file")
    return candidate if candidate.is_absolute() else root / candidate


def resolve_reference(root: pathlib.Path, reference: str) -> pathlib.Path:
    """Resolve an explicitly selected file while retaining its original identity."""
    raw = raw_reference(root, reference)
    resolved = raw.resolve()
    if resolved.is_dir():
        raise ReviewError("Evidence path must be a file, not a directory")
    return resolved


def resolve_under(root: pathlib.Path, relative: str) -> pathlib.Path:
    """Retain the legacy strict repository-only resolution contract."""
    if not isinstance(relative, str) or not relative or relative in {".", ".."}:
        raise ReviewError("Path must name a repository-relative file")
    candidate = pathlib.Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or any(char in relative for char in (":", "*", "?", "\x00")):
        raise ReviewError("Path is not a safe repository-relative file")
    raw = root / candidate
    resolved = raw.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ReviewError("Path escapes repository") from error
    for ancestor in (raw, *raw.parents):
        if ancestor == root:
            break
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            raise ReviewError("Linked evidence paths are unsupported")
    if resolved == root.resolve() or resolved.is_dir():
        raise ReviewError("Evidence path must be a file, not a directory")
    return resolved


def exclusion_matches(root: pathlib.Path, reference: str, exclusions: list[dict[str, Any]]) -> bool:
    def normalized(value: str) -> str:
        path = pathlib.Path(value)
        if not path.is_absolute():
            path = root / path
        result = os.path.normpath(str(path.absolute())).replace("\\", "/")
        return result.casefold() if os.name == "nt" else result

    candidate = normalized(reference).rstrip("/")
    for item in exclusions:
        prefix = normalized(item["path"]).rstrip("/")
        if candidate == prefix or candidate.startswith(prefix + "/"):
            return True
    return False


def required_mapped_paths(manifest: dict[str, Any]) -> set[str]:
    mapped = {path for paths in manifest.get("requirement_paths", {}).values() for path in paths}
    return set(manifest.get("required_context_paths", [])) | mapped

def validate_manifest(manifest: dict[str, Any]) -> tuple[pathlib.Path, str, str, list[str]]:
    if not isinstance(manifest.get("repository"), str):
        raise ReviewError("Manifest repository must be a directory path")
    repository = pathlib.Path(manifest["repository"]).resolve()
    if not repository.is_dir():
        raise ReviewError("Manifest repository is not a directory")
    phase = manifest.get("phase")
    if not isinstance(phase, str) or phase not in PHASES:
        raise ReviewError("Manifest phase must be plan or implementation")
    run_id = safe_identifier(manifest.get("run_id"), "run_id")
    for field in ("selected_paths", "context_paths", "guidance_paths", "requirements", "verification_evidence", "required_context_paths"):
        value = manifest.get(field, [])
        if not isinstance(value, list) or len(value) > 500 or any(not isinstance(item, str) or not item.strip() or len(item) > 10000 for item in value):
            raise ReviewError(f"Manifest {field} must be a bounded list of nonempty strings")
        if field in {"selected_paths", "requirements", "verification_evidence"} and not value:
            raise ReviewError(f"Manifest {field} is required; report unrun verification explicitly")
        if len(value) != len(set(value)):
            raise ReviewError(f"Manifest {field} contains duplicates")
    baseline = manifest.get("baseline")
    if baseline is not None and (not isinstance(baseline, str) or not baseline or baseline.startswith("-")):
        raise ReviewError("Manifest baseline must be a Git ref")
    if phase == "implementation" and not baseline:
        raise ReviewError("Implementation review requires a verified baseline")
    required_context = manifest.get("required_context_paths", [])
    if not set(required_context).issubset(set(manifest.get("context_paths", []))):
        raise ReviewError("Manifest required_context_paths must be a subset of context_paths")
    read_roots = manifest.get("read_roots", [])
    if not isinstance(read_roots, list) or len(read_roots) > 100 or any(not isinstance(path, str) or not pathlib.Path(path).is_absolute() for path in read_roots):
        raise ReviewError("Manifest read_roots must be a bounded list of absolute directory paths")
    resolved_roots = [pathlib.Path(path).resolve() for path in read_roots]
    if len(set(resolved_roots)) != len(resolved_roots):
        raise ReviewError("Manifest read_roots contains duplicate directories")
    if any(not path.is_dir() for path in resolved_roots):
        raise ReviewError("Each manifest read_root must be an existing directory")
    if "read_roots" in manifest:
        manifest["read_roots"] = [str(path) for path in resolved_roots]
    if "requirement_paths" in manifest:
        mappings = manifest["requirement_paths"]
        if not isinstance(mappings, dict) or len(mappings) != len(manifest["requirements"]):
            raise ReviewError("Manifest requirement_paths must map every requirement to evidence paths")
        allowed_paths = set(manifest["selected_paths"] + manifest.get("context_paths", []) + manifest.get("guidance_paths", []))
        if set(mappings) != set(manifest["requirements"]):
            raise ReviewError("Manifest requirement_paths must map every requirement exactly once")
        for requirement, paths in mappings.items():
            if not isinstance(paths, list) or not paths or len(paths) > 100 or any(not isinstance(path, str) or path not in allowed_paths for path in paths):
                raise ReviewError(f"Manifest requirement_paths for {requirement} must name selected, context, or guidance paths")
            if len(paths) != len(set(paths)):
                raise ReviewError(f"Manifest requirement_paths for {requirement} contains duplicates")
    if "parent_checks" in manifest:
        checks = manifest["parent_checks"]
        if not isinstance(checks, list) or len(checks) > 200:
            raise ReviewError("Manifest parent_checks must be a bounded list")
        for item in checks:
            if not isinstance(item, dict) or set(item) != {"subject", "owner", "status", "evidence"}:
                raise ReviewError("Each parent_check requires subject, owner, status, and evidence")
            if any(not isinstance(item[key], str) or not item[key].strip() or len(item[key]) > limit for key, limit in (("subject", 1000), ("owner", 200), ("status", 20), ("evidence", 4000))):
                raise ReviewError("Parent check fields must be bounded nonempty strings")
            if item["status"] not in {"pending", "passed", "failed"}:
                raise ReviewError("Parent check status must be pending, passed, or failed")
    exclusions = manifest.get("exclusions", [])
    if not isinstance(exclusions, list) or len(exclusions) > 500:
        raise ReviewError("Manifest exclusions must be a bounded list")
    for item in exclusions:
        if not isinstance(item, dict) or set(item) != {"path", "reason"} or any(not isinstance(item[k], str) or not item[k].strip() or len(item[k]) > 2000 for k in item):
            raise ReviewError("Each exclusion requires bounded path and reason strings")
        if not pathlib.Path(item["path"]).is_absolute() and ".." in pathlib.Path(item["path"]).parts:
            raise ReviewError("Exclusion paths must be absolute or repository-relative without parent traversal")
    required_paths = set(manifest["selected_paths"]) | set(required_context) | required_mapped_paths(manifest)
    for path in manifest["selected_paths"] + manifest.get("context_paths", []):
        raw_reference(repository, path)
        if exclusion_matches(repository, path, exclusions):
            continue
        if path in required_paths:
            resolve_reference(repository, path)
    for path in set(required_context) | required_mapped_paths(manifest):
        if exclusion_matches(repository, path, exclusions):
            raise ReviewError(f"Required or mapped evidence is excluded: {path}")
    for path in manifest.get("guidance_paths", []):
        guidance = pathlib.Path(path)
        if not guidance.is_absolute():
            raise ReviewError("Guidance paths must be absolute")
        if exclusion_matches(repository, path, exclusions):
            raise ReviewError(f"Supplied role guidance is excluded: {path}")
    focus = manifest.get("prompt", "")
    if not isinstance(focus, str) or len(focus) > 10000:
        raise ReviewError("Manifest prompt must be a bounded string")
    return repository, phase, run_id, manifest["selected_paths"]

def cleanup_snapshot(snapshot: pathlib.Path) -> None:
    resolved = snapshot.resolve()
    temporary_root = pathlib.Path(tempfile.gettempdir()).resolve()
    if snapshot.is_symlink() or resolved.parent != temporary_root or not resolved.name.startswith("claude-cross-review-"):
        raise ReviewError("Refusing to clean an unowned snapshot")
    try:
        if snapshot.exists():
            shutil.rmtree(snapshot)
    except OSError as error:
        raise ReviewError("Review snapshot cleanup failed") from error

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


def is_safe_executable(path: pathlib.Path) -> bool:
    return path.is_file() and path.suffix.lower() not in {".bat", ".cmd", ".ps1", ".sh"}


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
    try:
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        category = "permission" if isinstance(error, PermissionError) else "process"
        raise ReviewError("Local Claude preflight failed", diagnostic_category=category,
                          exception_type=type(error).__name__) from error


def redact_text(value: str, limit: int = 500) -> str:
    value = re.sub(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,]+", r"\1=[redacted]", value)
    return value.replace("\x00", "")[:limit]


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


def git_evidence(repository: pathlib.Path, baseline: str, paths: list[str], *,
                 diff_directory: pathlib.Path | None = None, max_file_bytes: int | None = None,
                 max_packet_bytes: int | None = None, packet_bytes_before: int = 0) -> dict[str, Any]:
    def git(*arguments: str) -> str:
        result = subprocess.run(["git", "--literal-pathspecs", *arguments], cwd=repository, capture_output=True,
                                encoding="utf-8", errors="surrogateescape", timeout=20, check=False)
        if result.returncode:
            raise ReviewError("Scoped Git evidence collection failed; verify repository and baseline")
        return result.stdout

    def write_diff(name: str, arguments: tuple[str, ...]) -> dict[str, Any]:
        assert diff_directory is not None
        target = diff_directory / f"{name}.diff"
        target.parent.mkdir(parents=True, exist_ok=True)
        # Git hunk lines may contain arbitrary source bytes. Keep valid UTF-8 and
        # escape undecodable bytes so reviewers receive a line-readable UTF-8 artifact.
        reader_errors: list[BaseException] = []
        with target.open("wb", buffering=0) as output:
            process = subprocess.Popen(["git", "--literal-pathspecs", *arguments], cwd=repository,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            started = time.monotonic()
            other_diff_bytes = sum(item.stat().st_size for item in diff_directory.glob("*.diff") if item != target)

            def stream_text_diff() -> None:
                decoder = codecs.getincrementaldecoder("utf-8")("backslashreplace")
                try:
                    assert process.stdout is not None
                    while True:
                        block = process.stdout.read1(64 * 1024)
                        if not block:
                            break
                        output.write(decoder.decode(block).encode("utf-8"))
                    output.write(decoder.decode(b"", final=True).encode("utf-8"))
                except BaseException as error:
                    reader_errors.append(error)
                finally:
                    if process.stdout is not None:
                        process.stdout.close()

            reader = threading.Thread(target=stream_text_diff, name=f"claude-review-git-{name}", daemon=True)
            reader.start()
            failure: ReviewError | None = None
            while process.poll() is None:
                if reader_errors:
                    failure = ReviewError(f"Could not write Git {name} diff as UTF-8")
                    break
                size = target.stat().st_size
                if max_file_bytes is not None and size > max_file_bytes:
                    failure = ReviewError(f"--max-file-bytes={max_file_bytes} limit exceeded by Git {name} diff at {target} ({size} bytes)")
                    break
                if max_packet_bytes is not None and packet_bytes_before + other_diff_bytes + size > max_packet_bytes:
                    failure = ReviewError(f"--max-packet-bytes={max_packet_bytes} limit exceeded by Git {name} diff at {target}")
                    break
                if time.monotonic() - started > 20:
                    failure = ReviewError("Scoped Git evidence collection timed out")
                    break
                time.sleep(0.01)
            if failure is not None and process.poll() is None:
                process.kill()
            process.wait()
            reader.join()
            if failure is not None:
                target.unlink(missing_ok=True)
                raise failure
            if reader_errors:
                target.unlink(missing_ok=True)
                raise ReviewError(f"Could not write Git {name} diff as UTF-8") from reader_errors[0]
        if process.returncode:
            target.unlink(missing_ok=True)
            raise ReviewError("Scoped Git evidence collection failed; verify repository and baseline")
        size = target.stat().st_size
        if max_file_bytes is not None and size > max_file_bytes:
            target.unlink(missing_ok=True)
            raise ReviewError(f"--max-file-bytes={max_file_bytes} limit exceeded by Git {name} diff at {target} ({size} bytes)")
        if max_packet_bytes is not None and packet_bytes_before + other_diff_bytes + size > max_packet_bytes:
            target.unlink(missing_ok=True)
            raise ReviewError(f"--max-packet-bytes={max_packet_bytes} limit exceeded by Git {name} diff at {target}")
        return {"path": target.name, "sha256": sha256_file(target), "bytes": size}

    base = git("rev-parse", "--verify", "--end-of-options", baseline + "^{commit}").strip()
    head = git("rev-parse", "--verify", "HEAD").strip()
    merge = git("merge-base", base, head).strip()
    result: dict[str, Any] = {"head": head, "baseline": base, "merge_base": merge}
    if not paths:
        result["deleted_paths"] = []
        if diff_directory is not None:
            result["diffs"] = {}
        return result
    prefix = ("diff", "--no-ext-diff", "--no-textconv", "--no-color")
    diff_arguments = {
        "committed": (*prefix, merge, head, "--", *paths),
        "staged": (*prefix, "--cached", "--", *paths),
        "unstaged": (*prefix, "--", *paths),
    }
    if diff_directory is None:
        for name, arguments in diff_arguments.items():
            result[name] = git(*arguments)
    else:
        result["diffs"] = {name: write_diff(name, arguments) for name, arguments in diff_arguments.items()}
    result["names"] = git(*prefix, "--name-status", "-M", merge, "--", *paths)
    deleted: set[str] = set()
    name_outputs = (
        git(*prefix, "--name-status", "-z", "-M", merge, head, "--", *paths),
        git(*prefix, "--name-status", "-z", "-M", "--cached", "--", *paths),
        git(*prefix, "--name-status", "-z", "-M", "--", *paths),
    )
    for output in name_outputs:
        fields = output.split("\x00")
        index = 0
        while index < len(fields) and fields[index]:
            status = fields[index]
            index += 1
            count = 2 if status.startswith(("R", "C")) else 1
            paths_in_record = fields[index:index + count]
            index += count
            if status.startswith(("D", "R")):
                deleted.add(paths_in_record[0])
    result["deleted_paths"] = sorted(deleted)
    return result


def _reference_kind(reference: str, manifest: dict[str, Any]) -> str:
    if reference in manifest.get("guidance_paths", []):
        return "guidance"
    if reference in manifest.get("selected_paths", []) or reference in required_mapped_paths(manifest):
        return "required"
    return "optional"


def _source_links(raw: pathlib.Path) -> list[dict[str, str]]:
    links = []
    for ancestor in reversed((raw, *raw.parents)):
        try:
            if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
                links.append({"path": str(ancestor.absolute()), "target": os.readlink(ancestor)})
        except OSError:
            continue
    return links


def _git_path_key(path: str) -> str:
    normalized = pathlib.PurePosixPath(path).as_posix()
    return normalized.casefold() if os.name == "nt" else normalized


def _repository_git_path(repository: pathlib.Path, reference: str) -> str | None:
    path = pathlib.Path(reference)
    if path.is_absolute():
        if os.pardir in path.parts:
            # Preserve source capture, but avoid inventing a lexical Git identity
            # when symlink traversal can change what a following `..` resolves to.
            for ancestor in path.parents:
                try:
                    if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
                        return None
                except OSError:
                    return None
        root_absolute = os.path.abspath(str(repository))
        path_absolute = os.path.abspath(str(path))
        root_key = os.path.normcase(root_absolute)
        path_key = os.path.normcase(path_absolute)
        try:
            common = os.path.commonpath((root_key, path_key))
        except ValueError:
            return None
        if common != root_key:
            return None
        relative = os.path.relpath(path_absolute, root_absolute)
    else:
        relative = str(path)
    if relative == os.curdir or relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return None
    candidate = repository / pathlib.Path(relative)
    for ancestor in candidate.parents:
        if ancestor == repository:
            break
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            return None
    return pathlib.Path(relative).as_posix()


def _packet_source_path(reference: str, raw: pathlib.Path, snapshot: pathlib.Path, used: set[str]) -> pathlib.Path:
    normalized = pathlib.Path(reference).as_posix()
    parts = pathlib.PurePosixPath(normalized).parts
    reserved_name = parts[0] if parts else ""
    reserved = not pathlib.Path(reference).is_absolute() and (
        reserved_name.casefold() == "_clanker_packet" if os.name == "nt" else reserved_name == "_clanker_packet")
    external = pathlib.Path(reference).is_absolute()
    if external or reserved:
        namespace = "external" if external else "repository"
        token = sha256_bytes(reference.encode("utf-8", errors="surrogateescape"))[:16]
        relative = pathlib.Path("_clanker_packet") / "sources" / namespace / f"{token}-{raw.name or 'evidence'}"
    else:
        relative = pathlib.Path(*pathlib.PurePosixPath(normalized).parts)
    key = relative.as_posix().casefold() if os.name == "nt" else relative.as_posix()
    if key in used:
        token = sha256_bytes(reference.encode("utf-8", errors="surrogateescape"))[:16]
        relative = pathlib.Path("_clanker_packet") / "sources" / "mapped" / f"{token}-{raw.name or 'evidence'}"
        key = relative.as_posix().casefold() if os.name == "nt" else relative.as_posix()
    used.add(key)
    return snapshot / relative


def _copy_evidence(source: pathlib.Path, target: pathlib.Path, max_file_bytes: int | None, *,
                   max_packet_bytes: int | None = None, packet_bytes_before: int = 0) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as input_file, target.open("wb") as output_file:
            while True:
                block = input_file.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if max_file_bytes is not None and size > max_file_bytes:
                    raise ReviewError(f"--max-file-bytes={max_file_bytes} limit exceeded by {source} ({size} bytes)")
                if max_packet_bytes is not None and packet_bytes_before + size > max_packet_bytes:
                    raise ReviewError(f"--max-packet-bytes={max_packet_bytes} limit exceeded while copying {source}")
                output_file.write(block)
                digest.update(block)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return digest.hexdigest(), size


def collect_snapshot(repository: pathlib.Path, selected_paths: list[str], manifest: dict[str, Any], *,
                     max_file_bytes: int | None = None, max_packet_bytes: int | None = None,
                     snapshot_directory: pathlib.Path | None = None) -> tuple[pathlib.Path, list[dict[str, Any]], str]:
    if snapshot_directory is None:
        snapshot = pathlib.Path(tempfile.mkdtemp(prefix="claude-cross-review-"))
    else:
        snapshot = snapshot_directory
        snapshot.mkdir(parents=True, exist_ok=False)
    files: list[dict[str, Any]] = []
    packet_bytes = 0
    warnings: list[str] = []
    used_snapshot_paths: set[str] = set()
    exclusions = manifest.get("exclusions", [])
    try:
        references = dict.fromkeys(selected_paths + manifest.get("context_paths", []))
        for reference in references:
            raw = pathlib.Path(reference) if pathlib.Path(reference).is_absolute() else repository / pathlib.Path(reference)
            entry: dict[str, Any] = {"path": reference, "kind": _reference_kind(reference, manifest)}
            if exclusion_matches(repository, reference, exclusions):
                entry.update(state="excluded", reason="parent-declared scope exclusion")
            else:
                if reference in selected_paths:
                    git_path = _repository_git_path(repository, reference)
                    if git_path is not None:
                        entry["git_path"] = git_path
                try:
                    resolved = resolve_reference(repository, reference)
                except (ReviewError, OSError) as error:
                    if entry["kind"] != "optional" or (isinstance(error, ReviewError) and str(error) != "Evidence path must be a file, not a directory"):
                        raise
                    reason = "optional context is a directory" if isinstance(error, ReviewError) else "optional context could not be resolved"
                    entry.update(state="unavailable", reason=reason)
                    files.append(entry)
                    continue
                entry["resolved_path"] = str(resolved)
                links = _source_links(raw)
                if links:
                    entry["source_links"] = links
                if not resolved.exists():
                    entry["state"] = "missing"
                else:
                    target = _packet_source_path(reference, raw, snapshot, used_snapshot_paths)
                    try:
                        digest, size = _copy_evidence(resolved, target, max_file_bytes, max_packet_bytes=max_packet_bytes,
                                                      packet_bytes_before=packet_bytes)
                    except OSError as error:
                        if entry["kind"] != "optional":
                            raise
                        entry.update(state="unavailable", reason="optional context could not be read")
                        files.append(entry)
                        continue
                    packet_bytes += size
                    if size > FORMER_FILE_INPUT_BYTES:
                        warnings.append(f"Evidence file {reference} is {size} bytes, above the former 1 MB input threshold.")
                    entry.update(state="included", sha256=digest, bytes=size, snapshot_path=target.relative_to(snapshot).as_posix())
            files.append(entry)
        guidance = []
        for index, raw_path in enumerate(manifest.get("guidance_paths", [])):
            raw = pathlib.Path(raw_path)
            if not raw.is_absolute():
                raise ReviewError("Guidance paths must be absolute")
            source = resolve_reference(repository, raw_path)
            if not source.is_file():
                raise ReviewError(f"Supplied role guidance is unavailable: {raw_path}")
            target_relative = pathlib.Path("_clanker_packet") / "guidance" / f"{index:02d}-{sha256_bytes(raw_path.encode('utf-8', errors='surrogateescape'))[:12]}-{raw.name}"
            target = snapshot / target_relative
            digest, size = _copy_evidence(source, target, max_file_bytes, max_packet_bytes=max_packet_bytes,
                                          packet_bytes_before=packet_bytes)
            packet_bytes += size
            if size > FORMER_FILE_INPUT_BYTES:
                warnings.append(f"Role guidance {raw_path} is {size} bytes, above the former 1 MB input threshold.")
            entry = {"path": raw_path, "resolved_path": str(source), "state": "guidance", "kind": "guidance",
                     "sha256": digest, "bytes": size, "snapshot_path": target_relative.as_posix()}
            links = _source_links(raw)
            if links:
                entry["source_links"] = links
            guidance.append(entry)
            files.append(entry)
        git_paths = []
        for item in files:
            if item["state"] not in {"included", "missing"} or item["path"] not in selected_paths:
                continue
            if exclusion_matches(repository, item["path"], exclusions):
                continue
            git_path = item.get("git_path")
            if git_path is not None:
                git_paths.append(git_path)
        allowed_paths = []
        seen_git_paths = set()
        for path in git_paths:
            key = _git_path_key(path)
            if key not in seen_git_paths:
                seen_git_paths.add(key)
                allowed_paths.append(path)
        git: dict[str, Any] = {}
        public_git: dict[str, Any] = {}
        if manifest.get("baseline"):
            git_directory = snapshot / "_clanker_packet" / "diffs"
            git = git_evidence(repository, manifest["baseline"], allowed_paths,
                               diff_directory=git_directory, max_file_bytes=max_file_bytes,
                               max_packet_bytes=max_packet_bytes, packet_bytes_before=packet_bytes)
            diff_metadata = {}
            for name, item in git.get("diffs", {}).items():
                item = dict(item)
                item["path"] = (pathlib.Path("_clanker_packet") / "diffs" / item["path"]).as_posix()
                diff_metadata[name] = item
                packet_bytes += item["bytes"]
                if item["bytes"] > FORMER_FILE_INPUT_BYTES:
                    warnings.append(f"Git {name} diff is {item['bytes']} bytes, above the former 1 MB input threshold.")
            public_git = {key: value for key, value in git.items() if key != "diffs"}
            public_git["diffs"] = diff_metadata
            git_digest = {key: value for key, value in git.items() if key not in {"diffs", "deleted_paths"}}
            git_digest["diffs"] = {name: {key: item[key] for key in ("sha256", "bytes")} for name, item in diff_metadata.items()}
            files.append({"path": "@git", "state": "git", "kind": "git", "baseline": manifest["baseline"], "paths": allowed_paths,
                          "sha256": sha256_bytes(json.dumps(git_digest, sort_keys=True).encode("utf-8", errors="surrogateescape")),
                          "diffs": diff_metadata, "deleted_paths": git.get("deleted_paths", [])})
        if packet_bytes > FORMER_PACKET_INPUT_BYTES:
            warnings.append(f"Captured evidence is {packet_bytes} bytes, above the former 8 MB packet threshold.")
        manifest["guidance_provenance"] = guidance
        manifest["collection_warnings"] = warnings
        metadata = snapshot / "_clanker_packet" / "evidence.json"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata_bytes = json.dumps({"manifest": manifest, "files": files, "git": public_git}, indent=2).encode("utf-8")
        total_bytes = packet_bytes + len(metadata_bytes)
        if max_packet_bytes is not None and total_bytes > max_packet_bytes:
            raise ReviewError(f"--max-packet-bytes={max_packet_bytes} limit exceeded by packet at {snapshot} ({total_bytes} bytes)")
        if total_bytes > FORMER_PACKET_INPUT_BYTES and not any("former 8 MB" in warning for warning in warnings):
            warnings.append(f"Captured packet at {snapshot} is {total_bytes} bytes, above the former 8 MB packet threshold.")
            manifest["collection_warnings"] = warnings
            metadata_bytes = json.dumps({"manifest": manifest, "files": files, "git": public_git}, indent=2).encode("utf-8")
            total_bytes = packet_bytes + len(metadata_bytes)
            if max_packet_bytes is not None and total_bytes > max_packet_bytes:
                raise ReviewError(f"--max-packet-bytes={max_packet_bytes} limit exceeded by packet at {snapshot} ({total_bytes} bytes)")
        metadata.write_bytes(metadata_bytes)
        return snapshot, files, evidence_fingerprint(files)
    except BaseException:
        if snapshot_directory is None:
            cleanup_snapshot(snapshot)
        else:
            shutil.rmtree(snapshot, ignore_errors=True)
        raise


def evidence_fingerprint(files: list[dict[str, Any]]) -> str:
    canonical = [{key: value for key, value in entry.items() if key in {"path", "state", "sha256"}} for entry in files]
    return sha256_bytes(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode())


def current_fingerprint(repository: pathlib.Path, files: list[dict[str, Any]]) -> str:
    current: list[dict[str, Any]] = []
    for entry in files:
        item = {"path": entry["path"], "state": entry["state"]}
        if entry["state"] == "git":
            item["sha256"] = _git_entry_fingerprint(repository, entry)
        elif entry["state"] != "excluded":
            reference = entry["path"]
            source = pathlib.Path(reference) if pathlib.Path(reference).is_absolute() else repository / pathlib.Path(reference)
            if source.is_file():
                item["sha256"] = sha256_file(source)
                if entry["state"] == "missing":
                    item["state"] = "included"
            else:
                item["state"] = "missing"
        current.append(item)
    return evidence_fingerprint(current)


def legacy_current_fingerprint(repository: pathlib.Path, files: list[dict[str, Any]]) -> str:
    current: list[dict[str, Any]] = []
    for entry in files:
        item = {"path": entry["path"], "state": entry["state"]}
        if entry["state"] == "git":
            git = git_evidence(repository, entry["baseline"], entry["paths"])
            item["sha256"] = sha256_bytes(json.dumps(
                {key: value for key, value in git.items() if key != "deleted_paths"}, sort_keys=True).encode())
        elif entry["state"] != "excluded":
            reference = entry["path"]
            source = pathlib.Path(reference) if entry["state"] == "guidance" else resolve_under(repository, reference)
            if source.is_file() and not source.is_symlink():
                item["sha256"] = sha256_file(source)
                if entry["state"] == "missing":
                    item["state"] = "included"
            else:
                item["state"] = "missing"
        current.append(item)
    return evidence_fingerprint(current)


def _git_entry_fingerprint(repository: pathlib.Path, entry: dict[str, Any]) -> str:
    temporary = pathlib.Path(tempfile.mkdtemp(prefix="claude-cross-review-compare-"))
    try:
        git = git_evidence(repository, entry["baseline"], entry["paths"], diff_directory=temporary)
        digest = {key: value for key, value in git.items() if key not in {"diffs", "deleted_paths"}}
        digest["diffs"] = {name: {key: item[key] for key in ("sha256", "bytes")} for name, item in git.get("diffs", {}).items()}
        return sha256_bytes(json.dumps(digest, sort_keys=True).encode("utf-8", errors="surrogateescape"))
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def compare_source_changes(repository: pathlib.Path, files: list[dict[str, Any]],
                           manifest_path: str | pathlib.Path | None = None,
                           manifest_sha256: str | None = None) -> dict[str, Any]:
    repository = pathlib.Path(repository).resolve()
    entries: list[dict[str, str]] = []
    unavailable = False

    def add(path: str, status: str, kind: str, reason: str, resolved_path: str | None = None) -> None:
        nonlocal unavailable
        item = {"path": path, "status": status, "kind": kind, "reason": reason}
        if resolved_path:
            item["resolved_path"] = resolved_path
        entries.append(item)
        unavailable = unavailable or status == "unavailable"

    if not repository.is_dir():
        add(str(repository), "unavailable", "required", "repository read scope is unavailable")

    for item in files:
        kind = item.get("kind") or ("git" if item.get("state") == "git" else "guidance" if item.get("state") == "guidance" else "required")
        original = item.get("path", "")
        if item.get("state") == "excluded":
            continue
        if item.get("state") == "git":
            try:
                actual = _git_entry_fingerprint(repository, item)
            except (ReviewError, OSError, subprocess.SubprocessError, ValueError, TypeError):
                add(original, "unavailable", "git", "scoped Git comparison failed")
            else:
                if actual != item.get("sha256"):
                    add(original, "changed", "git", "scoped Git evidence changed")
            continue
        try:
            raw = pathlib.Path(original) if pathlib.Path(original).is_absolute() else repository / pathlib.Path(original)
            if item.get("state") == "missing" and item.get("source_links", []) != _source_links(raw):
                add(original, "changed", kind, "source link identity changed")
                continue
            if not raw.exists():
                if item.get("state") in {"missing"}:
                    continue
                if item.get("state") == "unavailable":
                    add(original, "unavailable", kind, "source was not captured and is no longer available", item.get("resolved_path"))
                    continue
                add(original, "removed", kind, "captured source is no longer available", item.get("resolved_path"))
                continue
            if raw.is_dir():
                reason = "optional context was not captured because it is a directory" if item.get("state") == "unavailable" else "source path became a directory"
                add(original, "unavailable", kind, reason, item.get("resolved_path"))
                continue
            resolved = raw.resolve()
            captured_resolved = item.get("resolved_path")
            if captured_resolved and pathlib.Path(captured_resolved) != resolved:
                add(original, "changed", kind, "source resolved to a different path", str(resolved))
                continue
            if item.get("source_links", []) != _source_links(raw):
                add(original, "changed", kind, "source link identity changed", str(resolved))
                continue
            if item.get("state") == "missing":
                add(original, "changed", kind, "previously unavailable source is now present", str(resolved))
                continue
            if not resolved.is_file():
                add(original, "unavailable", kind, "source is not a readable file", str(resolved))
                continue
            if item.get("state") == "unavailable":
                try:
                    with resolved.open("rb") as source:
                        source.read(1)
                except OSError:
                    add(original, "unavailable", kind, "source was not captured and remains unreadable", str(resolved))
                else:
                    add(original, "changed", kind, "source became available after capture", str(resolved))
                continue
            if sha256_file(resolved) != item.get("sha256"):
                add(original, "changed", kind, "source content changed", str(resolved))
        except (OSError, ReviewError, ValueError, TypeError):
            add(original, "unavailable", kind, "source comparison failed", item.get("resolved_path"))

    if manifest_path and manifest_sha256:
        path = pathlib.Path(manifest_path)
        try:
            if not path.is_file():
                add(str(path), "removed", "manifest", "captured manifest is no longer available")
            elif sha256_file(path) != manifest_sha256:
                add(str(path), "changed", "manifest", "manifest content changed")
        except OSError:
            add(str(path), "unavailable", "manifest", "manifest comparison failed")

    status = "unavailable" if unavailable else "changed" if entries else "current"
    return {"status": status, "attribution": "unattributed", "entries": entries}


def validate_model_report(value: Any, phase: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewError("Claude output must be a JSON object")
    if value.get("phase") not in {None, phase}:
        raise ReviewError("Claude output phase does not match manifest")
    verdict = value.get("verdict")
    coverage = value.get("coverage")
    findings = value.get("findings")
    limitations = value.get("limitations", [])
    if verdict not in VERDICTS or not isinstance(coverage, list) or not coverage or not isinstance(findings, list) or not isinstance(limitations, list):
        raise ReviewError("Claude output has invalid verdict, coverage, findings, or limitations")
    if any(not isinstance(item, str) or not item.strip() for item in limitations):
        raise ReviewError("Claude output has invalid limitations")
    coverage_subjects: dict[str, str] = {}
    for item in coverage:
        if not isinstance(item, dict) or not isinstance(item.get("subject"), str) or not isinstance(item.get("evidence"), str) or not item["evidence"].strip() or not item["subject"].strip() or item.get("status") not in {"covered", "partial", "unreviewed"}:
            raise ReviewError("Claude output has invalid coverage item")
        if item["subject"] in coverage_subjects:
            raise ReviewError("Claude output has conflicting coverage subjects")
        coverage_subjects[item["subject"]] = item["status"]
    finding_ids: set[str] = set()
    for finding in findings:
        required = ("id", "severity", "location", "scenario", "evidence", "confidence", "suggested_remedy")
        if not isinstance(finding, dict) or any(not isinstance(finding.get(key), str) or not finding[key] for key in required):
            raise ReviewError("Claude output has incomplete finding")
        if finding["severity"] not in SEVERITIES or finding["confidence"] not in CONFIDENCES:
            raise ReviewError("Claude output finding has invalid enum")
        if finding["id"] in finding_ids:
            raise ReviewError("Claude output has duplicate finding IDs")
        finding_ids.add(finding["id"])
    if verdict == "clean" and any(item["severity"] in {"blocking", "major"} for item in findings):
        raise ReviewError("Clean verdict conflicts with material findings")
    consulted_paths = value.get("consulted_paths", [])
    if not isinstance(consulted_paths, list) or len(consulted_paths) > 500 or any(not isinstance(path, str) or not path.strip() or len(path) > 10000 for path in consulted_paths):
        raise ReviewError("Claude output has invalid consulted_paths")
    return {"verdict": verdict, "coverage": coverage, "findings": findings, "limitations": limitations,
            "consulted_paths": list(dict.fromkeys(consulted_paths)), "observed_settings": value.get("observed_settings", {})}


def start_review_process(command: list[str], snapshot: pathlib.Path, *, environment: dict[str, str] | None = None,
                         stdout: Any = subprocess.PIPE, stderr: Any = subprocess.PIPE) -> subprocess.Popen[str]:
    """Start an owned contained process with a per-child environment."""
    child_environment = os.environ if environment is None else environment
    options = dict(cwd=snapshot, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                   text=True, encoding="utf-8", errors="replace", start_new_session=os.name != "nt",
                   env={name: value for name, value in child_environment.items() if name not in MODEL_ENVIRONMENT_KEYS})
    if os.name != "nt":
        return subprocess.Popen(command, **options)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    options["startupinfo"] = startup
    # Create suspended: the process must join our kill-on-close job before it can
    # launch descendants. Resume its threads only after assignment succeeds.
    import ctypes
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    class BasicLimits(ctypes.Structure):
        _fields_ = [("per_process", ctypes.c_int64), ("per_job", ctypes.c_int64), ("flags", w.DWORD),
                    ("minimum", ctypes.c_size_t), ("maximum", ctypes.c_size_t), ("active", w.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
    class Limits(ctypes.Structure):
        _fields_ = [("basic", BasicLimits), ("io", ctypes.c_uint64 * 6), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
    class ThreadEntry(ctypes.Structure):
        _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("id", w.DWORD), ("owner", w.DWORD),
                    ("base_priority", w.LONG), ("delta_priority", w.LONG), ("flags", w.DWORD)]
    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "CreateToolhelp32Snapshot": ([w.DWORD, w.DWORD], w.HANDLE),
        "Thread32First": ([w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
        "Thread32Next": ([w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
        "OpenThread": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        "ResumeThread": ([w.HANDLE], w.DWORD),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ReviewError("Cannot create owned Windows review job")
    process = None
    try:
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ReviewError("Cannot configure owned Windows review job")
        process = subprocess.Popen(command, creationflags=0x00000004, **options)  # CREATE_SUSPENDED
        if not kernel.AssignProcessToJobObject(job, w.HANDLE(int(process._handle))):
            raise ReviewError("Cannot contain Windows reviewer in an owned job")
        threads = kernel.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
        if threads == w.HANDLE(-1).value:
            raise ReviewError("Cannot enumerate suspended reviewer threads")
        resumed = False
        try:
            entry = ThreadEntry()
            entry.size = ctypes.sizeof(entry)
            found = kernel.Thread32First(threads, ctypes.byref(entry))
            while found:
                if entry.owner == process.pid:
                    thread = kernel.OpenThread(0x0002, False, entry.id)  # THREAD_SUSPEND_RESUME
                    if not thread:
                        raise ReviewError("Cannot open suspended reviewer thread")
                    try:
                        if kernel.ResumeThread(thread) == 0xFFFFFFFF:
                            raise ReviewError("Cannot resume contained reviewer")
                        resumed = True
                    finally:
                        kernel.CloseHandle(thread)
                found = kernel.Thread32Next(threads, ctypes.byref(entry))
        finally:
            kernel.CloseHandle(threads)
        if not resumed:
            raise ReviewError("No suspended reviewer thread was resumed")
        process._review_job = job
        return process
    except BaseException:
        kernel.CloseHandle(job)
        if process is not None:
            process.kill()
            process.communicate(timeout=5)
        raise


def close_review_job(process: subprocess.Popen[str]) -> None:
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return
    job = getattr(process, "_review_job", None)
    if job is not None:
        import ctypes
        from ctypes import wintypes
        close = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
        close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
        if not close(job):
            raise ReviewError("Cannot close owned Windows review job")
        process._review_job = None


def terminate(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        close_review_job(process)
    else:
        # Kill the entire session group even if its leader has already exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired as error:
        raise ReviewError("Owned Claude process did not terminate") from error


def required_subjects(manifest: dict[str, Any]) -> list[str]:
    repository = pathlib.Path(manifest.get("repository", "."))
    exclusions = manifest.get("exclusions", [])
    selected = [path for path in manifest.get("selected_paths", []) if not exclusion_matches(repository, path, exclusions)]
    required_context = [path for path in manifest.get("required_context_paths", []) if not exclusion_matches(repository, path, exclusions)]
    return list(dict.fromkeys(selected + required_context + manifest.get("requirements", [])))


def assess_readiness(manifest: dict[str, Any], files: list[dict[str, Any]], snapshot: pathlib.Path | None = None) -> dict[str, Any]:
    by_path = {item["path"]: item for item in files}
    git_entry = by_path.get("@git", {})
    deleted_paths = {_git_path_key(path) for path in git_entry.get("deleted_paths", [])}
    blockers = []
    warnings = list(manifest.get("collection_warnings", []))
    exclusions = manifest.get("exclusions", [])

    def available(path: str) -> tuple[bool, str]:
        entry = by_path.get(path)
        if entry is None:
            return False, "evidence was not captured"
        if entry.get("state") in {"included", "guidance"}:
            return True, ""
        git_path = entry.get("git_path", path)
        if entry.get("state") == "missing" and path in manifest.get("selected_paths", []) and _git_path_key(git_path) in deleted_paths:
            return True, ""
        if entry.get("state") == "excluded":
            return False, entry.get("reason", "excluded evidence")
        if entry.get("state") == "missing":
            return False, "missing without a scoped deletion diff"
        if entry.get("state") == "unavailable":
            return False, entry.get("reason", "evidence is unavailable")
        return False, "evidence is unavailable"

    required_paths = [path for path in manifest.get("selected_paths", []) + manifest.get("required_context_paths", [])
                      if not exclusion_matches(pathlib.Path(manifest["repository"]), path, exclusions)]
    optional_paths = [path for path in manifest.get("context_paths", [])
                      if path not in required_paths and not exclusion_matches(pathlib.Path(manifest["repository"]), path, exclusions)]
    for path in dict.fromkeys(required_paths):
        ok, reason = available(path)
        if not ok:
            blockers.append({"subject": path, "reason": reason})
    for path in dict.fromkeys(optional_paths):
        ok, reason = available(path)
        if not ok:
            warnings.append(f"Optional context {path} is unavailable: {reason}.")
    for original in manifest.get("guidance_paths", []):
        ok, reason = available(original)
        if not ok:
            blockers.append({"subject": original, "reason": reason})
    for requirement, paths in manifest.get("requirement_paths", {}).items():
        for path in paths:
            ok, reason = available(path)
            if not ok:
                blockers.append({"subject": requirement, "path": path, "reason": reason})

    diff_bytes = sum(item["bytes"] for item in git_entry.get("diffs", {}).values())
    source_bytes = sum(item.get("bytes", 0) for item in files if item.get("state") in {"included", "guidance"})
    packet_bytes = sum(path.stat().st_size for path in snapshot.rglob("*") if path.is_file()) if snapshot is not None else source_bytes + diff_bytes
    subjects = required_subjects(manifest)
    if len(subjects) > SPLIT_WARNING_SUBJECTS:
        warnings.append(f"Packet has {len(subjects)} review subjects; consider splitting it into coherent scopes.")
    if packet_bytes > SPLIT_WARNING_BYTES:
        warnings.append(f"Packet evidence is {packet_bytes} bytes; consider splitting it into coherent scopes.")
    counts = {
        "selected": len(manifest.get("selected_paths", [])),
        "context": len(manifest.get("context_paths", [])),
        "guidance": len(manifest.get("guidance_paths", [])),
        "requirements": len(manifest.get("requirements", [])),
        "included": sum(item.get("state") in {"included", "guidance"} for item in files),
        "excluded": sum(item.get("state") == "excluded" for item in files),
        "missing": sum(item.get("state") == "missing" for item in files),
        "reviewable_deletions": sum(item.get("state") == "missing" and _git_path_key(item.get("git_path", item.get("path", ""))) in deleted_paths for item in files),
        "diff_bytes": diff_bytes,
        "packet_bytes": packet_bytes,
    }
    return {"status": "blocked" if blockers else "ready", "counts": counts, "warnings": warnings, "blockers": blockers}


def diagnostic_for(stage: str, error: BaseException, *, category: str | None = None) -> dict[str, Any]:
    message = str(error).lower() if isinstance(error, ReviewError) else ""
    if category is None:
        if isinstance(error, PermissionError):
            category = "filesystem" if stage in {"filesystem_preparation", "report_write", "cleanup"} else "permission"
        elif isinstance(error, ReviewError) and error.diagnostic_category in {"permission", "authentication", "usage", "model", "process", "unknown"}:
            category = error.diagnostic_category
        elif stage == "manifest_validation":
            category = "manifest"
        elif stage in {"filesystem_preparation", "report_write", "cleanup"}:
            category = "filesystem"
        elif stage == "evidence_preparation":
            category = "evidence"
        elif stage == "claude_resolution":
            category = "model"
        elif stage == "subscription_preflight":
            if "model" in message:
                category = "model"
            elif any(word in message for word in ("authentication", "login", "credential", "provider", "subscription")):
                category = "authentication"
            elif any(word in message for word in ("unsupported", "required controls", "effort", "--help")):
                category = "usage"
            else:
                category = "process"
        elif stage == "review_execution":
            category = "process" if isinstance(error, ReviewError) else "unknown"
        else:
            category = "unknown"
    actions = {
        "manifest": "Correct the manifest fields and rerun local preparation.",
        "filesystem": "Check report and reservation directory permissions, then retry.",
        "permission": "Check the local permission reported by the Claude CLI, then retry.",
        "coverage": "Provide readable evidence for each required path or narrow the manifest scope.",
        "evidence": "Check the scoped files and Git baseline, then rerun local preparation.",
        "authentication": "Verify the official Claude subscription login and provider settings.",
        "usage": "Check the CLI usage or rate limit and selected effort, then retry.",
        "model": "Verify the Claude executable and requested review model.",
        "process": "Check Claude CLI availability and retry after resolving the reported process failure.",
        "unknown": "Inspect events.jsonl and progress.json; use --debug to retain local Claude stdout/stderr on the next attempt.",
    }
    result: dict[str, Any] = {"stage": stage, "category": category, "action": actions[category]}
    if isinstance(error, ReviewError):
        result["detail"] = str(error)[:2000]
    if isinstance(error, ReviewError) and error.exit_code is not None:
        result["exit_code"] = error.exit_code
    elif isinstance(error, ReviewError) and stage == "review_execution":
        match = re.search(r"Claude review exited with code (-?\d+)", str(error))
        if match:
            result["exit_code"] = int(match.group(1))
    elif isinstance(error, ReviewError) and error.exception_type:
        result["exception_type"] = error.exception_type
    elif not isinstance(error, ReviewError):
        result["exception_type"] = type(error).__name__
    if "exit_code" in result:
        result["exit_code_hex"] = f"0x{result['exit_code'] & 0xFFFFFFFF:08X}"
    cause = error
    while cause.__cause__ is not None:
        cause = cause.__cause__
    if isinstance(cause, OSError):
        result["exception_type"] = type(cause).__name__
        for field in ("errno", "winerror"):
            value = getattr(cause, field, None)
            if isinstance(value, int):
                result[field] = value
    return result


CLI_FAILURE_PHRASES = {
    "permission": ("permission denied", "access denied", "not permitted"),
    "authentication": ("invalid api key", "unauthorized", "authentication failed", "not authenticated", "login required"),
    "usage": ("usage limit", "rate limit", "unknown option", "unrecognized option", "invalid option", "usage:"),
    "model": ("model not found", "unknown model", "invalid model", "model unavailable"),
}


def cli_failure_excerpt(output: str) -> str:
    # Only fixed recognized phrases enter reports, never surrounding private payloads.
    sample = (output[:MAX_OUTPUT_BYTES] + output[-MAX_OUTPUT_BYTES:]).lower()
    return "; ".join(phrase for phrases in CLI_FAILURE_PHRASES.values() for phrase in phrases if phrase in sample)[:2000]


def classify_cli_failure(output: str) -> str:
    sample = (output[:MAX_OUTPUT_BYTES] + output[-MAX_OUTPUT_BYTES:]).lower()
    for category, phrases in CLI_FAILURE_PHRASES.items():
        if any(phrase in sample for phrase in phrases):
            return category
    return "unknown"


def communicate_review(process: subprocess.Popen[str], prompt: str, timeout: int,
                       log: ReviewLog | None) -> tuple[str | None, str | None]:
    if log is None:
        return process.communicate(prompt, timeout=timeout)
    deadline = time.monotonic() + timeout
    pending_prompt: str | None = prompt
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, timeout)
        interval = min(HEARTBEAT_SECONDS, remaining)
        try:
            return process.communicate(pending_prompt, timeout=interval)
        except subprocess.TimeoutExpired as error:
            pending_prompt = None  # Retrying communicate must not send the prompt twice.
            log.output(error.stdout, error.stderr, claude_running=process.returncode is None)
            if interval >= remaining:
                raise


def probe_report_directory(directory: pathlib.Path) -> None:
    probe = directory / (".clanker-write-probe-" + uuid.uuid4().hex)
    try:
        with probe.open("x", encoding="utf-8") as output:
            output.write("probe")
    except OSError as error:
        raise ReviewError("Report directory is not writable") from error
    finally:
        probe.unlink(missing_ok=True)


def invoke(executable: pathlib.Path, snapshot: pathlib.Path, manifest: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    string = {"type": "string", "minLength": 1}
    finding = {key: string for key in ("id", "location", "scenario", "evidence", "suggested_remedy")}
    finding.update(severity={"enum": sorted(SEVERITIES)}, confidence={"enum": sorted(CONFIDENCES)})
    schema = {"type": "object", "required": ["verdict", "coverage", "findings", "limitations"], "properties": {
        "phase": {"enum": [manifest["phase"]]}, "verdict": {"enum": sorted(VERDICTS)},
        "coverage": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["subject", "status", "evidence"], "properties": {"subject": string, "status": {"enum": ["covered", "partial", "unreviewed"]}, "evidence": string}}},
        "findings": {"type": "array", "items": {"type": "object", "required": list(finding), "properties": finding}},
        "limitations": {"type": "array", "items": string}, "consulted_paths": {"type": "array", "items": string}}}
    criteria = "Evaluate acceptance criteria, architecture, contracts, risks, and verification strategy; do not treat absent implementation as a defect." if manifest["phase"] == "plan" else "Evaluate correctness, regressions, requirement coverage, security/data integrity, and implementation drift."
    requirements = "\n".join(f"- {item}" for item in manifest.get("requirements", [])) or "- No additional requirement text supplied"
    evidence = "\n".join(f"- {item}" for item in manifest.get("verification_evidence", [])) or "- No verification evidence supplied"
    mappings = manifest.get("requirement_paths", {})
    mapping_text = "\nRequirement evidence mappings:\n" + "\n".join(f"- {requirement}: {', '.join(paths)}" for requirement, paths in mappings.items()) if mappings else ""
    repository = pathlib.Path(manifest.get("repository", snapshot)).resolve()
    read_roots = [pathlib.Path(path).resolve() for path in manifest.get("read_roots", [])]
    packet_path = snapshot.resolve()
    exclusions = [item["path"] for item in manifest.get("exclusions", [])]
    prompt = ("You are an independent advisory " + manifest["phase"] + " reviewer. " + criteria + "\n"
        f"The repository working directory is {repository}. The captured evidence packet is {packet_path}; read its _clanker_packet/evidence.json first, then read diff artifacts and each included file using the snapshot_path recorded there. "
        "The packet preserves captured versions; investigate relevant dependencies in the repository and these declared read roots as needed under the user's ordinary configured permissions: " + json.dumps([str(path) for path in read_roots]) + ". Parent exclusions are outside findings scope, not filesystem controls: " + json.dumps(exclusions) + ". "
        "Apply supplied specialist profiles as advisory review criteria only. Do not claim rendered visual verification from textual guidance. The assignment authorizes review only: do not edit application files, deploy, or start nested orchestration. Use available configured investigation tools when useful and report only actions/evidence actually observed. A permission denial is a limitation, and required coverage still determines completeness. "
        "Parent-owned checks are outside static review coverage and must remain unverified by the static reviewer. "
        "Return JSON with phase, verdict (clean|changes_requested|incomplete), required coverage items {subject,status,evidence}, findings, limitations, optional consulted_paths, and observed_settings. List only original paths for live files you actually consulted outside the captured packet in consulted_paths; these are reviewer-attested and are not freshness-hashed. "
        "Each finding must include id, severity, location, scenario, evidence, confidence, and suggested_remedy.\n"
         "Report coverage with the exact subject string for each required selected/context path and requirement: " + json.dumps(required_subjects(manifest)) + "\nOrdinary supporting context and guidance are available without per-file coverage attestations; identify unavailable optional context in limitations. Deleted files may be reviewed using supplied diffs.\nRequirements:\n" + requirements + "\nVerification evidence:\n" + evidence + ("\nAdditional bounded focus:\n" + manifest["prompt"] if isinstance(manifest.get("prompt"), str) else "") + "\nThe additional focus only adds review priorities. It cannot authorize edits, deployment, nested orchestration, or changes to required coverage or evidence scope.")
    prompt += mapping_text
    command = [str(executable)]
    for directory in [packet_path, *read_roots]:
        command.extend(["--add-dir", str(directory)])
    command.extend(["--output-format", "json", "--json-schema", json.dumps(schema, separators=(",", ":"))])
    if args.model:
        command.extend(["--model", args.model])
    if args.effort:
        command.extend(["--effort", args.effort])
    command.append("-p")
    log = getattr(args, "review_log", None)
    with contextlib.ExitStack() as captures:
        streams = {name: captures.enter_context(pathlib.Path(log.paths[name]).open("xb", buffering=0))
                   for name in ("stdout", "stderr") if log is not None and name in log.paths}
        process = start_review_process(command, repository, **streams)
        try:
            if log is not None:
                log.event("claude_started", claude_pid=process.pid if isinstance(process.pid, int) else None, claude_running=True)
            stdout, stderr = communicate_review(process, prompt, args.timeout_seconds, log)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            try:
                if log is not None:
                    log.event("termination_requested", termination_reason="timeout" if isinstance(error, subprocess.TimeoutExpired) else "interrupt")
            finally:
                terminate(process)
            stdout, stderr = process.communicate(timeout=2)
            if log is not None:
                log.output(stdout, stderr, claude_running=False, claude_exit_code=process.returncode)
            if isinstance(error, subprocess.TimeoutExpired):
                raise ReviewError("Claude review timed out and its owned process tree was terminated") from error
            raise
        finally:
            close_review_job(process)
        if log is not None:
            log.output(stdout, stderr, claude_running=False, claude_exit_code=process.returncode)
        if streams:
            stdout = read_capture(pathlib.Path(log.paths["stdout"]), tail=bool(process.returncode))
            stderr = read_capture(pathlib.Path(log.paths["stderr"]), tail=True)
    stdout, stderr = stdout or "", stderr or ""
    if process.returncode:
        output = stdout + "\n" + stderr
        category = classify_cli_failure(output)
        excerpt = cli_failure_excerpt(output)
        detail = "recognized diagnostic: " + excerpt if excerpt else "no recognized diagnostic; inspect local --debug capture"
        raise ReviewError(f"Claude review exited with code {process.returncode}; {detail}", diagnostic_category=category, exit_code=process.returncode)
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


def report_directory(output: pathlib.Path, run_id: str, phase: str) -> pathlib.Path:
    root = output.resolve() / run_id
    if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise ReviewError("Report run directory must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 100):
        candidate = root / f"{phase}-{attempt}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise ReviewError("No unique report directory is available")


def write_report(directory: pathlib.Path, report: dict[str, Any]) -> pathlib.Path:
    report_path = directory / "report.json"
    metadata = {key: report.get(key) for key in ("schema_version", "phase", "scope_fingerprint", "created_at", "execution_status", "readiness", "diagnostic", "logs", "process", "parent_checks", "runtime", "requested_settings", "observed_settings", "source_evidence", "source_changes", "consulted_paths")}
    with (directory / "metadata.json").open("x", encoding="utf-8") as output:
        output.write(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    summary = [f"# Claude cross-review: {report['phase']}", "", f"Status: {report['execution_status']}", f"Verdict: {report.get('verdict', 'incomplete')}"]
    readiness = report.get("readiness")
    if readiness:
        summary.extend([f"Readiness: {readiness['status']}", "", "## Readiness"])
        summary.extend(f"- {name}: {value}" for name, value in readiness.get("counts", {}).items())
        summary.extend(f"- Warning: {item}" for item in readiness.get("warnings", []))
        summary.extend(f"- Blocked {item['subject']}: {item.get('reason', 'unavailable evidence')}" for item in readiness.get("blockers", []))
    diagnostic = report.get("diagnostic")
    if diagnostic:
        summary.extend(["", "## Diagnostic", f"- Stage: {diagnostic['stage']}", f"- Category: {diagnostic['category']}", f"- Action: {diagnostic['action']}"])
        for field in ("detail", "exit_code", "exit_code_hex", "exception_type", "errno", "winerror"):
            if field in diagnostic:
                summary.append(f"- {field}: {diagnostic[field]}")
    if report.get("logs"):
        summary.extend(["", "## Local diagnostics"])
        summary.extend(f"- {name}: {path}" for name, path in report["logs"].items())
    if report.get("source_changes"):
        summary.extend(["", "## Source changes", f"- Status: {report['source_changes']['status']}"])
        summary.extend(f"- {item['path']} ({item['kind']}, {item['status']}): {item['reason']}" for item in report["source_changes"].get("entries", []))
    if report.get("consulted_paths"):
        summary.extend(["", "## Reviewer-consulted paths"])
        summary.extend(f"- {path} (reviewer-attested live context; freshness is not verified)" for path in report["consulted_paths"])
    summary.extend(["", "## Coverage"])
    summary.extend(f"- {item['subject']}: {item['status']} - {item['evidence']}" for item in report.get("coverage", []))
    summary.extend(["", "## Findings"])
    for item in report.get("findings", []):
        summary.extend([f"### {item['id']} ({item['severity']}, {item['confidence']})", "", f"Location: {item['location']}",
                        "", item['scenario'], "", "Evidence: " + item['evidence'], "", "Remedy: " + item['suggested_remedy'], ""])
    if not report.get("findings"):
        summary.append("- None")
    summary.extend(["", "## Limitations"])
    summary.extend("- " + item for item in report.get("limitations", []))
    parent_checks = report.get("parent_checks", [])
    if parent_checks:
        summary.extend(["", "## Parent checks"])
        summary.extend(f"- {item['subject']} ({item['owner']}, {item['status']}): {item['evidence']}" for item in parent_checks)
    with (directory / "summary.md").open("x", encoding="utf-8") as output:
        output.write("\n".join(summary) + "\n")
    with report_path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report_path


def check_current(path: pathlib.Path) -> int:
    report = load_json(path)
    source = report.get("source_evidence", {})
    repository = pathlib.Path(source.get("repository", ""))
    files = source.get("files")
    if report.get("schema_version") == 2:
        try:
            if not isinstance(files, list) or "read_scope" not in source:
                raise ReviewError("Versioned report has no captured evidence scope")
            changes = compare_source_changes(repository, files, source.get("manifest_path"), source.get("manifest_sha256"))
        except (ReviewError, OSError, subprocess.SubprocessError, ValueError, TypeError):
            changes = {"status": "unavailable", "attribution": "unattributed", "entries": [
                {"path": str(repository), "status": "unavailable", "kind": "required", "reason": "source comparison failed"}]}
        current = changes["status"] == "current"
        recorded_changes = report.get("source_changes", {})
        eligible = current and recorded_changes.get("status") == "current" and report.get("execution_status") == "completed" and report.get("verdict") == "clean"
        print(json.dumps({"report": str(path), "current": current, "eligible_for_parent_review": eligible,
                          "execution_status": report.get("execution_status"), "source_changes": changes}, sort_keys=True))
        return 0 if current else 3
    if not repository.is_dir() or not isinstance(files, list):
        raise ReviewError("Report has no usable source evidence")
    try:
        actual = legacy_current_fingerprint(repository.resolve(), files)
    except (ReviewError, OSError, subprocess.SubprocessError):
        actual = None
    stale = actual != source.get("file_fingerprint", source.get("fingerprint"))
    manifest_path = source.get("manifest_path")
    if manifest_path and source.get("manifest_sha256"):
        candidate = pathlib.Path(manifest_path)
        stale = stale or not candidate.is_file() or sha256_file(candidate) != source["manifest_sha256"]
    approved = not stale and report.get("execution_status") == "completed" and report.get("verdict") == "clean"
    print(json.dumps({"report": str(path), "current": not stale, "eligible_for_parent_review": approved, "execution_status": "stale" if stale else report.get("execution_status")}, sort_keys=True))
    return 3 if stale else 0


def reservation_root() -> pathlib.Path:
    return pathlib.Path.home() / ".clanker" / "review-reservations"


def reserve_review(repository: pathlib.Path, manifest: dict[str, Any], manifest_path: pathlib.Path,
                   report_path: pathlib.Path) -> pathlib.Path:
    """Publish the intended scope before snapshotting; callers must quiesce writers first."""
    paths = [resolve_under(repository, p) for p in
             manifest["selected_paths"] + manifest.get("context_paths", [])]
    paths += [pathlib.Path(p).resolve() for p in manifest.get("guidance_paths", [])]
    paths.append(manifest_path.resolve())
    scope = [{"path": str(p), "sha256": sha256_file(p) if p.is_file() else None}
             for p in dict.fromkeys(paths)]
    root = reservation_root()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / (str(uuid.uuid4()) + ".json")
    pending = destination.with_suffix(".pending")
    try:
        pending.write_text(json.dumps({"pid": os.getpid(), "created_at": utc_now(),
            "repository": str(repository), "report_directory": str(report_path),
            "files": scope}, indent=2), encoding="utf-8")
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    return destination


def check_write_reservations(paths: list[str]) -> dict[str, Any]:
    """Check files or directory operations against all local review reservations."""
    candidates = []
    for raw in paths:
        path = pathlib.Path(raw)
        if not path.is_absolute():
            raise ReviewError("Write checks require absolute paths")
        candidates.append(path.resolve())
    conflicts = []
    try:
        records = sorted(p for p in reservation_root().iterdir() if p.suffix == ".json")
    except FileNotFoundError:
        records = []
    for record in records:
        data = load_json(record)
        files = data.get("files")
        if not isinstance(files, list):
            raise ReviewError("Invalid review reservation; coordinator recovery required")
        for item in files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not pathlib.Path(item["path"]).is_absolute():
                raise ReviewError("Invalid review reservation; coordinator recovery required")
            reserved = pathlib.Path(item["path"]).resolve()
            for candidate in candidates:
                if candidate == reserved or candidate in reserved.parents or reserved in candidate.parents:
                    conflicts.append({"requested_path": str(candidate), "reserved_path": str(reserved),
                                      "reservation": str(record), "pid": data.get("pid")})
    return {"allowed": not conflicts, "conflicts": conflicts}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an advisory Claude Code review from a JSON manifest.")
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--output-dir", type=pathlib.Path)
    parser.add_argument("--claude-exe")
    parser.add_argument("--model", default=DEFAULT_REVIEW_MODEL, help="Review model override (default: opus)")
    parser.add_argument("--effort", help="Explicit review effort selected from scope/risk or user override; no default")
    parser.add_argument("--timeout-seconds", type=finite_positive, default=DEFAULT_TIMEOUT_SECONDS, help="Wall-clock review limit in seconds (default: 2700 / 45 minutes)")
    parser.add_argument("--max-file-bytes", type=finite_positive, help="Optional maximum bytes copied for one source file or Git diff")
    parser.add_argument("--max-packet-bytes", type=finite_positive, help="Optional maximum total bytes retained in the evidence packet")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare and report the local evidence packet without resolving or launching Claude")
    parser.add_argument("--debug", action="store_true", help="Retain raw review stdout/stderr in local, Git-ignored files; never echo them to the console")
    parser.add_argument("--check-current", type=pathlib.Path)
    parser.add_argument("--check-writes", nargs="+", metavar="ABSOLUTE_PATH")
    args = parser.parse_args()
    if args.check_writes:
        if args.manifest or args.output_dir or args.check_current or args.prepare_only or args.max_file_bytes or args.max_packet_bytes:
            parser.error("--check-writes cannot be combined with review or freshness operations")
        try:
            result = check_write_reservations(args.check_writes)
            print(json.dumps(result))
            return 0 if result["allowed"] else 3
        except (ReviewError, OSError) as error:
            print(json.dumps({"allowed": False, "error": str(error)}), file=sys.stderr)
            return 2
    if args.check_current:
        if args.manifest or args.output_dir or args.prepare_only or args.max_file_bytes or args.max_packet_bytes:
            parser.error("--check-current cannot be combined with --manifest or --output-dir")
        try:
            return check_current(args.check_current)
        except ReviewError as error:
            print(json.dumps({"error": str(error)}), file=sys.stderr)
            return 2
    if not args.manifest or not args.output_dir:
        parser.error("--manifest and --output-dir are required unless using --check-current")
    if not args.prepare_only and (not args.effort or not args.effort.strip()):
        parser.error("--effort is required for review execution; select it from scope/risk or a user override")
    directory = None
    snapshot = None
    log = None
    report = {"schema_version": 2, "execution_status": "failed", "phase": "unknown", "scope_fingerprint": None,
              "requested_settings": {"model": args.model, "effort": args.effort, "timeout_seconds": args.timeout_seconds},
              "observed_settings": {}, "runtime": {}, "source_evidence": {}, "verdict": "incomplete",
              "findings": [], "coverage": [], "limitations": [], "diagnostic": None, "readiness": None,
              "parent_checks": [], "created_at": utc_now()}
    stage = "manifest_validation"
    try:
        manifest_hash = sha256_file(args.manifest)
        manifest = load_json(args.manifest)
        repository, phase, run_id, selected = validate_manifest(manifest)
        report["phase"] = phase
        stage = "filesystem_preparation"
        directory = report_directory(args.output_dir, run_id, phase)
        probe_report_directory(directory)
        log = ReviewLog(directory, args.debug and not args.prepare_only)
        args.review_log = log
        report["logs"] = log.paths
        print(json.dumps({"event": "review_started", "report_directory": str(directory), "logs": log.paths}, sort_keys=True), file=sys.stderr, flush=True)
        report["source_evidence"] = {"repository": str(repository), "baseline": manifest.get("baseline"),
            "requirements": manifest["requirements"], "verification_evidence": manifest["verification_evidence"], "exclusions": manifest.get("exclusions", []),
            "manifest_path": str(args.manifest.resolve()), "manifest_sha256": manifest_hash,
            "requirement_paths": manifest.get("requirement_paths"), "parent_checks": manifest.get("parent_checks", [])}
        report["parent_checks"] = manifest.get("parent_checks", [])
        stage = "evidence_preparation"
        log.event("stage", stage=stage)
        snapshot, files, fingerprint = collect_snapshot(repository, selected, manifest,
            max_file_bytes=args.max_file_bytes, max_packet_bytes=args.max_packet_bytes,
            snapshot_directory=directory / "packet")
        report["scope_fingerprint"] = sha256_bytes((fingerprint + manifest_hash).encode())
        report["source_evidence"]["read_scope"] = {"repository": str(repository), "packet": str(snapshot.resolve()),
            "additional_roots": manifest.get("read_roots", [])}
        report["source_evidence"].update(files=files, fingerprint=fingerprint, file_fingerprint=fingerprint,
            exclusions=manifest.get("exclusions", []) + [{"path": item["path"], "reason": item.get("reason", item["state"])} for item in files if item["state"] == "excluded"],
            guidance=manifest.get("guidance_provenance", []))
        readiness = assess_readiness(manifest, files, snapshot)
        report["readiness"] = readiness
        readiness_limitations = [warning for warning in readiness["warnings"] if warning.startswith("Optional context ")]
        report["limitations"].extend(readiness_limitations)
        if readiness["status"] == "blocked":
            report["diagnostic"] = diagnostic_for(stage, ReviewError("Required evidence is unavailable"), category="coverage")
            details = "; ".join(f"{item['subject']}: {item['reason']}" for item in readiness["blockers"])
            report["execution_status"] = "blocked"
            report["limitations"].append("Required evidence is unavailable: " + details)
        elif args.prepare_only:
            report["execution_status"] = "prepared"
        else:
            stage = "claude_resolution"
            log.event("stage", stage=stage)
            executable = resolve_claude(args.claude_exe)
            stage = "subscription_preflight"
            log.event("stage", stage=stage)
            runtime = preflight(executable, args.model, args.effort, repository)
            args.model = runtime["requested_model"]
            report["requested_settings"]["model"] = args.model
            report["runtime"] = runtime
            stage = "review_execution"
            log.event("stage", stage=stage)
            result = invoke(executable, snapshot, manifest, args)
            stage = "result_validation"
            log.event("stage", stage=stage)
            covered = {item["subject"] for item in result["coverage"] if item["status"] == "covered"}
            uncovered = sorted(set(required_subjects(manifest)) - covered)
            if uncovered or any(item["status"] != "covered" for item in result["coverage"] if item["subject"] in required_subjects(manifest)):
                result["limitations"].append("Required review coverage incomplete: " + ", ".join(uncovered))
                result["verdict"] = "incomplete"
            result["limitations"] = list(dict.fromkeys(report["limitations"] + result["limitations"]))
            report.update(result)
            report["execution_status"] = "completed"
    except KeyboardInterrupt:
        report["diagnostic"] = diagnostic_for(stage, ReviewError("Review interrupted"), category="process")
        report.update(execution_status="interrupted", verdict="incomplete")
        report["limitations"].append("Review interrupted")
    except (ReviewError, OSError, ValueError, TypeError, subprocess.SubprocessError) as caught:
        error = str(caught) if isinstance(caught, ReviewError) else "Review failed: " + type(caught).__name__
        diagnostic = diagnostic_for(stage, caught)
        report["diagnostic"] = diagnostic
        status = "timed_out" if "timed out" in error or diagnostic.get("exception_type") == "TimeoutExpired" else "blocked" if diagnostic["category"] in {"manifest", "filesystem", "permission", "coverage", "evidence", "authentication", "usage", "model"} else "failed"
        report.update(execution_status=status, verdict="incomplete")
        report["limitations"].append(error)
    finally:
        if log is not None:
            try:
                log.event("cleanup", stage="cleanup", execution_status=report["execution_status"], diagnostic=report["diagnostic"])
            except OSError:
                report.update(execution_status="failed", verdict="incomplete")
                report["limitations"].append("Local diagnostic log update failed")
        if snapshot is not None and snapshot.parent.resolve() == pathlib.Path(tempfile.gettempdir()).resolve():
            try:
                cleanup_snapshot(snapshot)
            except (ReviewError, OSError) as error:
                report.update(execution_status="failed", verdict="incomplete")
                report["diagnostic"] = diagnostic_for("cleanup", error)
                report["limitations"].append("Review snapshot cleanup failed; manual cleanup required")
    if directory is None:
        if report["diagnostic"] is None:
            report["diagnostic"] = diagnostic_for(stage, ReviewError("Review could not be prepared"))
        print(json.dumps({"error": report["limitations"], "diagnostic": report["diagnostic"]}), file=sys.stderr)
        return 2
    source_evidence = report.get("source_evidence", {})
    source_files = source_evidence.get("files")
    if isinstance(source_files, list) and "read_scope" in source_evidence:
        try:
            report["source_changes"] = compare_source_changes(
                pathlib.Path(source_evidence.get("repository", ".")), source_files,
                source_evidence.get("manifest_path"), source_evidence.get("manifest_sha256"))
        except (ReviewError, OSError, subprocess.SubprocessError, ValueError, TypeError):
            report["source_changes"] = {"status": "unavailable", "attribution": "unattributed",
                "entries": [{"path": str(source_evidence.get("repository", ".")), "status": "unavailable",
                             "kind": "required", "reason": "source comparison failed"}]}
    else:
        report["source_changes"] = {"status": "unavailable", "attribution": "unattributed",
            "entries": [{"path": str(source_evidence.get("manifest_path", args.manifest)), "status": "unavailable",
                         "kind": "manifest", "reason": "captured evidence scope is unavailable"}]}
    stage = "report_write"
    exit_code = 0 if report["execution_status"] in {"completed", "prepared"} else 2
    try:
        if log is not None:
            log.event("report_write", stage=stage, claude_running=False, execution_status=report["execution_status"],
                      launcher_exit_code=exit_code, diagnostic=report["diagnostic"])
            report["process"] = {key: log.progress[key] for key in ("launcher_pid", "claude_pid", "claude_exit_code", "claude_exit_code_hex", "launcher_exit_code", "stdout_bytes", "stderr_bytes", "last_output_at", "elapsed_seconds", "termination_reason") if key in log.progress}
        path = write_report(directory, report)
        if log is not None:
            log.event("finished", stage="finished")
    except OSError as error:
        diagnostic = diagnostic_for(stage, error)
        if log is not None:
            try:
                log.event("report_write_failed", launcher_exit_code=2, diagnostic=diagnostic)
            except OSError:
                pass
        print(json.dumps({"error": "Report write failed", "diagnostic": diagnostic, "logs": log.paths if log else {}}), file=sys.stderr, flush=True)
        return 2
    print(json.dumps({"report": str(path), "execution_status": report["execution_status"], "verdict": report["verdict"],
                      "launcher_exit_code": exit_code, "diagnostic": report["diagnostic"], "logs": report.get("logs", {})}, sort_keys=True), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
