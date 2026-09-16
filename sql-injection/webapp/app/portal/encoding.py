"""Contextual output encoding -- the heart of the XSS scenario.

The same user-supplied string is rendered into four different sinks:

    html   -- an HTML text node          <p>VALUE</p>
    attr   -- a (quoted) attribute value <input value="VALUE">
    js     -- an inline script string    <script>var x = "VALUE";</script>
    uri    -- a URL context              <a href="VALUE">

The XSS_ENCODING toggle decides what ``enc`` does:

  * "raw"    -- return the value untouched. Every sink is now injectable, and,
                crucially, the *same bytes* are inert in the html text node but
                executable in the attribute/js/uri contexts. That context
                dependence is exactly what a content-only detector cannot see.
  * "escape" -- apply the encoding correct for *that* context, neutralising the
                payload wherever it lands.

Templates always call ``{{ enc(value, 'attr') | safe }}``: the helper owns the
escaping decision, so Jinja's own autoescaping is turned off to keep one code
path in charge.
"""
import json
from urllib.parse import quote

from markupsafe import Markup

from .config import Config, resolve


def _escape_html(v: str) -> str:
    return (
        v.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _escape_attr(v: str) -> str:
    # Quote-and-entity encode so the value cannot break out of the surrounding
    # double quotes (the attribute-escape example in the tasklist).
    return _escape_html(v)


def _escape_js(v: str) -> str:
    # json.dumps yields a safely quoted JS string literal (escapes quotes,
    # backslashes, and </script> via the unicode-escaped forward slash below).
    return json.dumps(v).replace("</", "<\\/")[1:-1]  # strip the outer quotes


def _escape_uri(v: str) -> str:
    return quote(v, safe="")


_ESCAPERS = {
    "html": _escape_html,
    "attr": _escape_attr,
    "js": _escape_js,
    "uri": _escape_uri,
}


def make_enc(request_args):
    """Build an ``enc(value, context)`` bound to this request's toggle state."""
    mode = resolve("XSS_ENCODING", request_args, Config.XSS_ENCODING)

    def enc(value, context: str = "html") -> Markup:
        s = "" if value is None else str(value)
        if mode == "escape":
            s = _ESCAPERS.get(context, _escape_html)(s)
        # In "raw" mode the value is returned verbatim (vulnerable). Marked safe
        # either way: the helper, not Jinja, is the single escaping authority.
        return Markup(s)

    return enc
