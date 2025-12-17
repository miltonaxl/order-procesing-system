import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Inventory, InventoryReservation
from app.consumer import process_order_created, process_order_cancelled

# Mock the database session dependency
@pytest.fixture
def mock_db_session():
    """Fixture para mock de sesión de base de datos asíncrona"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock para el contexto asíncrono de get_session()
    async def mock_async_context():
        yield mock_session
    
    with patch("app.consumer.get_session", side_effect=mock_async_context):
        yield mock_session

# Mock the messaging dependency
@pytest.fixture
def mock_messaging():
    with patch("app.consumer.publish_event", new=AsyncMock()) as mock_publish_event:
        yield mock_publish_event

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
async def test_process_order_created_success(mock_db_session, mock_messaging, mock_message_context):
    """
    Test case 1: Successful inventory reservation and event publishing.
    """
    order_id = "test-order-id-1"
    items = [{"product_id": "prod-A", "quantity": 2}]
    
    # Mock initial inventory
    mock_inventory = Inventory(product_id="prod-A", stock=10)
    mock_db_session.get.return_value = mock_inventory

    # Mock incoming message con process() mockeado
    mock_message = AsyncMock()
    mock_message.body = json.dumps({
        "order_id": order_id,
        "items": items
    }).encode('utf-8')
    
    # Make process() a MagicMock (not AsyncMock) that returns the context manager
    mock_message.process = MagicMock(return_value=mock_message_context)

    await process_order_created(mock_message)

    # Verify stock was decremented
    assert mock_inventory.stock == 8
    
    # Verify that inventory was added to session
    mock_db_session.add.assert_any_call(mock_inventory)
    
    # Check that an InventoryReservation was added with correct attributes
    add_calls = mock_db_session.add.call_args_list
    assert len(add_calls) == 2, f"Expected 2 add calls, got {len(add_calls)}"
    
    # Find the InventoryReservation in the calls
    reservation = None
    for call in add_calls:
        obj = call[0][0]  # First positional argument
        if isinstance(obj, InventoryReservation):
            reservation = obj
            break
    
    assert reservation is not None, "InventoryReservation was not added to session"
    assert reservation.order_id == order_id, f"Expected order_id {order_id}, got {reservation.order_id}"
    assert reservation.product_id == "prod-A", f"Expected product_id 'prod-A', got {reservation.product_id}"
    assert reservation.quantity == 2, f"Expected quantity 2, got {reservation.quantity}"
    
    mock_db_session.commit.assert_called_once()

    # Verify InventoryReserved event was published
    mock_messaging.assert_called_once()
    args, _ = mock_messaging.call_args
    assert args[1] == "inventory.reserved"
    
    # Verify message.process() fue llamado
    mock_message.process.assert_called_once()

@pytest.mark.asyncio
async def test_process_order_created_insufficient_stock(mock_db_session, mock_messaging, mock_message_context):
    """
    Test case 2: Insufficient stock leads to InventoryUnavailable event.
    """
    order_id = "test-order-id-2"
    items = [{"product_id": "prod-A", "quantity": 12}]
    
    # Mock initial inventory
    mock_inventory = Inventory(product_id="prod-A", stock=10)
    mock_db_session.get.return_value = mock_inventory

    # Mock incoming message
    mock_message = AsyncMock()
    mock_message.body = json.dumps({
        "order_id": order_id,
        "items": items
    }).encode('utf-8')
    
    # Make process() a MagicMock (not AsyncMock) that returns the context manager
    mock_message.process = MagicMock(return_value=mock_message_context)

    await process_order_created(mock_message)

    # Verify stock was NOT decremented
    assert mock_inventory.stock == 10
    
    # Verify InventoryUnavailable event was published
    mock_messaging.assert_called_once()
    args, _ = mock_messaging.call_args
    assert args[1] == "inventory.unavailable"
    
    # Verify no commit was made
    mock_db_session.commit.assert_not_called()
    
    # Verify message.process() fue llamado
    mock_message.process.assert_called_once()

@pytest.mark.asyncio
async def test_process_order_cancelled_compensation(mock_db_session, mock_messaging, mock_message_context):
    """
    Test case 3: OrderCancelled event triggers inventory rollback (compensation).
    """
    order_id = "test-order-id-3"
    product_id = "prod-A"
    quantity = 3
    
    # Mock initial inventory
    mock_inventory = Inventory(product_id=product_id, stock=7) # Stock after initial reservation
    
    # Mock reservation record
    mock_reservation = InventoryReservation(
        order_id=order_id, 
        product_id=product_id, 
        quantity=quantity
    )
    
    # Mock database session to return reservation and inventory
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_reservation]
    mock_db_session.execute.return_value = mock_result
    
    mock_db_session.get.return_value = mock_inventory

    # Mock incoming message
    mock_message = AsyncMock()
    mock_message.body = json.dumps({
        "order_id": order_id,
        "event_type": "OrderCancelled"
    }).encode('utf-8')
    
    # Make process() a MagicMock (not AsyncMock) that returns the context manager
    mock_message.process = MagicMock(return_value=mock_message_context)

    await process_order_cancelled(mock_message)

    # Verify stock was incremented (7 + 3 = 10)
    assert mock_inventory.stock == 10
    
    # Verify stock update was added to session
    mock_db_session.add.assert_called_once_with(mock_inventory)
    
    # Verify reservation deletion was executed
    mock_db_session.execute.assert_called()
    
    # Verify commit was made
    mock_db_session.commit.assert_called_once()
    
    # Verify no event was published
    mock_messaging.assert_not_called()
    
    # Verify message.process() fue llamado
    mock_message.process.assert_called_once()