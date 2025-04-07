from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from core.config import Settings
settings = Settings()
# --------------------------
# Tenant Models
# --------------------------
class TenantCreate(BaseModel):
    name: str = Field(..., description="Tenant name")
    subdomain: str = Field(..., pattern=r"^[a-z0-9-]+$", description="Unique subdomain")
    email: EmailStr = Field(..., description="Admin email")
    plan: str = Field(..., description="Subscription plan: basic, pro, enterprise")
    custom_domain: Optional[str] = Field(None, description="Custom domain (optional)")

class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    custom_domain: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --------------------------
# Subscription Models
# --------------------------
class SubscriptionCreate(BaseModel):
    plan_id: int

class SubscriptionResponse(BaseModel):
    id: int
    tenant_id: int
    plan_id: int
    payment_status: str
    subscription_id: str
    amount : int
    next_billing_date: Optional[datetime]

    class Config:
        from_attributes = True

# --------------------------
# User Models
# --------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="admin", description="Default role: admin")

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True