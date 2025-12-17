import uvicorn
import json
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import init_db, get_session
from app.models import Order, OrderStatus
from sqlalchemy import select
from app.schemas import OrderCreate, OrderRead
from app.messaging import publish_event, setup_rabbitmq

from uuid import uuid4

app = FastAPI(title="Order Service")

import asyncio
from app.consumer import start_consumer

@app.on_event("startup")
async def startup_event():
    await init_db()
    await setup_rabbitmq()
    asyncio.create_task(start_consumer())

@app.post("/api/orders", response_model=OrderRead, status_code=201)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_session)):
    order_id = str(uuid4())
    new_order = Order(
        id=order_id,
        customer_id=order_data.customer_id,
        items=json.dumps([item.model_dump() for item in order_data.items]),
        total_amount=order_data.total_amount,
        status=OrderStatus.PENDING
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    # Publish OrderCreated event
    event_data = {
        "event_id": str(uuid4()),
        "event_type": "OrderCreated",
        "timestamp": new_order.created_at.isoformat(),
        "order_id": order_id,
        "items": [item.model_dump() for item in order_data.items],
        "total_amount": order_data.total_amount
    }
    await publish_event("order_exchange", "order.created", event_data)

    return OrderRead.model_validate(new_order)
    
    

@app.get("/api/orders", response_model=list[OrderRead], status_code=200)
async def get_orders(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Order))
    orders = result.scalars().all()
    #item convert to JSON FORMAT 
    for order in orders:
        order.items = json.loads(order.items)
    return [OrderRead.model_validate(order) for order in orders]

@app.get("/api/orders/{order_id}", response_model=OrderRead)
async def get_order(order_id: str, db: AsyncSession = Depends(get_session)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    #item convert to JSON FORMAT 
    order.items = json.loads(order.items)
    return OrderRead.model_validate(order)

# Placeholder for event consumers (e.g., PaymentProcessed, PaymentFailed)
# These would typically be in a separate consumer process or integrated into the main app
# For simplicity in this monorepo structure, we'll keep the consumer logic separate or in a dedicated consumer file.

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
