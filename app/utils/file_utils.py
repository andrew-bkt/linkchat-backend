import logging
from typing import List
from fastapi import UploadFile
from app.db.session import get_supabase

async def save_uploaded_files(files: List[UploadFile], chatbot_id: str) -> List[str]:
    supabase = get_supabase()
    file_urls = []
    logging.info(f"Attempting to save {len(files)} files for chatbot {chatbot_id}")
    for file in files:
        try:
            content = await file.read()
            file_path = f"{chatbot_id}/{file.filename}"
            logging.info(f"Uploading file: {file_path}")
            response = supabase.storage.from_("chatbot-documents").upload(file_path, content)
            
            logging.info(f"Upload response: {response}")
            
            # Check if the upload was successful
            if response:
                public_url = supabase.storage.from_("chatbot-documents").get_public_url(file_path)
                logging.info(f"File uploaded successfully. Public URL: {public_url}")
                file_urls.append(public_url)
            else:
                logging.error(f"Error uploading file {file_path}: Unexpected response format")
        except Exception as e:
            logging.error(f"Unexpected error while uploading file {file.filename}: {str(e)}")
            logging.exception("Exception details:")
    logging.info(f"Finished uploading files. Total successful uploads: {len(file_urls)}")
    return file_urls
