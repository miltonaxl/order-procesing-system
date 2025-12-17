# Order Service

This microservice handles the creation and management of customer orders. It exposes a REST API built with FastAPI and initiates the order processing saga by publishing events to RabbitMQ.

## Features

- **Create Order**: Accepts new orders and initiates the transaction.
- **Order Status**: Allows querying the current status of an order.
- **Saga Orchestration**: Publishes `OrderCreated` and reacts to downstream events (Payment/Inventory updates) to finalize or cancel orders.

## API Routes

| Method | Endpoint                 | Description                        |
| :----- | :----------------------- | :--------------------------------- |
| `POST` | `/api/orders`            | Create a new order.                |
| `GET`  | `/api/orders/{order_id}` | Retrieve order details and status. |

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (Orders table)
- **Messaging**: RabbitMQ (aio-pika)
