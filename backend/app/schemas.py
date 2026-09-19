from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    role: str = "seller"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class MusicianBase(BaseModel):
    name: str
    genre: str

class MusicianCreate(MusicianBase):
    pass

class MusicianResponse(MusicianBase):
    id: int
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True

class DiscBase(BaseModel):
    title: str
    musician_id: int
    price: float = Field(gt=0, description="Price must be greater than 0")
    stock: int = Field(ge=0, description="Stock must be non-negative")

class DiscCreate(DiscBase):
    pass

class DiscResponse(DiscBase):
    id: int
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True

class SaleBase(BaseModel):
    disc_id: int
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")

class SaleCreate(SaleBase):
    pass

class SaleResponse(SaleBase):
    id: int
    total_price: float
    sold_at: datetime
    seller_id: Optional[int] = None
    
    class Config:
        from_attributes = True