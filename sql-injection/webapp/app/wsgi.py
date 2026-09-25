"""WSGI entrypoint for the Kathara lab.

The `webapp` machine directory mounts at `/`, so this file lands at
`/app/wsgi.py` and the package at `/app/portal/`. webapp.startup runs
`cd /app && gunicorn wsgi:app`.
"""
from portal import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
