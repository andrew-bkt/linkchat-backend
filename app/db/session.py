# backend/app/db/session.py

from supabase import create_client, Client
from app.core.config import settings
import logging

def get_supabase() -> Client:
    supabase_url = settings.SUPABASE_URL
    supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY
    logging.info(f"Creating Supabase client with URL: {supabase_url}")
    supabase = create_client(supabase_url, supabase_key)
    return supabase
