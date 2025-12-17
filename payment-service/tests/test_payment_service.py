import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Payment
from app.consumer import process_inventory_reserved, simulate_payment_processing
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
async def test_process_inventory_reserved_success(mock_message_context):
    """
    Test case 1: Successful payment processing and event publishing.
    """
    order_id = "test-order-id-1"
    amount = 100.00
    
    # Mock the database session
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    # Mock idempotency check (no existing payment)
    mock_session.get.return_value = None
    
    with patch("app.consumer.get_session", side_effect=mock_async_context):
        with patch("app.consumer.simulate_payment_processing", new=AsyncMock(return_value=True)):
            with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
                # Mock incoming message
                mock_message = AsyncMock()
                mock_message.body = json.dumps({
                    "order_id": order_id,
                    "amount": amount
                }).encode('utf-8')
                
                # Make process() a MagicMock that returns the context manager
                mock_message.process = MagicMock(return_value=mock_message_context)

                await process_inventory_reserved(mock_message)

                # Verify payment was recorded
                assert mock_session.add.call_count >= 1
                assert mock_session.commit.call_count >= 1

                # Verify PaymentProcessed event was published
                mock_publish_event.assert_called_once()
                args, _ = mock_publish_event.call_args
                assert args[1] == "payment.processed"

@pytest.mark.asyncio
async def test_process_inventory_reserved_failure(mock_message_context):
    """
    Test case 2: Payment failure after retries leads to PaymentFailed event.
    """
    order_id = "test-order-id-2"
    amount = 100.00
    
    # Mock the database session
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    # Mock idempotency check (no existing payment)
    mock_session.get.return_value = None
    
    with patch("app.consumer.get_session", side_effect=mock_async_context):
        with patch("app.consumer.simulate_payment_processing", new=AsyncMock(side_effect=Exception("Payment failed"))):
            with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
                # Mock incoming message
                mock_message = AsyncMock()
                mock_message.body = json.dumps({
                    "order_id": order_id,
                    "amount": amount
                }).encode('utf-8')
                
                # Make process() a MagicMock that returns the context manager
                mock_message.process = MagicMock(return_value=mock_message_context)

                await process_inventory_reserved(mock_message)

                # Verify payment failure was recorded
                assert mock_session.add.call_count >= 1
                assert mock_session.commit.call_count >= 1

                # Verify PaymentFailed event was published
                mock_publish_event.assert_called_once()
                args, _ = mock_publish_event.call_args
                assert args[1] == "payment.failed"

@pytest.mark.asyncio
async def test_process_inventory_reserved_idempotency(mock_message_context):
    """
    Test case 3: Duplicate event is ignored (idempotency check).
    """
    order_id = "test-order-id-3"
    amount = 100.00
    
    # Mock the database session
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    # Mock idempotency check (existing payment found)
    mock_session.get.return_value = Payment(order_id=order_id, amount=amount, status="PROCESSED")
    
    with patch("app.consumer.get_session", side_effect=mock_async_context):
        with patch("app.consumer.simulate_payment_processing", new=AsyncMock(return_value=True)):
            with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
                # Mock incoming message
                mock_message = AsyncMock()
                mock_message.body = json.dumps({
                    "order_id": order_id,
                    "amount": amount
                }).encode('utf-8')
                
                # Make process() a MagicMock that returns the context manager
                mock_message.process = MagicMock(return_value=mock_message_context)

                await process_inventory_reserved(mock_message)

                # Verify no new payment was recorded (only the idempotency check happened)
                # The get() is called once for idempotency check
                assert mock_session.get.call_count == 1
                
                # No add or commit should happen after the idempotency check
                # Note: The function returns early, so add/commit shouldn't be called
                mock_session.add.assert_not_called()
                mock_session.commit.assert_not_called()

                # Verify no event was published
                mock_publish_event.assert_not_called()
