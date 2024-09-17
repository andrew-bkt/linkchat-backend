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
        "instructions": instructions,
        "tone": tone,
        "token": token,
        "documents": file_urls
    }
    response = supabase.table("chatbots").insert(data).execute()
    logging.info(f"Supabase response for creating chatbot: {response}")
    
    if response.data:
        logging.info(f"Created chatbot with id: {chatbot_id}, token: {token}, and documents: {file_urls}")
        return Chatbot(id=chatbot_id, name=name, instructions=instructions, tone=tone, token=token)
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
    return [Chatbot(id=cb["id"], name=cb["name"], instructions=cb["instructions"], tone=cb["tone"], token=cb["token"]) for cb in chatbots]

@router.get("/{chatbot_id}", response_model=Chatbot)
def get_chatbot(chatbot_id: str, current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()
    response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return Chatbot(
        id=chatbot["id"], name=chatbot["name"], instructions=chatbot["instructions"],
        tone=chatbot["tone"], token=chatbot["token"], documents=chatbot["documents"]
    )

@router.get("/by-token/{token}", response_model=Chatbot)
async def get_chatbot_by_token(token: str):
    supabase = get_supabase()
    response = supabase.table("chatbots").select("*").eq("token", token).execute()
    logging.info(f"Get chatbot by token response: {response}")
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    chatbot = response.data[0]
    return Chatbot(
        id=chatbot["id"], name=chatbot["name"], instructions=chatbot["instructions"],
        tone=chatbot["tone"], token=chatbot["token"], documents=chatbot["documents"]
    )

@router.put("/{chatbot_id}", response_model=Chatbot)
async def update_chatbot(
    chatbot_id: str,
    name: str = Form(...),
    instructions: Optional[str] = Form(None),
    tone: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()

    # Fetch the existing chatbot
    response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update the fields
    update_data = {
        "name": name,
        "instructions": instructions,
        "tone": tone
    }

    # Handle file uploads
    if files:
        logging.info(f"Received {len(files)} files for chatbot update")
        for file in files:
            logging.info(f"File: {file.filename}, Content-Type: {file.content_type}")

        # Save new files to storage
        new_file_urls = await save_uploaded_files(files, chatbot_id)
        existing_files = chatbot.get("documents", [])
        update_data["documents"] = existing_files + new_file_urls
        logging.info(f"Updated file URLs for chatbot {chatbot_id}: {update_data['documents']}")

    response = supabase.table("chatbots").update(update_data).eq("id", chatbot_id).execute()
    logging.info(f"Supabase response for updating chatbot: {response}")

    if response.data:
        updated_chatbot = response.data[0]
        return Chatbot(
            id=updated_chatbot["id"],
            name=updated_chatbot["name"],
            instructions=updated_chatbot["instructions"],
            tone=updated_chatbot["tone"],
            token=updated_chatbot["token"],
            documents=updated_chatbot["documents"]
        )
    else:
        logging.error(f"Failed to update chatbot: {response.error}")
        raise HTTPException(status_code=400, detail="Failed to update chatbot")

@router.delete("/{chatbot_id}")
async def delete_chatbot(chatbot_id: str, current_user: User = Depends(deps.get_current_user)):
    supabase = get_supabase()

    # Fetch the chatbot
    response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete associated files
    if chatbot.get("documents"):
        await delete_files(chatbot["documents"])

    # Delete the chatbot from the database
    delete_response = supabase.table("chatbots").delete().eq("id", chatbot_id).execute()
    if len(delete_response.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to delete chatbot")

    return {"message": "Chatbot deleted successfully"}

@router.delete("/{chatbot_id}/files")
async def delete_chatbot_file(
    chatbot_id: str,
    file_url: str = Body(..., embed=True),
    current_user: User = Depends(deps.get_current_user)
):
    supabase = get_supabase()

    # Fetch the chatbot
    response = supabase.table("chatbots").select("*").eq("id", chatbot_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    chatbot = response.data
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Remove the file from the documents list
    documents = chatbot.get("documents", [])
    if file_url not in documents:
        raise HTTPException(status_code=404, detail="File not found")

    documents.remove(file_url)

    # Update the chatbot with the new documents list
    update_response = supabase.table("chatbots").update({"documents": documents}).eq("id", chatbot_id).execute()
    if not update_response.data:
        raise HTTPException(status_code=500, detail="Failed to update chatbot")

    # Delete the file from storage
    await delete_files([file_url])

    return {"message": "File deleted successfully"}

