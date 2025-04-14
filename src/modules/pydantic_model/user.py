from pydantic import BaseModel, validator, EmailStr
from datetime import date, datetime
from typing import Union, Optional, Dict

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirmPassword: str
    role_id: int
    department_id: int
    location_id: int
    first_name: str
    last_name: str
    phone_number: str  
    dob: Union[date, datetime, str]
    gender: str
    license_number: Optional[str] = None  
    specialty: Optional[str] = None
    qualifications: Optional[Dict] = None 
    availability: Optional[Dict] = None

    @validator("dob", pre=True)
    def parse_dob(cls, value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except Exception:
                raise ValueError("Invalid date format for dob. Use YYYY-MM-DD.")
        return value

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role_id: int
    tenant_id: int

    class Config:
        orm_mode = True  