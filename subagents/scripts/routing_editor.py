"""Loopback-only editor for explicit Clanker routing preference destinations."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import signal
import stat
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

import routing_policy as policy
from model_discovery import DiscoveryClosed, DiscoveryManager

MAX_DOCUMENT_BYTES = 262144
API_VERSION = 1
POLICY_VERSION = "2"


class EditorError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def linked(path: Path) -> bool:
    try:
        value = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, "st_file_attributes", 0) & 0x400)


def safe_path(root: Path, path: Path) -> Path:
    """Check lexical containment and every component below an already pinned root."""
    root, path = root.absolute(), path.absolute()
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise EditorError("Path is outside the configured destination", 403) from None
    current = root
    for part in relative.parts:
        if part in ("..", "."):
            raise EditorError("Invalid path component", 403)
        current = current / part
        if linked(current):
            raise EditorError("Linked configuration or asset paths are not allowed", 403)
    if not path.resolve().is_relative_to(root.resolve()):
        raise EditorError("Path escapes the configured destination", 403)
    return path


def revision(content: bytes | None) -> str:
    return "missing" if content is None else hashlib.sha256(content).hexdigest()


def reject_constant(value: str):
    raise ValueError("Non-finite JSON values are not supported")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json(content: bytes):
    return json.loads(content.decode("utf-8-sig"), parse_constant=reject_constant, object_pairs_hook=unique_object)


class PreferenceStore:
    """The browser selects scope only; paths are fixed by the process owner."""
    def __init__(self, project: Path | None = None, global_config_dir: Path | None = None):
        if global_config_dir is None:
            home = Path.home().resolve()
            self.targets = {"global": (home, home / ".clanker" / "orchestration-routing.json")}
        else:
            directory = Path(global_config_dir).absolute()
            anchor = directory.parent.resolve()
            self.targets = {"global": (anchor, anchor / directory.name / "orchestration-routing.json")}
        if project is not None:
            root = Path(project).resolve(strict=True)
            if not root.is_dir():
                raise EditorError("Project must be an existing directory")
            self.targets["project"] = (root, root / ".clanker" / "orchestration-routing.json")
        for anchor, target in self.targets.values():
            safe_path(anchor, target)
        self._mutex = threading.RLock()

    def target(self, scope: str) -> tuple[Path, Path]:
        if scope not in self.targets:
            raise EditorError("Selected configuration scope is unavailable")
        anchor, target = self.targets[scope]
        return anchor, safe_path(anchor, target)

    def read(self, scope: str) -> dict:
        anchor, target = self.target(scope)
        content = None
        try:
            if target.exists():
                if not target.is_file():
                    raise EditorError("Configuration destination is not a file")
                # Hash the full file for conflict-safe explicit repair, but retain
                # only bounded content for JSON parsing, even if it grows mid-read.
                digest = hashlib.sha256()
                chunks = []
                size = 0
                with target.open("rb") as source:
                    while chunk := source.read(65536):
                        digest.update(chunk)
                        size += len(chunk)
                        if size <= MAX_DOCUMENT_BYTES:
                            chunks.append(chunk)
                if size > MAX_DOCUMENT_BYTES:
                    return {"path": str(target), "revision": digest.hexdigest(), "document": None,
                            "error": "Invalid saved preferences: configuration file is too large"}
                content = b"".join(chunks)
            document = {"schema_version": 1} if content is None else parse_json(content)
            policy.validate_preferences(document)
            return {"path": str(target), "revision": revision(content), "document": document}
        except (ValueError, policy.RoutingError) as error:
            return {"path": str(target), "revision": revision(content), "document": None,
                    "error": "Invalid saved preferences: " + str(error)}

    def snapshot(self, scope: str, document: dict | None = None):
        self.target(scope)
        global_state = self.read("global")
        project_state = self.read("project") if scope == "project" else None
        states = {"global": global_state, "project": project_state}
        documents = {}
        for layer, state in states.items():
            if state is None:
                documents[layer] = None
            elif layer == scope and document is not None:
                documents[layer] = document
            elif state.get("error"):
                raise EditorError(state["error"])
            else:
                documents[layer] = state["document"]
        sources = {key: value["path"] for key, value in states.items() if value is not None}
        return policy.snapshot_from_documents(documents["global"], documents["project"], sources=sources)

    def configuration(self) -> dict:
        states = {"global": self.read("global"), "project": self.read("project") if "project" in self.targets else None}
        result = {"schema_version": API_VERSION, "policy_version": POLICY_VERSION, "scopes": states,
                  "bundle": policy.load_bundle(), "effective": None}
        try:
            for state in states.values():
                if state is not None and state.get("error"):
                    raise EditorError(state["error"])
            frozen = policy.snapshot_from_documents(
                states["global"]["document"],
                states["project"]["document"] if states["project"] else None,
                sources={key: value["path"] for key, value in states.items() if value is not None},
            )
            result["effective"] = policy.effective_configuration(frozen)
        except (EditorError, policy.RoutingError, ValueError) as error:
            result["error"] = str(error)
        return result

    def preview(self, scope: str, document: dict, request: dict | None = None) -> dict:
        policy.validate_preferences(document)
        snapshot = self.snapshot(scope, document)
        return {"effective": policy.effective_configuration(snapshot),
                "decision": policy.resolve(snapshot, request) if request is not None else None}

    def save(self, scope: str, document: dict, expected_revision: str) -> dict:
        if not isinstance(expected_revision, str) or not expected_revision:
            raise EditorError("A loaded revision is required")
        serialized = (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        if len(serialized) > MAX_DOCUMENT_BYTES:
            raise EditorError("Configuration document is too large")
        self.preview(scope, document)
        anchor, target = self.target(scope)
        lock = target.with_suffix(".json.lock")
        temp_path = None
        lock_owned = False
        with self._mutex:
            safe_path(anchor, target.parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            safe_path(anchor, lock)
            try:
                try:
                    lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except FileExistsError:
                    raise EditorError("Configuration is locked by another save. If its process has exited, inspect the .lock owner record before manually removing the stale lock.", 409) from None
                lock_owned = True
                with os.fdopen(lock_fd, "w", encoding="utf-8") as output:
                    json.dump({"pid": os.getpid(), "started_at": time.time()}, output)
                state = self.read(scope)
                if state["revision"] != expected_revision:
                    raise EditorError("Preferences changed since loading. Reload the latest revision before saving your draft.", 409)
                self.preview(scope, document)
                descriptor, name = tempfile.mkstemp(prefix="routing-", suffix=".tmp", dir=target.parent)
                temp_path = Path(name)
                with os.fdopen(descriptor, "wb") as output:
                    output.write(serialized)
                    output.flush()
                    os.fsync(output.fileno())
                safe_path(anchor, target)
                # Detect non-cooperating edits as late as possible. An external writer
                # can still race between this check and replace; no CAS is promised.
                if self.read(scope)["revision"] != expected_revision:
                    raise EditorError("Preferences changed during saving; saved content was preserved.", 409)
                os.replace(temp_path, target)
                temp_path = None
            finally:
                if temp_path is not None:
                    safe_path(anchor, temp_path).unlink(missing_ok=True)
                if lock_owned:
                    safe_path(anchor, lock).unlink(missing_ok=True)
        return self.configuration()


def asset_root(explicit: Path | None = None) -> Path:
    package = Path(__file__).resolve().parent.parent
    candidates = [explicit] if explicit is not None else [package / "editor", package.parent / "routing-editor" / "dist"]
    for candidate in candidates:
        if candidate is None or not candidate.exists():
            continue
        candidate = candidate.absolute()
        if linked(candidate):
            raise EditorError("Linked editor asset directories are not allowed")
        root = candidate.resolve()
        manifest = safe_path(root, root / "compatibility.json")
        index = safe_path(root, root / "index.html")
        if not manifest.is_file() or not index.is_file():
            raise EditorError("Editor build is incomplete; rebuild routing-editor")
        metadata = parse_json(manifest.read_bytes())
        if metadata != {"schema_version": API_VERSION, "policy_version": POLICY_VERSION}:
            raise EditorError("Editor build is incompatible with this routing helper; rebuild and reinstall")
        return root
    raise EditorError("Editor build is unavailable. In routing-editor run npm ci and npm run build, then restart this command.")


class WranglerInstaller:
    """Only run the installer belonging to this helper's source checkout."""

    def __init__(self):
        self.root = Path(__file__).resolve().parents[2]
        self.lock = threading.Lock()

    def command(self):
        script = self.root / ("wrangle.ps1" if os.name == "nt" else "wrangle.sh")
        if not script.is_file() or script.is_symlink() or not (self.root / "global_rules.md").is_file():
            raise EditorError("Run Wrangler is available only from the ClankerWrangler source checkout.", 409)
        executable = shutil.which("pwsh") or shutil.which("powershell") if os.name == "nt" else shutil.which("bash")
        if not executable:
            raise EditorError("The installer requires PowerShell on Windows or Bash on other platforms.", 409)
        return [executable, "-NoProfile", "-NonInteractive", "-File", str(script)] if os.name == "nt" else [executable, str(script)]

    def status(self):
        try:
            self.command()
            return {"available": True, "running": self.lock.locked()}
        except EditorError as error:
            return {"available": False, "running": False, "reason": str(error)}

    def run(self):
        if not self.lock.acquire(blocking=False):
            raise EditorError("Wrangler is already running. Wait for it to finish.", 409)
        try:
            command = self.command()
            # The known installers only copy local files; no browser arguments or shell strings.
            with tempfile.TemporaryFile() as output:
                try:
                    result = subprocess.run(command, cwd=self.root, stdin=subprocess.DEVNULL,
                                            stdout=output, stderr=subprocess.STDOUT, timeout=120,
                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                    success, message = result.returncode == 0, "Wrangler completed." if result.returncode == 0 else "Wrangler failed; some files may have been installed."
                except subprocess.TimeoutExpired:
                    success, message = False, "Wrangler exceeded two minutes; installation may be partial."
                output.seek(0, 2)
                size = output.tell()
                output.seek(max(0, size - 65536))
                text = output.read().decode("utf-8", errors="replace")
            return {"success": success, "message": message, "output": text, "truncated": size > 65536}
        except OSError:
            raise EditorError("Could not start Wrangler. Check the local installer and permissions.", 500) from None
        finally:
            self.lock.release()


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, store: PreferenceStore, assets: Path, port: int = 0, discovery=None):
        self.store = store
        self.assets = asset_root(assets)
        self.token = secrets.token_urlsafe(32)
        self.installer = WranglerInstaller()
        super().__init__(("127.0.0.1", port), EditorHandler)
        self.origin = "http://127.0.0.1:" + str(self.server_port)
        self.discovery = discovery if discovery is not None else DiscoveryManager()

    def server_close(self):
        try:
            if hasattr(self, "discovery"):
                self.discovery.close()
        finally:
            super().server_close()


class EditorHandler(BaseHTTPRequestHandler):
    server: EditorServer

    def log_message(self, format, *args):
        # Request bodies, paths and authorization headers never enter server logs.
        pass

    def send_content(self, status: int, content: bytes, mime: str):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(content)

    def json_response(self, status: int, value):
        self.send_content(status, json.dumps(value, allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")

    def boundary(self, api: bool, write: bool = False):
        if self.headers.get("Host") != self.server.origin.removeprefix("http://"):
            raise EditorError("Unexpected Host", 403)
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            raise EditorError("Unexpected Origin", 403)
        if write and origin != self.server.origin:
            raise EditorError("A same-origin request is required", 403)
        if api and not secrets.compare_digest(self.headers.get("X-Clanker-Token", ""), self.server.token):
            raise EditorError("Editor session authorization is required", 403)

    def payload(self):
        if self.headers.get_content_type() != "application/json":
            raise EditorError("Expected application/json", 415)
        if self.headers.get("Transfer-Encoding"):
            raise EditorError("Transfer encoding is unsupported")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise EditorError("Content-Length is required") from None
        if length < 0 or length > MAX_DOCUMENT_BYTES:
            raise EditorError("Request is too large", 413)
        self.connection.settimeout(10)
        value = parse_json(self.rfile.read(length))
        if not isinstance(value, dict):
            raise EditorError("Expected a JSON object")
        return value

    def handle_error(self, error):
        if isinstance(error, DiscoveryClosed):
            self.json_response(503, {"error": "Model discovery is shutting down."})
        elif isinstance(error, EditorError):
            self.json_response(error.status, {"error": str(error)})
        elif isinstance(error, (policy.RoutingError, ValueError, TypeError)):
            self.json_response(400, {"error": str(error)})
        else:
            self.json_response(500, {"error": "Could not access the selected configuration. Check local filesystem permissions."})

    def do_GET(self):
        try:
            parsed = urlsplit(self.path)
            path = unquote(parsed.path)
            api = path.startswith("/api/")
            self.boundary(api)
            if parsed.query or parsed.fragment:
                raise EditorError("Query parameters are unsupported")
            if path == "/api/wrangler":
                self.json_response(200, self.server.installer.status())
            elif path == "/api/config":
                self.json_response(200, {**self.server.store.configuration(), "wrangler": self.server.installer.status()})
            elif path == "/api/models":
                self.json_response(200, self.server.discovery.catalog())
            elif api:
                raise EditorError("Unknown endpoint", 404)
            else:
                if "\\" in path or any(part in ("..", ".") for part in path.split("/")):
                    raise EditorError("Invalid asset path", 403)
                relative = "index.html" if path == "/" else path.lstrip("/")
                target = safe_path(self.server.assets, self.server.assets / relative)
                if not target.is_file():
                    raise EditorError("Asset not found", 404)
                mime = "text/javascript" if target.suffix == ".js" else mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                content = target.read_bytes()
                if relative == "index.html":
                    meta = ('<meta name="clanker-session-token" content="' + self.server.token + '">').encode("ascii")
                    content = content.replace(b"<head>", b"<head>" + meta, 1) if b"<head>" in content else meta + content
                self.send_content(200, content, mime)
        except (DiscoveryClosed, EditorError, policy.RoutingError, ValueError, TypeError, OSError) as error:
            self.handle_error(error)

    def do_POST(self):
        try:
            self.boundary(True, write=True)
            if self.path not in ("/api/preview", "/api/save", "/api/models/refresh", "/api/wrangler"):
                raise EditorError("Unknown endpoint", 404)
            value = self.payload()
            if self.path == "/api/wrangler":
                if value:
                    raise EditorError("Wrangler accepts only an empty object; paths and commands cannot be supplied.")
                self.json_response(200, self.server.installer.run())
                return
            if self.path == "/api/models/refresh":
                if value:
                    raise EditorError("Model refresh accepts only an empty object")
                self.json_response(200, self.server.discovery.catalog(force=True))
                return
            allowed = {"scope", "document", "request"} if self.path == "/api/preview" else {"scope", "document", "revision"}
            if set(value) - allowed or not {"scope", "document"}.issubset(value):
                raise EditorError("Unsupported or missing request fields")
            if value["scope"] not in ("global", "project"):
                raise EditorError("Invalid configuration scope")
            if self.path == "/api/preview":
                result = self.server.store.preview(value["scope"], value["document"], value.get("request"))
            else:
                result = self.server.store.save(value["scope"], value["document"], value.get("revision"))
                result["wrangler"] = self.server.installer.status()
            self.json_response(200, result)
        except (DiscoveryClosed, EditorError, policy.RoutingError, ValueError, TypeError, OSError) as error:
            self.handle_error(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, help="Existing project whose routing overrides may be edited")
    parser.add_argument("--global-config-dir", type=Path, help="Explicit alternative to ~/.clanker, useful for isolated testing")
    parser.add_argument("--assets", type=Path, help="Explicit compatible built editor directory")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    def stop_requested(signum, frame):
        raise KeyboardInterrupt
    previous_term = signal.signal(signal.SIGTERM, stop_requested)
    try:
        if not 0 <= args.port <= 65535:
            raise EditorError("Port must be between 0 and 65535")
        store = PreferenceStore(args.project, args.global_config_dir)
        with EditorServer(store, asset_root(args.assets), args.port) as server:
            print("Open the local editor: " + server.origin + "/#token=" + server.token, flush=True)
            print("Global preferences: " + str(store.target("global")[1]), flush=True)
            if args.project:
                print("Project preferences: " + str(store.target("project")[1]), flush=True)
            print("Press Ctrl+C to stop. No agents or model inference are launched by this editor.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (EditorError, policy.RoutingError, OSError, ValueError) as error:
        print("Editor unavailable: " + str(error))
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_term)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
