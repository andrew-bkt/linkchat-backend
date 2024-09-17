# backend/app/main.py
import logging
from fastapi import FastAPI, Request
from app.api.v1.api import api_router
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://linkchat-ecru.vercel.app",
        "https://linkchat-ofxyfsmc2-andrew-bkts-projects.vercel.app",
        "http://localhost:3000"  # for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.middleware("http")
async def log_request(request, call_next):
    logger = logging.getLogger("app")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    response = await call_next(request)
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    return response

@app.get("/")
def read_root():
    return {"message": "Welcome to the API"}

@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    return {}  # This will handle OPTIONS requests for all routes
