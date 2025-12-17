from pydantic import BaseModel, Field, field_validator
from typing import List, Any
import json
from datetime import datetime
from app.models import OrderStatus

class Item(BaseModel):
    product_id: str = Field(..., example="product-1")
    quantity: int = Field(..., gt=0, example=2)

class OrderCreate(BaseModel):
    customer_id: str = Field(..., example="customer-123")
    items: List[Item]
    total_amount: float = Field(..., gt=0.0)


class OrderRead(BaseModel):
    id: str
    customer_id: str
    items: List[Item]
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    @field_validator('items', mode='before')
    @classmethod
    def parse_items(cls, v: Any) -> List[Item]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
