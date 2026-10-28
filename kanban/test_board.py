import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from uuid import uuid4

from board import BoardError, ROOT, TaskStore, build, make_server


def task(**changes):
    return {
        "title": "Review lab setup",
        "description": "## Instructions\n\nRun the lab.\n\n---\n\nCheck Unicode: café.\n",
        "assignee": "Meghan",
        "priority": "high",
        "labels": ["docs", "lab"],
        "acceptanceCriteria": ["Commands run from a clean checkout", "Output matches the README"],
        "status": "todo",
        **changes,
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "tasks"
        self.store = TaskStore(self.directory)

    def test_markdown_persists_all_fields_across_store_instances(self):
        created = self.store.create_task(task())
        files = list(self.directory.iterdir())
        self.assertEqual([created["id"] + ".md"], [path.name for path in files])
        markdown = files[0].read_text(encoding="utf-8")
        self.assertTrue(markdown.startswith("---\n{"))
        self.assertIn("## Instructions", markdown)
        self.assertIn('"acceptanceCriteria": [', markdown)
        self.assertEqual([{"id": created["id"], **task()}], TaskStore(self.directory).list_tasks())

    def test_edit_and_move_keep_the_same_filename(self):
        created = self.store.create_task(task())
        changed = task(title="Verify lab setup", status="in-progress", priority="low", assignee="", labels=[], acceptanceCriteria=[])
        self.store.update_task(created["id"], changed)
        self.assertEqual([{"id": created["id"], **changed}], self.store.list_tasks())
        self.assertEqual([created["id"] + ".md"], [path.name for path in self.directory.iterdir()])
        self.store.delete_task(created["id"])
        self.assertEqual([], self.store.list_tasks())
        self.assertEqual([], list(self.directory.iterdir()))

    def test_manual_markdown_edits_appear_on_next_load(self):
        created = self.store.create_task(task())
        path = self.directory / (created["id"] + ".md")
        path.write_text(path.read_text(encoding="utf-8").replace('"status": "todo"', '"status": "done"'), encoding="utf-8")
        self.assertEqual("done", self.store.list_tasks()[0]["status"])

    def test_invalid_fields_never_create_files(self):
        invalid = [
            task(title="  "), task(status="blocked"), task(priority="urgent"), task(labels="docs"),
            task(acceptanceCriteria=[True]), task(description=None), task(assignee=[]), task(labels=[""]),
            task(labels=["one,two"]), task(labels=["one\ntwo"]), task(acceptanceCriteria=["one\ntwo"]),
            {**task(), "id": "client-provided"}, {key: value for key, value in task().items() if key != "title"},
        ]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(BoardError):
                self.store.create_task(data)
        self.assertFalse(self.directory.exists())

    def test_malformed_markdown_reports_filename(self):
        self.directory.mkdir()
        name = str(uuid4()) + ".md"
        (self.directory / name).write_text("---\nnot json\n---\n\nDescription", encoding="utf-8")
        with self.assertRaisesRegex(BoardError, name):
            self.store.list_tasks()

    def test_traversal_and_symlinks_cannot_change_other_files(self):
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text("keep this", encoding="utf-8")
        self.directory.mkdir()
        task_id = str(uuid4())
        link = self.directory / (task_id + ".md")
        link.symlink_to(outside)
        for operation in (
            lambda: self.store.list_tasks(),
            lambda: self.store.update_task(task_id, task()),
            lambda: self.store.delete_task(task_id),
            lambda: self.store.delete_task("../outside"),
        ):
            with self.assertRaises(BoardError):
                operation()
        self.assertEqual("keep this", outside.read_text(encoding="utf-8"))
        self.assertTrue(link.is_symlink())

    def test_export_contains_read_only_snapshot_and_only_browser_assets(self):
        created = self.store.create_task(task())
        output = Path(self.temporary.name) / "site"
        build(output, self.store)
        self.assertEqual({"index.html", "app.js", "style.css", "board.json", ".nojekyll"}, {path.name for path in output.iterdir()})
        self.assertEqual({"readOnly": True, "tasks": [created]}, json.loads((output / "board.json").read_text(encoding="utf-8")))
        for name in ("index.html", "app.js", "style.css"):
            self.assertEqual((ROOT / "web" / name).read_bytes(), (output / name).read_bytes())
        self.store.update_task(created["id"], task(status="done"))
        build(output, self.store)
        self.assertEqual("done", json.loads((output / "board.json").read_text(encoding="utf-8"))["tasks"][0]["status"])

    def test_export_refuses_source_tasks_and_unrelated_files(self):
        self.store.create_task(task())
        destinations = [ROOT, ROOT / "web", self.directory, self.directory / "export", self.directory.parent]
        for destination in destinations:
            with self.subTest(destination=destination), self.assertRaises(BoardError):
                build(destination, self.store)
        output = Path(self.temporary.name) / "existing"
        output.mkdir()
        keep = output / "keep.txt"
        keep.write_text("keep this", encoding="utf-8")
        with self.assertRaises(BoardError):
            build(output, self.store)
        self.assertEqual("keep this", keep.read_text(encoding="utf-8"))


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = TaskStore(Path(self.temporary.name) / "tasks")
        self.server = make_server(self.store, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, data=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        payload = raw if raw is not None else json.dumps(data) if data is not None else None
        connection.request(method, path, body=payload, headers={"Content-Type": "application/json", **(headers or {})})
        response = connection.getresponse()
        body = response.read()
        status, content_type = response.status, response.getheader("Content-Type", "")
        connection.close()
        return status, json.loads(body) if body and content_type.startswith("application/json") else body

    def test_browser_api_create_edit_move_reload_delete(self):
        self.assertEqual((200, {"readOnly": False, "tasks": []}), self.request("GET", "/board.json"))
        status, created = self.request("POST", "/api/tasks", task())
        self.assertEqual(201, status)
        self.assertEqual(task(), {key: value for key, value in created.items() if key != "id"})
        endpoint = "/api/tasks/" + created["id"]
        changed = task(title="Updated title", status="in-progress", description="A new description", labels=["updated"], acceptanceCriteria=["Updated criterion"])
        self.assertEqual((200, {"id": created["id"], **changed}), self.request("PUT", endpoint, changed))
        self.assertEqual((200, {"readOnly": False, "tasks": [{"id": created["id"], **changed}]}), self.request("GET", "/board.json"))
        self.assertEqual("in-progress", TaskStore(self.store.directory).list_tasks()[0]["status"])
        self.assertEqual((204, b""), self.request("DELETE", endpoint))
        self.assertEqual([], self.request("GET", "/board.json")[1]["tasks"])
        self.assertEqual(404, self.request("DELETE", endpoint)[0])
        self.assertEqual(404, self.request("PUT", endpoint, task())[0])

    def test_invalid_requests_return_json_and_leave_tasks_unchanged(self):
        for headers, raw, status in (
            ({"Origin": "https://example.com"}, None, 403),
            ({"Host": "attacker.example"}, None, 403),
            ({"Content-Type": "text/plain"}, None, 415),
            ({"Sec-Fetch-Site": "cross-site"}, None, 403),
            ({}, "{invalid", 400),
        ):
            with self.subTest(headers=headers, raw=raw):
                actual, data = self.request("POST", "/api/tasks", task(), headers=headers, raw=raw)
                self.assertEqual(status, actual)
                self.assertIn("error", data)
        self.assertEqual(400, self.request("POST", "/api/tasks", task(status="unknown"))[0])
        self.assertEqual([], self.store.list_tasks())

    def test_same_origin_fetch_is_allowed(self):
        origin = "http://127.0.0.1:" + str(self.server.server_port)
        self.assertEqual(201, self.request("POST", "/api/tasks", task(), headers={"Origin": origin})[0])

    def test_server_only_serves_board_assets(self):
        for path in ("/", "/index.html", "/app.js", "/style.css"):
            self.assertEqual(200, self.request("GET", path)[0])
        for path in ("/../README.md", "/%2e%2e/README.md", "/board.py", "/tasks/", "/.git/config"):
            self.assertEqual(404, self.request("GET", path)[0])
        self.assertEqual(400, self.request("DELETE", "/api/tasks/../../README.md")[0])
        self.assertEqual(403, self.request("GET", "/board.json", headers={"Host": "evil.test"})[0])

    def test_invalid_markdown_is_visible_in_api_errors(self):
        self.store.directory.mkdir()
        name = str(uuid4()) + ".md"
        (self.store.directory / name).write_text("broken", encoding="utf-8")
        status, data = self.request("GET", "/board.json")
        self.assertEqual(400, status)
        self.assertIn(name, data["error"])


if __name__ == "__main__":
    unittest.main()
