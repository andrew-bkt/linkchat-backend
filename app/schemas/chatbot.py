# backend/app/schemas/chatbot.py

from pydantic import BaseModel
from typing import Optional

class ChatbotBase(BaseModel):
    name: str

class ChatbotCreate(ChatbotBase):
    pass

class ChatbotInDB(ChatbotBase):
    id: str
    user_id: str
    token: str

class Chatbot(ChatbotBase):
    id: str
    token: str