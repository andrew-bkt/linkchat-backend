# backend/app/api/v1/endpoints/chatbots.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Body
from typing import List, Optional
import uuid
from app.schemas.chatbot import Chatbot, ChatbotInDB, ChatbotCreate
from app.schemas.user import User
from app.api import deps
from app.db.session import get_supabase
from app.services.link_generator import generate_unique_token
from app.utils.file_utils import save_uploaded_files, delete_files
import logging
from pydantic import ValidationError
from postgrest.exceptions import APIError

router = APIRouter()

@router.post("/", response_model=Chatbot)
async def create_chatbot(
    name: str = Form(...),
    instructions: Optional[str] = Form(None),
    tone: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()

    try:
        # Generate a unique token for the chatbot
        token = generate_unique_token()

        chatbot_data = {
            "id": str(uuid.uuid4()),
            "name": name,
            "instructions": instructions,
            "tone": tone,
            "user_id": current_user.id,
            "token": token,
            "documents": []
        }
        logging.info(f"Attempting to create chatbot with data: {chatbot_data}")
        
        response = supabase.table("chatbots").insert(chatbot_data).execute()
        
        if not response.data:
            logging.error(f"Failed to create chatbot. Supabase response: {response}")
            raise HTTPException(status_code=400, detail="Failed to create chatbot")

        chatbot = response.data[0]
        logging.info(f"Chatbot created successfully: {chatbot}")
        
        if files:
            logging.info(f"Received {len(files)} files for chatbot")
            new_file_urls = await save_uploaded_files(files, chatbot["id"])
            update_response = supabase.table("chatbots").update({"documents": new_file_urls}).eq("id", chatbot["id"]).execute()
            logging.info(f"Updated chatbot with file URLs. Response: {update_response}")

            chatbot["documents"] = new_file_urls
        
        created_chatbot = Chatbot(
            id=chatbot["id"],
            name=chatbot["name"],
            instructions=chatbot["instructions"],
            tone=chatbot["tone"],
            token=chatbot["token"],
            documents=chatbot.get("documents", [])
        )
        
        return created_chatbot
    except ValidationError as ve:
        logging.error(f"Validation error: {ve.errors()}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logging.error(f"Error creating chatbot: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[Chatbot])
def get_user_chatbots(current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    response = supabase.table("chatbots").select("*").eq("user_id", current_user.id).execute()
    if not response.data:
        return []
    chatbots = response.data
    return [Chatbot(id=cb["id"], name=cb["name"], instructions=cb["instructions"], tone=cb["tone"], token=cb["token"], documents=cb.get("documents", [])) for cb in chatbots]

@router.get("/{chatbot_id}", response_model=Chatbot)
async def get_chatbot(chatbot_id: str, current_user: User = Depends(deps.get_current_user)):
    logging.info(f"Fetching chatbot with id: {chatbot_id}")
    if not chatbot_id or chatbot_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid chatbot ID")

    supabase = get_supabase()
    try:
        response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    except APIError as e:
        logging.error(f"Supabase API error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid chatbot ID format")
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        logging.warning(f"User {current_user.id} attempted to access chatbot owned by another user.")
        raise HTTPException(status_code=403, detail="Not authorized to access this chatbot")

    return Chatbot(
        id=chatbot["id"],
        name=chatbot["name"],
        instructions=chatbot["instructions"],
        tone=chatbot["tone"],
        token=chatbot["token"],
        documents=chatbot.get("documents", [])
    )

@router.delete("/{chatbot_id}", response_model=None)
async def delete_chatbot(chatbot_id: str, current_user: User = Depends(deps.get_current_user)):
    logging.info(f"Deleting chatbot with id: {chatbot_id}")
    supabase = get_supabase()

    try:
        response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    except APIError as e:
        logging.error(f"Supabase API error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid chatbot ID format")

    if not response.data:
        logging.warning(f"Chatbot with ID {chatbot_id} not found")
        raise HTTPException(status_code=404, detail="Chatbot not found")

    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        logging.warning(f"User {current_user.id} attempted to delete chatbot owned by another user.")
        raise HTTPException(status_code=403, detail="Not authorized to delete this chatbot")

    try:
        # Delete associated documents first if they exist
        if chatbot.get("documents"):
            delete_files(chatbot["documents"])
            logging.info(f"Deleted associated documents: {chatbot['documents']}")

        # Delete the chatbot entry from the database
        delete_response = supabase.table("chatbots").delete().eq("id", chatbot_id).execute()
        if delete_response.status_code != 200:
            logging.error(f"Failed to delete chatbot. Supabase response: {delete_response}")
            raise HTTPException(status_code=400, detail="Failed to delete chatbot")
        logging.info(f"Chatbot {chatbot_id} deleted successfully")
    except Exception as e:
        logging.error(f"Error deleting chatbot: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"detail": "Chatbot deleted successfully"}

