import os
import sys
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.core.config import settings
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Chat Application", debug=True)

origins = [
    "https://linkchat-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    return response

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logger.error(f"Unhandled exception: {''.join(tb)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting up application")
    logger.info(f"DEBUG mode: {app.debug}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'Not set')}")
    logger.info(f"DATABASE_URL: {settings.DATABASE_URL}")
    logger.info(f"OPENAI_API_KEY: {'Set' if settings.OPENAI_API_KEY else 'Not set'}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))