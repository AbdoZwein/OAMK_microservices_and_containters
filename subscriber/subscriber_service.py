"""
Subscriber microservice (stand-in for Notify / Analytics consumers).

Realizes the consumer side of the PUBLISH-SUBSCRIBE pattern from the design.
It connects a ZeroMQ SUB socket to the Ordering service's publisher and prints
every order event it receives. This is a choreography consumer: it simply
reacts to events and the publisher does not know it exists.
"""

import json
import os
import zmq

# Address of the Ordering service's publisher, using the Docker service name.
ORDERING_HOST = os.environ.get("ORDERING_HOST", "ordering")
PUB_PORT = os.environ.get("PUB_PORT", "5556")

# Topic to subscribe to. Empty string would mean "all topics".
TOPIC = os.environ.get("TOPIC", "orders")


def main():
    context = zmq.Context()
    sub = context.socket(zmq.SUB)
    sub.connect("tcp://" + ORDERING_HOST + ":" + PUB_PORT)
    # Subscribe to the chosen topic; only matching messages are delivered.
    sub.setsockopt_string(zmq.SUBSCRIBE, TOPIC)
    print("[subscriber] subscribed to topic '" + TOPIC + "' on "
          + ORDERING_HOST + ":" + PUB_PORT, flush=True)

    while True:
        # Messages arrive as "topic {json}". Split off the topic prefix.
        message = sub.recv_string()
        topic, _, payload = message.partition(" ")
        event = json.loads(payload)
        print("[subscriber] received " + event.get("eventType", "?")
              + " for " + event.get("orderId", "?")
              + ": " + json.dumps(event), flush=True)


if __name__ == "__main__":
    main()
