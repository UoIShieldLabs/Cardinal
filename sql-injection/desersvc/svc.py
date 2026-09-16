"""deser-svc — reconstructs untrusted serialized objects for the webapp.

The webapp's object-import endpoint forwards raw serialized bytes here; this
service rebuilds them. That reconstruction IS the insecure-deserialization
vulnerability: the danger is not in the bytes but in what the object *does* when
rebuilt against the classes present here.

  POST /reconstruct?mode=unsafe   -> pickle.loads on the raw bytes (arbitrary
                                     object graph; a __reduce__ gadget executes).
  POST /reconstruct?mode=safe     -> refuse pickle; accept only a JSON data-only
                                     settings object (nothing executes).

The benign twin (a legitimately pickled settings dict) and a malicious object
(whose __reduce__ runs a command) arrive as the same kind of request on the
same endpoint — only the reconstructed object differs.
"""
import io
import json
import pickle

from flask import Flask, jsonify, request

app = Flask(__name__)


class _Restricted(pickle.Unpickler):
    """Allow only a tiny allowlist of builtins -- no callables, no os/system."""

    _ALLOWED = {("builtins", "dict"), ("builtins", "list"), ("builtins", "str")}

    def find_class(self, module, name):
        if (module, name) in self._ALLOWED:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"blocked global {module}.{name}")


def _summ(obj):
    try:
        return {"type": type(obj).__name__, "repr": repr(obj)[:200]}
    except Exception:
        return {"type": type(obj).__name__}


@app.route("/reconstruct", methods=["POST"])
def reconstruct():
    mode = request.args.get("mode", "unsafe").lower()
    raw = request.get_data()
    try:
        if mode == "safe":
            # Data-only: reject serialized code entirely; expect JSON.
            obj = json.loads(raw.decode("utf-8"))
            kind = "json"
        else:
            obj = pickle.load(io.BytesIO(raw))  # vulnerable reconstruction
            kind = "pickle"
        return jsonify(ok=True, mode=mode, kind=kind, value=_summ(obj))
    except Exception as exc:
        return jsonify(ok=False, mode=mode, error=str(exc)), 400


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
