# Notification Service

This microservice is responsible for simulating user notifications (e.g., email, SMS) based on significant system events.

## Features

- **Event Logging**: Listens to system events and logs "notifications" to the console.
- **Saga Participation**:
  - Consumes: `OrderConfirmed`, `PaymentProcessed`, `PaymentFailed`

## API Routes

_This service does not expose public HTTP endpoints. It communicates entirely via RabbitMQ messages/events._

## Tech Stack

- **Messaging**: RabbitMQ (aio-pika)
