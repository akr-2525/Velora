from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    interests: str  # e.g., "technology, finance, ai"

class UserResponse(UserCreate):
    id: int

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    interests: str