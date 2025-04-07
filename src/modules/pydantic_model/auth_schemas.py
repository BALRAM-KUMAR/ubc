from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional

# --------------------------
# Common Base Models
# --------------------------
class BaseResponse(BaseModel):
    message: str
    status_code: int

# --------------------------
# User Models
# --------------------------
class UserBase(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

class UserCreate(UserBase):
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    tenant_id: int
    role_id: int
    email: EmailStr
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --------------------------
# Subscription Models
# --------------------------
class SubscriptionPlan(BaseModel):
    plan: str = Field(..., description="Subscription plan type: basic, pro, enterprise")
    payment_method: str = Field(..., description="Payment method: stripe, paypal")

class SubscriptionResponse(BaseModel):
    id: int
    tenant_id: int
    plan: str
    payment_status: str
    next_billing_date: Optional[datetime]

    class Config:
        from_attributes = True

# --------------------------
# Token Models
# --------------------------
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None