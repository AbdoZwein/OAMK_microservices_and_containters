"""
Ordering microservice (orchestrator).

Realizes two communication patterns from the design:
  1. REQUEST-REPLY  : it sends a capture request to the Payment service and
                      waits for the PaymentCaptured reply (ZeroMQ REQ socket).
  2. PUBLISH-SUBSCRIBE : once the order is paid, it publishes an order event
                      on a PUB socket; loosely coupled subscribers receive it.

This is the orchestration workflow from the design: Ordering drives the
process, checks the Payment reply, then announces the result.
"""

import json
import os
import time
import zmq

# Address of the Payment service. Uses the Docker service name "payment" so it
# resolves on the isolated network without needing the internet.
PAYMENT_HOST = os.environ.get("PAYMENT_HOST", "payment")
PAYMENT_PORT = os.environ.get("PAYMENT_PORT", "5555")

# Port this service publishes order events on.
PUB_PORT = os.environ.get("PUB_PORT", "5556")


def make_order_placed(order_id):
    """Build an OrderPlaced event (the request sent to Payment)."""
    return {
        "eventType": "OrderPlaced",
        "version": 1,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "orderId": order_id,
        "customerId": "CUST-552",
        "items": [{"productId": "P-77", "qty": 2}],
        "amount": {"value": 18.50, "currency": "EUR"},
    }


def main():
    context = zmq.Context()

    # REQ socket = the "request" half of request-reply. Connects to Payment.
    req = context.socket(zmq.REQ)
    req.connect("tcp://" + PAYMENT_HOST + ":" + PAYMENT_PORT)

    # PUB socket = publishes events to any subscribers (publish-subscribe).
    pub = context.socket(zmq.PUB)
    pub.bind("tcp://*:" + PUB_PORT)

    print("[ordering] connected to payment at " + PAYMENT_HOST + ":" + PAYMENT_PORT, flush=True)
    print("[ordering] publishing order events on port " + PUB_PORT, flush=True)

    # Give subscribers a moment to connect before the first publish, otherwise
    # early messages can be missed (a known ZeroMQ pub/sub "slow joiner" effect).
    time.sleep(2)

    counter = 10231
    while True:
        order_id = "ORD-" + str(counter)
        order = make_order_placed(order_id)

        # --- Request-reply step (orchestration) ---
        print("[ordering] placing order " + order_id + ", requesting payment...", flush=True)
        req.send_json(order)
        payment_reply = req.recv_json()  # wait for Payment's reply
        print("[ordering] payment reply: " + json.dumps(payment_reply), flush=True)

        # --- Publish step (choreography for downstream consumers) ---
        # Only proceed if payment was captured (checking the output).
        if payment_reply.get("status") == "captured":
            event = {
                "eventType": "OrderPaid",
                "version": 1,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "orderId": order_id,
                "paymentId": payment_reply.get("paymentId"),
            }
            # The topic ("orders") lets subscribers filter by subject.
            pub.send_string("orders " + json.dumps(event))
            print("[ordering] published event: " + json.dumps(event), flush=True)

        counter += 1
        time.sleep(5)  # place a new order every 5 seconds


if __name__ == "__main__":
    main()
