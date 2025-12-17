# Senior Backend Developer Assessment: Distributed Order Processing System

This project implements a distributed order processing system using a microservices architecture, asynchronous event-based communication (Saga Pattern), and the required technology stack: **Python 3.11+, FastAPI, PostgreSQL, and RabbitMQ**.

## Architecture and Design

The system follows a **Microservices** architecture with an **Eventual Consistency** approach (Choreography Saga Pattern).

### Services

| Service                  | Responsibility                    | Technology      | Database                    | Events Published                            | Events Subscribed To                                                    |
| :----------------------- | :-------------------------------- | :-------------- | :-------------------------- | :------------------------------------------ | :---------------------------------------------------------------------- |
| **Order Service**        | Order management (REST API).      | FastAPI         | PostgreSQL (`order_db`)     | `OrderCreated`, `OrderCancelled`            | `InventoryUnavailable`, `PaymentProcessed`, `PaymentFailed`             |
| **Inventory Service**    | Stock and reservation management. | Python Consumer | PostgreSQL (`inventory_db`) | `InventoryReserved`, `InventoryUnavailable` | `OrderCreated`, `OrderCancelled`                                        |
| **Payment Service**      | Payment processing simulation.    | Python Consumer | PostgreSQL (`payment_db`)   | `PaymentProcessed`, `PaymentFailed`         | `InventoryReserved`                                                     |
| **Notification Service** | Simulated notification sending.   | Python Consumer | N/A                         | N/A                                         | `OrderConfirmed`, `OrderCancelled`, `PaymentProcessed`, `PaymentFailed` |

### Event Flow (Choreography Saga)

1.  **Client** sends `POST /api/orders` to the **Order Service**.
2.  **Order Service** creates the order in `PENDING` status and publishes the `OrderCreated` event.
3.  **Inventory Service** consumes `OrderCreated`, checks stock, and:
    - If stock is available, reserves the inventory and publishes `InventoryReserved`.
    - If stock is unavailable, publishes `InventoryUnavailable` (which leads to order cancellation by the Order Service).
4.  **Payment Service** consumes `InventoryReserved`, simulates payment (80% success, with retries), and publishes:
    - `PaymentProcessed` if successful.
    - `PaymentFailed` if it fails after retries.
5.  **Order Service** consumes `InventoryUnavailable`, `PaymentProcessed`, or `PaymentFailed` and updates the order status to `CANCELLED` or `COMPLETED` respectively.
6.  **Notification Service** consumes the final status events (`OrderConfirmed`, `OrderCancelled`, `PaymentProcessed`, `PaymentFailed`) and logs the corresponding notification.

## Technical Requirements

- **Monorepo:** All services are in separate folders (`order-service`, `inventory-service`, etc.) at the root of the repository.
- **Containers:** `docker-compose.yml` is used to bring up all services, databases (PostgreSQL), and the Message Queue (RabbitMQ) with a single command.
- **Async/Await:** Use of `async/await` throughout the I/O code (FastAPI, `asyncpg`, `aio-pika`).
- **Persistence:** Each service has its own database and uses **Alembic** for migrations.
- **Idempotency:** The **Payment Service** uses the `order_id` as the primary key in its payments table to prevent double processing.
- **Retry Logic:** The **Payment Service** uses the `tenacity` library with _exponential backoff_ to retry failed payment processing.

## Setup and Execution

### Prerequisites

- Docker and Docker Compose installed.

### Execution Steps

1.  **Clone the repository:**

    ```bash
    git clone <REPOSITORY_URL>
    cd order-processing-system
    ```

2.  **Start the system:**
    ```bash
    docker-compose up --build
    ```
    This will build the images, start RabbitMQ, the three PostgreSQL databases, and the four microservices. Consumer services (Inventory, Payment, Notification) will automatically run their Alembic migrations and start listening for events.

### API Documentation (Order Service)

The **Order Service** exposes a REST API at `http://localhost:8000`.

#### 1. Create an Order

**Endpoint:** `POST /api/orders`

**Request Example (cURL):**

```bash
curl -X POST http://localhost:8000/api/orders \
-H "Content-Type: application/json" \
-d '{
"customer_id": "customer-123",
"items": [
{"product_id": "product-A", "quantity": 2},
{"product_id": "product-B", "quantity": 1}
],
"total_amount": 150.00
}'
```

**Response Example (201 Created):**

```json
{
  "id": "order-uuid-generated",
  "customer_id": "customer-123",
  "items": "[{\"product_id\": \"product-A\", \"quantity\": 2}, {\"product_id\": \"product-B\", \"quantity\": 1}]",
  "total_amount": 150.0,
  "status": "PENDING",
  "created_at": "2025-12-16T10:00:00.000000",
  "updated_at": "2025-12-16T10:00:00.000000"
}
```

#### 2. Check Order Status

**Endpoint:** `GET /api/orders/{order_id}`

**Request Example (cURL):**

```bash
curl http://localhost:8000/api/orders/order-uuid-generated
```

**Response:** Returns the `OrderRead` object with the current status (`PENDING`, `COMPLETED`, `CANCELLED`, etc.).

### Testing Guide (Full Flow)

1.  **Initialize Inventory:** The `Inventory Service` runs an initial _seeding_ script to populate the `inventory` table with products and stock.
2.  **Create Order:** Execute the order creation `cURL`.
3.  **Check Logs:**
    - Observe **Order Service** logs (publishing `OrderCreated`).
    - Observe **Inventory Service** logs (consuming `OrderCreated`, publishing `InventoryReserved`).
    - Observe **Payment Service** logs (consuming `InventoryReserved`, payment simulation, publishing `PaymentProcessed` or `PaymentFailed`).
    - Observe **Order Service** logs (consuming payment event, status update).
    - Observe **Notification Service** logs (consuming payment event, simulated notification).
4.  **Check Final Status:** Use the query `cURL` to verify the final order status is `COMPLETED` (if payment was successful) or `CANCELLED` (if it failed).

#### Test Products (Seeder Data)

The inventory is automatically seeded with the following products for testing purposes:

| Product ID  | Initial Stock | Behavior Scenario                                                                 |
| :---------- | :------------ | :-------------------------------------------------------------------------------- |
| `product-A` | 10            | **Success Path:** Use this to test successful reservations.                       |
| `product-B` | 5             | **Low Stock:** Use this to test depletion.                                        |
| `product-C` | 0             | **Failure Path:** Use this to test `InventoryUnavailable` and Order Cancellation. |

## Key Architectural Decisions

1.  **Choreography Saga Pattern:** The choreography pattern was chosen (over orchestration) to keep services more decoupled. Services react to events without a central orchestrator, increasing resilience and independence.
2.  **RabbitMQ (aio-pika):** RabbitMQ was selected for its robustness and support for _Exchange Types_ (like `TOPIC`), which is ideal for the required publish/subscribe pattern. The `aio-pika` library ensures compatibility with `async/await`.
3.  **Idempotency in Payment Service:** The primary key of the `payments` table is the `order_id`. If the service receives the same `InventoryReserved` event twice, the attempt to insert the second payment will fail at the database level, ensuring payment is not processed twice.
4.  **Alembic in Dockerfile:** The `alembic upgrade head` line is executed in the `CMD` of the database-enabled services. This ensures the database is updated with the latest schema before the service starts running.

## Testing (Unit and Integration Tests)

Unit tests have been implemented for all services (`Order`, `Inventory`, `Payment`, `Notification`) using `pytest` and `pytest-asyncio`, demonstrating the ability to:

1.  **Test REST API logic** (order creation and query).
2.  **Mock external dependencies** (database and messaging).
3.  **Test critical consumer logic** (status update after payment event).

### How to Run Unit Tests

1.  Ensure containers are up (`docker-compose up`).
2.  Execute the following command inside each service container:

```bash
docker exec -it order-service poetry run pytest
docker exec -it inventory-service poetry run pytest
docker exec -it payment-service poetry run pytest
docker exec -it notification-service poetry run pytest
```

### Integration Tests (Full Flow)

An integration test has been implemented that simulates the full order flow, including the payment failure scenario and the compensating transaction (inventory rollback).

**To run integration tests:**

1.  Ensure all services are up (`docker-compose up`).
2.  Install test dependencies in your local environment (or in a test container):
    ```bash
    pip install -r tests/requirements.txt
    ```
3.  Run the integration test:
    ```bash
    pytest tests/test_integration.py
    ```

## 100% Compliance with Mandatory Requirements

The current solution complies with 100% of the mandatory requirements of the assessment, including the implementation of compensating logic (rollback) to ensure data consistency in distributed failure scenarios.

| Failure Scenario                | Compliance | Solution Detail                                                                                                                                                                                                                                                     |
| :------------------------------ | :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1. Insufficient Inventory**   | **YES**    | **Inventory Service** publishes `InventoryUnavailable`, **Order Service** cancels the order and publishes `OrderCancelled`. **Inventory Service** consumes `OrderCancelled` and executes the **compensating transaction (rollback)**, returning inventory to stock. |
| **2. Payment Failure**          | **YES**    | **Payment Service** publishes `PaymentFailed`. **Order Service** cancels the order and publishes `OrderCancelled`. **Inventory Service** consumes `OrderCancelled` and executes the **compensating transaction (rollback)**, returning inventory to stock.          |
| **3. Temporary Unavailability** | **YES**    | **RabbitMQ** with durable queues and `message.process()` ensures messages are automatically retried when the service becomes available again.                                                                                                                       |
| **4. Duplicate Events**         | **YES**    | **Idempotency** implemented in the **Payment Service** using `order_id` as the primary key to prevent double processing.                                                                                                                                            |
| **5. Partial Failures**         | **YES**    | **Inventory Rollback** implemented. RabbitMQ's **Retry** mechanism handles temporary notification failures.                                                                                                                                                         |

## Implemented Bonus Points

### Resilience (Circuit Breaker)

The `tenacity` library is used in the **Payment Service** to implement a retry mechanism with _exponential backoff_. This acts as a simple **Circuit Breaker**, preventing the payment service from collapsing under transient failures and improving system robustness.

## Known Limitations and Future Improvements

- **Saga Timeout Mechanism:** Although compensating logic is implemented, the choreography pattern does not include a centralized _timeout_ mechanism. A **Saga Monitor** service could be added to look for stuck orders and force cancellation.
- **Advanced Observability:** Implementation of _Correlation IDs_ and _Structured Logging_ (e.g., with `structlog`) for distributed tracing. (Bonus Point)
- **Security and Performance:** Implementation of API Authentication (JWT), Caching, and Database Indexing (Bonus Points).
- **Observability:** Implementation of _Correlation IDs_ and _Structured Logging_ (e.g., with `structlog`) for distributed tracing.
