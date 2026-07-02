import os
import json
import asyncpg
from typing import Optional
from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from models import CarModel, InventoryUnit

mcp = FastMCP("Dealership_Postgres_MCP")
raw_dsn = os.getenv("DATABASE_URL", "postgresql://admin:123@postgres:5432/dealership_crm")
db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1) if raw_dsn.startswith("postgresql://") else raw_dsn

engine = create_async_engine(db_url, echo = False)
AsyncSessionLocal = async_sessionmaker(engine, class_ = AsyncSession, expire_on_commit = False)

@mcp.tool()
async def get_car_models(make: str = None) -> str:
    """
    Query the general catalog of car models.
    Use this when the customer asks general questions like "What SUVs do you sell?" or "Tell me about the Civic."
    
    Args:
        make: (Optional) The brand of the car (e.g., 'Honda', 'Toyota').
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(CarModel)
            if make:
                stmt = stmt.where(CarModel.make.ilike(f"%{make}%"))
            result = await session.execute(stmt)
            models = result.scalars().all()

            if not models:
                return "No models found matching that criteria."
            results_list = [
                {
                    "make": m.make,
                    "model_name": m.model_name,
                    "transmission": m.transmission,
                    "year": m.year,
                    "Ex_Showroom_price": float(m.Ex_Showroom_price) if m.Ex_Showroom_price else None,
                    "brochere_url": m.brochere_url
                } for m in models
            ]
            return json.dumps(results_list, indent=2)
    except Exception as e:
        return f"Database error: {str(e)}"
    
@mcp.tool()
async def check_inventory(model_name: str, color: Optional[str] = None, max_price: Optional[float] = None) -> str:
    """
    Check the physical metal on the dealership lot.
    Use this when the customer asks transactional questions like "Do you have a red Civic in stock?"
    
    Args:
        model_name: The specific model name (e.g., 'Civic', 'RAV4').
        color: (Optional) The desired exterior color.
        max_price: (Optional) The maximum budget for the Ex_Showroom_price.
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(InventoryUnit, CarModel).join(CarModel, InventoryUnit.model_id == CarModel.model_id)
            stmt = stmt.where(CarModel.model_name.ilike(f"%{model_name}%"))
            if color:
                stmt = stmt.where(InventoryUnit.color.ilike(f"%{color}%"))
            if max_price:
                stmt = stmt.where(CarModel.Ex_Showroom_price <= max_price)
            result = await session.execute(stmt)
            rows = result.all()
            if not rows:
                return "No physical inventory found matching that criteria. Recommend offering to order one."
            results_list = [
                {
                    "vin": inv.vin,
                    "make": car.make,
                    "model_name": car.model_name,
                    "color": inv.color,
                    "status": inv.status,
                    "Ex_Showroom_price": float(car.Ex_Showroom_price) if car.Ex_Showroom_price else None
                } for inv, car in rows
            ]
            
            return json.dumps(results_list, indent=2)
    except Exception as e:
        return f"Database error: {str(e)}"
    
if __name__ == "__main__":
    mcp.run()