"""Import/export settings -- the insecure-deserialization surface.

Export serializes the user's settings into an opaque blob (benign serialization
noise). Import accepts such a blob back and hands it to ``deser-svc`` for
reconstruction -- the webapp does not itself trust or interpret the object; it
forwards the raw bytes, exactly as the tasklist specifies.

The danger is entirely semantic: a benign blob rebuilds into a plain settings
dict, while a crafted blob (e.g. a pickle whose __reduce__ runs a command)
executes on reconstruction. Nothing in the raw bytes distinguishes them; only
what deser-svc rebuilds them into does. The DESER_MODE toggle chooses whether
deser-svc reconstructs arbitrary objects (unsafe) or a restricted data-only
form (safe).
"""
import base64
import pickle

import requests
from flask import Blueprint, Response, g, redirect, render_template, request, url_for

from ..config import Config, resolve

bp = Blueprint("settings", __name__)


@bp.route("/settings")
def settings():
    if not g.get("session", {}).get("user"):
        return redirect(url_for("auth.login"))
    return render_template("settings.html", active_nav="settings", result=None, error=None)


@bp.route("/settings/export")
def export_settings():
    """Produce a benign serialized settings blob (the legitimate twin)."""
    user = g.get("session", {}).get("user")
    if not user:
        return redirect(url_for("auth.login"))
    settings_obj = {"theme": "dark", "lang": "en", "owner": user["username"]}
    blob = base64.b64encode(pickle.dumps(settings_obj)).decode()
    return Response(blob, mimetype="text/plain",
                    headers={"Content-Disposition": "attachment; filename=settings.b64"})


@bp.route("/settings/import", methods=["POST"])
def import_settings():
    """Forward a user-supplied serialized object to deser-svc for reconstruction."""
    if not g.get("session", {}).get("user"):
        return redirect(url_for("auth.login"))

    blob_b64 = request.form.get("blob", "").strip()
    mode = resolve("DESER_MODE", request.args, Config.DESER_MODE)

    error, result = None, None
    try:
        raw = base64.b64decode(blob_b64)
    except Exception:
        return render_template("settings.html", active_nav="settings",
                               result=None, error="Not valid base64"), 400

    # Hand the untrusted bytes to deser-svc. The webapp is a pass-through and
    # never deserializes the object itself.
    try:
        resp = requests.post(
            Config.DESER_SVC_URL,
            data=raw,
            headers={"Content-Type": "application/octet-stream"},
            params={"mode": mode},
            timeout=10,
        )
        result = resp.json()
    except requests.RequestException as exc:
        error = f"deser-svc unavailable: {exc}"

    return render_template("settings.html", active_nav="settings",
                           result=result, error=error)
