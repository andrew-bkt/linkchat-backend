#app/api/v1/api.py

from fastapi import APIRouter
from app.api.v1.endpoints import users, chatbots, chat

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chatbots.router, prefix="/chatbots", tags=["chatbots"])
api_router.include_router(chat.router, tags=["chat"])
