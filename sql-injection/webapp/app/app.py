"""Cardinal Phase 1 webapp — a minimal staff portal (system under test).

Deliberately vulnerable. The directory-search and login routes each reach the
database through two implementations chosen by a flag:

  * concat  — the input is concatenated straight into the SQL text (VULNERABLE).
  * param   — the input is bound as a value; the query structure is fixed (SAFE).

The flag defaults from the SQL_MODE env var (``concat`` for Phase 1) and can be
overridden per request with ``?impl=concat|param`` — so the *same* route serves
an attack and its byte-identical benign twin, differing only in whether the
concatenated path parses the input as structure or as data.

Scope note: this is the trimmed SQLi-only app for the Kathara lab. The richer
multi-scenario portal (XSS/deser, redis sessions, JSON API) lives in
``sql-injection/webapp/`` and is reused in later phases.
"""
import os

import pymysql
from flask import (
    Flask, redirect, render_template, request, session, url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cardinal-phase1-not-secret")

# --- Config (data tier) -----------------------------------------------------
DB_HOST = os.environ.get("DB_HOST", "172.31.0.30")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "portal")
DB_PASS = os.environ.get("DB_PASS", "portal")
DB_NAME = os.environ.get("DB_NAME", "portal")

# Per-deployment default SQL path. Phase 1 pins the vulnerable path.
SQL_MODE = os.environ.get("SQL_MODE", "concat").strip().lower()

# Columns the directory search returns — note the count (7): any UNION-based
# injection through /search must supply 7 columns.
_DIR_COLS = "id, name, title, department, email, phone, location"


def get_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor,
        autocommit=True, charset="utf8mb4",
    )


def resolve_impl():
    """Per-request override wins, else the deployment default."""
    val = request.args.get("impl")
    return (val or SQL_MODE).strip().lower()


# --- Directory search (SQLi anchor + future XSS echo) -----------------------

def search_directory(conn, term, impl):
    if impl == "param":
        # SAFE: term bound as a value; the query's structure is fixed.
        sql = ("SELECT " + _DIR_COLS + " FROM directory "
               "WHERE name LIKE %s ORDER BY name LIMIT 50")
        with conn.cursor() as cur:
            cur.execute(sql, ("%" + term + "%",))
            return cur.fetchall(), sql
    # VULNERABLE (default): term concatenated straight into the SQL text, so an
    # input like  ' OR '1'='1  adds a new clause to the parse tree.
    sql = ("SELECT " + _DIR_COLS + " FROM directory "
           "WHERE name LIKE '%" + term + "%' ORDER BY name LIMIT 50")
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall(), sql


# --- Login ------------------------------------------------------------------

def login_lookup(conn, username, password, impl):
    if impl == "param":
        sql = ("SELECT id, username, display_name FROM users "
               "WHERE username = %s AND password = %s")
        with conn.cursor() as cur:
            cur.execute(sql, (username, password))
            return cur.fetchone(), sql
    # VULNERABLE: classic auth-bypass surface (' OR '1'='1' -- ).
    sql = ("SELECT id, username, display_name FROM users "
           "WHERE username = '" + username + "' AND password = '" + password + "'")
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone(), sql


# --- Routes -----------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"))


@app.route("/login", methods=["GET", "POST"])
def login():
    impl = resolve_impl()
    if request.method == "GET":
        return render_template("login.html", error=None, executed_sql=None,
                               user=session.get("user"))

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    conn = get_conn()
    try:
        row, executed_sql = login_lookup(conn, username, password, impl)
    finally:
        conn.close()

    if not row:
        return render_template("login.html", error="Invalid credentials",
                               executed_sql=executed_sql, user=None), 401

    session["user"] = {"id": row["id"], "username": row["username"],
                       "display_name": row.get("display_name")}
    return redirect(url_for("profile", id=row["id"]))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


@app.route("/search")
def search():
    term = request.args.get("q", "")
    impl = resolve_impl()

    results, executed_sql = [], None
    conn = get_conn()
    try:
        if term:
            results, executed_sql = search_directory(conn, term, impl)
        else:
            with conn.cursor() as cur:
                cur.execute("SELECT " + _DIR_COLS +
                            " FROM directory ORDER BY name LIMIT 100")
                results = cur.fetchall()
    finally:
        conn.close()

    # `term` is echoed back into the page (harmless now; the XSS sink in a later
    # phase). It is passed to the template as-is.
    return render_template("search.html", term=term, results=results, impl=impl,
                           executed_sql=executed_sql, user=session.get("user"))


@app.route("/profile/<int:id>")
def profile(id):
    # Parameterized on purpose: the "safe" control route, not an injection point.
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _DIR_COLS + " FROM directory WHERE id = %s",
                        (id,))
            person = cur.fetchone()
    finally:
        conn.close()
    return render_template("profile.html", person=person, pid=id,
                           user=session.get("user"))


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
