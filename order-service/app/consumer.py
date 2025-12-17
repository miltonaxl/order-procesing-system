import asyncio
import os
import json
import aio_pika
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Order, OrderStatus
from app.messaging import publish_event
from uuid import uuid4
from datetime import datetime

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")

async def update_order_status(order_id: str, new_status: OrderStatus, db: AsyncSession):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.add(order)
        await db.commit()
        await db.refresh(order)
        print(f"Order {order_id} status updated to {new_status.value}")
        return order
    return None

async def process_inventory_unavailable(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            order_id = event_data["order_id"]
            print(f"Order Service received InventoryUnavailable for order {order_id}")

            async for session in get_session():
                order = await update_order_status(order_id, OrderStatus.CANCELLED, session)
                if order:
                    # Publish OrderCancelled event for Inventory Service to release inventory (if any was reserved)
                    event_to_publish = {
                        "event_id": str(uuid4()),
                        "event_type": "OrderCancelled",
                        "timestamp": str(order.updated_at),
                        "order_id": order_id,
                        "reason": "Inventory Unavailable"
                    }
                    await publish_event("order_exchange", "order.cancelled", event_to_publish)

        except Exception as e:
            print(f"Error processing InventoryUnavailable: {e}")

async def process_payment_processed(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            order_id = event_data["order_id"]
            print(f"Order Service received PaymentProcessed for order {order_id}")

            async for session in get_session():
                order = await update_order_status(order_id, OrderStatus.COMPLETED, session)
                if order:
                    # Publish OrderConfirmed event for Notification Service
                    event_to_publish = {
                        "event_id": str(uuid4()),
                        "event_type": "OrderConfirmed",
                        "timestamp": str(order.updated_at),
                        "order_id": order_id,
                        "total_amount": order.total_amount
                    }
                    await publish_event("order_exchange", "order.confirmed", event_to_publish)

        except Exception as e:
            print(f"Error processing PaymentProcessed: {e}")

async def process_payment_failed(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            order_id = event_data["order_id"]
            print(f"Order Service received PaymentFailed for order {order_id}")

            async for session in get_session():
                order = await update_order_status(order_id, OrderStatus.CANCELLED, session)
                if order:
                    # Publish OrderCancelled event for Inventory Service to release inventory
                    event_to_publish = {
                        "event_id": str(uuid4()),
                        "event_type": "OrderCancelled",
                        "timestamp": str(order.updated_at),
                        "order_id": order_id,
                        "reason": "Payment Failed"
                    }
                    await publish_event("order_exchange", "order.cancelled", event_to_publish)

        except Exception as e:
            print(f"Error processing PaymentFailed: {e}")

async def start_consumer():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        # Declare exchanges
        inventory_exchange = await channel.declare_exchange("inventory_exchange", aio_pika.ExchangeType.TOPIC, durable=True)
        payment_exchange = await channel.declare_exchange("payment_exchange", aio_pika.ExchangeType.TOPIC, durable=True)

        # Declare queue and bind to relevant events
        queue = await channel.declare_queue("order_q", durable=True)
        await queue.bind(inventory_exchange, "inventory.unavailable")
        await queue.bind(payment_exchange, "payment.processed")
        await queue.bind(payment_exchange, "payment.failed")

        print("Order Service Consumer is listening for events...")
        
        async def on_message(message: aio_pika.IncomingMessage):
            if message.routing_key == "inventory.unavailable":
                await process_inventory_unavailable(message)
            elif message.routing_key == "payment.processed":
                await process_payment_processed(message)
            elif message.routing_key == "payment.failed":
                await process_payment_failed(message)
            else:
                async with message.process():
                    print(f"Ignored event with routing key: {message.routing_key}")

        await queue.consume(on_message, no_ack=False)

        # Keep the main task running
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(start_consumer())
    except KeyboardInterrupt:
        print("Order Service Consumer stopped.")
