from pydantic import BaseModel, EmailStr
from typing import List, Optional


class UserBase(BaseModel):
    name: str
    email: EmailStr
    department: Optional[str] = "General"


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int

    model_config = {
        "from_attributes": True
    }


class UserList(BaseModel):
    count: int
    users: List[User]
