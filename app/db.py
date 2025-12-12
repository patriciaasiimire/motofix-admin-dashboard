import os
import asyncpg
from fastapi import FastAPI, Depends, Request
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL")

# Create a pool in startup and store on app.state
async def init_db_pool(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    app.state._db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

async def close_db_pool(app: FastAPI):
    pool = getattr(app.state, "_db_pool", None)
    if pool:
        await pool.close()

# Dependency to acquire a connection from the pool and yield it
async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquire a DB connection from the app-wide pool stored on app.state.
    Using the Request object avoids fragile __import__ lookups that can fail in production.
    """
    pool = getattr(request.app.state, "_db_pool", None)

    if pool is None:
        # Read DATABASE_URL at call time so tests can monkeypatch env before calling
        local_db_url = os.getenv("DATABASE_URL")
        # If no pool and no DATABASE_URL configured, surface a controlled HTTP error
        if not local_db_url:
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail="Database not configured")

        # Fallback: try to create a temporary connection (not ideal for production).
        # Convert connection errors into HTTPExceptions so tests receive proper status codes
        try:
            conn = await asyncpg.connect(local_db_url)
        except Exception:
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            yield conn
        finally:
            await conn.close()
    else:
        async with pool.acquire() as conn:
            yield conn