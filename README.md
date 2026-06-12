# Coffee Shop Microservices Prototype

A prototype of containerized microservices from the coffee shop course project.
Three services run on an isolated Docker network and communicate using ZeroMQ,
realizing two of the communication patterns from the design.

## Services

| Service      | Role                          | Sockets / pattern                         |
|--------------|-------------------------------|-------------------------------------------|
| `payment`    | Captures payment              | ZeroMQ REP (request-reply server)         |
| `ordering`   | Orchestrator: places orders   | ZeroMQ REQ (request-reply client) + PUB   |
| `subscriber` | Notify / Analytics consumer   | ZeroMQ SUB (publish-subscribe consumer)   |

## Communication patterns realized

1. **Request-reply** (`ordering` -> `payment`): Ordering sends an `OrderPlaced`
   request and waits for the `PaymentCaptured` reply. This is the checked,
   orchestrated step.
2. **Publish-subscribe** (`ordering` -> `subscriber`): once paid, Ordering
   publishes an `OrderPaid` event on the `orders` topic. Loosely coupled
   subscribers receive it without the publisher knowing about them.

## Flow

```
ordering --(OrderPlaced, request)--> payment
ordering <--(PaymentCaptured, reply)-- payment
ordering --(OrderPaid, publish on "orders")--> subscriber
```

## Isolated network

The services share the `coffee-net` network defined in `docker-compose.yml`.
It is declared `internal: true`, so the containers can reach each other by
service name but have no access to the internet. No external connection is
needed to run the prototype.

## How to run

Requirements: Docker and Docker Compose.

```bash
# from the project root (the folder with docker-compose.yml)
docker compose up --build
```

You will see interleaved logs from the three services: Ordering placing an
order every 5 seconds, Payment replying, and the Subscriber receiving the
published event.

To stop:

```bash
docker compose down
```

## Configuration

Ports and host names are set with environment variables in
`docker-compose.yml` (for example `PAYMENT_PORT`, `PUB_PORT`, `TOPIC`), so the
services can be reconfigured without changing the source code.

## Project structure

```
.
├── docker-compose.yml          # services + isolated network
├── ordering/
│   ├── Dockerfile
│   └── ordering_service.py
├── payment/
│   ├── Dockerfile
│   └── payment_service.py
└── subscriber/
    ├── Dockerfile
    └── subscriber_service.py
```
