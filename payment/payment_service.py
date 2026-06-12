"""
Payment microservice.

Realizes the REQUEST-REPLY communication pattern from the design.
It binds a ZeroMQ REP (reply) socket and waits for capture requests from the
Ordering service. For each request it produces a PaymentCaptured event and
sends it back as the reply. No real payment logic is implemented; this is a
prototype that demonstrates the service interaction.
"""

import json
import os
import time
import zmq

# Port the payment service listens on (taken from environment, with a default).
PORT = os.environ.get("PAYMENT_PORT", "5555")


def make_payment_captured(request):
    """Build a PaymentCaptured event for a given OrderPlaced request."""
    return {
        "eventType": "PaymentCaptured",
        "version": 1,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "orderId": request.get("orderId"),
        "paymentId": "PAY-" + str(request.get("orderId", "0")).split("-")[-1],
        "status": "captured",
    }


def main():
    context = zmq.Context()
    # REP socket = the "reply" half of request-reply. It waits for a request,
    # then must send exactly one reply before it can receive the next request.
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:" + PORT)
    print("[payment] listening on port " + PORT, flush=True)

    while True:
        # Blocking receive: wait for a request from the Ordering service.
        message = socket.recv_json()
        print("[payment] received capture request: " + json.dumps(message), flush=True)

        # Build the reply event and send it back to the requester.
        reply = make_payment_captured(message)
        socket.send_json(reply)
        print("[payment] sent reply: " + json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
