# backend/app/api/deps.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError
from app.core.config import settings
from app.schemas.user import User

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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

        print(f"Received token: {token}")  # For debugging
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.ALGORITHM],
            audience=expected_audience,
            issuer=expected_issuer,
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            print("Invalid token payload")
            raise credentials_exception
    except ExpiredSignatureError:
        print("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTClaimsError as e:
        print(f"JWT claims error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid claims: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print(f"JWT error: {e}")
        raise credentials_exception
    return User(id=user_id, email=email)