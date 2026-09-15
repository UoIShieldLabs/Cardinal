"""Application factory for the Cardinal webapp (system under test).

A small internal staff portal: login, browse/edit your own profile, search a
shared directory, comment on records, import/export settings. Ordinary by
design -- every attack surface is reached through a feature a real user
exercises daily, so attack and benign traffic are indistinguishable at entry.
"""
from flask import Flask, g, request

from .config import Config
from .encoding import make_enc
from . import session as sess


_AVATAR_COLORS = [
    "#3b5bdb", "#0ca678", "#e8590c", "#7048e8", "#c2255c",
    "#1098ad", "#f08c00", "#5c940d", "#d6336c", "#1c7ed6",
]


def _initials(name):
    if not name:
        return "?"
    parts = [p for p in str(name).replace(",", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _avatar_color(name):
    if not name:
        return _AVATAR_COLORS[0]
    return _AVATAR_COLORS[sum(ord(c) for c in str(name)) % len(_AVATAR_COLORS)]


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Jinja autoescaping is off: the contextual `enc` helper is the single
    # authority on output encoding (see app/encoding.py).
    app.jinja_env.autoescape = False

    from .routes.auth import bp as auth_bp
    from .routes.directory import bp as directory_bp
    from .routes.profile import bp as profile_bp
    from .routes.comments import bp as comments_bp
    from .routes.settings import bp as settings_bp
    from .routes.core import bp as core_bp
    from .routes.api import bp as api_bp

    for bp in (core_bp, auth_bp, directory_bp, profile_bp, comments_bp,
               settings_bp, api_bp):
        app.register_blueprint(bp)

    @app.before_request
    def load_session():
        sid = request.cookies.get("sid")
        g.sid = sid
        g.session = sess.load_session(sid)
        # Per-request, toggle-aware contextual encoder.
        g.enc = make_enc(request.args)

    @app.context_processor
    def inject_helpers():
        return {
            "enc": g.get("enc"),
            "current_user": g.get("session", {}).get("user"),
            "initials": _initials,
            "avatar_color": _avatar_color,
        }

    @app.after_request
    def persist_session(resp):
        # If a route created/destroyed a session it sets g.sid explicitly.
        return resp

    return app
