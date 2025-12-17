import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.consumer import process_notification_event
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
@patch("builtins.print")
async def test_process_notification_event_success(mock_print, mock_message_context):
    """
    Test case 1: Successful processing of a notification event (logging).
    """
    order_id = "test-order-id-1"
    
    # Mock incoming message
    mock_message = AsyncMock()
    mock_message.body = json.dumps({
        "event_id": "evt-125",
        "event_type": "PaymentProcessed",
        "timestamp": "2025-12-16T10:00:00Z",
        "order_id": order_id,
        "payment_id": "pay-uuid",
        "amount": 100.00
    }).encode('utf-8')
    
    # Make process() a MagicMock that returns the context manager
    mock_message.process = MagicMock(return_value=mock_message_context)

    await process_notification_event(mock_message)

    # Verify message was processed
    mock_message.process.assert_called_once()
    
    # Verify notification was logged to console
    mock_print.assert_any_call("--- NOTIFICATION SENT ---")
    mock_print.assert_any_call(f"Order ID: {order_id}")

@pytest.mark.asyncio
@patch("builtins.print")
async def test_process_notification_event_order_confirmed(mock_print, mock_message_context):
    """
    Test case 2: Successful processing of an OrderConfirmed event.
    """
    order_id = "test-order-id-2"
    
    # Mock incoming message
    mock_message = AsyncMock()
    mock_message.body = json.dumps({
        "event_id": "evt-126",
        "event_type": "OrderConfirmed",
        "timestamp": "2025-12-16T10:00:00Z",
        "order_id": order_id,
        "total_amount": 150.00
    }).encode('utf-8')
    
    # Make process() a MagicMock that returns the context manager
    mock_message.process = MagicMock(return_value=mock_message_context)

    await process_notification_event(mock_message)

    # Verify message was processed
    mock_message.process.assert_called_once()
    
    # Verify notification was logged to console
    mock_print.assert_any_call("--- NOTIFICATION SENT ---")
    mock_print.assert_any_call(f"Order ID: {order_id}")
    mock_print.assert_any_call("Event Type: OrderConfirmed")
