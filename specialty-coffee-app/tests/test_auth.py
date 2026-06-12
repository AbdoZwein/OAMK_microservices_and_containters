"""
Unit tests for the auth service.

Run with:   python -m pytest tests/test_auth.py -v

Covers login success, login failure (wrong password / unknown user), and token
verification (valid, tampered, and a round-trip through verify()).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "auth"))

os.environ["MONITOR_URL"] = "http://localhost:9/none"
import auth_service


def test_login_success():
    client = auth_service.app.test_client()
    resp = client.post("/login", json={"username": "alice", "password": "coffee123"})
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password():
    client = auth_service.app.test_client()
    resp = client.post("/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user():
    client = auth_service.app.test_client()
    resp = client.post("/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_verify_valid_token():
    client = auth_service.app.test_client()
    token = client.post("/login", json={"username": "bob", "password": "espresso"}).get_json()["token"]
    resp = client.post("/verify", json={"token": token})
    assert resp.status_code == 200
    assert resp.get_json()["valid"] is True
    assert resp.get_json()["sub"] == "bob"


def test_verify_tampered_token():
    client = auth_service.app.test_client()
    token = client.post("/login", json={"username": "alice", "password": "coffee123"}).get_json()["token"]
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    resp = client.post("/verify", json={"token": tampered})
    assert resp.status_code == 401
    assert resp.get_json()["valid"] is False
