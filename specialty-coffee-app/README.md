# Coffee Shop Microservices Application

A small microservice-based distributed application for an online specialty
coffee shop. It has a frontend (UI), backend microservices, and databases, runs
as containers on an isolated network, and realizes the designs produced earlier
in the course (DDD model, communication patterns, migration plan, test plan).

## Architecture

```
                 browser
                    |
              [ frontend ]        widget-based UI (catalog, orders, monitoring)
                    |
              [ gateway ]         single entry point, routes requests
            /    |     |      \
   [ auth ] [ catalog ] [ ordering ] [ monitoring ]
                    |    \
              [ payment ]  +--> events + logs --> [ monitoring ]
                 |    |
          order.db   payment.db    (separate databases: Split Tables)
```

- **frontend** — serves the widget-based fragmented UI. Each widget loads its
  own data independently through the gateway (UI Composition pattern).
- **gateway** — single entry point; hides internal structure and routes to
  backend services.
- **catalog** — product catalog (read), request-reply.
- **ordering** — orchestrator. Creates orders, calls payment and checks the
  reply, owns its own `order.db`.
- **payment** — captures payment, owns its own `payment.db`.
- **monitoring** — collects logs and events from all services centrally and
  exposes simple metrics.
- **auth** — login service; issues a signed token and verifies tokens. Order
  placement is protected and requires a valid token.

## Workflow and communication patterns

- **Orchestration** for the order flow: `ordering` drives the process and waits
  for `payment`'s reply before marking the order `Paid`.
- **Request-reply** between the UI/gateway and services, and between ordering
  and payment.
- **Event publishing** of `OrderPaid` to the monitoring service.

## Implemented extra features (for grade)

- **Database (Split Tables pattern)** — ordering and payment each own a separate
  SQLite database on their own volume; no cross-service foreign keys.
- **Widget-based fragmented UI** — the page is composed of independent widgets.
- **Logging** — every service emits structured JSON logs (see `common_log.py`).
- **Monitoring microservice** — collects logs and events centrally, exposes
  `/metrics`.
- **Authentication** — an auth service issues signed tokens on login; the
  gateway verifies the token before allowing an order to be placed.
- **Unit & integration testing** — see `tests/`.
- **End-to-end testing** — see `tests/test_e2e.py`.

## Isolated network

Backend services share the `backend` network, declared `internal: true`, so
they have no internet access and communicate only by service name. A second
`edge` network exposes just the frontend (port 8000) and gateway (port 8080) to
the host browser.

## How to run

Requirements: Docker and Docker Compose.

```bash
docker compose up --build
```

Then open the UI:

```
http://localhost:8000
```

Log in first using the Login widget (demo users: alice / coffee123, or
bob / espresso). Then click "Order" on a product. The order is placed through
the gateway (which checks the token), paid via the ordering -> payment
orchestration, stored in the databases, and the Recent Orders and Monitoring
widgets update.

Stop and clean up:

```bash
docker compose down            # add -v to also remove the database volumes
```

## Running the tests

Unit and integration tests run without containers:

```bash
pip install flask pytest
python -m pytest tests/test_unit.py tests/test_integration.py -v
```

End-to-end tests run against the live application (start it first):

```bash
docker compose up --build -d
python -m pytest tests/test_e2e.py -v
```

## Project structure

```
.
├── docker-compose.yml          # services, isolated network, db volumes
├── requirements.txt
├── common_log.py               # shared structured-logging helper
├── frontend/                   # widget-based UI service (incl. login widget)
├── gateway/                    # API gateway (verifies tokens)
├── auth/                       # login + token verification
├── catalog/                    # catalog service
├── ordering/                   # ordering orchestrator (+ order.db)
├── payment/                    # payment service (+ payment.db)
├── monitoring/                 # central logs + events + metrics
├── tests/                      # unit, integration, end-to-end tests
└── TEST_PLAN.md                # test plan for the application
```
