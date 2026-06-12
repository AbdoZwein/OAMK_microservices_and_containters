"""
Payment microservice.

Bounded context: Payment. Owns its OWN database (payment.db), separate from the
Order database. This realizes the Split Tables / database-per-service pattern:
each service stores only its own data and there are no cross-service foreign
keys. Exposes a request-reply HTTP interface used by the Ordering orchestrator.
"""

import os
import sqlite3
import time
from flask import Flask, request, jsonify
from common_log import log

app = Flask(__name__)
SERVICE = "payment"
DB_PATH = os.environ.get("PAYMENT_DB", "/data/payment.db")


def init_db():
    """Create the payment table in this service's own database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS payments (
                     paymentId TEXT PRIMARY KEY,
                     orderId   TEXT,
                     amount    REAL,
                     status    TEXT,
                     ts        TEXT )""")
    con.commit()
    con.close()


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


@app.route("/capture", methods=["POST"])
def capture():
    """Capture a payment for an order and store it (request-reply)."""
    req = request.get_json(force=True)
    order_id = req.get("orderId")
    amount = req.get("amount", {}).get("value", 0)

    payment_id = "PAY-" + str(order_id).split("-")[-1]
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Store in this service's own database only.
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT OR REPLACE INTO payments VALUES (?,?,?,?,?)",
                (payment_id, order_id, amount, "captured", ts))
    con.commit()
    con.close()

    log(SERVICE, "payment captured", order_id=order_id,
        extra={"paymentId": payment_id, "amount": amount})

    # PaymentCaptured event returned as the reply.
    return jsonify({
        "eventType": "PaymentCaptured",
        "version": 1,
        "timestamp": ts,
        "orderId": order_id,
        "paymentId": payment_id,
        "status": "captured",
    })


if __name__ == "__main__":
    init_db()
    log(SERVICE, "payment service starting")
    app.run(host="0.0.0.0", port=5002)
