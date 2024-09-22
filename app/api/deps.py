# backend/app/api/deps.py

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError
from app.core.config import settings
from app.schemas.user import User
from typing import Optional

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Define the expected audience and issuer
        expected_audience = "authenticated"
        expected_issuer = f"{settings.SUPABASE_URL}/auth/v1"

        # Log only the first 10 characters of the token for security
        logger.debug(f"Received token: {token[:10]}...")  
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            audience=expected_audience,
            issuer=expected_issuer,
        )
        user_id: Optional[str] = payload.get("sub")
        email: Optional[str] = payload.get("email")
        if user_id is None or email is None:
            logger.warning("Invalid token payload")
            raise credentials_exception
    except ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTClaimsError as e:
        logger.error(f"JWT claims error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid claims: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        raise credentials_exception
    
    logger.info(f"User authenticated: {user_id}")
    return User(id=user_id, email=email)
