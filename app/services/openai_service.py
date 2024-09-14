# backend/app/services/openai_service.py

from openai import OpenAI
from app.core.config import settings
import logging
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
import requests
import tempfile
import os

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def get_chatbot_response(chatbot: dict, user_message: str) -> str:
    try:
        logging.info(f"Chatbot object received in get_chatbot_response: {chatbot}")
        
        system_message = f"You are a chatbot named {chatbot['name']}. "
        document_content = ""

        if chatbot.get('documents'):
            for doc_url in chatbot['documents']:
                # Download the PDF file
                response = requests.get(doc_url)
                if response.status_code == 200:
                    # Create a temporary file to store the PDF
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                        temp_file.write(response.content)
                        temp_file_path = temp_file.name

                    # Load the PDF
                    loader = PyPDFLoader(temp_file_path)
                    pages = loader.load()

                    # Extract text from pages
                    for page in pages:
                        document_content += page.page_content + "\n\n"

                    # Remove the temporary file
                    os.unlink(temp_file_path)
                else:
                    logging.error(f"Failed to download document: {doc_url}")

            # Add document content to system message
            system_message += f"Respond as if you are an expert of the documents contents. Do not quote the documents as if the ideas are not your own. Speak as though the contents of the document are fact and your own views. Here are the content of the documents: {document_content}"

        logging.info(f"System message for OpenAI: {system_message}")
        
        response = client.chat.completions.create(
            model="gpt-4o",  # or "gpt-3.5-turbo" if you prefer
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,  # Increased max_tokens to allow for longer responses
            n=1,
            temperature=0.7,
        )
        bot_reply = response.choices[0].message.content.strip()
        return bot_reply
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "Sorry, I couldn't process your request due to an API error."
