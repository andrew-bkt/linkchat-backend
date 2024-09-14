# backend/app/api/v1/endpoints/chatbots.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from typing import List
import uuid
from app.schemas.chatbot import Chatbot
from app.schemas.user import User
from app.api import deps
from app.db.session import get_supabase
from app.services.link_generator import generate_unique_token
from app.utils.file_utils import save_uploaded_files
import logging

router = APIRouter()

@router.post("/", response_model=Chatbot)
async def create_chatbot(
    name: str = Form(...),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()
    chatbot_id = str(uuid.uuid4())
    token = generate_unique_token()

    logging.info(f"Received request to create chatbot. Name: {name}, User: {current_user.id}")
    logging.info(f"Received {len(files) if files else 0} files for chatbot creation")
    
    if files:
        for file in files:
            logging.info(f"File: {file.filename}, Content-Type: {file.content_type}")

        # Save files to storage
        file_urls = await save_uploaded_files(files, chatbot_id)
        logging.info(f"File URLs for chatbot {chatbot_id}: {file_urls}")
    else:
        file_urls = []
        logging.info("No files received for upload")

    # Save chatbot info to Supabase
    data = {
        "id": chatbot_id,
        "user_id": current_user.id,
        "name": name,
        "token": token,
        "documents": file_urls
    }
    response = supabase.table("chatbots").insert(data).execute()
    
    logging.info(f"Supabase response for creating chatbot: {response}")
    
    if response.data:
        logging.info(f"Created chatbot with id: {chatbot_id}, token: {token}, and documents: {file_urls}")
        return Chatbot(id=chatbot_id, name=name, token=token)
    else:
        logging.error(f"Failed to create chatbot: {response.error}")
        raise HTTPException(status_code=400, detail="Failed to create chatbot")



@router.get("/", response_model=List[Chatbot])
def get_user_chatbots(current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    response = supabase.table("chatbots").select("*").eq("user_id", current_user.id).execute()
    if not response.data:
        return []
    chatbots = response.data
    return [Chatbot(id=cb["id"], name=cb["name"], token=cb["token"]) for cb in chatbots]

@router.get("/{chatbot_id}", response_model=Chatbot)
def get_chatbot(chatbot_id: str, current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return Chatbot(id=chatbot["id"], name=chatbot["name"], token=chatbot["token"])

@router.get("/by-token/{token}", response_model=Chatbot)
async def get_chatbot_by_token(token: str):
    supabase = get_supabase()
    response = supabase.table("chatbots").select("*").eq("token", token).execute()
    logging.info(f"Get chatbot by token response: {response}")
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    chatbot = response.data[0]
    return Chatbot(id=chatbot["id"], name=chatbot["name"], token=chatbot["token"])