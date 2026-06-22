from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routes.auth import router as auth_router
from db import db_manager

app = FastAPI(title="Auth Service", version="1.0.0")

# Setup CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    await db_manager.connect_to_database()


@app.on_event("shutdown")
async def shutdown_event():
    await db_manager.close_database_connection()
