import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gowanus.biz",
        "https://linkchat-80lw4govo-andrew-bkts-projects.vercel.app",
        "https://linkchat-ecru.vercel.app",
        "https://linkchat-ofxyfsmc2-andrew-bkts-projects.vercel.app",
        "http://localhost:3000",  # for local development
        "http://localhost:8000",  # for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for Logging Requests and Responses
@app.middleware("http")
async def log_request(request: Request, call_next):
    logging.info(f"Received request: {request.method} {request.url}")
    logging.info(f"Request headers: {request.headers}")
    response = await call_next(request)
    logging.info(f"Response status code: {response.status_code}")
    logging.info(f"Response headers: {response.headers}")
    return response

# Include API Router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

