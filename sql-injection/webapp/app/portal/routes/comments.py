"""Records + comments -- a stored-XSS sink on a shared object.

Any user can post a comment on a directory record; comment bodies are rendered
back to every viewer. This is the stored-XSS vector (as opposed to the reflected
echo on /search): a payload persisted here executes in another user's session.
Comment bodies are rendered into HTML-body and attribute contexts.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..db import get_conn

bp = Blueprint("comments", __name__)


@bp.route("/records/<int:record_id>", methods=["GET", "POST"])
def record(record_id):
    conn = get_conn()
    try:
        if request.method == "POST":
            user = g.get("session", {}).get("user")
            author = user["username"] if user else "anonymous"
            # Stored verbatim; render-time encoding decides safety.
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO comments (record_id, author, body) VALUES (%s, %s, %s)",
                    (record_id, author, request.form.get("body", "")),
                )
            flash("Comment posted.", "ok")
            return redirect(url_for("comments.record", record_id=record_id))

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, title, department, email, phone, location "
                "FROM directory WHERE id=%s",
                (record_id,),
            )
            rec = cur.fetchone()
            cur.execute(
                "SELECT author, body, created_at FROM comments "
                "WHERE record_id=%s ORDER BY created_at",
                (record_id,),
            )
            comment_rows = cur.fetchall()
    finally:
        conn.close()

    if not rec:
        return render_template("record.html", active_nav="directory",
                               record=None, comments=[]), 404
    return render_template("record.html", active_nav="directory",
                           record=rec, comments=comment_rows)
