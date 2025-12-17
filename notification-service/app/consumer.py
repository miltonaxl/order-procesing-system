import asyncio
import os
import json
import aio_pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")

async def process_notification_event(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            event_data = json.loads(message.body.decode())
            event_type = event_data.get("event_type", "UNKNOWN")
            order_id = event_data.get("order_id", "N/A")

            # Simulate sending notification (log to console/file)
            print(f"--- NOTIFICATION SENT ---")
            print(f"Event Type: {event_type}")
            print(f"Order ID: {order_id}")
            print(f"Full Event Data: {event_data}")
            print(f"-------------------------")

        except Exception as e:
            print(f"Error processing notification event: {e}")
            # Re-queue the message or send to a Dead Letter Queue (DLQ)

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        # Declare exchanges
        order_exchange = await channel.declare_exchange("order_exchange", aio_pika.ExchangeType.TOPIC, durable=True)
        payment_exchange = await channel.declare_exchange("payment_exchange", aio_pika.ExchangeType.TOPIC, durable=True)

        # Declare queue and bind to all relevant events
        queue = await channel.declare_queue("notification_q", durable=True)
        await queue.bind(order_exchange, "order.confirmed")
        await queue.bind(order_exchange, "order.cancelled")
        await queue.bind(payment_exchange, "payment.processed")
        await queue.bind(payment_exchange, "payment.failed")

        print("Notification Service is listening for events...")
        await queue.consume(process_notification_event)

        # Keep the main task running
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Notification Service stopped.")
