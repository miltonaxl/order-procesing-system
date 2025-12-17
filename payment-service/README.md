# Payment Service

This microservice handles payment processing simulation. It listens for successful inventory reservations and attempts to process payment.

## Features

- **Payment Processing**: Simulates payment processing logic (e.g., 80% success rate).
- **Saga Participation**:
  - Consumes: `InventoryReserved`
  - Publishes: `PaymentProcessed`, `PaymentFailed`

## API Routes

_This service does not expose public HTTP endpoints. It communicates entirely via RabbitMQ messages/events._

## Tech Stack

- **Database**: PostgreSQL (Payments table)
- **Messaging**: RabbitMQ (aio-pika)
