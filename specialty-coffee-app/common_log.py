"""
Shared logging helper.

Each microservice imports this to write structured (JSON) logs and to forward
them to the central monitoring service. This realizes the "monitor small
things, aggregate centrally" approach: every service logs locally AND ships the
log line to the monitoring microservice so the whole workflow can be followed
using the orderId as a correlation id.
"""

import json
import os
import time
import urllib.request

# Address of the monitoring service (Docker service name on the isolated net).
MONITOR_URL = os.environ.get("MONITOR_URL", "http://monitoring:6000/logs")


def log(service, message, order_id=None, level="INFO", extra=None):
    """Write a structured log line and forward it to the monitoring service."""
    entry = {
        "service": service,
        "level": level,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "orderId": order_id,            # correlation id across services
        "message": message,
    }
    if extra:
        entry.update(extra)

    # Local log (visible in the container logs / docker compose output).
    print(json.dumps(entry), flush=True)

    # Forward to the central monitoring service. Best-effort: never crash the
    # caller if monitoring is briefly unavailable.
    try:
        data = json.dumps(entry).encode("utf-8")
        req = urllib.request.Request(
            MONITOR_URL, data=data,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass
