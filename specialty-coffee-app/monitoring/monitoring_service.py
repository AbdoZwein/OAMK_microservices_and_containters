"""
Monitoring microservice.

Collects logs and events from all other services centrally (the "additional
service to collect logs and make them available centrally" from the material).
Services POST their structured logs to /logs and their events to /events.
The collected data can be read back at /logs and /events for inspection.
"""

from collections import deque
from flask import Flask, request, jsonify

app = Flask(__name__)
SERVICE = "monitoring"

# Bounded in-memory ring buffers so the prototype never grows without limit.
LOGS = deque(maxlen=500)
EVENTS = deque(maxlen=500)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


@app.route("/logs", methods=["POST", "GET"])
def logs():
    if request.method == "POST":
        LOGS.append(request.get_json(force=True))
        return jsonify({"stored": True})
    # GET: return the collected logs (newest last).
    return jsonify(list(LOGS))


@app.route("/events", methods=["POST", "GET"])
def events():
    if request.method == "POST":
        evt = request.get_json(force=True)
        EVENTS.append(evt)
        print("[monitoring] event: " + str(evt), flush=True)
        return jsonify({"stored": True})
    return jsonify(list(EVENTS))


@app.route("/metrics")
def metrics():
    """Simple aggregated metrics from the collected logs/events."""
    errors = sum(1 for l in LOGS if l.get("level") == "ERROR")
    paid = sum(1 for e in EVENTS if e.get("eventType") == "OrderPaid")
    return jsonify({
        "logCount": len(LOGS),
        "eventCount": len(EVENTS),
        "errors": errors,
        "ordersPaid": paid,
    })


if __name__ == "__main__":
    print("[monitoring] monitoring service starting", flush=True)
    app.run(host="0.0.0.0", port=6000)
