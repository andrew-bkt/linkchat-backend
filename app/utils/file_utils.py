# backend/app/utils/file_utils.py

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
            file_size = len(content)  # get file size
            logging.info(f"File {file.filename} size: {file_size} bytes")
            
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

async def delete_files(file_urls: List[str]):
    supabase = get_supabase()
    logging.info(f"Attempting to delete {len(file_urls)} files")
    for url in file_urls:
        try:
            # Extract the file path from the public URL
            file_path = url.split("chatbot-documents/")[-1]
            logging.info(f"Deleting file: {file_path}")
            
            // Delete the file from Supabase storage
            response = supabase.storage.from_("chatbot-documents").remove(file_path)
            
            if response:
                logging.info(f"Successfully deleted file: {file_path}")
            else:
                logging.warning(f"File not found or already deleted: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting file {url}: {str(e)}")
            logging.exception("Exception details:")
    logging.info("Finished deleting files")

