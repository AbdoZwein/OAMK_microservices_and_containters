"""
Auth microservice.

Bounded context: Authentication. Owns its OWN user store (separate from the
other services, consistent with the database-per-service pattern). Issues a
signed token on successful login and verifies tokens for other services.

The token is a compact HMAC-signed value built with the Python standard library
only (no extra dependencies): base64(payload).base64(hmac_sha256(payload)).
This is enough to demonstrate authentication for the prototype; a production
system would use a vetted library and proper password hashing/expiry handling.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from flask import Flask, request, jsonify
from common_log import log

app = Flask(__name__)
SERVICE = "auth"

# Secret used to sign tokens. Set via environment in docker-compose.
SECRET = os.environ.get("AUTH_SECRET", "dev-secret-change-me").encode("utf-8")

# Token lifetime in seconds.
TOKEN_TTL = int(os.environ.get("TOKEN_TTL", "3600"))

# Simple in-memory user store owned by this service. In production this is the
# Auth DB with properly hashed passwords; here passwords are stored hashed with
# SHA-256 for the demo so they are not kept in plain text.
def _hash(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

USERS = {
    "ubuntu": {"password": _hash("admin123"), "role": "customer"},
    "abdo":   {"password": _hash("admin123"),  "role": "customer"},
}


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64decode(s):
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def make_token(username, role):
    """Build a signed token: base64(payload).base64(signature)."""
    payload = {"sub": username, "role": role, "exp": int(time.time()) + TOKEN_TTL}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(SECRET, payload_bytes, hashlib.sha256).digest()
    return _b64(payload_bytes) + "." + _b64(sig)


def verify_token(token):
    """Return the payload if the token is valid and not expired, else None."""
    try:
        payload_part, sig_part = token.split(".")
        payload_bytes = _b64decode(payload_part)
        expected = hmac.new(SECRET, payload_bytes, hashlib.sha256).digest()
        # Constant-time comparison to avoid timing attacks.
        if not hmac.compare_digest(expected, _b64decode(sig_part)):
            return None
        payload = json.loads(payload_bytes)
        if payload.get("exp", 0) < int(time.time()):
            return None  # expired
        return payload
    except Exception:
        return None


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


@app.route("/login", methods=["POST"])
def login():
    """Validate credentials and return a token."""
    body = request.get_json(force=True)
    username = body.get("username", "")
    password = body.get("password", "")

    user = USERS.get(username)
    if not user or user["password"] != _hash(password):
        log(SERVICE, "login failed", level="WARN", extra={"username": username})
        return jsonify({"error": "invalid credentials"}), 401

    token = make_token(username, user["role"])
    log(SERVICE, "login success", extra={"username": username})
    return jsonify({"token": token, "username": username, "role": user["role"]})


@app.route("/verify", methods=["POST"])
def verify():
    """Verify a token on behalf of another service (e.g. the gateway)."""
    body = request.get_json(force=True)
    payload = verify_token(body.get("token", ""))
    if payload is None:
        return jsonify({"valid": False}), 401
    return jsonify({"valid": True, "sub": payload["sub"], "role": payload["role"]})


if __name__ == "__main__":
    log(SERVICE, "auth service starting")
    app.run(host="0.0.0.0", port=5004)
