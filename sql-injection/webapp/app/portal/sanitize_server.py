"""Server-side input sanitization (Tier 1) — applied on the server, so leaving
the browser (curl) does NOT bypass it. Each type is defeated by a documented
*payload* evasion instead. Selected per request with ?serversan=.

  denylist   remove SQL keywords + comment markers, single pass, replace-all.
             DOCUMENTED BYPASS: self-nesting (UNUNIONION -> UNION), case,
             inline comments, function synonyms.
  escape     double single quotes ('' ). Blocks string-context break-out.
             DOCUMENTED BYPASS: numeric context (no quote to escape) — see ?id=.
  allowlist  reject anything outside [A-Za-z0-9 ]. The "correct" lexical defense;
             it holds for this field. DOCUMENTED BYPASS: second-order injection
             (store a clean-looking value, re-used unsanitized later) or applying
             it to the wrong parameter.

Returns (text, rejected). `rejected` is True only for the allowlist when the
input contains disallowed characters.
"""
import re

_BLACKLIST = [
    "union", "select", "insert", "update", "delete", "drop",
    "sleep", "benchmark", "information_schema", "--", "#", "/*", "*/",
]


def _strip(text: str) -> str:
    out = text
    for bad in _BLACKLIST:
        out = re.sub(re.escape(bad), "", out, flags=re.IGNORECASE)
    return out


def purify_server(text: str, mode: str):
    text = text or ""
    if mode == "denylist":
        return _strip(text), False
    if mode == "escape":
        return text.replace("'", "''"), False
    if mode == "allowlist":
        if re.fullmatch(r"[A-Za-z0-9 ]*", text):
            return text, False
        return text, True  # rejected
    return text, False
