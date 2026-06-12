# Test Plan: Coffee Shop Microservices

This test plan covers the implemented services, focusing on the Ordering
(orchestrator) and Payment services, plus the catalog and the end-to-end
workflow through the gateway.

## 1. Test environment, stubs and mocks

The application runs on an isolated network. For automated tests:

- **Unit tests** run each service in isolation through Flask's test client, with
  no other service running and the monitoring URL pointing at an unreachable
  address so logging is a no-op.
- **Integration tests** start a **stub Payment** server that returns a
  predefined `PaymentCaptured` reply, so the Ordering orchestration can be
  tested without the real Payment service.
- **End-to-end tests** run against the full running application via the gateway,
  with all real services and the monitoring service collecting logs/events.

## 2. Testing approaches

### Unit testing (single service / function)
- Domain testing: a valid order produces a captured payment.
- Boundary value analysis: zero amount still yields a valid reply.
- Equivalence testing: the paymentId is derived correctly from the orderId.
- Catalog returns the expected product list.

### Integration testing (services together)
- Bottom-up: each service passes its unit tests first, then Ordering and a stub
  Payment are tested together over HTTP.
- Verifies the orchestration step: order created, payment called, reply checked,
  order marked `Paid`, and the order persisted in the database.

### End-to-end testing (entire workflow)
- Catalog reachable through the gateway.
- A full order placed through the gateway returns `Paid` and appears in the
  orders list.
- Monitoring metrics reflect at least one paid order.

## 3. Logging and monitoring

- Every service writes structured JSON logs and forwards them to the central
  monitoring service.
- The `orderId` is the correlation id, carried through request, reply, and
  event, so an action can be followed across services.
- The monitoring service exposes `/metrics` (orders paid, events, logs, errors)
  used by the monitoring widget and the end-to-end test.

## 4. Test cases summary

| ID  | Type        | Case                                            | Expected            |
|-----|-------------|-------------------------------------------------|---------------------|
| U1  | Unit        | Payment capture, valid order                    | status = captured   |
| U2  | Unit        | Payment capture, zero amount                    | status = captured   |
| U3  | Unit        | paymentId derived from orderId                  | PAY-555             |
| U4  | Unit        | Catalog lists products                          | >= 1 product        |
| A1  | Unit        | Login with valid credentials                    | token issued        |
| A2  | Unit        | Login with wrong password                       | 401                 |
| A3  | Unit        | Login unknown user                              | 401                 |
| A4  | Unit        | Verify valid token                              | valid = true        |
| A5  | Unit        | Verify tampered token                           | 401                 |
| I1  | Integration | Order flow with stub payment                    | status = Paid       |
| I2  | Integration | Order persisted                                 | count increases     |
| E1  | End-to-end  | Catalog via gateway                             | >= 1 product        |
| E2  | End-to-end  | Order without token                             | rejected 401        |
| E3  | End-to-end  | Full order workflow (logged in)                 | status = Paid       |
| E4  | End-to-end  | Monitoring recorded the order                   | ordersPaid >= 1     |

## 5. How to run

```bash
# unit + integration (no containers needed)
python -m pytest tests/test_unit.py tests/test_integration.py -v

# end-to-end (application must be running)
docker compose up --build -d
python -m pytest tests/test_e2e.py -v
```
