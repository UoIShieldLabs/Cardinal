"""Own-profile view/edit -- a stored-XSS surface across every context.

Profile fields are written by the user and later rendered back into the page in
different sinks: the bio into an HTML text node, the display name into an
attribute, a status string into an inline <script>, and a homepage into a URL.
A payload stored in one field is inert or executable depending purely on which
sink renders it -- the context, not the bytes, decides.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..db import get_conn

bp = Blueprint("profile", __name__)


def _require_user():
    return g.get("session", {}).get("user")


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))

    conn = get_conn()
    try:
        if request.method == "POST":
            # Stored as-is: no server-side sanitisation. The XSS_ENCODING toggle
            # governs safety at *render* time, per sink, not at storage time.
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET display_name=%s, bio=%s, status=%s, homepage=%s "
                    "WHERE id=%s",
                    (
                        request.form.get("display_name", ""),
                        request.form.get("bio", ""),
                        request.form.get("status", ""),
                        request.form.get("homepage", ""),
                        user["id"],
                    ),
                )
            flash("Profile saved.", "ok")
            return redirect(url_for("profile.profile"))

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, display_name, title, department, bio, status, homepage "
                "FROM users WHERE id=%s",
                (user["id"],),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    return render_template("profile.html", active_nav="profile", profile=row)
