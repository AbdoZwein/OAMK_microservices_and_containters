"""
Ordering microservice (orchestrator).

Bounded context: Ordering. Owns its OWN database (order.db), separate from the
Payment database (Split Tables / database-per-service pattern).

Workflow pattern: ORCHESTRATION. Ordering drives the process: it creates the
order, calls Payment (request-reply) and checks the reply, then records the
result and emits an OrderPaid event to the monitoring service.
"""

import os
import sqlite3
import time
import json
import urllib.request
from flask import Flask, request, jsonify
from common_log import log

app = Flask(__name__)
SERVICE = "ordering"
DB_PATH = os.environ.get("ORDER_DB", "/data/order.db")

PAYMENT_URL = os.environ.get("PAYMENT_URL", "http://payment:5002/capture")
MONITOR_EVENTS = os.environ.get("MONITOR_EVENTS", "http://monitoring:6000/events")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS orders (
                     orderId   TEXT PRIMARY KEY,
                     productId TEXT,
                     qty       INTEGER,
                     amount    REAL,
                     status    TEXT,
                     ts        TEXT )""")
    con.commit()
    con.close()


def next_order_id():
    """Generate the next order id from the count in this service's DB."""
    con = sqlite3.connect(DB_PATH)
    n = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    con.close()
    return "ORD-" + str(10231 + n)


def publish_event(event):
    """Publish an event to the monitoring service (best-effort)."""
    try:
        data = json.dumps(event).encode("utf-8")
        r = urllib.request.Request(MONITOR_EVENTS, data=data,
                                   headers={"Content-Type": "application/json"})
        urllib.request.urlopen(r, timeout=1)
    except Exception:
        pass


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


@app.route("/orders", methods=["POST"])
def create_order():
    """Create an order and run the orchestrated workflow."""
    body = request.get_json(force=True)
    product_id = body.get("productId", "P-77")
    qty = int(body.get("qty", 1))
    price = float(body.get("price", 18.50))
    amount = round(price * qty, 2)

    order_id = next_order_id()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log(SERVICE, "order placed", order_id=order_id,
        extra={"productId": product_id, "qty": qty, "amount": amount})

    # Store the new order in this service's own database.
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?)",
                (order_id, product_id, qty, amount, "AwaitingPayment", ts))
    con.commit()
    con.close()

    # --- Orchestration step: call Payment and wait for the reply ---
    pay_request = {"orderId": order_id, "amount": {"value": amount, "currency": "EUR"}}
    try:
        data = json.dumps(pay_request).encode("utf-8")
        r = urllib.request.Request(PAYMENT_URL, data=data,
                                   headers={"Content-Type": "application/json"})
        reply = json.loads(urllib.request.urlopen(r, timeout=3).read())
    except Exception as e:
        log(SERVICE, "payment call failed", order_id=order_id,
            level="ERROR", extra={"error": str(e)})
        return jsonify({"orderId": order_id, "status": "PaymentError"}), 502

    # Check the output before proceeding (orchestration checks each step).
    if reply.get("status") == "captured":
        new_status = "Paid"
        log(SERVICE, "order paid", order_id=order_id,
            extra={"paymentId": reply.get("paymentId")})
        publish_event({
            "eventType": "OrderPaid",
            "version": 1,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "orderId": order_id,
            "paymentId": reply.get("paymentId"),
        })
    else:
        new_status = "PaymentFailed"
        log(SERVICE, "payment not captured", order_id=order_id, level="WARN")

    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE orders SET status=? WHERE orderId=?", (new_status, order_id))
    con.commit()
    con.close()

    return jsonify({"orderId": order_id, "amount": amount, "status": new_status})


@app.route("/orders")
def list_orders():
    """Return recent orders (for the UI orders widget)."""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT orderId, productId, qty, amount, status, ts "
        "FROM orders ORDER BY ts DESC LIMIT 10").fetchall()
    con.close()
    keys = ["orderId", "productId", "qty", "amount", "status", "ts"]
    return jsonify([dict(zip(keys, row)) for row in rows])


if __name__ == "__main__":
    init_db()
    log(SERVICE, "ordering service starting")
    app.run(host="0.0.0.0", port=5003)
