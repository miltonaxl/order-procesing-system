import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session, init_db
from app.models import Inventory

async def seed_inventory():
    await init_db()
    async for session in get_session():
        # Check if inventory is already seeded
        if await session.get(Inventory, "product-A"):
            print("Inventory already seeded.")
            return

        # Seed initial inventory
        products = [
            Inventory(product_id="product-A", stock=10),
            Inventory(product_id="product-B", stock=5),
            Inventory(product_id="product-C", stock=0), # For testing InventoryUnavailable
        ]
        session.add_all(products)
        await session.commit()
        print("Inventory seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_inventory())
