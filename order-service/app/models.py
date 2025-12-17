from sqlalchemy import Column, String, Float, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True, nullable=False)
    items = Column(String, nullable=False) # Storing as JSON string for simplicity
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
