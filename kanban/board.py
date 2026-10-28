#!/usr/bin/env python3
"""Local Markdown Kanban editor and read-only static exporter."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
ASSETS = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}
STATUSES = ("todo", "in-progress", "done")
PRIORITIES = ("low", "medium", "high")
FIELDS = {"title", "description", "assignee", "priority", "labels", "acceptanceCriteria", "status"}
TASK_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


class BoardError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def validate_task(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise BoardError("Task fields must be exactly: " + ", ".join(sorted(FIELDS)))
    for field in ("title", "description", "assignee", "status", "priority"):
        if not isinstance(data[field], str):
            raise BoardError(field + " must be a string")
    if not data["title"].strip():
        raise BoardError("A title is required")
    if data["status"] not in STATUSES:
        raise BoardError("Status must be todo, in-progress, or done")
    if data["priority"] not in PRIORITIES:
        raise BoardError("Priority must be low, medium, or high")
    for field in ("labels", "acceptanceCriteria"):
        if not isinstance(data[field], list) or any(
            not isinstance(value, str) or not value.strip() for value in data[field]
        ):
            raise BoardError(field + " must be an array of nonempty strings")
        if any("\n" in value or "\r" in value for value in data[field]):
            raise BoardError(field + " entries must each fit on one line")
    if any("," in label for label in data["labels"]):
        raise BoardError("Labels cannot contain commas")
    return {**data, "title": data["title"].strip(), "assignee": data["assignee"].strip()}


class TaskStore:
    def __init__(self, directory=ROOT / "tasks"):
        self.directory = Path(directory).resolve()

    def _path(self, task_id):
        if not TASK_ID.fullmatch(task_id):
            raise BoardError("Invalid task ID")
        path = self.directory / (task_id + ".md")
        if path.is_symlink():
            raise BoardError("Task symlinks are not supported: " + path.name)
        return path

    def _read(self, path):
        try:
            self._path(path.stem)
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n"):
                raise ValueError("Expected JSON front matter between --- lines")
            metadata, separator, body = text[4:].partition("\n---\n")
            if not separator:
                raise ValueError("Expected a closing --- line after JSON front matter")
            data = json.loads(metadata)
            if not isinstance(data, dict) or "description" in data or "id" in data:
                raise ValueError("Keep id out of front matter and description in the Markdown body")
            data["description"] = body[1:] if body.startswith("\n") else body
            return {"id": path.stem, **validate_task(data)}
        except (ValueError, UnicodeError) as error:
            raise BoardError(path.name + ": " + str(error)) from error

    def _write(self, task_id, data):
        path = self._path(task_id)
        self.directory.mkdir(parents=True, exist_ok=True)
        metadata = {key: value for key, value in data.items() if key != "description"}
        text = "---\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n\n" + data["description"]
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory, suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                file.write(text)
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return {"id": task_id, **data}

    def list_tasks(self):
        return [self._read(path) for path in sorted(self.directory.glob("*.md"))]

    def create_task(self, data):
        return self._write(str(uuid4()), validate_task(data))

    def update_task(self, task_id, data):
        path = self._path(task_id)
        if not path.is_file():
            raise BoardError("Task not found", 404)
        self._read(path)
        return self._write(task_id, validate_task(data))

    def delete_task(self, task_id):
        path = self._path(task_id)
        if not path.is_file():
            raise BoardError("Task not found", 404)
        path.unlink()


def build(output, store):
    output = Path(output).resolve()
    overlaps_tasks = output == store.directory or output in store.directory.parents or store.directory in output.parents
    overlaps_source = output == ROOT or output in ROOT.parents or ROOT in output.parents
    if overlaps_tasks or (overlaps_source and output != ROOT / "dist"):
        raise BoardError("Build output must be separate from the source and task directories")
    names = set(ASSETS) | {"board.json", ".nojekyll"}
    if output.exists() and (not output.is_dir() or any(path.name not in names or path.is_symlink() or not path.is_file() for path in output.iterdir())):
        raise BoardError("Build output must be empty or contain only generated board files")
    snapshot = json.dumps({"readOnly": True, "tasks": store.list_tasks()}, ensure_ascii=False, indent=2)
    assets = {name: (ROOT / "web" / name).read_bytes() for name in ASSETS}
    output.mkdir(parents=True, exist_ok=True)
    for name, content in assets.items():
        (output / name).write_bytes(content)
    (output / "board.json").write_text(snapshot + "\n", encoding="utf-8")
    (output / ".nojekyll").touch()


class BoardHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format, *args):
        pass

    def _respond(self, status, data=None, content_type="application/json"):
        body = b"" if data is None else data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _check_request(self, mutation):
        port = self.server.server_port
        hosts = {"127.0.0.1:" + str(port), "localhost:" + str(port)}
        if port == 80:
            hosts.update({"127.0.0.1", "localhost"})
        host = self.headers.get("Host", "")
        if host not in hosts:
            raise BoardError("Only the local board host is allowed", 403)
        if mutation:
            origin = self.headers.get("Origin")
            if origin is not None and origin != "http://" + host:
                raise BoardError("Only same-origin changes are allowed", 403)
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise BoardError("Only same-origin changes are allowed", 403)
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise BoardError("Changes require application/json", 415)

    def _data(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise BoardError("Invalid Content-Length") from error
        if not 0 < size <= 1024 * 1024:
            raise BoardError("Request body must contain JSON and be at most 1 MiB", 413)
        try:
            return json.loads(self.rfile.read(size))
        except (ValueError, UnicodeError) as error:
            raise BoardError("Request body must be valid JSON") from error

    def _handle(self, method):
        try:
            self._check_request(method != "GET")
            path = urlsplit(self.path).path
            if method == "GET" and path == "/board.json":
                self._respond(200, {"readOnly": False, "tasks": self.server.store.list_tasks()})
            elif method == "GET" and (path == "/" or path[1:] in ASSETS):
                name = "index.html" if path == "/" else path[1:]
                self._respond(200, (ROOT / "web" / name).read_bytes(), ASSETS[name])
            elif method == "POST" and path == "/api/tasks":
                self._respond(201, self.server.store.create_task(self._data()))
            elif method in ("PUT", "DELETE") and path.startswith("/api/tasks/"):
                task_id = path[len("/api/tasks/"):]
                if method == "PUT":
                    self._respond(200, self.server.store.update_task(task_id, self._data()))
                else:
                    self.server.store.delete_task(task_id)
                    self._respond(204)
            else:
                raise BoardError("Not found", 404)
        except BoardError as error:
            self._respond(error.status, {"error": str(error)})
        except OSError as error:
            self._respond(500, {"error": str(error)})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")


def make_server(store, port=8765):
    server = HTTPServer(("127.0.0.1", port), BoardHandler)
    server.store = store
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Run the local editor")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    export = commands.add_parser("build", help="Export the read-only board")
    export.add_argument("--output", type=Path, default=ROOT / "dist")
    export.add_argument("--tasks-dir", type=Path, default=ROOT / "tasks")
    args = parser.parse_args()
    store = TaskStore(args.tasks_dir)
    try:
        if args.command == "build":
            build(args.output, store)
            print("Read-only board written to " + str(args.output.resolve()))
        else:
            with make_server(store, args.port) as server:
                print("Cardinal board at http://127.0.0.1:" + str(server.server_port), flush=True)
                print("Tasks in " + str(store.directory), flush=True)
                server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (BoardError, OSError, ValueError) as error:
        print("Error: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
