"""Directory search -- the SQLi anchor *and* a reflected-XSS sink.

Two scenarios ride this one route:

  * SQLi: the search term feeds the concatenated or parameterized query
    (SQL_IMPL toggle). The benign twin ("Alice") and the attack ("' OR '1'='1")
    are the same action on the same route; only the parse tree differs.
  * Reflected XSS: the search term is echoed back into the results page. The
    template renders it into the HTML-body, attribute, JS, and URI contexts so
    the *same* echoed string is inert in one sink and executable in another.

With no search term the page browses the full directory (a normal feature); a
term switches it to the search path above.
"""
from flask import Blueprint, render_template, request

from ..config import Config, resolve
from ..db import get_conn, SEARCH_IMPLS

bp = Blueprint("directory", __name__)


@bp.route("/search")
def search():
    term = request.args.get("q", "")
    impl = resolve("SQL_IMPL", request.args, Config.SQL_IMPL)
    fn = SEARCH_IMPLS.get(impl, SEARCH_IMPLS["concat"])

    results, executed_sql = [], None
    conn = get_conn()
    try:
        if term:
            results, executed_sql = fn(conn, term)
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, title, department, email, phone, location "
                    "FROM directory ORDER BY name LIMIT 100"
                )
                results = cur.fetchall()
    finally:
        conn.close()

    # `term` is passed straight to the template, which reflects it into every
    # XSS context via the toggle-aware `enc` helper.
    return render_template(
        "search.html",
        active_nav="directory",
        term=term,
        results=results,
        impl=impl,
        executed_sql=executed_sql,
    )
