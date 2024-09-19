from fastapi import APIRouter
from app.api.v1.endpoints import users, chatbots, chat, surveybots

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chatbots.router, prefix="/chatbots", tags=["chatbots"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(surveybots.router, prefix="/surveybots", tags=["surveybots"])