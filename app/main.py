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
# Default origins from environment variable (comma-separated)
origins = os.getenv("CORS_ORIGINS", "").split(",")

# Always include production and common dev URLs
default_origins = [
    "https://motofix-control-center.onrender.com",  # production frontend
    "http://localhost:8080",                        # localhost dev
    "http://localhost:5173",                        # Vite dev server
]

# Merge and remove empty strings
origins = list(set([o for o in origins + default_origins if o]))

allow_origin_regex = r"https?://(.+\.)?motofix-control-center\.onrender\.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["https://motofix-control-center.onrender.com"],
    allow_origin_regex=allow_origin_regex,
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