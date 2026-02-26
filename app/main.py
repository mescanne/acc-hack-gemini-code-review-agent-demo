import asyncio
import logging
import socket
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, status, Depends
from pythonjsonlogger import jsonlogger

from . import models
from .config import get_settings, Settings
from .database import init_db, close_db, get_db_connection


# Configure logging
class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["levelname"] = record.levelname
        log_record["name"] = record.name


log = logging.getLogger("uvicorn.access")
formatter = JsonFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(lifespan=lifespan)


# Dependency for database pool
async def get_pool() -> asyncpg.Pool:
    return await get_db_connection()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health(
    settings: Settings = Depends(get_settings), pool: asyncpg.Pool = Depends(get_pool)
):
    try:
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "hostname": socket.gethostname(),
            "db_host": settings.DB_HOST,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "unhealthy", "error": str(e), "hostname": socket.gethostname()},
        )


@app.get("/", status_code=status.HTTP_200_OK)
def index():
    return {
        "message": "Application API",
        "version": "2.0.0",
        "hostname": socket.gethostname(),
        "endpoints": [
            {"method": "GET", "path": "/health", "description": "Health check"},
            {
                "method": "GET",
                "path": "/api/users",
                "description": "List all users",
            },
            {
                "method": "GET",
                "path": "/api/users/{id}",
                "description": "Get user by ID",
            },
            {
                "method": "POST",
                "path": "/api/users",
                "description": "Create new user",
            },
            {
                "method": "DELETE",
                "path": "/api/users/{id}",
                "description": "Delete user",
            },
        ],
    }


@app.get("/api/users", response_model=models.UserList)
async def get_users(pool: asyncpg.Pool = Depends(get_pool)):
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch("SELECT * FROM users ORDER BY id")
        users = [models.User.model_validate(dict(row)) for row in rows]
        return {"count": len(users), "users": users}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": str(e)}
        )


@app.get("/api/users/{user_id}", response_model=models.User)
async def get_user(user_id: int, pool: asyncpg.Pool = Depends(get_pool)):
    try:
        async with pool.acquire() as connection:
            row = await connection.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if row:
            return models.User.model_validate(dict(row))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error": "User not found"}
        )
    except Exception as e:
        # Re-raise HTTPException
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": str(e)}
        )


@app.post("/api/users", response_model=models.User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: models.UserCreate, pool: asyncpg.Pool = Depends(get_pool)
):
    try:
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "INSERT INTO users (name, email, department) VALUES ($1, $2, $3) RETURNING *",
                user.name,
                user.email,
                user.department,
            )
        return models.User.model_validate(dict(row))
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Email already exists"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": str(e)}
        )


@app.delete("/api/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, pool: asyncpg.Pool = Depends(get_pool)):
    try:
        async with pool.acquire() as connection:
            deleted_id = await connection.fetchval(
                "DELETE FROM users WHERE id = $1 RETURNING id", user_id
            )
        if deleted_id is not None:
            return {"message": f"User {user_id} deleted"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error": "User not found"}
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": str(e)}
        )


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
