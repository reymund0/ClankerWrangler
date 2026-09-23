#!/usr/bin/env python3
"""Bounded, metadata-only catalogs from locally installed Codex and Claude CLIs."""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import claude_cross_review as containment

CACHE_SECONDS = 300.0
PROBE_SECONDS = 30.0
CLEANUP_SECONDS = 5.0
MAX_OUTPUT_BYTES = 1_048_576
MAX_LINE_BYTES = 262_144
MAX_CODEX_PAGES = 20
MAX_MODELS = 1_000
MAX_TEXT_BYTES = 8_192
PROVIDERS = ("codex", "claude")
CREDENTIAL_NAMES = frozenset(("ANTHROPIC_API_KEY", "OPENAI_API_KEY"))
CLAUDE_PROVIDER_PREFIXES = (
    "ANTHROPIC_", "AWS_", "GOOGLE_", "GCP_", "AZURE_",
    "BEDROCK_", "VERTEX_", "FOUNDRY_",
)
CLAUDE_HELP_FLAGS = (
    "--bare", "--safe-mode", "--restricted", "--strict-mcp-config",
    "--input-format", "--output-format", "stream-json", "--no-session-persistence",
    "--permission-mode", "--permission-prompts",
)


class DiscoveryError(Exception):
    """A sanitized provider discovery failure."""


class DiscoveryClosed(Exception):
    """The editor is closing and no discovery work may begin."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _safe_text(value: Any, field: str, *, required: bool = True) -> str | None:
    if not isinstance(value, str):
        if required:
            raise DiscoveryError("CLI returned malformed model metadata")
        return None
    encoded = value.encode("utf-8", "strict")
    if not value or len(encoded) > MAX_TEXT_BYTES or any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise DiscoveryError("CLI returned malformed model metadata")
    return value


def _safe_error(error: BaseException) -> str:
    if isinstance(error, DiscoveryError):
        return str(error)
    if isinstance(error, (OSError, subprocess.SubprocessError, ValueError, TypeError, UnicodeError, json.JSONDecodeError)):
        return "Local CLI discovery failed"
    return "Local CLI discovery failed"


def _child_environment(provider: str) -> dict[str, str]:
    def allowed(name: str) -> bool:
        upper = name.upper()
        if upper in CREDENTIAL_NAMES:
            return False
        if provider != "claude":
            return True
        return not containment.provider_override(upper) and not upper.startswith(CLAUDE_PROVIDER_PREFIXES)
    return {name: value for name, value in os.environ.items() if allowed(name)}


class _OutputBudget:
    def __init__(self) -> None:
        self.total = 0
        self.overflow = threading.Event()
        self._lock = threading.Lock()

    def add(self, size: int) -> bool:
        with self._lock:
            self.total += size
            if self.total > MAX_OUTPUT_BYTES:
                self.overflow.set()
                return False
        return True


class _OutputReader:
    """Drain both pipes without retaining unbounded protocol output."""

    def __init__(self, process: subprocess.Popen[str], budget: _OutputBudget | None = None):
        self.process = process
        self.lines: queue.Queue[bytes] = queue.Queue()
        self._budget = budget or _OutputBudget()
        self.overflow = self._budget.overflow
        self.done = threading.Event()
        self._threads = [
            threading.Thread(target=self._read, args=(process.stdout, True), daemon=True),
            threading.Thread(target=self._read, args=(process.stderr, False), daemon=True),
        ]
        for worker in self._threads:
            worker.start()

    def _add(self, size: int) -> bool:
        return self._budget.add(size)

    def _read(self, stream: Any, protocol: bool) -> None:
        partial = bytearray()
        try:
            raw = getattr(stream, "buffer", stream)
            while not self.overflow.is_set():
                read = getattr(raw, "read1", None) or raw.read
                block = read(8192)
                if not block:
                    break
                if isinstance(block, str):
                    block = block.encode("utf-8", "replace")
                if not self._add(len(block)):
                    break
                if not protocol:
                    continue
                partial.extend(block)
                while True:
                    newline = partial.find(b"\n")
                    if newline < 0:
                        if len(partial) > MAX_LINE_BYTES:
                            self.overflow.set()
                        break
                    line = bytes(partial[:newline]).rstrip(b"\r")
                    del partial[:newline + 1]
                    if len(line) > MAX_LINE_BYTES:
                        self.overflow.set()
                        break
                    if line:
                        self.lines.put(line)
            if protocol and partial and not self.overflow.is_set():
                if len(partial) > MAX_LINE_BYTES:
                    self.overflow.set()
                else:
                    self.lines.put(bytes(partial))
        finally:
            if protocol:
                self.done.set()

    def join(self) -> None:
        for worker in self._threads:
            worker.join(timeout=1)

    def close(self) -> None:
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        for worker in self._threads:
            worker.join(timeout=1)


class DiscoveryManager:
    """Discover provider catalogs lazily, with bounded refresh and in-memory cache."""

    def __init__(
        self,
        codex_executable: str | Path | None = None,
        claude_executable: str | Path | None = None,
        *,
        monotonic: Any = time.monotonic,
    ):
        self._configured = {
            "codex": codex_executable if codex_executable is not None else os.environ.get("CLANKER_CODEX"),
            "claude": claude_executable if claude_executable is not None else os.environ.get("CLANKER_CLAUDE"),
        }
        self._monotonic = monotonic
        self._condition = threading.Condition(threading.RLock())
        self._closed = False
        self._active = False
        self._attempted_at: dict[str, float | None] = {provider: None for provider in PROVIDERS}
        self._success: dict[str, dict[str, Any] | None] = {provider: None for provider in PROVIDERS}
        self._failures: dict[str, str | None] = {provider: None for provider in PROVIDERS}
        self._processes: set[subprocess.Popen[str]] = set()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            processes = list(self._processes)
            self._condition.notify_all()
        for process in processes:
            self._stop(process)
        cleanup_deadline = time.monotonic() + CLEANUP_SECONDS
        with self._condition:
            while self._active and time.monotonic() < cleanup_deadline:
                self._condition.wait(timeout=0.05)

    def catalog(self, force: bool = False) -> dict[str, dict[str, dict[str, Any]]]:
        with self._condition:
            if self._closed:
                raise DiscoveryClosed()
            current = self._monotonic()
            fresh = all(
                self._attempted_at[provider] is not None
                and current - self._attempted_at[provider] < CACHE_SECONDS
                for provider in PROVIDERS
            )
            if not force and fresh:
                return self._snapshot(cached=True)
            if self._active:
                while self._active and not self._closed:
                    self._condition.wait()
                if self._closed:
                    raise DiscoveryClosed()
                return self._snapshot(cached=False)
            self._active = True
        try:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="model-discovery") as pool:
                results = dict(zip(PROVIDERS, (future.result() for future in (
                    pool.submit(self._probe_codex), pool.submit(self._probe_claude)
                ))))
        finally:
            with self._condition:
                now = self._monotonic()
                for provider in PROVIDERS:
                    self._attempted_at[provider] = now
                    result = locals().get("results", {}).get(provider)
                    if isinstance(result, dict):
                        self._success[provider] = result
                        self._failures[provider] = None
                    elif isinstance(result, BaseException):
                        self._failures[provider] = _safe_error(result)
                self._active = False
                self._condition.notify_all()
        with self._condition:
            if self._closed:
                raise DiscoveryClosed()
            return self._snapshot_locked(cached=False)

    def _snapshot(self, *, cached: bool) -> dict[str, dict[str, dict[str, Any]]]:
        with self._condition:
            return self._snapshot_locked(cached=cached)

    def _snapshot_locked(self, *, cached: bool) -> dict[str, dict[str, dict[str, Any]]]:
        providers: dict[str, dict[str, Any]] = {}
        for provider in PROVIDERS:
            success = self._success[provider]
            failure = self._failures[provider]
            if success is None:
                providers[provider] = {
                    "status": "unavailable", "source": provider + "-cli",
                    "cli_version": None, "updated_at": None,
                    "error": failure or "Local CLI discovery is unavailable", "models": [],
                }
            else:
                providers[provider] = copy.deepcopy(success)
                providers[provider]["status"] = "stale" if failure else ("cached" if cached else "live")
                providers[provider]["error"] = failure
        return {"providers": providers}

    def _record_process(self, process: subprocess.Popen[str]) -> None:
        with self._condition:
            if self._closed:
                self._stop(process)
                raise DiscoveryClosed()
            self._processes.add(process)

    def _release_process(self, process: subprocess.Popen[str]) -> None:
        with self._condition:
            self._processes.discard(process)

    def _stop(self, process: subprocess.Popen[str]) -> None:
        with self._condition:
            if getattr(process, "_discovery_stopped", False):
                return
            process._discovery_stopped = True
        try:
            containment.terminate(process)
        except (OSError, containment.ReviewError, subprocess.SubprocessError):
            pass
        try:
            containment.close_review_job(process)
        except (OSError, containment.ReviewError):
            pass

    def _start(self, command: list[str], directory: Path, provider: str = "codex") -> subprocess.Popen[str]:
        process = containment.start_review_process(command, directory, environment=_child_environment(provider))
        self._record_process(process)
        return process

    def _run_lines(self, command: list[str], directory: Path, deadline: float, budget: _OutputBudget, provider: str, stdin: list[dict[str, Any]] | None = None) -> list[bytes]:
        if self._monotonic() >= deadline:
            raise DiscoveryError("Local CLI discovery timed out")
        process = self._start(command, directory, provider)
        reader = _OutputReader(process, budget)
        try:
            if stdin:
                for message in stdin:
                    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
                process.stdin.flush()
            while process.poll() is None:
                if reader.overflow.is_set():
                    self._stop(process)
                    raise DiscoveryError("Local CLI discovery output exceeded its limit")
                if self._monotonic() >= deadline:
                    self._stop(process)
                    raise DiscoveryError("Local CLI discovery timed out")
                time.sleep(0.01)
            reader.join()
            if reader.overflow.is_set():
                raise DiscoveryError("Local CLI discovery output exceeded its limit")
            lines: list[bytes] = []
            while True:
                try:
                    lines.append(reader.lines.get_nowait())
                except queue.Empty:
                    break
            if process.returncode:
                raise DiscoveryError("Local CLI discovery command failed")
            return lines
        finally:
            self._stop(process)
            reader.close()
            self._release_process(process)

    def _open_stream(self, command: list[str], directory: Path, budget: _OutputBudget, provider: str) -> tuple[subprocess.Popen[str], _OutputReader]:
        process = self._start(command, directory, provider)
        return process, _OutputReader(process, budget)

    def _next_message(self, process: subprocess.Popen[str], reader: _OutputReader, deadline: float) -> dict[str, Any]:
        while True:
            if reader.overflow.is_set():
                self._stop(process)
                raise DiscoveryError("Local CLI discovery output exceeded its limit")
            if self._monotonic() >= deadline:
                self._stop(process)
                raise DiscoveryError("Local CLI discovery timed out")
            try:
                line = reader.lines.get(timeout=0.02)
            except queue.Empty:
                if process.poll() is not None and reader.done.is_set():
                    try:
                        line = reader.lines.get_nowait()
                    except queue.Empty:
                        raise DiscoveryError("Local CLI returned incomplete metadata") from None
                else:
                    continue
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise DiscoveryError("Local CLI returned malformed metadata") from error
            if not isinstance(value, dict):
                raise DiscoveryError("Local CLI returned malformed metadata")
            return value

    def _resolve(self, provider: str) -> Path:
        configured = self._configured[provider]
        if configured is None:
            name = "codex" if provider == "codex" else "claude"
            candidates: list[Path] = []
            if provider == "codex" and os.name == "nt":
                appdata = os.environ.get("APPDATA")
                if appdata:
                    vendor = Path(appdata) / "npm" / "node_modules" / "@openai" / "codex" / "node_modules" / "@openai" / "codex-win32-x64" / "vendor" / "x86_64-pc-windows-msvc"
                    candidates.extend(vendor / folder / "codex.exe" for folder in ("bin", "codex"))
            if provider == "claude" and os.name == "nt":
                candidates.append(Path.home() / ".local" / "bin" / "claude.exe")
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
        else:
            candidates = [Path(configured)]
        for candidate in candidates:
            try:
                candidate = candidate.expanduser()
                if not candidate.is_absolute() or not candidate.is_file():
                    continue
                if os.name == "nt" and candidate.suffix.lower() in {".cmd", ".bat", ".ps1"}:
                    continue
                if os.name == "nt" and candidate.suffix.lower() != ".exe":
                    continue
                if os.name != "nt" and not os.access(candidate, os.X_OK):
                    continue
                return candidate
            except OSError:
                continue
        raise DiscoveryError("Local " + provider + " CLI executable is unavailable or unsupported")

    def _version(self, executable: Path, directory: Path, deadline: float, budget: _OutputBudget, provider: str) -> str | None:
        lines = self._run_lines([str(executable), "--version"], directory, deadline, budget, provider)
        if not lines:
            return None
        try:
            value = b" ".join(lines).decode("utf-8").strip()
        except UnicodeDecodeError:
            return None
        if len(value.encode("utf-8", "replace")) > MAX_TEXT_BYTES or any(ord(char) < 32 or ord(char) == 127 for char in value):
            return None
        return value or None

    def _probe_codex(self) -> dict[str, Any] | BaseException:
        try:
            return self._probe_codex_inner()
        except BaseException as error:
            return error

    def _probe_codex_inner(self) -> dict[str, Any]:
        deadline = self._monotonic() + PROBE_SECONDS
        budget = _OutputBudget()
        executable = self._resolve("codex")
        with tempfile.TemporaryDirectory(prefix="clanker-model-discovery-") as temporary:
            directory = Path(temporary)
            version = self._version(executable, directory, deadline, budget, "codex")
            process, reader = self._open_stream([str(executable), "app-server"], directory, budget, "codex")
            models: list[dict[str, Any]] = []
            cursors: set[str] = set()
            try:
                self._send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "clanker-model-discovery", "version": "1"}, "capabilities": {}}})
                self._await_id(process, reader, deadline, 1)
                self._send(process, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
                cursor: str | None = None
                for page in range(MAX_CODEX_PAGES):
                    params: dict[str, Any] = {"limit": 100, "includeHidden": False}
                    if cursor is not None:
                        params["cursor"] = cursor
                    self._send(process, {"jsonrpc": "2.0", "id": page + 2, "method": "model/list", "params": params})
                    result = self._await_id(process, reader, deadline, page + 2)
                    rows = result.get("data", result.get("models"))
                    if not isinstance(rows, list):
                        raise DiscoveryError("Codex CLI returned malformed model metadata")
                    for row in rows:
                        models.append(self._codex_model(row))
                        if len(models) > MAX_MODELS:
                            raise DiscoveryError("Codex CLI returned too many models")
                    next_cursor = result.get("nextCursor")
                    if next_cursor is None:
                        break
                    cursor = _safe_text(next_cursor, "nextCursor")
                    if cursor in cursors:
                        raise DiscoveryError("Codex CLI repeated a pagination cursor")
                    cursors.add(cursor)
                else:
                    raise DiscoveryError("Codex CLI exceeded pagination limit")
            finally:
                self._stop(process)
                reader.close()
                self._release_process(process)
            return {"status": "live", "source": "codex-cli", "cli_version": version, "updated_at": _utc_now(), "error": None, "models": models}

    def _send(self, process: subprocess.Popen[str], message: dict[str, Any]) -> None:
        try:
            process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise DiscoveryError("Local CLI returned incomplete metadata") from error

    def _await_id(self, process: subprocess.Popen[str], reader: _OutputReader, deadline: float, identifier: int) -> dict[str, Any]:
        while True:
            message = self._next_message(process, reader, deadline)
            if "method" in message or message.get("id") != identifier:
                continue
            if "error" in message:
                raise DiscoveryError("Local CLI rejected metadata discovery")
            result = message.get("result")
            if not isinstance(result, dict):
                raise DiscoveryError("Local CLI returned malformed metadata")
            return result

    def _codex_model(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise DiscoveryError("Codex CLI returned malformed model metadata")
        identifier = _safe_text(value.get("model"), "model")
        label = _safe_text(value.get("displayName"), "displayName")
        reported = value.get("supportedReasoningEfforts")
        if reported is None:
            efforts = None
        elif isinstance(reported, list):
            efforts = []
            for effort in reported:
                if not isinstance(effort, dict):
                    raise DiscoveryError("Codex CLI returned malformed model metadata")
                item = _safe_text(effort.get("reasoningEffort"), "reasoningEffort")
                if item not in efforts:
                    efforts.append(item)
        else:
            raise DiscoveryError("Codex CLI returned malformed model metadata")
        default = value.get("defaultReasoningEffort")
        if default is not None:
            default = _safe_text(default, "defaultReasoningEffort")
        return {"id": identifier, "label": label, "provider": "codex", "efforts": efforts, "default_effort": default}

    def _probe_claude(self) -> dict[str, Any] | BaseException:
        try:
            return self._probe_claude_inner()
        except BaseException as error:
            return error

    def _probe_claude_inner(self) -> dict[str, Any]:
        deadline = self._monotonic() + PROBE_SECONDS
        budget = _OutputBudget()
        executable = self._resolve("claude")
        with tempfile.TemporaryDirectory(prefix="clanker-model-discovery-") as temporary:
            directory = Path(temporary)
            help_lines = self._run_lines([str(executable), "--help"], directory, deadline, budget, "claude")
            help_text = b"\n".join(help_lines).decode("utf-8", "replace")
            if any(flag not in help_text for flag in CLAUDE_HELP_FLAGS):
                raise DiscoveryError("Claude CLI does not support restricted metadata discovery")
            version = self._version(executable, directory, deadline, budget, "claude")
            command = [
                str(executable), "--print", "--input-format", "stream-json", "--output-format", "stream-json",
                "--verbose", "--bare", "--safe-mode", "--restricted", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--tools", "", "--allowedTools", "",
                "--disallowedTools", "*", "--permission-mode", "dontAsk", "--permission-prompts", "none",
                "--no-session-persistence", "--setting-sources", "",
            ]
            process, reader = self._open_stream(command, directory, budget, "claude")
            try:
                request_id = "clanker-model-discovery"
                self._send(process, {"type": "control_request", "request_id": request_id, "request": {"subtype": "initialize"}})
                response = self._next_message(process, reader, deadline)
                # CLI startup notifications can precede the initialize response.
                # Keep the original deadline and output budget while skipping them.
                while response.get("type") == "system" and response.get("subtype") == "commands_changed":
                    response = self._next_message(process, reader, deadline)
                payload = response.get("response")
                if response.get("type") != "control_response" or not isinstance(payload, dict) or payload.get("request_id") != request_id:
                    raise DiscoveryError("Claude CLI returned malformed model metadata")
                initialized = payload.get("response")
                if not isinstance(initialized, dict) or not isinstance(initialized.get("models"), list):
                    raise DiscoveryError("Claude CLI returned malformed model metadata")
                models = [self._claude_model(model) for model in initialized["models"]]
                if len(models) > MAX_MODELS:
                    raise DiscoveryError("Claude CLI returned too many models")
            finally:
                self._stop(process)
                reader.close()
                self._release_process(process)
            return {"status": "live", "source": "claude-cli", "cli_version": version, "updated_at": _utc_now(), "error": None, "models": models}

    def _claude_model(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise DiscoveryError("Claude CLI returned malformed model metadata")
        identifier = _safe_text(value.get("value"), "value")
        label = _safe_text(value.get("displayName"), "displayName")
        reported = value.get("supportedEffortLevels")
        if reported is None:
            efforts = None
        elif isinstance(reported, list):
            efforts = []
            for effort in reported:
                item = _safe_text(effort, "supportedEffortLevels")
                if item not in efforts:
                    efforts.append(item)
        else:
            raise DiscoveryError("Claude CLI returned malformed model metadata")
        return {"id": identifier, "label": label, "provider": "claude", "efforts": efforts, "default_effort": None}
