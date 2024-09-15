# backend/app/schemas/chatbot.py

from pydantic import BaseModel
from typing import Optional, List

class ChatbotBase(BaseModel):
    name: str
    instructions: Optional[str] = None
    tone: Optional[str] = None

class ChatbotCreate(ChatbotBase):
    pass

class ChatbotInDB(ChatbotBase):
    id: str
    user_id: str
    token: str
    documents: List[str]

class Chatbot(ChatbotBase):
    id: str
    token: str
