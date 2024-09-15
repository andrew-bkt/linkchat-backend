# backend/app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(title="LLM Chat Application")

# CORS configuration
origins = [
    "https://linkchat-production.up.railway.app",
    "http://localhost:3000",  # React frontend
    "http://localhost:8000",  # FastAPI backend (for development)
    # Add other allowed origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(api_router, prefix="/api/v1")
