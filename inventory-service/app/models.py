from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Inventory(Base):
    __tablename__ = "inventory"

    product_id = Column(String, primary_key=True, index=True)
    stock = Column(Integer, nullable=False)

class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    order_id = Column(String, primary_key=True, index=True)
    product_id = Column(String, ForeignKey("inventory.product_id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
