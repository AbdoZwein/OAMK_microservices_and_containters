"""
Catalog microservice.

Bounded context: Product Catalog. Owns its own product data and exposes a
read-only HTTP interface. Realizes the request-reply pattern (the UI/gateway
asks, the service replies).
"""

from flask import Flask, jsonify
from common_log import log

app = Flask(__name__)
SERVICE = "catalog"

# Catalog data owned by this service (its own "database" / aggregate store).
# Kept in memory for the prototype; in production this is the Catalog DB.
PRODUCTS = [
    {"productId": "P-77", "name": "Ethiopia Yirgacheffe", "price": 18.50},
    {"productId": "P-78", "name": "Colombia Huila", "price": 16.00},
    {"productId": "P-79", "name": "Kenya AA", "price": 19.50},
]


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


@app.route("/products")
def products():
    """Return the product catalog (request-reply)."""
    log(SERVICE, "served product list", extra={"count": len(PRODUCTS)})
    return jsonify(PRODUCTS)


if __name__ == "__main__":
    log(SERVICE, "catalog service starting")
    app.run(host="0.0.0.0", port=5001)
