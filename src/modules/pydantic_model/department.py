from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    required_roles: Optional[Dict[str, Any]] = None

class DepartmentResponse(DepartmentCreate):
    id: int
    clinic_id: int
    location_id: int
    # created_at: datetime