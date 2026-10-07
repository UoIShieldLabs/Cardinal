"""Directory search -- the SQLi anchor, reflected-XSS sink, and the surface we
use to demonstrate SERVER-SIDE defenses (Tiers 1-3) and the documented attacks
that bypass them.

Toggles (all per request):
  ?impl=concat|param|proc   SQL path (proc = stored-procedure dynamic SQL, Tier 2)
  ?serversan=denylist|escape|allowlist   server-side input sanitization (Tier 1)
  ?id=<expr>                numeric-context filter (Tier 1 escape blind spot)
  ?sort=<col>               ORDER BY identifier, concatenated (Tier 2 param hole)
"""
from flask import Blueprint, render_template, request

from ..config import Config, resolve
from ..db import (get_conn, SEARCH_IMPLS, filter_directory_by_id,
                  search_directory_param_sorted)
from ..sanitize_server import purify_server

bp = Blueprint("directory", __name__)


@bp.route("/search")
def search():
    raw_term = request.args.get("q", "")
    impl = resolve("SQL_IMPL", request.args, Config.SQL_IMPL)
    serversan = request.args.get("serversan", "off").strip().lower()
    id_expr = request.args.get("id")
    sort = request.args.get("sort")

    # Tier 1: server-side sanitization runs on the server (curl cannot skip it).
    term, rejected = purify_server(raw_term, serversan)

    results, executed_sql = [], None
    conn = get_conn()
    try:
        if rejected:
            executed_sql = "(input rejected by server-side allowlist)"
        elif id_expr is not None:
            id_clean, _ = purify_server(id_expr, serversan)
            results, executed_sql = filter_directory_by_id(conn, id_clean)
        elif sort is not None:
            results, executed_sql = search_directory_param_sorted(conn, term, sort)
        elif term:
            fn = SEARCH_IMPLS.get(impl, SEARCH_IMPLS["concat"])
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

    return render_template(
        "search.html",
        active_nav="directory",
        term=raw_term,
        results=results,
        impl=impl,
        executed_sql=executed_sql,
    )
