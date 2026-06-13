"""
API Gateway.

Single entry point for the frontend. Hides the internal service structure and
routes each request to the correct backend microservice. The browser only ever
talks to the gateway, never directly to a backend service.

Authentication: the gateway exposes /api/login (proxied to the auth service)
and PROTECTS order placement by verifying the caller's token with the auth
service before forwarding the request to ordering.
"""

import os
import json
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, Response
from common_log import log

app = Flask(__name__)
SERVICE = "gateway"

CATALOG_URL = os.environ.get("CATALOG_URL", "http://catalog:5001")
ORDERING_URL = os.environ.get("ORDERING_URL", "http://ordering:5003")
MONITOR_URL2 = os.environ.get("MONITOR_BASE", "http://monitoring:6000")
AUTH_URL = os.environ.get("AUTH_URL", "http://auth:5004")


# The UI page is served by the frontend (port 8000) but calls the gateway
# (port 8080), so browser requests are cross-origin. Allow them and answer the
# preflight OPTIONS request the browser sends before POSTs with a JSON body or
# an Authorization header.
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return Response(status=204)


def proxy_get(url):
    with urllib.request.urlopen(url, timeout=3) as r:
        return r.read(), r.status


def proxy_post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.read(), r.status


def proxy(method, url, payload=None):
    """Forward an arbitrary method (POST/PUT/DELETE) to a backend service."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.read(), r.status


def token_is_valid(token):
    """Ask the auth service to verify a token. Returns True/False."""
    if not token:
        return False
    try:
        data = json.dumps({"token": token}).encode("utf-8")
        req = urllib.request.Request(AUTH_URL + "/verify", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read()).get("valid", False)
    except Exception:
        return False


def bearer_token():
    """Extract the token from the Authorization: Bearer <token> header."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):]
    return ""


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


# --- Auth route ---
@app.route("/api/login", methods=["POST"])
def login():
    try:
        body, status = proxy_post(AUTH_URL + "/login", request.get_json(force=True))
        return Response(body, status=status, mimetype="application/json")
    except urllib.error.HTTPError as e:
        # Pass through auth failures (e.g. 401 invalid credentials).
        return Response(e.read(), status=e.code, mimetype="application/json")


# --- Catalog routes ---
# Listing is public; adding/editing/removing products requires a valid token.
@app.route("/api/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        if not token_is_valid(bearer_token()):
            log(SERVICE, "catalog change rejected: unauthorized", level="WARN")
            return jsonify({"error": "unauthorized"}), 401
        try:
            body, status = proxy("POST", CATALOG_URL + "/products", request.get_json(force=True))
        except urllib.error.HTTPError as e:
            return Response(e.read(), status=e.code, mimetype="application/json")
        return Response(body, status=status, mimetype="application/json")
    body, status = proxy_get(CATALOG_URL + "/products")
    return Response(body, status=status, mimetype="application/json")


@app.route("/api/products/<product_id>", methods=["PUT", "DELETE"])
def product_item(product_id):
    if not token_is_valid(bearer_token()):
        log(SERVICE, "catalog change rejected: unauthorized", level="WARN")
        return jsonify({"error": "unauthorized"}), 401
    payload = request.get_json(force=True) if request.method == "PUT" else None
    try:
        body, status = proxy(request.method, CATALOG_URL + "/products/" + product_id, payload)
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code, mimetype="application/json")
    return Response(body, status=status, mimetype="application/json")


# --- Ordering routes ---
@app.route("/api/orders", methods=["GET", "POST"])
def orders():
    if request.method == "POST":
        # Protected: a valid token is required to place an order.
        if not token_is_valid(bearer_token()):
            log(SERVICE, "order rejected: unauthorized", level="WARN")
            return jsonify({"error": "unauthorized"}), 401
        log(SERVICE, "routing new order to ordering service")
        body, status = proxy_post(ORDERING_URL + "/orders", request.get_json(force=True))
    else:
        body, status = proxy_get(ORDERING_URL + "/orders")
    return Response(body, status=status, mimetype="application/json")


# --- Monitoring routes (for the monitoring widget) ---
@app.route("/api/metrics")
def metrics():
    body, status = proxy_get(MONITOR_URL2 + "/metrics")
    return Response(body, status=status, mimetype="application/json")


if __name__ == "__main__":
    log(SERVICE, "gateway starting")
    app.run(host="0.0.0.0", port=8080)
