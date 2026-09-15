"""Server-side sessions stored as serialized blobs in Redis (the ``cache`` tier).

Sessions are pickled on purpose. Per the testbed design this does two things:

  * makes the deserialization surface realistic -- session handling is a classic
    real-world deserialization sink; and
  * keeps benign serialized data continuously flowing through the system, so a
    malicious object has legitimate serialization noise to hide in.

The browser only ever holds an opaque session id (a cookie); the pickled blob
lives in Redis, keyed by that id.
"""
import pickle
import secrets

import redis

from .config import Config

_client = None


def client():
    global _client
    if _client is None:
        _client = redis.Redis(
            host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0
        )
    return _client


def _key(sid: str) -> str:
    return "sess:" + sid


def new_session(data: dict) -> str:
    sid = secrets.token_urlsafe(24)
    save_session(sid, data)
    return sid


def load_session(sid: str) -> dict:
    if not sid:
        return {}
    raw = client().get(_key(sid))
    if raw is None:
        return {}
    # Benign path: our own pickled dict. The blob is trusted here because we
    # wrote it; the untrusted deserialization surface is the import endpoint.
    return pickle.loads(raw)


def save_session(sid: str, data: dict) -> None:
    client().setex(_key(sid), Config.SESSION_TTL, pickle.dumps(data))


def destroy_session(sid: str) -> None:
    if sid:
        client().delete(_key(sid))
