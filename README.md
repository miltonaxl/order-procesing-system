# Senior Backend Developer Assessment: Distributed Order Processing System

This repository contains the solution for the Senior Backend Developer Assessment, implementing a distributed order processing system using a microservices architecture and the Choreography Saga Pattern.

## Documentation

Please select your preferred language for the detailed documentation:

- **[English Documentation (README.en.md)](README.en.md)**
- **[Documentación en Español (README.es.md)](README.es.md)**

---

## Quick Start

To run the entire system, ensure you have Docker and Docker Compose installed, then execute:

```bash
docker-compose up --build
```

## Service Routes & Architecture

### 📦 Order Service (Port 8000)

| Method | Endpoint                 | Description                                                                                  |
| :----- | :----------------------- | :------------------------------------------------------------------------------------------- |
| `POST` | `/api/orders`            | Create a new order. Payload: `{ "customer_id": "...", "items": [...], "total_amount": ... }` |
| `GET`  | `/api/orders/{order_id}` | Get order status.                                                                            |
| `GET`  | `/api/orders`            | Get all orders.                                                                              |

### 📦 Background Services

The following services operate as background workers consuming RabbitMQ events and do not expose public HTTP endpoints:

- **Inventory Service**: Manages stock reservation.
- **Payment Service**: Processes payments.
- **Notification Service**: Sends notifications.
