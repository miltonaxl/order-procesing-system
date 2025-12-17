import os
import json
import aio_pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")
connection = None
channel = None

async def setup_rabbitmq():
    global connection, channel
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        # Declare exchange for order events
        await channel.declare_exchange("order_exchange", aio_pika.ExchangeType.TOPIC, durable=True)
        print("RabbitMQ setup complete.")
    except Exception as e:
        print(f"Error setting up RabbitMQ: {e}")

async def publish_event(exchange_name: str, routing_key: str, message_data: dict):
    if not channel:
        print("RabbitMQ channel not available. Cannot publish event.")
        return

    message_body = json.dumps(message_data).encode('utf-8')
    message = aio_pika.Message(
        message_body,
        content_type='application/json',
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    )

    try:
        # Get the exchange declared in setup_rabbitmq or declare it if it doesn't exist
        # Since we want to be safe, let's just get it or rely on setup to have created it.
        # But we need the exchange object to publish to it directly (for topic exchange).
        # Alternatively, we can use channel.default_exchange specific method? No.
        
        exchange = await channel.get_exchange(exchange_name)
        await exchange.publish(
            message,
            routing_key=routing_key
        )
        print(f"Published event to {routing_key}: {message_data['event_type']}")
    except Exception as e:
        print(f"Error publishing event: {e}")

# Consumer logic would go here, but for simplicity, we'll put it in a separate consumer file or a separate function
# that runs in the background.
