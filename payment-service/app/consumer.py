import asyncio
import os
import json
import aio_pika
import random
from datetime import datetime
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session, init_db
from app.models import Payment
from uuid import uuid4

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def simulate_payment_processing(order_id: str, amount: float) -> bool:
    # Simulate payment processing with 80% success rate
    if random.random() < 0.8:
        print(f"Payment for order {order_id} processed successfully.")
        return True
    else:
        print(f"Payment for order {order_id} failed. Retrying...")
        raise Exception("Payment simulation failed")

async def process_inventory_reserved(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            print(f"Payment Service received InventoryReserved: {event_data}")

            order_id = event_data["order_id"]
            # In a real scenario, we would fetch the order details to get the amount
            # For simplicity, we'll assume the amount is passed or known.
            # Let's assume the amount is 100 for now, or we need to update the event structure.
            # Since the OrderCreated event had total_amount, we should pass it through.
            # For now, we'll use a placeholder amount.
            amount = 100.0 # Placeholder

            # Check for idempotency (if payment for this order is already processed)
            async for session in get_session():
                existing_payment = await session.get(Payment, order_id)
                if existing_payment:
                    print(f"Payment for order {order_id} already processed. Skipping.")
                    return

            try:
                success = await simulate_payment_processing(order_id, amount)
                if success:
                    # Record payment success
                    async for session in get_session():
                        new_payment = Payment(
                            order_id=order_id,
                            amount=amount,
                            status="PROCESSED"
                        )
                        session.add(new_payment)
                        await session.commit()

                    # Publish PaymentProcessed event
                    event_to_publish = {
                        "event_id": str(uuid4()),
                        "event_type": "PaymentProcessed",
                        "timestamp": str(datetime.utcnow()),
                        "order_id": order_id,
                        "payment_id": str(uuid4()),
                        "amount": amount
                    }
                    await publish_event("payment_exchange", "payment.processed", event_to_publish)
            except Exception:
                # Record payment failure
                async for session in get_session():
                    new_payment = Payment(
                        order_id=order_id,
                        amount=amount,
                        status="FAILED"
                    )
                    session.add(new_payment)
                    await session.commit()

                # Publish PaymentFailed event
                event_to_publish = {
                    "event_id": str(uuid4()),
                    "event_type": "PaymentFailed",
                    "timestamp": str(datetime.utcnow()),
                    "order_id": order_id,
                    "reason": "Payment failed after retries"
                }
                await publish_event("payment_exchange", "payment.failed", event_to_publish)

        except Exception as e:
            print(f"Error processing InventoryReserved in Payment Service: {e}")
            # Re-queue the message or send to a Dead Letter Queue (DLQ)

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

async def main():
    await init_db()
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        # Declare exchanges
        inventory_exchange = await channel.declare_exchange("inventory_exchange", aio_pika.ExchangeType.TOPIC, durable=True)
        payment_exchange = await channel.declare_exchange("payment_exchange", aio_pika.ExchangeType.TOPIC, durable=True)

        # Declare queue and bind to InventoryReserved event
        queue = await channel.declare_queue("payment_q", durable=True)
        await queue.bind(inventory_exchange, "inventory.reserved")

        print("Payment Service is listening for events...")
        await queue.consume(process_inventory_reserved)

        # Keep the main task running
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Payment Service stopped.")
