from fastapi import FastAPI
from .routers import admin

app = FastAPI(
    title="MOTOFIX Admin Dashboard API",
    description="Private admin endpoint – only accessible to you",
    version="1.0.0"
)

app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "Motofix Admin API – Protected. Welcome boss"}