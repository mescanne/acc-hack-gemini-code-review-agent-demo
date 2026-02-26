import asyncpg
from .config import get_settings

pool = None


async def init_db():
    global pool
    settings = get_settings()
    dsn = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    pool = await asyncpg.create_pool(dsn)


async def get_db_connection():
    if pool is None:
        await init_db()
    # async with pool.acquire() as connection:
    #     yield connection
    return pool


async def close_db():
    if pool:
        await pool.close()
