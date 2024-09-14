# backend/app/api/v1/endpoints/chat.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.db.session import get_supabase
from app.services.openai_service import get_chatbot_response
import logging

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@router.post("/{token}/chat", response_model=ChatResponse)
async def chat_with_bot(token: str, chat_request: ChatRequest, request: Request):
    logging.info(f"Received chat request for token: {token}")
    try:
        supabase = get_supabase()
        response = supabase.table("chatbots").select("*").eq("token", token).execute()
        
        logging.info(f"Supabase response: {response}")
        
        if not response.data:
            logging.warning(f"Chatbot not found for token: {token}")
            raise HTTPException(status_code=404, detail="Chatbot not found")
        
        chatbot = response.data[0]  # Get the first item from the data list
        logging.info(f"Full chatbot object: {chatbot}")
        
        user_message = chat_request.message
        logging.info(f"Processing message for chatbot: {chatbot['name']}")
        
        # Get response from OpenAI, passing the entire chatbot object
        bot_reply = await get_chatbot_response(chatbot, user_message)
        
        logging.info(f"Received reply from OpenAI for chatbot: {chatbot['name']}")
        return ChatResponse(reply=bot_reply)
    
    except HTTPException as he:
        logging.error(f"HTTP Exception in chat_with_bot: {str(he)}")
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in chat_with_bot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


logging.basicConfig(level=logging.INFO)
