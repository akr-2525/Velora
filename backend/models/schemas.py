from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    name: str
    email: EmailStr
    interests: str

class UserCreate(UserBase):
    password: str # <--- Require a password for registration

class UserResponse(UserBase):
    id: int
    # Notice we DO NOT put the password in the response. It stays hidden!
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    interests: str