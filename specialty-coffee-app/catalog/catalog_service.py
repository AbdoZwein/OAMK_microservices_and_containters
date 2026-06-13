"""
Catalog microservice.

Bounded context: Product Catalog. Owns its own product data and exposes an
HTTP interface to list, add, edit and remove products (request-reply pattern:
the UI/gateway asks, the service replies).
"""

from flask import Flask, request, jsonify
from common_log import log

app = Flask(__name__)
SERVICE = "catalog"

# Catalog data owned by this service (its own "database" / aggregate store).
# Kept in memory for the prototype; in production this is the Catalog DB.
# Changes persist for the life of the container, not across restarts.
PRODUCTS = [
    {"productId": "P-77", "name": "Ethiopia Yirgacheffe", "price": 18.50},
    {"productId": "P-78", "name": "Colombia Huila", "price": 16.00},
    {"productId": "P-79", "name": "Kenya AA", "price": 19.50},
]


def _next_id():
    """Allocate the next P-<n> id from the existing products."""
    nums = [int(p["productId"].split("-")[1]) for p in PRODUCTS
            if p["productId"].startswith("P-") and p["productId"].split("-")[1].isdigit()]
    return "P-" + str((max(nums) + 1) if nums else 80)


def _find(product_id):
    for p in PRODUCTS:
        if p["productId"] == product_id:
            return p
    return None


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE})


@app.route("/products")
def products():
    """Return the product catalog (request-reply)."""
    log(SERVICE, "served product list", extra={"count": len(PRODUCTS)})
    return jsonify(PRODUCTS)


@app.route("/products", methods=["POST"])
def add_product():
    """Add a new product to the catalog."""
    body = request.get_json(force=True)
    name = str(body.get("name", "")).strip()
    try:
        price = round(float(body.get("price", 0)), 2)
    except (TypeError, ValueError):
        price = 0
    if not name or price <= 0:
        return jsonify({"error": "name and a positive price are required"}), 400
    product = {"productId": body.get("productId") or _next_id(), "name": name, "price": price}
    PRODUCTS.append(product)
    log(SERVICE, "product added", extra={"productId": product["productId"]})
    return jsonify(product), 201


@app.route("/products/<product_id>", methods=["PUT"])
def edit_product(product_id):
    """Edit an existing product's name and/or price."""
    product = _find(product_id)
    if product is None:
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    if str(body.get("name", "")).strip():
        product["name"] = str(body["name"]).strip()
    if "price" in body:
        try:
            new_price = round(float(body["price"]), 2)
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number"}), 400
        if new_price <= 0:
            return jsonify({"error": "price must be positive"}), 400
        product["price"] = new_price
    log(SERVICE, "product edited", extra={"productId": product_id})
    return jsonify(product)


@app.route("/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    """Remove a product from the catalog."""
    global PRODUCTS
    if _find(product_id) is None:
        return jsonify({"error": "not found"}), 404
    PRODUCTS = [p for p in PRODUCTS if p["productId"] != product_id]
    log(SERVICE, "product removed", extra={"productId": product_id})
    return jsonify({"deleted": product_id})


if __name__ == "__main__":
    log(SERVICE, "catalog service starting")
    app.run(host="0.0.0.0", port=5001)
