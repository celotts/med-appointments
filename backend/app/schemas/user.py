import uuid
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None


class UserCreate(UserBase):
    email: EmailStr
    password: str
    full_name: str
    role_id: uuid.UUID


class UserUpdate(UserBase):
    password: str | None = None


class UserInDBBase(UserBase):
    id: uuid.UUID
    email: EmailStr
    full_name: str

    class Config:
        from_attributes = True


class User(UserInDBBase):
    pass
