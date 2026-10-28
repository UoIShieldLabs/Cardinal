# Cardinal board

Create, edit, move, and delete tasks in a local browser. Each task lives in a Markdown file under `kanban/tasks/`.

## Start the board

With Python 3.9 or newer, run these commands from the repository root.

```sh
cd kanban
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python board.py serve
```

On Windows PowerShell, use `py -3 -m venv .venv` and activate with `.venv\Scripts\Activate.ps1` instead.

Open <http://127.0.0.1:8765>. Use **New task** or a column's **+** button to create a task. Click a task title to edit all its fields.

Drag a task to another column or use its status menu. The status menu also works with a keyboard or touchscreen. To delete a task, open it and click **Delete task**, then confirm.

Changes save to Markdown immediately. Reload the page to pick up changes made in a text editor or another tab. Commit the task files to share them through Git. The server does not commit or push.

To use another port, run `python board.py serve --port 8766` from `kanban/`. Stop the server with Ctrl+C.

## Edit task files

The filename is the task's stable UUID, such as `8bd21e6b-fb57-477c-8330-d47e2f58db35.md`. Keep that filename when renaming or moving a task.

The metadata is a JSON object between `---` lines. JSON is valid YAML, but this tool accepts JSON syntax only. Keep the double quotes and commas. The Markdown body is the description.

```markdown
---
{
  "title": "Review the lab setup guide",
  "status": "todo",
  "assignee": "Meghan",
  "priority": "medium",
  "labels": ["docs", "lab"],
  "acceptanceCriteria": [
    "The commands work on a fresh checkout",
    "The guide lists all prerequisites"
  ]
}
---

Review the setup commands in the lab README.

Include any missing prerequisites and troubleshooting steps.
```

Use `todo`, `in-progress`, or `done` for status. Use `low`, `medium`, or `high` for priority. An empty assignee is unassigned. Labels and acceptance criteria are arrays of strings. Each entry must fit on one line, and labels cannot contain commas. In the browser, separate labels with commas and acceptance criteria with newlines.

The browser displays descriptions as plain text and preserves line breaks. Markdown source stays in the file. The board starts empty. The example above does not create a task.

Invalid task files produce an error that names the file. Fix the file and reload. The export also fails on invalid files rather than publishing an incomplete board.

## Publish a read-only board

1. In the GitHub repository, open **Settings > Pages**.
2. Set **Build and deployment > Source** to **GitHub Actions**.
3. Push the board and task files to `main`, or run **Kanban board** from the **Actions** tab on `main`.
4. Open the URL in the workflow's **github-pages** deployment.

The [workflow](../.github/workflows/kanban-pages.yml) tests the tool, builds a snapshot, and deploys it using GitHub's [Pages workflow actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). Pull requests run the tests and build without deploying.

The published board shows task details with editing controls hidden. It has no write API. Every task field is included in the snapshot, so publish only task content intended for the site's audience. Local changes appear on Pages after you commit and push them and the workflow succeeds.

To preview the same read-only artifact locally, run these commands in order.

```sh
python board.py build --output dist
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

Open <http://127.0.0.1:8766>. The generated directory contains only the board assets and task snapshot. It is ignored by Git. The build refuses output directories containing unrelated files.

## Run the checks

```sh
python -m unittest discover -s . -p 'test_*.py' -v
```

The tests use temporary task directories. They exercise Markdown persistence, local HTTP operations, invalid input, file boundaries, and read-only export.

## Maintain the tool

`board.py` owns task validation, file persistence, the loopback HTTP server, and static export. `web/` contains the shared browser interface. Local `board.json` and the exported snapshot have the same task format, with a `readOnly` flag controlling the interface.

This is a single-user local tool. It reads files on each refresh and saves complete tasks. If two tabs edit the same task, the last save wins. Run one editor server per checkout. The server binds to `127.0.0.1` and serves only board assets and the task API.
