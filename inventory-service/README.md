# Inventory Service

This microservice manages product stock and reservations. It operates primarily as a background consumer that listens to order events to reserve inventory.

## Features

- **Stock Management**: Checks available inventory for requested items in an order.
- **Reservation**: Reserves stock if available, or signals unavailability.
- **Saga Participation**:
  - Consumes: `OrderCreated`, `OrderCancelled`
  - Publishes: `InventoryReserved`, `InventoryUnavailable`

## API Routes

_This service does not expose public HTTP endpoints. It communicates entirely via RabbitMQ messages/events._

## Tech Stack

- **Database**: PostgreSQL (Inventory, InventoryReservation tables)
- **Messaging**: RabbitMQ (aio-pika)
