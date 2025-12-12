# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import admin, auth
from app.db import init_db_pool, close_db_pool

app = FastAPI(
    title="MOTOFIX Admin Dashboard API",
    description="Private admin endpoint – only accessible to you",
    version="1.0.0"
)

# ─────────────── CORS CONFIGURATION ───────────────
# Parse additional origins from environment variable (comma-separated)
env_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# Always include production and common dev URLs
allowed_origins = [
    "https://motofix-control-center.onrender.com",  # Production frontend
    "http://localhost:5173",                        # Vite dev server
    "http://localhost:8080",                       # Other local dev if needed
] + env_origins

# Remove duplicates while preserving order
seen = set()
allowed_origins = [x for x in allowed_origins if not (x in seen or seen.add(x))]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────── INCLUDE ROUTERS ───────────────
app.include_router(auth.router)      # /api/login
app.include_router(admin.router)     # /admin/*

# ─────────────── STARTUP / SHUTDOWN ───────────────
@app.on_event("startup")
async def on_startup():
    await init_db_pool(app)

@app.on_event("shutdown")
async def on_shutdown():
    await close_db_pool(app)

# ─────────────── ROOT ───────────────
@app.get("/")
def root():
    return {"message": "Motofix Admin API – Protected. Welcome boss"}