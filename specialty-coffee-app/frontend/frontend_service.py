"""
Frontend microservice (widget-based fragmented UI).

Serves a single page composed of independent WIDGETS, each responsible for one
service's data and loaded separately (UI Composition pattern from the material):
  - Login widget    -> /api/login   (authentication)
  - Catalog widget  -> /api/products
  - Order widget    -> /api/orders
  - Monitoring widget-> /api/metrics
Each widget fetches its own data from the gateway, so widgets can be developed
and updated independently. Placing an order requires a logged-in user; the
token is sent as an Authorization: Bearer header.
"""

import os
from flask import Flask, Response
from common_log import log

app = Flask(__name__)
SERVICE = "frontend"

GATEWAY_PUBLIC = os.environ.get("GATEWAY_PUBLIC", "http://localhost:8080")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Coffee Shop</title>
<style>
  body { font-family: Arial, sans-serif; margin: 0; background: #f8fafc; color: #1a1a1a; }
  header { background: #b45309; color: #fff; padding: 16px 24px; display: flex;
           justify-content: space-between; align-items: center; }
  header h1 { margin: 0; font-size: 20px; }
  #userbar { font-size: 13px; }
  #userbar button { margin-left: 8px; }
  .widgets { display: flex; flex-wrap: wrap; gap: 16px; padding: 20px; }
  .widget { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
            padding: 16px; flex: 1; min-width: 280px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
  .widget h2 { font-size: 15px; margin: 0 0 10px; color: #92400e;
               border-bottom: 2px solid #fde68a; padding-bottom: 6px; }
  .product { display: flex; justify-content: space-between; align-items: center;
             padding: 6px 0; border-bottom: 1px solid #f1f5f9; }
  button { background: #b45309; color: #fff; border: none; padding: 5px 10px;
           border-radius: 5px; cursor: pointer; font-size: 12px; }
  button:hover { background: #92400e; }
  button:disabled { background: #cbd5e1; cursor: not-allowed; }
  input { padding: 5px 7px; border: 1px solid #cbd5e1; border-radius: 5px; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid #f1f5f9; }
  th { color: #555; }
  .metric { display: flex; justify-content: space-between; padding: 5px 0; font-size: 13px; }
  .tag { padding: 1px 7px; border-radius: 10px; font-size: 11px; }
  .Paid { background: #dcfce7; color: #166534; }
  .PaymentFailed, .PaymentError { background: #fee2e2; color: #991b1b; }
  .AwaitingPayment { background: #fef3c7; color: #92400e; }
  /* Auth gate: a full-screen login shown before the app is revealed. */
  #gate { position: fixed; inset: 0; background: #f8fafc; display: flex;
          align-items: center; justify-content: center; }
  #gate .card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
                padding: 28px; width: 320px; box-shadow: 0 4px 16px rgba(0,0,0,.08); }
  #gate h2 { margin: 0 0 4px; color: #92400e; font-size: 20px; }
  #gate p.sub { margin: 0 0 18px; color: #64748b; font-size: 13px; }
  #gate input { width: 100%; box-sizing: border-box; padding: 9px 11px; font-size: 14px;
                margin-bottom: 10px; }
  #gate button { width: 100%; padding: 9px; font-size: 14px; }
  #loginMsg { font-size: 12px; color: #991b1b; min-height: 14px; margin-top: 6px; }
  #app { display: none; }   /* hidden until a successful login */
</style>
</head>
<body>

<!-- Auth gate: the first and only thing shown until login succeeds. -->
<div id="gate">
  <div class="card">
    <h2>Specialty Coffee Shop</h2>
    <p class="sub">Please log in to continue</p>
    <input id="username" placeholder="username" value="ubuntu"
           onkeydown="if(event.key==='Enter')login()" />
    <input id="password" type="password" placeholder="password" value="admin123"
           onkeydown="if(event.key==='Enter')login()" />
    <button onclick="login()">Log in</button>
    <div id="loginMsg"></div>
    <div style="font-size:11px;color:#94a3b8;margin-top:10px;">
      Demo users: ubuntu / admin123, abdo / admin123
    </div>
  </div>
</div>

<!-- The application: revealed only after authentication. -->
<div id="app">
  <header>
    <h1>Specialty Coffee Shop</h1>
    <div id="userbar">
      <span id="who"></span>
      <button onclick="logout()">Log out</button>
    </div>
  </header>
  <div class="widgets">

    <!-- Catalog widget: owned by the catalog service -->
    <div class="widget" id="catalog-widget">
      <h2>Catalog</h2>
      <div id="catalog">Loading...</div>
    </div>

    <!-- Orders widget: owned by the ordering service -->
    <div class="widget" id="orders-widget">
      <h2>Recent Orders</h2>
      <div id="orders">Loading...</div>
    </div>

    <!-- Monitoring widget: owned by the monitoring service -->
    <div class="widget" id="monitor-widget">
      <h2>Monitoring</h2>
      <div id="metrics">Loading...</div>
    </div>

  </div>
</div>

<script>
const GW = "__GATEWAY__";
let token = null;          // auth token, set after login
let username = null;
let refreshTimer = null;

// --- Auth gate logic ---
async function login() {
  const u = document.getElementById("username").value;
  const p = document.getElementById("password").value;
  const msg = document.getElementById("loginMsg");
  msg.textContent = "";
  const res = await fetch(GW + "/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: p })
  });
  if (!res.ok) { msg.textContent = "Invalid credentials"; return; }
  const data = await res.json();
  token = data.token;
  username = data.username;
  showApp();
}

function showApp() {
  document.getElementById("gate").style.display = "none";
  document.getElementById("app").style.display = "block";
  document.getElementById("who").textContent = "Logged in as " + username;
  // The app widgets each load their own data once authenticated.
  loadCatalog(); loadOrders(); loadMetrics();
  refreshTimer = setInterval(() => { loadOrders(); loadMetrics(); }, 4000);
}

function logout() {
  token = null; username = null;
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  document.getElementById("app").style.display = "none";
  document.getElementById("gate").style.display = "flex";
  document.getElementById("password").value = "";
  document.getElementById("loginMsg").textContent = "";
}

function loggedIn() { return token !== null; }

// --- Catalog widget logic ---
async function loadCatalog() {
  const res = await fetch(GW + "/api/products");
  const items = await res.json();
  document.getElementById("catalog").innerHTML = items.map(p =>
    `<div class="product"><span>${p.name} &mdash; &euro;${p.price.toFixed(2)}</span>
     <button onclick="order('${p.productId}', ${p.price})">Order</button></div>`
  ).join("");
}

// Placing an order sends the token; rejected if not logged in.
async function order(productId, price) {
  if (!loggedIn()) return;
  const res = await fetch(GW + "/api/orders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + token
    },
    body: JSON.stringify({ productId, qty: 1, price })
  });
  if (res.status === 401) { alert("Session expired. Please log in again."); logout(); return; }
  loadOrders();
  loadMetrics();
}

// --- Orders widget logic ---
async function loadOrders() {
  const res = await fetch(GW + "/api/orders");
  const orders = await res.json();
  if (!orders.length) { document.getElementById("orders").innerHTML = "<em>No orders yet</em>"; return; }
  document.getElementById("orders").innerHTML =
    "<table><tr><th>Order</th><th>Amount</th><th>Status</th></tr>" +
    orders.map(o =>
      `<tr><td>${o.orderId}</td><td>&euro;${o.amount.toFixed(2)}</td>
       <td><span class="tag ${o.status}">${o.status}</span></td></tr>`
    ).join("") + "</table>";
}

// --- Monitoring widget logic ---
async function loadMetrics() {
  const res = await fetch(GW + "/api/metrics");
  const m = await res.json();
  document.getElementById("metrics").innerHTML =
    `<div class="metric"><span>Orders paid</span><b>${m.ordersPaid}</b></div>
     <div class="metric"><span>Events collected</span><b>${m.eventCount}</b></div>
     <div class="metric"><span>Log entries</span><b>${m.logCount}</b></div>
     <div class="metric"><span>Errors</span><b>${m.errors}</b></div>`;
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    log(SERVICE, "served UI page")
    return Response(PAGE.replace("__GATEWAY__", GATEWAY_PUBLIC), mimetype="text/html")


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    log(SERVICE, "frontend starting")
    app.run(host="0.0.0.0", port=8000)
