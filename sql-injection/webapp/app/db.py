"""Thin MySQL access layer for the data tier.

Two things live here on purpose:

  * ``get_conn`` -- a per-request PyMySQL connection to the ``db`` container.
  * The two SQL *paths* the SQLi scenario contrasts: a string-concatenated query
    (vulnerable) and a parameterized query (safe). Both are reached through the
    same route; a toggle selects which one runs, so the only difference between
    an attack and its benign twin is whether the concatenated path parses the
    input as structure or as data.
"""
import pymysql

from .config import Config


def get_conn():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        charset="utf8mb4",
    )


# --- Directory search -------------------------------------------------------
# The SQLi anchor. Same user action, two implementations behind a flag.

_DIR_COLS = "id, name, title, department, email, phone, location"


def search_directory_concat(conn, term: str):
    """VULNERABLE: the term is concatenated straight into the SQL text, so an
    input like  ' OR '1'='1  adds a new logical clause to the parse tree."""
    sql = (
        "SELECT " + _DIR_COLS + " FROM directory "
        "WHERE name LIKE '%" + term + "%' ORDER BY name LIMIT 50"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall(), sql


def search_directory_param(conn, term: str):
    """SAFE: the term is bound as a value; the query's structure is fixed."""
    sql = (
        "SELECT " + _DIR_COLS + " FROM directory "
        "WHERE name LIKE %s ORDER BY name LIMIT 50"
    )
    with conn.cursor() as cur:
        cur.execute(sql, ("%" + term + "%",))
        return cur.fetchall(), sql


# --- Login ------------------------------------------------------------------
# The login route also reaches the DB and shares the same two-path design.

def login_concat(conn, username: str, password: str):
    """VULNERABLE: classic auth-bypass surface (' OR '1'='1' -- )."""
    sql = (
        "SELECT id, username, display_name, bio, homepage FROM users "
        "WHERE username = '" + username + "' AND password = '" + password + "'"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone(), sql


def login_param(conn, username: str, password: str):
    """SAFE: credentials bound as values."""
    sql = (
        "SELECT id, username, display_name, bio, homepage FROM users "
        "WHERE username = %s AND password = %s"
    )
    with conn.cursor() as cur:
        cur.execute(sql, (username, password))
        return cur.fetchone(), sql


# Dispatch helpers keyed by the resolved SQL_IMPL toggle.
SEARCH_IMPLS = {"concat": search_directory_concat, "param": search_directory_param}
LOGIN_IMPLS = {"concat": login_concat, "param": login_param}
