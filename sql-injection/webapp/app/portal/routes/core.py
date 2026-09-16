"""Landing page, dashboard, health check, and the toggle-state endpoint."""
from flask import Blueprint, g, redirect, render_template, request, url_for

from ..config import Config, TOGGLES, resolve
from ..db import get_conn

bp = Blueprint("core", __name__)


@bp.route("/")
def index():
    if g.get("session", {}).get("user"):
        return redirect(url_for("core.dashboard"))
    return render_template("index.html")


@bp.route("/dashboard")
def dashboard():
    if not g.get("session", {}).get("user"):
        return redirect(url_for("auth.login"))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM directory")
            n_people = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(DISTINCT department) AS n FROM directory")
            n_depts = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM comments")
            n_comments = cur.fetchone()["n"]
            cur.execute(
                "SELECT c.author, c.body, c.created_at, d.id AS rid, d.name "
                "FROM comments c JOIN directory d ON d.id = c.record_id "
                "ORDER BY c.created_at DESC LIMIT 5"
            )
            recent = cur.fetchall()
            cur.execute(
                "SELECT id, name, title, department FROM directory ORDER BY id DESC LIMIT 4"
            )
            newest = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "dashboard.html",
        active_nav="dashboard",
        n_people=n_people,
        n_depts=n_depts,
        n_comments=n_comments,
        recent=recent,
        newest=newest,
    )


@bp.route("/healthz")
def healthz():
    return {"status": "ok"}


@bp.route("/state")
def state():
    """Report the effective attack-surface toggles for this request.

    Useful for the experiment harness to confirm which condition a request ran
    under (defaults, or per-request overrides via ?impl / ?enc / ?deser)."""
    return {
        "sql_impl": resolve("SQL_IMPL", request.args, Config.SQL_IMPL),
        "xss_encoding": resolve("XSS_ENCODING", request.args, Config.XSS_ENCODING),
        "deser_mode": resolve("DESER_MODE", request.args, Config.DESER_MODE),
        "override_args": TOGGLES,
        "authenticated": bool(g.get("session", {}).get("user")),
    }
