# backend/app/schemas/user.py

from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str

class User(UserBase):
    id: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"