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
    "http://localhost:3000",
    "http://localhost:8000",
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

# Enable logging for debugging CORS issues
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request URL: {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    return response
