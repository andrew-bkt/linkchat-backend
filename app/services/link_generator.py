# backend/app/services/link_generator.py

import secrets

def generate_unique_token() -> str:
    return secrets.token_urlsafe(16)