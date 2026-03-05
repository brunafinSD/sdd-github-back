from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the current database reference. Available after lifespan startup."""
    if db is None:
        raise RuntimeError("Database not initialized. Is the app lifespan running?")
    return db


@asynccontextmanager
async def lifespan(app) -> AsyncGenerator[None]:
    """Initialize Motor client on startup, close on shutdown."""
    global client, db
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]

    # Create indexes
    await db.games.create_index([("status", 1), ("date", -1)])
    await db.transactions.create_index([("createdAt", -1)])
    await db.transactions.create_index("type")
    await db.transactions.create_index("cashTarget")
    await db.transactions.create_index("gameId")

    yield
    client.close()
    client = None
    db = None
