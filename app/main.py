import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.core.config import settings
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Chat Application")

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
    allow_origin_regex=None,
    expose_headers=[],
    max_age=600,
)

app.include_router(api_router, prefix="/api/v1")

@app.middleware("http")
async def log_cors_details(request, call_next):
    logger.info(f"Request origin: {request.headers.get('origin')}")
    logger.info(f"Request method: {request.method}")
    response = await call_next(request)
    logger.info(f"CORS headers: {response.headers.get('access-control-allow-origin')}")
    return response

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    return response

@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.on_event("startup")
async def startup_event():
    logger.info(f"DATABASE_URL: {settings.DATABASE_URL}")
    logger.info(f"OPENAI_API_KEY: {'Set' if settings.OPENAI_API_KEY else 'Not set'}")
    # Add other important environment variables here

@app.get("/health")
async def health_check():
    return {"status": "ok"}