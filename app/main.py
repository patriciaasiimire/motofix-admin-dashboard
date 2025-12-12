# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import admin
import os

from app.routers import admin  # your existing admin router
from app.routers import auth
from app.db import init_db_pool, close_db_pool

app = FastAPI(
    title="MOTOFIX Admin Dashboard API",
    description="Private admin endpoint – only accessible to you",
    version="1.0.0"
)

# Configure CORS so the frontend (local dev or deployed) can call the API
# Allow origins from env var `CORS_ORIGINS` comma-separated, fallback to localhost dev port
origins = os.getenv("CORS_ORIGINS", "http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)      # /api/login
app.include_router(admin.router)     # /admin/*

# Startup/shutdown to manage DB pool
@app.on_event("startup")
async def on_startup():
    await init_db_pool(app)

@app.on_event("shutdown")
async def on_shutdown():
    await close_db_pool(app)

@app.get("/")
def root():
    return {"message": "Motofix Admin API – Protected. Welcome boss"}