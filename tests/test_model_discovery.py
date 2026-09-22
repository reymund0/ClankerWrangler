import ctypes
import os
import queue
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "subagents" / "scripts"))
import model_discovery as discovery


def successful(provider):
    return {
        "status": "live", "source": provider + "-cli", "cli_version": "1",
        "updated_at": "2026-09-21T00:00:00+00:00", "error": None,
        "models": [{"id": provider + "-model", "label": provider, "provider": provider,
                    "efforts": ["low"], "default_effort": "low"}],
    }


def process_exited(pid):
    if os.name != "nt":
        return not Path("/proc/" + str(pid)).exists()
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes, kernel.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
    kernel.GetExitCodeProcess.argtypes, kernel.GetExitCodeProcess.restype = [w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [w.HANDLE], w.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return True
    try:
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise OSError(ctypes.get_last_error(), "GetExitCodeProcess failed")
        return code.value != 259
    finally:
        kernel.CloseHandle(handle)


class DiscoveryManagerTests(unittest.TestCase):
    def manager(self, clock=None):
        return discovery.DiscoveryManager(monotonic=clock or time.monotonic)

    def test_catalog_shape_cache_and_stale_success(self):
        now = [10.0]
        manager = self.manager(lambda: now[0])
        manager._probe_codex = lambda: successful("codex")
        manager._probe_claude = lambda: successful("claude")
        first = manager.catalog()
        self.assertEqual(first["providers"]["codex"]["status"], "live")
        first["providers"]["codex"]["models"][0]["id"] = "mutated"
        cached = manager.catalog()
        self.assertEqual(cached["providers"]["codex"]["status"], "cached")
        self.assertEqual(cached["providers"]["codex"]["models"][0]["id"], "codex-model")
        manager._probe_codex = lambda: discovery.DiscoveryError("Codex CLI returned malformed model metadata")
        manager._probe_claude = lambda: successful("claude")
        stale = manager.catalog(force=True)
        self.assertEqual(stale["providers"]["codex"]["status"], "stale")
        self.assertEqual(stale["providers"]["codex"]["models"][0]["id"], "codex-model")
        self.assertEqual(stale["providers"]["claude"]["status"], "live")
        now[0] += discovery.CACHE_SECONDS + 1
        manager._probe_codex = lambda: successful("codex")
        refreshed = manager.catalog()
        self.assertEqual(refreshed["providers"]["codex"]["status"], "live")

    def test_concurrent_requests_share_one_refresh(self):
        manager = self.manager()
        entered, release = threading.Event(), threading.Event()
        count = [0]
        lock = threading.Lock()

        def probe(provider):
            with lock:
                count[0] += 1
            entered.set()
            release.wait(2)
            return successful(provider)

        manager._probe_codex = lambda: probe("codex")
        manager._probe_claude = lambda: probe("claude")
        results = []
        first = threading.Thread(target=lambda: results.append(manager.catalog()))
        second = threading.Thread(target=lambda: results.append(manager.catalog()))
        first.start()
        self.assertTrue(entered.wait(1))
        second.start()
        release.set()
        first.join(3)
        second.join(3)
        self.assertEqual(count[0], 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["providers"]["codex"]["models"], results[1]["providers"]["codex"]["models"])

    def test_active_catalog_close_raises_and_leaves_no_active_processes(self):
        manager = self.manager()
        entered, release = threading.Event(), threading.Event()

        def probe(provider):
            entered.set()
            release.wait(2)
            return successful(provider)

        manager._probe_codex = lambda: probe("codex")
        manager._probe_claude = lambda: probe("claude")
        result = []
        leader = threading.Thread(target=lambda: result.append(self._catalog_result(manager)))
        leader.start()
        self.assertTrue(entered.wait(1))
        closer = threading.Thread(target=manager.close)
        closer.start()
        for _ in range(40):
            with manager._condition:
                if manager._closed:
                    break
            time.sleep(.05)
        with manager._condition:
            self.assertTrue(manager._closed)
        release.set()
        leader.join(3)
        closer.join(3)
        self.assertIsInstance(result[0], discovery.DiscoveryClosed)
        with manager._condition:
            self.assertFalse(manager._active)
            self.assertEqual(manager._processes, set())

    @staticmethod
    def _catalog_result(manager):
        try:
            return manager.catalog()
        except discovery.DiscoveryClosed as error:
            return error

    @unittest.skipUnless(os.name == "nt", "Windows npm executable layouts")
    def test_windows_codex_npm_current_and_legacy_layouts(self):
        with tempfile.TemporaryDirectory() as temporary:
            vendor = Path(temporary) / "npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc"
            legacy, current = vendor / "codex/codex.exe", vendor / "bin/codex.exe"
            legacy.parent.mkdir(parents=True)
            legacy.touch()
            with patch.dict(os.environ, {"APPDATA": temporary}), patch.object(discovery.shutil, "which", return_value=None):
                manager = self.manager()
                manager._configured["codex"] = None
                self.assertEqual(manager._resolve("codex"), legacy)
                current.parent.mkdir(parents=True)
                current.touch()
                self.assertEqual(manager._resolve("codex"), current)

    def test_constructor_defers_invalid_executable_and_close_rejects_new_work(self):
        manager = discovery.DiscoveryManager(codex_executable="relative-command", claude_executable="also-relative")
        catalog = manager.catalog()
        self.assertEqual(catalog["providers"]["codex"]["status"], "unavailable")
        self.assertEqual(catalog["providers"]["claude"]["status"], "unavailable")
        manager.close()
        with self.assertRaises(discovery.DiscoveryClosed):
            manager.catalog()

    def test_model_mapping_preserves_exact_ids_and_unknown_efforts(self):
        manager = self.manager()
        codex = manager._codex_model({
            "model": "alias:opaque", "displayName": "Alias", "supportedReasoningEfforts": None,
            "defaultReasoningEffort": None,
        })
        claude = manager._claude_model({
            "value": "sonnet[context]", "displayName": "Sonnet", "supportedEffortLevels": None,
        })
        self.assertEqual(codex["id"], "alias:opaque")
        self.assertIsNone(codex["efforts"])
        self.assertEqual(claude["id"], "sonnet[context]")
        self.assertIsNone(claude["efforts"])
        with self.assertRaises(discovery.DiscoveryError):
            manager._codex_model({"model": "bad\nvalue", "displayName": "Alias"})

    def test_rejects_unsupported_claude_help_before_protocol(self):
        manager = self.manager()
        manager._resolve = lambda provider: Path(sys.executable)
        manager._run_lines = lambda *args: [b"--bare --safe-mode"]
        with self.assertRaises(discovery.DiscoveryError):
            manager._probe_claude_inner()

    def test_codex_repeated_cursor_is_rejected(self):
        manager = self.manager()
        manager._resolve = lambda provider: Path(sys.executable)
        manager._version = lambda *args: "test"
        process, reader = MagicMock(), MagicMock()
        manager._open_stream = lambda *args: (process, reader)
        manager._send = lambda *args: None
        manager._stop = lambda *args: None
        manager._release_process = lambda *args: None
        responses = iter((
            {"id": 1, "result": {}},
            {"id": 2, "result": {"data": [{"model": "one", "displayName": "One", "supportedReasoningEfforts": []}], "nextCursor": "again"}},
            {"id": 3, "result": {"data": [], "nextCursor": "again"}},
        ))
        manager._next_message = lambda *args: next(responses)
        with self.assertRaisesRegex(discovery.DiscoveryError, "repeated"):
            manager._probe_codex_inner()
        reader.close.assert_called_once()

    def test_await_id_skips_server_request_with_matching_id(self):
        manager = self.manager()
        messages = iter((
            {"jsonrpc": "2.0", "id": 2, "method": "client/request", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "result": {"data": []}},
        ))
        manager._next_message = lambda *args: next(messages)
        self.assertEqual(manager._await_id(MagicMock(), MagicMock(), time.monotonic() + 1, 2), {"data": []})

    def test_exited_process_waits_for_delayed_stdout_after_stderr_eof(self):
        entered, release, empty_seen = threading.Event(), threading.Event(), threading.Event()

        class Stream:
            def __init__(self, chunks, gate=None):
                self.chunks, self.gate = list(chunks), gate

            def read1(self, size):
                if self.gate is not None:
                    entered.set()
                    self.gate.wait(1)
                    self.gate = None
                return self.chunks.pop(0) if self.chunks else b""

            read = read1

            def close(self):
                pass

        class ObservedQueue(queue.Queue):
            def get(self, *args, **kwargs):
                try:
                    return super().get(*args, **kwargs)
                except queue.Empty:
                    empty_seen.set()
                    raise

        manager = self.manager()
        process = MagicMock()
        process.poll.return_value = 0
        process.stdin = MagicMock()
        process.stdout = Stream([b'{"id": 1, "result": {}}\n'], release)
        process.stderr = Stream([])
        reader = discovery._OutputReader(process)
        reader.lines = ObservedQueue()
        result = []
        worker = threading.Thread(target=lambda: result.append(manager._next_message(process, reader, time.monotonic() + 1)))
        try:
            self.assertTrue(entered.wait(1))
            worker.start()
            self.assertTrue(empty_seen.wait(1))
            self.assertFalse(reader.done.is_set())
            release.set()
            worker.join(2)
            self.assertEqual(result, [{"id": 1, "result": {}}])
        finally:
            release.set()
            worker.join(2)
            reader.close()

    def test_successful_codex_multipage_protocol_uses_metadata_messages_only(self):
        manager = self.manager()
        manager._resolve = lambda provider: Path(sys.executable)
        manager._version = lambda *args: "codex-test"
        process, reader = MagicMock(), MagicMock()
        manager._open_stream = lambda *args: (process, reader)
        manager._stop = lambda *args: None
        manager._release_process = lambda *args: None
        sent = []
        manager._send = lambda _, message: sent.append(message)
        responses = iter((
            {"id": 1, "result": {}},
            {"id": 2, "result": {"data": [{"model": "first", "displayName": "First", "supportedReasoningEfforts": [{"reasoningEffort": "low"}], "defaultReasoningEffort": "low"}], "nextCursor": "later"}},
            {"id": 3, "result": {"data": [{"model": "second", "displayName": "Second", "supportedReasoningEfforts": None}]}},
        ))
        manager._next_message = lambda *args: next(responses)
        result = manager._probe_codex_inner()
        self.assertEqual([model["id"] for model in result["models"]], ["first", "second"])
        self.assertEqual(sent, [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "clanker-model-discovery", "version": "1"}, "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "model/list", "params": {"limit": 100, "includeHidden": False}},
            {"jsonrpc": "2.0", "id": 3, "method": "model/list", "params": {"limit": 100, "includeHidden": False, "cursor": "later"}},
        ])

    def test_successful_claude_initialize_uses_restricted_metadata_command(self):
        manager = self.manager()
        manager._resolve = lambda provider: Path(sys.executable)
        calls = []

        def run_lines(command, directory, deadline, budget, provider):
            calls.append((command, provider))
            return [(" ".join(discovery.CLAUDE_HELP_FLAGS)).encode()] if command[-1] == "--help" else [b"claude-test"]

        manager._run_lines = run_lines
        process, reader = MagicMock(), MagicMock()
        open_calls = []
        manager._open_stream = lambda command, directory, budget, provider: (open_calls.append((command, provider)) or (process, reader))
        manager._stop = lambda *args: None
        manager._release_process = lambda *args: None
        sent = []
        manager._send = lambda _, message: sent.append(message)
        manager._next_message = lambda *args: {
            "type": "control_response",
            "response": {"request_id": "clanker-model-discovery", "response": {"models": [
                {"value": "default", "displayName": "Default", "supportedEffortLevels": ["low", "high"]}
            ]}},
        }
        result = manager._probe_claude_inner()
        self.assertEqual(result["models"], [{"id": "default", "label": "Default", "provider": "claude", "efforts": ["low", "high"], "default_effort": None}])
        self.assertEqual(calls, [([str(Path(sys.executable)), "--help"], "claude"), ([str(Path(sys.executable)), "--version"], "claude")])
        self.assertEqual(open_calls, [([
            str(Path(sys.executable)), "--print", "--input-format", "stream-json", "--output-format", "stream-json",
            "--verbose", "--bare", "--safe-mode", "--restricted", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--tools", "", "--allowedTools", "",
            "--disallowedTools", "*", "--permission-mode", "dontAsk", "--permission-prompts", "none",
            "--no-session-persistence", "--setting-sources", "",
        ], "claude")])
        self.assertEqual(sent, [{"type": "control_request", "request_id": "clanker-model-discovery", "request": {"subtype": "initialize"}}])

    def test_short_live_ndjson_is_read_before_process_exit(self):
        manager = self.manager()
        code = "import sys,time; sys.stdout.write('{\\\"id\\\":1,\\\"result\\\":{}}\\n'); sys.stdout.flush(); time.sleep(3)"
        process = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        reader = discovery._OutputReader(process)
        try:
            self.assertEqual(manager._next_message(process, reader, time.monotonic() + 1), {"id": 1, "result": {}})
        finally:
            process.kill()
            process.wait(timeout=3)
            reader.close()

    def test_timeout_and_exit_parent_cleanup_kill_owned_grandchildren(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for exit_parent in (False, True):
                pid_file = directory / ("timeout.pid" if not exit_parent else "orphan.pid")
                child = "import time; time.sleep(60)"
                parent = (
                    "import pathlib,subprocess,sys,time; "
                    "p=subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); "
                    "pathlib.Path(sys.argv[1]).write_text(str(p.pid)); "
                    + ("time.sleep(60)" if not exit_parent else "time.sleep(.05)")
                )
                manager = self.manager()
                deadline = time.monotonic() + (0.15 if not exit_parent else 3)
                if exit_parent:
                    lines = manager._run_lines([sys.executable, "-c", parent, str(pid_file)], directory, deadline, discovery._OutputBudget(), "codex")
                    self.assertEqual(lines, [])
                else:
                    with self.assertRaisesRegex(discovery.DiscoveryError, "timed out"):
                        manager._run_lines([sys.executable, "-c", parent, str(pid_file)], directory, deadline, discovery._OutputBudget(), "codex")
                for _ in range(40):
                    if pid_file.exists() and process_exited(int(pid_file.read_text())):
                        break
                    time.sleep(.05)
                self.assertTrue(pid_file.exists())
                self.assertTrue(process_exited(int(pid_file.read_text())))

    def test_output_bounds_and_credential_environment(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 1048577)"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        reader = discovery._OutputReader(process)
        self.assertTrue(reader.overflow.wait(3))
        process.kill()
        process.wait(timeout=3)
        reader.join()
        reader.close()
        old = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "secret"
        try:
            self.assertNotIn("ANTHROPIC_API_KEY", discovery._child_environment("claude"))
        finally:
            if old is None:
                del os.environ["ANTHROPIC_API_KEY"]
            else:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_claude_child_environment_removes_overrides_without_mutating_parent(self):
        overrides = {
            "CLAUDE_CODE_USE_BEDROCK": "1",
            "CLAUDE_CODE_OAUTH_TOKEN": "token",
            "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR": "7",
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "GOOGLE_APPLICATION_CREDENTIALS": "C:/private.json",
            "AZURE_CLIENT_SECRET": "secret",
            "ANTHROPIC_BASE_URL": "https://provider.example",
        }
        with patch.dict(os.environ, overrides):
            child = discovery._child_environment("claude")
            self.assertTrue(all(name not in child for name in overrides))
            self.assertEqual({name: os.environ[name] for name in overrides}, overrides)
            self.assertEqual(discovery._child_environment("codex")["CLAUDE_CODE_USE_BEDROCK"], "1")

    def test_close_kills_owned_grandchild(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            pid_file = directory / "child.pid"
            child = "import time; time.sleep(60)"
            parent = (
                "import pathlib,subprocess,sys,time; "
                "p=subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); "
                "pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)"
            )
            manager = self.manager()
            process = manager._start([sys.executable, "-c", parent, str(pid_file)], directory)
            for _ in range(40):
                if pid_file.exists():
                    break
                time.sleep(0.05)
            self.assertTrue(pid_file.exists())
            pid = int(pid_file.read_text())
            manager.close()
            process.communicate(timeout=3)
            for _ in range(40):
                if process_exited(pid):
                    break
                time.sleep(0.05)
            self.assertTrue(process_exited(pid))


if __name__ == "__main__":
    unittest.main()
