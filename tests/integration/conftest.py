import pytest_asyncio

from app.infrastructure.config import Settings
from app.infrastructure.database import Database


_schema_ready = False


@pytest_asyncio.fixture
async def db():
    global _schema_ready
    settings = Settings(postgres_db="sentinel_test")
    database = Database(settings.database_url)
    await database.connect()
    if not _schema_ready:
        await database.init_schema()
        await database.seed_defaults()
        _schema_ready = True
    async with database._pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE observations, notifications, notification_feedback CASCADE"
        )
    yield database
    await database.disconnect()
