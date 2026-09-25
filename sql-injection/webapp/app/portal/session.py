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
            host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0,
            socket_connect_timeout=2, socket_timeout=2,
        )
    return _client


def _key(sid: str) -> str:
    return "sess:" + sid


# Redis is the real session store (serialized blobs -- see module docstring). If
# the cache tier is briefly unreachable we degrade to "no session" rather than
# 500 the whole app: the request is treated as anonymous. Writes silently no-op.
# This keeps the portal booting even while cache is starting; it does not change
# the deserialization surface (that lives in the import endpoint, not here).
class _RedisDown(Exception):
    pass


def new_session(data: dict) -> str:
    sid = secrets.token_urlsafe(24)
    save_session(sid, data)
    return sid


def load_session(sid: str) -> dict:
    if not sid:
        return {}
    try:
        raw = client().get(_key(sid))
    except redis.RedisError:
        return {}
    if raw is None:
        return {}
    # Benign path: our own pickled dict. The blob is trusted here because we
    # wrote it; the untrusted deserialization surface is the import endpoint.
    return pickle.loads(raw)


def save_session(sid: str, data: dict) -> None:
    try:
        client().setex(_key(sid), Config.SESSION_TTL, pickle.dumps(data))
    except redis.RedisError:
        pass


def destroy_session(sid: str) -> None:
    if sid:
        try:
            client().delete(_key(sid))
        except redis.RedisError:
            pass
