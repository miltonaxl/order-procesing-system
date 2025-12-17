import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import OrderStatus, Order
import json

# Mock para el contexto asíncrono de message.process()
@pytest.fixture
def mock_message_context():
    """Crear un contexto asíncrono mockeado para message.process()"""
    class AsyncContextManager:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return AsyncContextManager()

@pytest.mark.asyncio
async def test_consumer_payment_processed(mock_message_context):
    """
    Test case 1: Consumer processes PaymentProcessed event correctly.
    """
    from app.consumer import process_payment_processed
    from app.models import Order

    # Mock the database session and the order object
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    mock_order = Order(
        id="test-order-id",
        customer_id="cust-123",
        items='[{"product_id": "prod-1", "quantity": 2}]',
        total_amount=100.00,
        status=OrderStatus.PENDING
    )

    # Mock the database query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_order
    mock_session.execute.return_value = mock_result

    with patch("app.consumer.get_session", side_effect=mock_async_context):
        with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
            # Mock the incoming message
            mock_message = AsyncMock()
            mock_message.body = json.dumps({
                "event_id": "evt-125",
                "event_type": "PaymentProcessed",
                "order_id": "test-order-id",
                "payment_id": "pay-uuid",
                "amount": 100.00
            }).encode('utf-8')
            
            # Make process() a MagicMock that returns the context manager
            mock_message.process = MagicMock(return_value=mock_message_context)

            await process_payment_processed(mock_message)

            # Verify message was processed
            mock_message.process.assert_called_once()

            # Verify status update was made
            assert mock_order.status == OrderStatus.COMPLETED
            mock_session.commit.assert_called_once()

            # Verify OrderConfirmed event was published
            mock_publish_event.assert_called_once()
            args, _ = mock_publish_event.call_args
            assert args[1] == "order.confirmed"
            assert args[2]["event_type"] == "OrderConfirmed"

@pytest.mark.asyncio
async def test_consumer_payment_failed(mock_message_context):
    """
    Test case 2: Consumer processes PaymentFailed event correctly.
    """
    from app.consumer import process_payment_failed
    from app.models import Order

    # Mock the database session and the order object
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    mock_order = Order(
        id="test-order-id",
        customer_id="cust-123",
        items='[{"product_id": "prod-1", "quantity": 2}]',
        total_amount=100.00,
        status=OrderStatus.PAYMENT_PROCESSING
    )

    # Mock the database query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_order
    mock_session.execute.return_value = mock_result

    with patch("app.consumer.get_session", side_effect=mock_async_context):
        with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
            # Mock the incoming message
            mock_message = AsyncMock()
            mock_message.body = json.dumps({
                "event_id": "evt-126",
                "event_type": "PaymentFailed",
                "order_id": "test-order-id",
                "reason": "Insufficient funds"
            }).encode('utf-8')
            
            # Make process() a MagicMock that returns the context manager
            mock_message.process = MagicMock(return_value=mock_message_context)

            await process_payment_failed(mock_message)

            # Verify message was processed
            mock_message.process.assert_called_once()

            # Verify status update was made
            assert mock_order.status == OrderStatus.CANCELLED
            mock_session.commit.assert_called_once()

            # Verify OrderCancelled event was published
            mock_publish_event.assert_called_once()
            args, _ = mock_publish_event.call_args
            assert args[1] == "order.cancelled"
            assert args[2]["event_type"] == "OrderCancelled"

@pytest.mark.asyncio
async def test_consumer_inventory_unavailable(mock_message_context):
    """
    Test case 3: Consumer processes InventoryUnavailable event correctly.
    """
    from app.consumer import process_inventory_unavailable
    from app.models import Order

    # Mock the database session and the order object
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    mock_order = Order(
        id="test-order-id",
        customer_id="cust-123",
        items='[{"product_id": "prod-1", "quantity": 2}]',
        total_amount=100.00,
        status=OrderStatus.PENDING
    )

    # Mock the database query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_order
    mock_session.execute.return_value = mock_result

    with patch("app.consumer.get_session", side_effect=mock_async_context):
        with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
            # Mock the incoming message
            mock_message = AsyncMock()
            mock_message.body = json.dumps({
                "event_id": "evt-127",
                "event_type": "InventoryUnavailable",
                "order_id": "test-order-id",
                "reason": "Out of stock"
            }).encode('utf-8')
            
            # Make process() a MagicMock that returns the context manager
            mock_message.process = MagicMock(return_value=mock_message_context)

            await process_inventory_unavailable(mock_message)

            # Verify message was processed
            mock_message.process.assert_called_once()

            # Verify status update was made
            assert mock_order.status == OrderStatus.CANCELLED
            mock_session.commit.assert_called_once()

            # Verify OrderCancelled event was published
            mock_publish_event.assert_called_once()
            args, _ = mock_publish_event.call_args
            assert args[1] == "order.cancelled"
            assert args[2]["event_type"] == "OrderCancelled"