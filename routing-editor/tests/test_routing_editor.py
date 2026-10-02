"""Isolated persistence and actual loopback HTTP contract tests."""
import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import routing_editor as editor
import routing_policy as policy

EMPTY = {"schema_version": 1}
LUNA = {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}}
LEGACY = {**LUNA, "adaptive_profiles": {"codex:gpt-5.6-luna": {"tiers": {"mechanical": "low", "routine": "medium",
          "complex": "high", "exceptional": "xhigh"}, "default_ceiling": "xhigh"}}}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.store = editor.PreferenceStore(global_config_dir=self.root / "global")

    def legacy_file(self, scope="global"):
        path = self.store.target(scope)[1]
        path.parent.mkdir(exist_ok=True)
        original = b"\xef\xbb\xbf" + (json.dumps(LEGACY, indent=4) + "\r\n").encode()
        path.write_bytes(original)
        return path, original

    def test_legacy_open_preview_reload_are_read_only(self):
        path, original = self.legacy_file()
        state = self.store.configuration()["scopes"]["global"]
        self.assertTrue(state["migration_pending"])
        self.assertEqual(state["revision"], editor.revision(original))
        self.assertEqual(state["document"]["adaptive_profiles"]["codex:gpt-5.6-luna"], {
            "tiers": {"straightforward": "medium", "involved": "high", "demanding": "xhigh"}, "default_ceiling": "xhigh"})
        request = {"interaction": "implementation", "tier": "involved", "reason": "Coordinate bounded decisions"}
        preview = self.store.preview("global", state["document"], request)["decision"]
        self.assertEqual(preview["effort"], "high")
        self.assertEqual(self.store.read("global"), state)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(path.parent.iterdir()), [path])

    def test_conversion_only_save_exact_backup_scope_isolation_and_reuse(self):
        path, original = self.legacy_file()
        project = self.project / ".clanker" / "orchestration-routing.json"
        project.parent.mkdir()
        project_original = b"invalid project preferences must be ignored"
        project.write_bytes(project_original)
        state = self.store.read("global")
        saved = self.store.save("global", state["document"], state["revision"])["scopes"]["global"]
        backup = Path(saved["migration_backup"])
        self.assertEqual(backup.parent, path.parent)
        self.assertEqual(backup.read_bytes(), original)
        self.assertFalse(saved["migration_pending"])
        self.assertNotIn("mechanical", json.loads(path.read_bytes())["adaptive_profiles"]["codex:gpt-5.6-luna"]["tiers"])
        self.assertEqual(project.read_bytes(), project_original)
        self.assertEqual(list(project.parent.iterdir()), [project])
        # Restoring exact original bytes reuses its content-addressed backup.
        path.write_bytes(original)
        again = self.store.save("global", LEGACY, state["revision"])["scopes"]["global"]
        self.assertEqual(again["migration_backup"], str(backup))
        self.assertEqual(backup.read_bytes(), original)
        normal = self.store.save("global", again["document"], again["revision"])["scopes"]["global"]
        self.assertNotIn("migration_backup", normal)
        self.assertEqual(len(list(path.parent.glob("*.bak"))), 1)

    def test_migration_backup_failure_and_conflict_preserve_source(self):
        path, original = self.legacy_file()
        state = self.store.read("global")
        backup = path.with_name(path.name + ".pre-three-tier." + state["revision"] + ".bak")
        real_open = editor.os.open
        def deny_backup(name, *args, **kwargs):
            if Path(name) == backup:
                raise PermissionError("backup denied")
            return real_open(name, *args, **kwargs)
        with patch.object(editor.os, "open", side_effect=deny_backup):
            with self.assertRaises(PermissionError):
                self.store.save("global", state["document"], state["revision"])
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(list(path.parent.glob("*.lock")))
        backup.write_bytes(b"different content")
        with self.assertRaises(editor.EditorError):
            self.store.save("global", state["document"], state["revision"])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(backup.read_bytes(), b"different content")
        path.write_bytes(original + b" ")
        with self.assertRaises(editor.EditorError) as caught:
            self.store.save("global", state["document"], state["revision"])
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(path.read_bytes(), original + b" ")

    def test_project_requests_are_rejected_without_touching_global(self):
        global_path, global_original = self.legacy_file()
        for action in (lambda: self.store.read("project"),
                       lambda: self.store.preview("project", EMPTY),
                       lambda: self.store.save("project", EMPTY, "missing")):
            with self.assertRaises(editor.EditorError):
                action()
        self.assertEqual(global_path.read_bytes(), global_original)
        self.assertEqual(list(global_path.parent.iterdir()), [global_path])

    def test_failed_replace_retains_recoverable_migration_backup(self):
        path, original = self.legacy_file()
        state = self.store.read("global")
        with patch.object(editor.os, "replace", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                self.store.save("global", state["document"], state["revision"])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(next(path.parent.glob("*.bak")).read_bytes(), original)
        self.assertFalse(list(path.parent.glob("*.tmp")))
        self.assertFalse(list(path.parent.glob("*.lock")))

    def test_linked_migration_backup_rejected(self):
        path, original = self.legacy_file()
        state = self.store.read("global")
        outside = self.root / "outside.json"
        outside.write_bytes(original)
        backup = path.with_name(path.name + ".pre-three-tier." + state["revision"] + ".bak")
        try:
            backup.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(editor.EditorError):
            self.store.save("global", state["document"], state["revision"])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(outside.read_bytes(), original)

    def test_backup_reparse_guard_and_failed_flush_preserve_source(self):
        path, original = self.legacy_file()
        state = self.store.read("global")
        backup = path.with_name(path.name + ".pre-three-tier." + state["revision"] + ".bak")
        real_linked = editor.linked
        with patch.object(editor, "linked", side_effect=lambda candidate: candidate == backup or real_linked(candidate)):
            with self.assertRaises(editor.EditorError):
                self.store.save("global", state["document"], state["revision"])
        self.assertEqual(path.read_bytes(), original)
        with patch.object(editor.os, "fsync", side_effect=OSError("flush failed")):
            with self.assertRaises(OSError):
                self.store.save("global", state["document"], state["revision"])
        self.assertFalse(backup.exists())
        self.assertEqual(path.read_bytes(), original)

    def test_legacy_file_growth_before_backup_is_a_conflict(self):
        path, original = self.legacy_file()
        state = self.store.read("global")
        real_preview = self.store.preview
        calls = 0
        expanded = original + b" " * editor.MAX_DOCUMENT_BYTES
        def grow_after_validation(*args):
            nonlocal calls
            result = real_preview(*args)
            calls += 1
            if calls == 2:
                path.write_bytes(expanded)
            return result
        with patch.object(self.store, "preview", side_effect=grow_after_validation):
            with self.assertRaises(editor.EditorError) as caught:
                self.store.save("global", state["document"], state["revision"])
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(path.read_bytes(), expanded)
        self.assertFalse(list(path.parent.glob("*.bak")))

    def test_create_read_global_only(self):
        state = self.store.configuration()
        self.assertEqual(set(state["scopes"]), {"global"})
        self.assertEqual(state["scopes"]["global"]["revision"], "missing")
        self.store.save("global", LUNA, "missing")
        self.assertEqual(self.store.read("global")["document"], LUNA)
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertFalse(list(self.root.rglob("*.lock")))
        self.assertFalse(list(self.root.rglob("*.tmp")))

    def test_stale_revision_from_second_instance(self):
        second = editor.PreferenceStore(global_config_dir=self.root / "global")
        loaded = second.read("global")
        self.store.save("global", LUNA, "missing")
        with self.assertRaises(editor.EditorError) as caught:
            second.save("global", EMPTY, loaded["revision"])
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.store.read("global")["document"], LUNA)

    def test_concurrent_instances_one_winner(self):
        other = editor.PreferenceStore(global_config_dir=self.root / "global")
        gate = threading.Barrier(2)
        def save(store):
            gate.wait()
            try:
                store.save("global", LUNA, "missing")
                return "saved"
            except editor.EditorError as error:
                return error.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, [self.store, other]))
        self.assertCountEqual(results, ["saved", 409])

    def test_invalid_and_failed_writes_preserve_bytes(self):
        self.store.save("global", EMPTY, "missing")
        before = self.store.target("global")[1].read_bytes()
        rev = self.store.read("global")["revision"]
        with self.assertRaises((policy.RoutingError, editor.EditorError)):
            self.store.save("global", {"schema_version": 99}, rev)
        with patch.object(editor.os, "replace", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                self.store.save("global", LUNA, rev)
        self.assertEqual(self.store.target("global")[1].read_bytes(), before)
        self.assertFalse(list(self.root.rglob("*.tmp")))
        self.assertFalse(list(self.root.rglob("*.lock")))

    def test_external_edit_before_final_check_preserved(self):
        self.store.save("global", EMPTY, "missing")
        path = self.store.target("global")[1]
        rev = self.store.read("global")["revision"]
        original_read = self.store.read
        calls = 0
        def modified_read(scope):
            nonlocal calls
            calls += 1
            # save: preview read, locked revision read, preview read, final read.
            if calls == 4:
                path.write_text(json.dumps(LUNA), encoding="utf-8")
            return original_read(scope)
        with patch.object(self.store, "read", side_effect=modified_read):
            with self.assertRaises(editor.EditorError) as caught:
                self.store.save("global", EMPTY, rev)
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(json.loads(path.read_text()), LUNA)

    def test_stale_lock_not_removed(self):
        _, path = self.store.target("global")
        path.parent.mkdir()
        lock = path.with_suffix(".json.lock")
        lock.write_text('{"pid":999999,"started_at":0}', encoding="utf-8")
        with self.assertRaises(editor.EditorError) as caught:
            self.store.save("global", EMPTY, "missing")
        self.assertEqual(caught.exception.status, 409)
        self.assertTrue(lock.exists())
        self.assertIn("owner", str(caught.exception))

    def test_malformed_file_can_be_explicitly_repaired(self):
        _, path = self.store.target("global")
        path.parent.mkdir()
        path.write_bytes(b"broken json")
        state = self.store.read("global")
        self.assertIsNone(state["document"])
        self.assertIn("error", state)
        self.store.save("global", EMPTY, state["revision"])
        self.assertEqual(self.store.read("global")["document"], EMPTY)

    def test_oversized_file_can_be_reset_without_overwriting_a_newer_revision(self):
        _, path = self.store.target("global")
        path.parent.mkdir()
        content = b" " * (editor.MAX_DOCUMENT_BYTES + 1)
        path.write_bytes(content)
        state = self.store.configuration()["scopes"]["global"]
        self.assertIsNone(state["document"])
        self.assertEqual(state["revision"], editor.revision(content))
        self.assertIn("too large", state["error"])
        path.write_bytes(content + b" ")
        with self.assertRaises(editor.EditorError) as caught:
            self.store.save("global", EMPTY, state["revision"])
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(path.read_bytes(), content + b" ")
        self.store.save("global", EMPTY, self.store.read("global")["revision"])
        self.assertEqual(self.store.read("global")["document"], EMPTY)

    def test_preview_and_cli_resolver_same_inputs(self):
        request = {"interaction": "implementation", "tier": "demanding", "reason": "Several difficult interacting state transitions"}
        result = self.store.preview("global", LUNA, request)["decision"]
        snap = self.store.snapshot("global", LUNA)
        self.assertEqual(result, policy.resolve(snap, request))
        self.assertEqual(result["effort"], "xhigh")
        self.assertEqual(result["proposed_effort"], "max")
        self.assertFalse(self.store.target("global")[1].exists())

    def test_disabled_project_and_path_escape(self):
        store = editor.PreferenceStore(global_config_dir=self.root / "elsewhere")
        self.assertNotIn("project", store.configuration()["scopes"])
        with self.assertRaises(editor.EditorError):
            store.save("project", EMPTY, "missing")
        with self.assertRaises(editor.EditorError):
            editor.safe_path(self.project, self.root / "escape")

    def test_symlink_global_directory_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.root / "global").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(editor.EditorError):
            self.store.read("global")
        self.assertFalse(list(outside.iterdir()))


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        (self.assets / "index.html").write_text("<!doctype html><title>Editor</title>")
        (self.assets / "compatibility.json").write_text(json.dumps({"schema_version": 1, "policy_version": "4"}))
        self.store = editor.PreferenceStore(global_config_dir=self.root / "prefs")
        self.catalog = {"providers": {provider: {"status": "unavailable", "source": provider + "-cli",
                        "cli_version": None, "updated_at": None, "error": "CLI unavailable", "models": []}
                        for provider in ("codex", "claude")}}
        self.discovery = Mock()
        self.discovery.catalog.return_value = self.catalog
        self.server = editor.EditorServer(self.store, self.assets, discovery=self.discovery)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        merged = {"X-Clanker-Token": self.server.token, "Origin": self.server.origin, "Content-Type": "application/json"}
        merged.update(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, json.dumps(body) if body is not None else None, merged)
        response = connection.getresponse()
        content = response.read()
        result = response.status, content, dict(response.getheaders())
        connection.close()
        return result

    def test_page_bootstraps_session_without_uri_token(self):
        status, body, headers = self.request("GET", "/", headers={"X-Clanker-Token": ""})
        self.assertEqual(status, 200)
        self.assertIn(('content="' + self.server.token + '"').encode(), body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.request("GET", "/", headers={"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request("GET", "/", headers={"Host": "example.com"})[0], 403)

    def test_wrangler_requires_auth_origin_and_empty_payload(self):
        self.server.installer = Mock()
        self.server.installer.run.return_value = {"success": True, "message": "Done", "output": "copied", "truncated": False}
        self.assertEqual(self.request("POST", "/api/wrangler", {}, {"X-Clanker-Token": "wrong"})[0], 403)
        self.assertEqual(self.request("POST", "/api/wrangler", {}, {"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request("POST", "/api/wrangler", {"command": "anything"})[0], 400)
        self.server.installer.run.assert_not_called()
        status, body, _ = self.request("POST", "/api/wrangler", {})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["success"])
        self.server.installer.run.assert_called_once()

    def test_load_preview_save(self):
        status, body, _ = self.request("GET", "/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["scopes"]["global"]["revision"], "missing")
        request = {"scope": "global", "document": LUNA, "request": {"interaction": "implementation", "tier": "straightforward", "reason": "Clear bounded task"}}
        status, body, _ = self.request("POST", "/api/preview", request)
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["decision"]["effort"], "high")
        self.assertFalse(self.store.target("global")[1].exists())
        status, body, _ = self.request("POST", "/api/save", {"scope": "global", "document": LUNA, "revision": "missing"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.store.read("global")["document"], LUNA)

    def test_project_scope_rejected_before_store_access(self):
        with patch.object(self.store, "preview") as preview, patch.object(self.store, "save") as save:
            for endpoint in ("/api/preview", "/api/save"):
                status, body, _ = self.request("POST", endpoint, {"scope": "project", "document": EMPTY})
                self.assertEqual(status, 400, body)
            preview.assert_not_called()
            save.assert_not_called()

    def test_session_and_origin_boundaries(self):
        for headers in ({"X-Clanker-Token": "wrong"}, {"Origin": "https://other.example"}, {"Host": "rebind.example"}):
            self.assertEqual(self.request("GET", "/api/config", headers=headers)[0], 403)
        self.assertEqual(self.request("POST", "/api/save", {"scope": "global", "document": EMPTY, "revision": "missing"}, {"Origin": "null"})[0], 403)

    def test_paths_and_execution_not_exposed(self):
        self.assertEqual(self.request("GET", "/%2e%2e/outside")[0], 403)
        self.assertEqual(self.request("GET", "/api/config?path=elsewhere")[0], 400)
        self.assertEqual(self.request("POST", "/api/execute", {})[0], 404)
        self.assertEqual(self.request("POST", "/api/save", {"scope": "global", "document": EMPTY, "revision": "missing", "path": "elsewhere"})[0], 400)
        self.assertFalse(self.store.target("global")[1].exists())

    def test_oversized_and_wrong_content_type(self):
        self.assertEqual(self.request("POST", "/api/preview", {"scope": "global", "document": EMPTY}, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/preview", {"large": "x" * editor.MAX_DOCUMENT_BYTES})[0], 413)

    def test_conflict_response_and_security_headers(self):
        self.store.save("global", EMPTY, "missing")
        status, body, headers = self.request("POST", "/api/save", {"scope": "global", "document": LUNA, "revision": "missing"})
        self.assertEqual(status, 409)
        self.assertIn("error", json.loads(body))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_catalog_get_refresh_and_preferences_unchanged(self):
        before = self.store.configuration()
        for method, path, payload in (("GET", "/api/models", None), ("POST", "/api/models/refresh", {})):
            status, body, headers = self.request(method, path, payload)
            self.assertEqual(status, 200, body)
            self.assertEqual(json.loads(body), self.catalog)
            self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.discovery.catalog.call_args_list[0].kwargs, {})
        self.assertEqual(self.discovery.catalog.call_args_list[1].kwargs, {"force": True})
        self.assertEqual(self.store.configuration(), before)
        self.assertFalse(self.store.target("global")[1].exists())

    def test_discovery_rejected_requests_never_probe(self):
        for headers in ({"X-Clanker-Token": "wrong"}, {"Origin": "https://other.example"}, {"Host": "rebind.example"}):
            self.assertEqual(self.request("GET", "/api/models", headers=headers)[0], 403)
            self.assertEqual(self.request("POST", "/api/models/refresh", {}, headers)[0], 403)
        for payload in ({"path": "elsewhere"}, {"provider": "codex"}, {"args": []}, []):
            self.assertEqual(self.request("POST", "/api/models/refresh", payload)[0], 400)
        self.assertEqual(self.request("GET", "/api/models?path=elsewhere")[0], 400)
        self.assertEqual(self.request("POST", "/api/models/refresh?path=elsewhere", {})[0], 404)
        self.assertEqual(self.request("POST", "/api/models/refresh", {}, {"Origin": "null"})[0], 403)
        self.assertEqual(self.request("POST", "/api/models/refresh", {}, {"Content-Type": "text/plain"})[0], 415)
        self.discovery.catalog.assert_not_called()

    def test_discovery_closed_has_specific_503(self):
        self.discovery.catalog.side_effect = editor.DiscoveryClosed()
        for method, path, payload in (("GET", "/api/models", None), ("POST", "/api/models/refresh", {})):
            status, body, _ = self.request(method, path, payload)
            self.assertEqual(status, 503)
            self.assertEqual(json.loads(body), {"error": "Model discovery is shutting down."})

    def test_config_responds_while_discovery_is_pending(self):
        entered, release = threading.Event(), threading.Event()
        def slow_catalog():
            entered.set()
            release.wait(3)
            return self.catalog
        self.discovery.catalog.side_effect = slow_catalog
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(self.request, "GET", "/api/models")
            try:
                self.assertTrue(entered.wait(1))
                self.assertEqual(self.request("GET", "/api/config")[0], 200)
            finally:
                release.set()
            self.assertEqual(result.result(timeout=3)[0], 200)

    def test_server_close_closes_discovery(self):
        self.server.shutdown()
        self.server.server_close()
        self.discovery.close.assert_called_once_with()

    def test_incompatible_or_missing_assets(self):
        with self.assertRaises(editor.EditorError):
            editor.asset_root(self.root / "missing")
        (self.assets / "compatibility.json").write_text('{"schema_version":2,"policy_version":"1"}')
        with self.assertRaises(editor.EditorError):
            editor.asset_root(self.assets)
        (self.assets / "compatibility.json").write_text('{"schema_version":1,"policy_version":"2"}')
        with self.assertRaisesRegex(editor.EditorError, "rebuild and reinstall"):
            editor.asset_root(self.assets)


if __name__ == "__main__":
    unittest.main()

class WranglerTests(unittest.TestCase):
    def test_result_and_duplicate_guard(self):
        installer = editor.WranglerInstaller()
        installer.lock.acquire()
        with self.assertRaises(editor.EditorError):
            installer.run()
        installer.lock.release()
        def execute(command, **kwargs):
            self.assertNotIn("shell", kwargs)
            kwargs["stdout"].write(b"installer output")
            return Mock(returncode=1)
        with patch.object(installer, "command", return_value=["fixed-installer"]), patch.object(editor.subprocess, "run", side_effect=execute):
            result = installer.run()
        self.assertFalse(result["success"])
        self.assertEqual(result["output"], "installer output")
        self.assertFalse(installer.lock.locked())

    def test_timeout_and_unavailable_checkout(self):
        installer = editor.WranglerInstaller()
        with tempfile.TemporaryDirectory() as temporary:
            installer.root = Path(temporary)
            self.assertFalse(installer.status()["available"])
        with patch.object(installer, "command", return_value=["fixed-installer"]), patch.object(editor.subprocess, "run", side_effect=editor.subprocess.TimeoutExpired("fixed", 120)):
            result = installer.run()
        self.assertFalse(result["success"])
        self.assertIn("partial", result["message"])
        self.assertFalse(installer.lock.locked())
