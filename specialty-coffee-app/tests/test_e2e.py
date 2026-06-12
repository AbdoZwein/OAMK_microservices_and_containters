"""
End-to-end test (entire workflow through the running containers).

Talks to the LIVE application through the gateway, exercising the whole path:
    gateway -> auth (login) -> ordering -> payment -> monitoring
plus catalog and metrics, and the authentication protection on ordering.

Prerequisite: the application must be running, e.g.
    docker compose up --build -d

Run with:   python -m pytest tests/test_e2e.py -v
"""

import os
import json
import urllib.request
import urllib.error

GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8080")


def _get(path):
    with urllib.request.urlopen(GATEWAY + path, timeout=5) as r:
        return json.loads(r.read())


def _post(path, payload, token=None):
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(GATEWAY + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read()), r.status


def _login(username="ubuntu", password="admin123"):
    body, _ = _post("/api/login", {"username": username, "password": password})
    return body["token"]


def test_catalog_reachable_through_gateway():
    products = _get("/api/products")
    assert len(products) >= 1


def test_order_rejected_without_token():
    """Ordering must be rejected with 401 when no token is supplied."""
    try:
        _post("/api/orders", {"productId": "P-77", "qty": 1, "price": 18.5})
        assert False, "expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_full_order_workflow_authenticated():
    """Log in, place an order with the token, and confirm it is Paid."""
    token = _login()
    result, _ = _post("/api/orders", {"productId": "P-77", "qty": 1, "price": 18.5}, token=token)
    assert result["status"] == "Paid"
    order_id = result["orderId"]
    orders = _get("/api/orders")
    assert any(o["orderId"] == order_id for o in orders)


def test_monitoring_recorded_the_order():
    metrics = _get("/api/metrics")
    assert metrics["ordersPaid"] >= 1
