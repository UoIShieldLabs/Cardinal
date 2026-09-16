"""Authentication -- one of the two DB-reaching SQLi routes.

Login runs the same two-path design as directory search: a concatenated query
(vulnerable to auth-bypass injection) and a parameterized query (safe), chosen
by the SQL_IMPL toggle. The benign twin is a normal username/password; the
attack is an input like  ' OR '1'='1' --  that rewrites the query's structure.
"""
from flask import Blueprint, flash, g, make_response, redirect, render_template, request, url_for

from ..config import Config, resolve
from ..db import get_conn, LOGIN_IMPLS
from .. import session as sess

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None, last_sql=None)

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    impl = resolve("SQL_IMPL", request.args, Config.SQL_IMPL)
    fn = LOGIN_IMPLS.get(impl, LOGIN_IMPLS["concat"])

    conn = get_conn()
    try:
        row, executed_sql = fn(conn, username, password)
    finally:
        conn.close()

    if not row:
        return render_template("login.html", error="Invalid credentials",
                               last_sql=executed_sql), 401

    sid = sess.new_session({"user": {
        "id": row["id"],
        "username": row["username"],
        "display_name": row.get("display_name"),
    }})
    flash(f"Welcome back, {row.get('display_name') or row['username']}.", "ok")
    resp = make_response(redirect(url_for("core.dashboard")))
    resp.set_cookie("sid", sid, httponly=True, samesite="Lax")
    return resp


@bp.route("/logout")
def logout():
    sess.destroy_session(g.get("sid"))
    resp = make_response(redirect(url_for("core.index")))
    resp.delete_cookie("sid")
    return resp
