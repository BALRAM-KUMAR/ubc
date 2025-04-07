# app/clinic.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ClinicCreate(BaseModel):
    name: str
    description: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None

class ClinicResponse(ClinicCreate):
    id: int
    created_at: datetime