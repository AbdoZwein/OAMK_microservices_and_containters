"""
Integration test (Ordering + Payment together, using a STUB Payment).

Run with:   python -m pytest tests/test_integration.py -v

This tests the orchestration step: Ordering creating an order and calling
Payment over HTTP. Instead of the real Payment service we start a small STUB
Payment server (predefined reply) so the test is fast and isolated. This is
the bottom-up / top-down approach: collaborators replaced by a stub.
"""

import os
import sys
import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ordering"))

# Stub Payment server: always replies "captured".
class StubPayment(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length))
        reply = {"eventType": "PaymentCaptured", "version": 1,
                 "timestamp": "2026-01-01T00:00:00Z",
                 "orderId": req.get("orderId"),
                 "paymentId": "PAY-STUB", "status": "captured"}
        body = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep test output clean


def start_stub():
    server = HTTPServer(("127.0.0.1", 5599), StubPayment)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def setup_module(module):
    # Point Ordering at the stub payment and a throwaway database.
    os.environ["PAYMENT_URL"] = "http://127.0.0.1:5599/capture"
    os.environ["ORDER_DB"] = os.path.join(tempfile.gettempdir(), "test_order.db")
    os.environ["MONITOR_URL"] = "http://localhost:9/none"
    os.environ["MONITOR_EVENTS"] = "http://localhost:9/none"
    start_stub()
    import ordering_service
    ordering_service.init_db()
    module.client = ordering_service.app.test_client()


def test_order_flow_with_stub_payment():
    """Ordering should mark the order Paid after the stub captures payment."""
    resp = client.post("/orders", json={"productId": "P-77", "qty": 2, "price": 18.5})
    data = resp.get_json()
    assert data["status"] == "Paid"
    assert data["amount"] == 37.0          # 18.5 * 2
    assert data["orderId"].startswith("ORD-")


def test_orders_are_persisted():
    """The created order should appear in the orders list."""
    before = len(client.get("/orders").get_json())
    client.post("/orders", json={"productId": "P-78", "qty": 1, "price": 16.0})
    after = len(client.get("/orders").get_json())
    assert after == before + 1
