import asyncio
import os
import json
import aio_pika
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_session, init_db
from app.models import Inventory, InventoryReservation
from uuid import uuid4

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")

async def publish_event(exchange_name: str, routing_key: str, message_data: dict):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
        message_body = json.dumps(message_data).encode('utf-8')
        message = aio_pika.Message(
            message_body,
            content_type='application/json',
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        await exchange.publish(message, routing_key=routing_key)
        print(f"Published event to {routing_key}: {message_data['event_type']}")

async def process_order_created(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            print(f"Inventory Service received OrderCreated: {event_data}")

            order_id = event_data["order_id"]
            items = event_data["items"]

            async for session in get_session():
                inventory_reserved = True
                reservations = []

                # 1. Check stock and prepare reservations
                for item in items:
                    product_id = item["product_id"]
                    quantity = item["quantity"]

                    inventory = await session.get(Inventory, product_id)
                    if not inventory or inventory.stock < quantity:
                        inventory_reserved = False
                        break
                    
                    reservations.append(InventoryReservation(
                        order_id=order_id,
                        product_id=product_id,
                        quantity=quantity
                    ))

                if inventory_reserved:
                    # 2. Decrement stock and save reservations
                    for res in reservations:
                        inventory = await session.get(Inventory, res.product_id)
                        inventory.stock -= res.quantity
                        session.add(inventory)
                        session.add(res)
                    await session.commit()

                    # 3. Publish InventoryReserved event
                    event_to_publish = {
                        "event_id": str(uuid4()),
                        "event_type": "InventoryReserved",
                        "timestamp": str(datetime.utcnow()),
                        "order_id": order_id,
                        "reservation_id": str(uuid4())
                    }
                    await publish_event("inventory_exchange", "inventory.reserved", event_to_publish)
                else:
                    # 4. Publish InventoryUnavailable event
                    event_to_publish = {
                        "event_id": str(uuid4()),
                        "event_type": "InventoryUnavailable",
                        "timestamp": str(datetime.utcnow()),
                        "order_id": order_id,
                        "reason": "Insufficient stock"
                    }
                    await publish_event("inventory_exchange", "inventory.unavailable", event_to_publish)

        except Exception as e:
            print(f"Error processing OrderCreated in Inventory Service: {e}")

async def process_order_cancelled(message: aio_pika.IncomingMessage):
    """
    Compensating transaction: Release reserved inventory.
    """
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            order_id = event_data["order_id"]
            print(f"Inventory Service received OrderCancelled: {event_data}")

            async for session in get_session():
                # 1. Find reservations for the cancelled order
                result = await session.execute(
                    select(InventoryReservation).where(InventoryReservation.order_id == order_id)
                )
                reservations = result.scalars().all()

                if not reservations:
                    print(f"No active reservation found for order {order_id}. Idempotent.")
                    return

                # 2. Rollback: Increment stock and delete reservation records
                for res in reservations:
                    inventory = await session.get(Inventory, res.product_id)
                    if inventory:
                        inventory.stock += res.quantity
                        session.add(inventory)
                
                # Delete all reservations for this order
                await session.execute(
                    delete(InventoryReservation).where(InventoryReservation.order_id == order_id)
                )
                
                await session.commit()
                print(f"Inventory successfully released for order {order_id}.")

        except Exception as e:
            print(f"Error processing OrderCancelled (Compensation) in Inventory Service: {e}")

async def main():
    await init_db()
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        # Declare exchanges
        order_exchange = await channel.declare_exchange("order_exchange", aio_pika.ExchangeType.TOPIC, durable=True)
        inventory_exchange = await channel.declare_exchange("inventory_exchange", aio_pika.ExchangeType.TOPIC, durable=True)

        # Declare queue and bind to OrderCreated and OrderCancelled events
        queue = await channel.declare_queue("inventory_q", durable=True)
        await queue.bind(order_exchange, "order.created")
        await queue.bind(order_exchange, "order.cancelled")

        print("Inventory Service is listening for events...")
        
        async def on_message(message: aio_pika.IncomingMessage):
            if message.routing_key == "order.created":
                await process_order_created(message)
            elif message.routing_key == "order.cancelled":
                await process_order_cancelled(message)
            else:
                async with message.process():
                    print(f"Ignored event with routing key: {message.routing_key}")

        await queue.consume(on_message, no_ack=False)

        # Keep the main task running
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Inventory Service stopped.")
