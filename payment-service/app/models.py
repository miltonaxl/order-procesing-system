from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"

    order_id = Column(String, primary_key=True, index=True) # Using order_id as primary key for idempotency
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False) # PROCESSED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
