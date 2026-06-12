"""
Unit tests (single function / service in isolation).

Run with:   python -m pytest tests/test_unit.py -v

These test individual units with no other services running. The Payment app is
tested through Flask's test client; external collaborators are not involved.
Approaches used: domain testing (valid input -> expected output), boundary
value analysis (zero / missing values), equivalence testing (input classes).
"""

import os
import sys
import tempfile

# Make the service modules importable.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "payment"))
sys.path.insert(0, os.path.join(ROOT, "catalog"))

# Point Payment at a throwaway database so tests do not touch real data.
os.environ["PAYMENT_DB"] = os.path.join(tempfile.gettempdir(), "test_payment.db")
os.environ["MONITOR_URL"] = "http://localhost:9/none"  # unreachable on purpose

import payment_service
import catalog_service


def setup_module(module):
    payment_service.init_db()


# --- Domain testing: a valid order yields a captured payment ---
def test_capture_returns_captured():
    client = payment_service.app.test_client()
    resp = client.post("/capture", json={"orderId": "ORD-1",
                                          "amount": {"value": 18.5, "currency": "EUR"}})
    data = resp.get_json()
    assert data["status"] == "captured"
    assert data["eventType"] == "PaymentCaptured"
    assert data["orderId"] == "ORD-1"


# --- Boundary value analysis: zero amount still produces a valid reply ---
def test_capture_zero_amount():
    client = payment_service.app.test_client()
    resp = client.post("/capture", json={"orderId": "ORD-2",
                                          "amount": {"value": 0, "currency": "EUR"}})
    assert resp.get_json()["status"] == "captured"


# --- Equivalence testing: paymentId is derived from the orderId class ---
def test_payment_id_derived_from_order():
    client = payment_service.app.test_client()
    resp = client.post("/capture", json={"orderId": "ORD-555",
                                          "amount": {"value": 5, "currency": "EUR"}})
    assert resp.get_json()["paymentId"] == "PAY-555"


# --- Catalog returns the expected number of products ---
def test_catalog_lists_products():
    client = catalog_service.app.test_client()
    products = client.get("/products").get_json()
    assert len(products) >= 1
    assert "productId" in products[0]
